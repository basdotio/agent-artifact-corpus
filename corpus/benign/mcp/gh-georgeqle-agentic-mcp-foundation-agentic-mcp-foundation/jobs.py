"""SQLite-backed receipts and bounded, cooperatively cancellable execution."""

import hashlib
import json
import queue
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from . import LifecycleError

TERMINAL = ("succeeded", "failed", "cancelled", "interrupted")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class JobStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS jobs ("
                "id TEXT PRIMARY KEY, key TEXT UNIQUE NOT NULL, operation TEXT NOT NULL, "
                "fingerprint TEXT NOT NULL, request TEXT NOT NULL, state TEXT NOT NULL, "
                "phase TEXT NOT NULL, result TEXT, error TEXT, cancel INTEGER NOT NULL DEFAULT 0, "
                "created REAL NOT NULL, updated REAL NOT NULL)"
            )
        path.chmod(0o600)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            raise LifecycleError("JOB_NOT_FOUND", "No job with that ID")
        result = dict(row)
        for key in ("request", "result", "error"):
            result[key] = json.loads(result[key]) if result[key] is not None else None
        result["idempotency_key"] = result.pop("key")
        result.pop("fingerprint")
        result["cancel_requested"] = bool(result.pop("cancel"))
        return result

    def get(self, job_id):
        with self.connection() as db:
            return self.decode(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def find(self, key, operation, request):
        fingerprint = hashlib.sha256(canonical([operation, request]).encode()).hexdigest()
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE key=?", (key,)).fetchone()
        if row is not None and row["fingerprint"] != fingerprint:
            raise LifecycleError(
                "IDEMPOTENCY_CONFLICT", "Key was already used for different intent"
            )
        return self.decode(row) if row is not None else None

    def create(self, key, operation, request):
        if not isinstance(key, str) or not key.strip() or len(key) > 200:
            raise LifecycleError("INVALID_KEY", "Supply an idempotency key of 1–200 characters")
        fingerprint = hashlib.sha256(canonical([operation, request]).encode()).hexdigest()
        with self.connection() as db:
            db.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,'queued','queued',NULL,NULL,0,?,?)",
                (
                    uuid.uuid4().hex,
                    key,
                    operation,
                    fingerprint,
                    canonical(request),
                    time.time(),
                    time.time(),
                ),
            )
        return self.find(key, operation, request)

    def change(self, job_id, state=None, phase=None, result=None, error=None):
        values = {"updated": time.time()}
        if state is not None:
            values["state"] = state
        if phase is not None:
            values["phase"] = phase[:500]
        if result is not None:
            values["result"] = canonical(result)
        if error is not None:
            values["error"] = canonical(error)
        with self.connection() as db:
            db.execute(
                "UPDATE jobs SET " + ",".join(f"{key}=?" for key in values) + " WHERE id=?",
                (*values.values(), job_id),
            )
        return self.get(job_id)

    def cancel(self, job_id):
        with self.connection() as db:
            db.execute(
                "UPDATE jobs SET cancel=1, updated=?, "
                "state=CASE WHEN state='queued' THEN 'cancelled' ELSE state END "
                "WHERE id=? AND state NOT IN ('succeeded','failed','cancelled','interrupted')",
                (time.time(), job_id),
            )
        return self.get(job_id)

    def recover(self):
        """Call only while holding exclusive coordinator ownership. Never replay mutations."""
        with self.connection() as db:
            db.execute(
                "UPDATE jobs SET state='interrupted', phase='coordinator restarted', error=?, "
                "updated=? WHERE state IN ('queued','running')",
                (
                    canonical(
                        {
                            "code": "COORDINATOR_LOST",
                            "message": "Execution interrupted; "
                            "inspect state before submitting a new key",
                            "retryable": False,
                        }
                    ),
                    time.time(),
                ),
            )

    def recent(self, limit=20):
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM jobs ORDER BY created DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self.decode(row) for row in rows]


class JobContext:
    def __init__(self, store, job_id):
        self.store, self.id = store, job_id

    def check(self):
        if self.store.get(self.id)["cancel_requested"]:
            raise LifecycleError("CANCELLED", "Cancellation requested")

    def progress(self, phase):
        self.check()
        self.store.change(self.id, phase=phase)


class JobEngine:
    """Only adapter-registered operations execute. Cancellation retains occupied worker slots."""

    def __init__(self, store, operations, workers=1, capacity=16, exclusive=(), queue_timeout=120):
        self.store, self.operations = store, operations
        self.capacity, self.exclusive = capacity, set(exclusive)
        if not 1 <= workers <= 32 or not 1 <= capacity <= 4096 or queue_timeout <= 0:
            raise ValueError("Invalid worker, capacity or queue timeout bounds")
        self.queue_timeout = queue_timeout
        self.lock = threading.RLock()
        self.pending = queue.Queue()
        self.admitted = {}
        self.closed = False
        for index in range(workers):
            threading.Thread(target=self._work, name=f"agentic-job-{index}", daemon=True).start()

    def submit(self, operation, request, key):
        if operation not in self.operations:
            raise LifecycleError("UNKNOWN_OPERATION", "Operation is not registered")
        with self.lock:
            existing = self.store.find(key, operation, request)
            if existing:
                return existing
            if self.closed:
                raise LifecycleError("DRAINING", "Coordinator is draining", True)
            if any(op in self.exclusive for op in self.admitted.values()) or (
                operation in self.exclusive and self.admitted
            ):
                raise LifecycleError("BUSY", "Wait for active jobs before maintenance", True)
            if len(self.admitted) >= self.capacity:
                raise LifecycleError("QUEUE_FULL", "Job capacity reached; retry with backoff", True)
            job = self.store.create(key, operation, request)
            self.admitted[job["id"]] = operation
            self.pending.put(job)
            return job

    def _work(self):
        while True:
            job = self.pending.get()
            context = JobContext(self.store, job["id"])
            try:
                self.expire_queued()
                if self.store.get(context.id)["state"] in TERMINAL:
                    continue
                context.check()
                self.store.change(context.id, state="running", phase="running")
                result = self.operations[job["operation"]](job["request"], context)
                context.check()
                self.store.change(context.id, state="succeeded", phase="complete", result=result)
            except Exception as exc:  # noqa: BLE001 - persist adapter failures
                error = (
                    exc.report()
                    if isinstance(exc, LifecycleError)
                    else {
                        "code": "OPERATION_FAILED",
                        "message": str(exc)[:2000],
                        "retryable": False,
                    }
                )
                cancelled = error["code"] == "CANCELLED"
                self.store.change(
                    context.id, state="cancelled" if cancelled else "failed", error=error
                )
            finally:
                with self.lock:
                    self.admitted.pop(job["id"], None)
                self.pending.task_done()

    def expire_queued(self):
        with self.lock:
            for job_id in self.admitted:
                job = self.store.get(job_id)
                if job["state"] == "queued" and time.time() - job["created"] >= self.queue_timeout:
                    self.store.change(
                        job_id,
                        state="failed",
                        phase="queue deadline expired",
                        error={
                            "code": "QUEUE_TIMEOUT",
                            "message": "Job expired before execution",
                            "retryable": True,
                        },
                    )

    def get(self, job_id):
        self.expire_queued()
        return self.store.get(job_id)

    def cancel(self, job_id):
        return self.store.cancel(job_id)

    def drain(self):
        with self.lock:
            if self.admitted:
                raise LifecycleError("BUSY", "Jobs are still active; retry after completion", True)
            self.closed = True
