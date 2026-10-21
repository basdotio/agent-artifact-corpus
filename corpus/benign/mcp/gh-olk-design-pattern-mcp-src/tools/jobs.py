"""Async SQLite job store for the submit_design_job / get_design_status / cancel_design trio.

Mirrors the sibling reference implementation (`architecture-pattern-mcp/src/tools/jobs.py`)
semantics: a singleton store sharing one aiosqlite connection, with transition setters
guarded by ``UPDATE ... WHERE id = ? AND status IN (...)`` so that terminal-state
immutability and cancel-only-from-pending/running hold atomically inside SQLite.

The DB path is re-evaluated on every call (house invariant 10): env
``DESIGN_PATTERN_JOBS_DB`` wins, then the module-level override set by
:meth:`JobsStore.configure` (the server sets it from ``ServerConfig.jobs.db_path``),
then the user-level default ``~/.config/design-pattern-mcp/jobs.db``.
"""

import aiosqlite
import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from src.errors import JobStateError

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "~/.config/design-pattern-mcp/jobs.db"


def _get_db_path() -> str:
    """Return the effective DB path, re-evaluated on every call for test isolation.

    Precedence: env ``DESIGN_PATTERN_JOBS_DB``, then the module-level override set by
    :meth:`JobsStore.configure`, then the user-level default.
    """
    return os.environ.get(
        "DESIGN_PATTERN_JOBS_DB",
        os.path.expanduser(JobsStore._configured_db_path or _DEFAULT_DB_PATH),
    )


class JobStatus:
    """Job lifecycle status values (jobs.status column)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobsStore:
    """Singleton async SQLite store for design-pattern selection job state.

    Transition setters are guarded (``WHERE ... AND status IN (...)``) — the guard is
    atomic inside SQLite, so terminal states are immutable and cancel is effective
    only from pending/running. A rejected transition (rowcount 0) raises
    :class:`~src.errors.JobStateError`.
    """

    _instance: "JobsStore | None" = None
    _db: aiosqlite.Connection | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    # Module-level override set by configure(); consulted by _get_db_path when the
    # DESIGN_PATTERN_JOBS_DB env var is unset. Class attribute rather than a module
    # global so configure() needs no ``global`` statement.
    _configured_db_path: str | None = None

    def __new__(cls) -> "JobsStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._db = None
        return cls._instance

    @classmethod
    async def get_instance(cls, lock: asyncio.Lock | None = None) -> "JobsStore":
        """Get or create the singleton instance, initialising the DB on first call."""
        # Read _db off the instance: self._db assignments shadow the class
        # attribute, so cls._db is always None and must not be used here.
        if cls._instance is None or cls._instance._db is None:
            async with (lock if lock is not None else cls._lock):
                if cls._instance is None or cls._instance._db is None:
                    cls._instance = cls()
                    await cls._instance._init()
        return cls._instance

    @classmethod
    def configure(cls, db_path: str) -> None:
        """Set the module-level DB-path override (the server wires ServerConfig.jobs.db_path).

        Takes effect only when the ``DESIGN_PATTERN_JOBS_DB`` env var is unset;
        call before :meth:`get_instance` (or after :meth:`reset_for_test`).
        """
        cls._configured_db_path = db_path

    @classmethod
    async def reset_for_test(cls) -> None:
        """Test helper: close the current connection, delete the DB file, drop the singleton.

        Use together with a temporarily overridden ``DESIGN_PATTERN_JOBS_DB`` env var
        to point the store at a per-test temporary directory.
        """
        # Close via the instance attribute (see get_instance): cls._db is a
        # shadowed class attribute that stays None. Awaiting close() also
        # joins the aiosqlite worker thread before the caller's event loop
        # closes — otherwise the worker races the loop shutdown and raises
        # "RuntimeError: Event loop is closed".
        instance = cls._instance
        if instance is not None:
            await instance.close()
            cls._instance = None
        cls._db = None
        db_path = _get_db_path()
        if os.path.exists(db_path):
            os.unlink(db_path)

    async def _init(self) -> None:
        db_path = _get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db = await aiosqlite.connect(db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS jobs ("
            "  id TEXT PRIMARY KEY,"
            "  status TEXT NOT NULL DEFAULT 'pending',"
            "  payload TEXT NOT NULL,"
            "  description TEXT NOT NULL DEFAULT '',"
            "  created_at TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL,"
            "  result TEXT,"
            "  error TEXT"
            ")"
        )
        await self._db.commit()
        logger.debug("JobsStore initialised", extra={"db_path": db_path})

    async def close(self) -> None:
        """Close the shared connection and drop the singleton."""
        if self._db is not None:
            await self._db.close()
            self._db = None
            JobsStore._instance = None

    def _conn(self) -> aiosqlite.Connection:
        """Initialised DB connection — get_instance() guarantees _db is set."""
        if self._db is None:
            raise RuntimeError("JobsStore not initialised — call JobsStore.get_instance() first")
        return self._db

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    async def create_job(self, payload: str, *, description: str = "") -> str:
        """Create a pending job carrying the serialized request payload; return its ID."""
        job_id = str(uuid.uuid4())
        now = self._now()
        await self._conn().execute(
            "INSERT INTO jobs (id, status, payload, description, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, JobStatus.PENDING, payload, description, now, now),
        )
        await self._conn().commit()
        logger.debug("Job created", extra={"job_id": job_id})
        return job_id

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Return the job row as a dict, or ``None`` for an unknown ID."""
        cursor = await self._conn().execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def _guarded_update(self, job_id: str, sql: str, params: tuple[Any, ...]) -> None:
        """Execute a guarded transition UPDATE and raise JobStateError on rejection.

        The ``AND status ...`` clause in ``sql`` is the guard — the check-and-set is
        atomic inside SQLite, so no caller-side check-then-act window exists. On
        rowcount 0 the current status is re-read for the error message.
        """
        cursor = await self._conn().execute(sql, params)
        await self._conn().commit()
        if cursor.rowcount == 0:
            job = await self.get_job(job_id)
            current_status: str | None = str(job["status"]) if job is not None else None
            raise JobStateError(job_id=job_id, current_status=current_status)

    async def set_running(self, job_id: str) -> None:
        """Transition pending -> running (guard: pending only)."""
        await self._guarded_update(
            job_id,
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ? AND status = ?",
            (JobStatus.RUNNING, self._now(), job_id, JobStatus.PENDING),
        )

    async def set_completed(self, job_id: str, result: str) -> None:
        """Transition running -> completed, storing the serialized result (guard: running only)."""
        await self._guarded_update(
            job_id,
            "UPDATE jobs SET status = ?, result = ?, updated_at = ? WHERE id = ? AND status = ?",
            (JobStatus.COMPLETED, result, self._now(), job_id, JobStatus.RUNNING),
        )

    async def set_failed(self, job_id: str, error: str) -> None:
        """Transition running -> failed, storing the serialized error (guard: running only)."""
        await self._guarded_update(
            job_id,
            "UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ? AND status = ?",
            (JobStatus.FAILED, error, self._now(), job_id, JobStatus.RUNNING),
        )

    async def set_cancelled(self, job_id: str) -> None:
        """Transition pending/running -> cancelled; cancel never leaves a terminal state."""
        await self._guarded_update(
            job_id,
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ? AND status IN (?, ?)",
            (JobStatus.CANCELLED, self._now(), job_id, JobStatus.PENDING, JobStatus.RUNNING),
        )

    async def is_cancelled(self, job_id: str) -> bool:
        """True when the job exists and its status is cancelled."""
        cursor = await self._conn().execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        return row is not None and row["status"] == JobStatus.CANCELLED
