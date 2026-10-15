"""Durable SQLite queue for read-only Agent tasks on one host.

Claims use an atomic transaction and a unique fencing token per attempt. Expired
claims can run again: this is at-least-once execution, not arbitrary-effect
exactly-once delivery. Only the current unexpired lease can commit a result.
SQLite WAL is intended for local disk, not a shared/network filesystem.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import threading
import time
import uuid


class LostLease(RuntimeError):
    """Another claim, lease expiration or cancellation invalidated this attempt."""


@dataclass(frozen=True)
class Job:
    id: str
    task: str
    payload: dict
    status: str
    attempts: int
    max_attempts: int
    worker: str | None
    lease_token: str | None
    lease_until: float | None
    cancel_requested: bool
    result: object
    error: str | None


def _decode(row):
    if row is None:
        return None
    return Job(row["id"], row["task"], json.loads(row["payload"]), row["status"],
               row["attempts"], row["max_attempts"], row["worker"], row["lease_token"],
               row["lease_until"], bool(row["cancel_requested"]),
               json.loads(row["result"]) if row["result"] is not None else None, row["error"])


def _duration(seconds):
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("lease_seconds must be finite and positive")
    return seconds


class JobQueue:
    def __init__(self, database):
        self.path = Path(database).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = self._connect()
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE, fingerprint TEXT NOT NULL,
                    task TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL,
                    worker TEXT, lease_token TEXT, lease_until REAL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0, result TEXT, error TEXT,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS jobs_claim ON jobs(status,created_at,id);
            """)
        finally:
            db.close()

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        return db

    @contextmanager
    def _transaction(self):
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def enqueue(self, task, payload=None, *, idempotency_key=None, max_attempts=3):
        if not isinstance(task, str) or not task.strip() or len(task) > 16000:
            raise ValueError("task must be a nonempty bounded string")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be 1..20")
        if idempotency_key is not None and (not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 200):
            raise ValueError("idempotency_key must be a bounded string")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if len(encoded) > 100000:
            raise ValueError("payload too large")
        fingerprint = hashlib.sha256(json.dumps([task, encoded, max_attempts], ensure_ascii=False).encode()).hexdigest()
        now, identity = time.time(), uuid.uuid4().hex
        with self._transaction() as db:
            if idempotency_key is not None:
                existing = db.execute("SELECT * FROM jobs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
                if existing is not None:
                    if existing["fingerprint"] != fingerprint:
                        raise ValueError("idempotency key reused with different task/payload/policy")
                    return _decode(existing)
            db.execute("INSERT INTO jobs(id,idempotency_key,fingerprint,task,payload,status,max_attempts,created_at,updated_at) VALUES (?,?,?,?,?,'queued',?,?,?)",
                       (identity, idempotency_key, fingerprint, task, encoded, max_attempts, now, now))
            return _decode(db.execute("SELECT * FROM jobs WHERE id=?", (identity,)).fetchone())

    def get(self, identity):
        db = self._connect()
        try:
            return _decode(db.execute("SELECT * FROM jobs WHERE id=?", (identity,)).fetchone())
        finally:
            db.close()

    def claim(self, worker, *, lease_seconds=30):
        _duration(lease_seconds)
        if not isinstance(worker, str) or not 1 <= len(worker) <= 200:
            raise ValueError("worker must be a bounded string")
        with self._transaction() as db:
            now = time.time()
            # Reclaim with the same transaction as selection. Every new attempt
            # gets a new token, so late results from the old worker cannot commit.
            db.execute("""UPDATE jobs SET status=CASE WHEN cancel_requested=1 THEN 'cancelled'
                       WHEN attempts>=max_attempts THEN 'failed' ELSE 'queued' END,
                       worker=NULL,lease_token=NULL,lease_until=NULL,error='worker lease expired',updated_at=?
                       WHERE status='running' AND lease_until<=?""", (now, now))
            row = db.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
            if row is None:
                return None
            db.execute("UPDATE jobs SET status='running',attempts=attempts+1,worker=?,lease_token=?,lease_until=?,updated_at=? WHERE id=?",
                       (worker, uuid.uuid4().hex, now + lease_seconds, now, row["id"]))
            return _decode(db.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())

    def _owned(self, db, job, now):
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job.id,)).fetchone()
        if row is None or row["status"] != "running" or row["lease_token"] != job.lease_token or row["worker"] != job.worker or row["lease_until"] <= now:
            raise LostLease("job lease is stale or expired")
        return row

    def heartbeat(self, job, *, lease_seconds=30):
        _duration(lease_seconds)
        with self._transaction() as db:
            now = time.time()
            row = self._owned(db, job, now)
            if row["cancel_requested"]:
                return False
            db.execute("UPDATE jobs SET lease_until=?,updated_at=? WHERE id=?", (now + lease_seconds, now, job.id))
            return True

    def complete(self, job, result):
        encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)
        if len(encoded) > 2000000:
            raise ValueError("result too large")
        with self._transaction() as db:
            now = time.time()
            row = self._owned(db, job, now)
            status = "cancelled" if row["cancel_requested"] else "completed"
            db.execute("UPDATE jobs SET status=?,result=?,error=NULL,worker=NULL,lease_token=NULL,lease_until=NULL,updated_at=? WHERE id=?",
                       (status, encoded if status == "completed" else None, now, job.id))
            return _decode(db.execute("SELECT * FROM jobs WHERE id=?", (job.id,)).fetchone())

    def fail(self, job, error, *, retry=True):
        with self._transaction() as db:
            now = time.time()
            row = self._owned(db, job, now)
            status = "cancelled" if row["cancel_requested"] else ("queued" if retry and row["attempts"] < row["max_attempts"] else "failed")
            db.execute("UPDATE jobs SET status=?,error=?,worker=NULL,lease_token=NULL,lease_until=NULL,updated_at=? WHERE id=?",
                       (status, str(error)[:4000], now, job.id))
            return _decode(db.execute("SELECT * FROM jobs WHERE id=?", (job.id,)).fetchone())

    def cancel(self, identity):
        with self._transaction() as db:
            db.execute("UPDATE jobs SET cancel_requested=1,status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END,updated_at=? WHERE id=? AND status IN ('queued','running')",
                       (time.time(), identity))
            return _decode(db.execute("SELECT * FROM jobs WHERE id=?", (identity,)).fetchone())


