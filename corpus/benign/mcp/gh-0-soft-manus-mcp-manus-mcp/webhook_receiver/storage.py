"""SQLite-backed storage for received webhook events, shared with the MCP server."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    task_id TEXT,
    received_at INTEGER NOT NULL,
    body_json TEXT NOT NULL,
    headers_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_received ON events(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
"""


@dataclass(frozen=True)
class StoredEvent:
    event_id: str
    event_type: str
    task_id: str | None
    received_at: int
    body: dict[str, Any]
    headers: dict[str, str]


class EventStore:
    """Thread-safe SQLite store. Suitable for a single-process writer + many readers."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connect().executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, isolation_level=None, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def insert(
        self,
        *,
        event_id: str,
        event_type: str,
        task_id: str | None,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> bool:
        """Insert event. Returns False if event_id already exists (idempotent)."""
        payload = (
            event_id,
            event_type,
            task_id,
            int(time.time()),
            json.dumps(body, ensure_ascii=False),
            json.dumps(headers, ensure_ascii=False),
        )
        with self._lock:
            try:
                self._connect().execute(
                    "INSERT INTO events(event_id, event_type, task_id, received_at, body_json, headers_json)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    payload,
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def get(self, event_id: str) -> StoredEvent | None:
        row = (
            self._connect()
            .execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            .fetchone()
        )
        return _row_to_event(row) if row else None

    def list(
        self,
        *,
        event_type: str | None = None,
        task_id: str | None = None,
        since_received_at: int | None = None,
        limit: int = 50,
        order: str = "desc",
    ) -> list[StoredEvent]:
        limit = max(1, min(limit, 500))
        clauses: list[str] = []
        args: list[Any] = []
        if event_type:
            clauses.append("event_type = ?")
            args.append(event_type)
        if task_id:
            clauses.append("task_id = ?")
            args.append(task_id)
        if since_received_at is not None:
            clauses.append("received_at > ?")
            args.append(since_received_at)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        direction = "DESC" if order.lower() == "desc" else "ASC"
        sql = f"SELECT * FROM events {where} ORDER BY received_at {direction} LIMIT ?"
        args.append(limit)
        rows = self._connect().execute(sql, args).fetchall()
        return [_row_to_event(r) for r in rows]

    def clear(
        self,
        *,
        before_received_at: int | None = None,
        event_type: str | None = None,
        task_id: str | None = None,
    ) -> int:
        clauses: list[str] = []
        args: list[Any] = []
        if before_received_at is not None:
            clauses.append("received_at < ?")
            args.append(before_received_at)
        if event_type:
            clauses.append("event_type = ?")
            args.append(event_type)
        if task_id:
            clauses.append("task_id = ?")
            args.append(task_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._lock:
            cur = self._connect().execute(f"DELETE FROM events {where}", args)
            return cur.rowcount or 0


def _row_to_event(row: sqlite3.Row) -> StoredEvent:
    return StoredEvent(
        event_id=row["event_id"],
        event_type=row["event_type"],
        task_id=row["task_id"],
        received_at=row["received_at"],
        body=json.loads(row["body_json"]),
        headers=json.loads(row["headers_json"]),
    )