class Worker:
    """Callback receives ``(job, is_cancelled)``; cooperate at safe boundaries.

    A heartbeat thread renews the lease during a blocking model call. Cancellation
    cannot forcibly interrupt that call; it discards the result and prevents new
    work when the callback checks is_cancelled. Stale completions are fenced.
    """
    def __init__(self, queue, handler, *, worker_id=None, lease_seconds=30):
        self.queue, self.handler = queue, handler
        self.worker_id = worker_id or uuid.uuid4().hex
        self.lease_seconds = _duration(lease_seconds)

    def run_once(self):
        job = self.queue.claim(self.worker_id, lease_seconds=self.lease_seconds)
        if job is None:
            return None
        done, lost = threading.Event(), threading.Event()

        def renew():
            while not done.wait(self.lease_seconds / 3):
                try:
                    if not self.queue.heartbeat(job, lease_seconds=self.lease_seconds):
                        return
                except (LostLease, sqlite3.Error):
                    lost.set()
                    return

        def cancelled():
            current = self.queue.get(job.id)
            if (lost.is_set() or current is None or current.status != "running"
                    or current.lease_token != job.lease_token or current.worker != job.worker
                    or current.lease_until is None or current.lease_until <= time.time()):
                # Ownership loss is an interruption, not a user cancellation.
                # Runtime propagates this error with its running journal intact,
                # so a new lease can resume the durable pending decision.
                raise LostLease("job ownership was lost")
            return current.cancel_requested

        heartbeat = threading.Thread(target=renew, daemon=True)
        heartbeat.start()
        try:
            result = self.handler(job, cancelled)
            self.queue.complete(job, result)
        except LostLease:
            pass
        except Exception as exc:
            try:
                self.queue.fail(job, f"{type(exc).__name__}: {exc}")
            except LostLease:
                pass
        finally:
            done.set()
            heartbeat.join()
        return self.queue.get(job.id)

    def run_forever(self, *, stop=None, poll_seconds=.25):
        stop = stop or threading.Event()
        if poll_seconds <= 0:
            raise ValueError("poll_seconds must be positive")
        while not stop.is_set():
            if self.run_once() is None:
                stop.wait(poll_seconds)
