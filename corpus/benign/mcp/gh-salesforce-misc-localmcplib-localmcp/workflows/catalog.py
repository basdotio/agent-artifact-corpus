"""Generic SQLite catalog for durable, caller-owned operations."""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import aiosqlite

_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_UNSET = object()


class OperationCatalogError(RuntimeError):
    """Base error for durable operation catalog access."""


class OperationNotFoundError(OperationCatalogError):
    """Raised for both missing and non-owned operations."""


@dataclass(frozen=True)
class OperationRecord:
    id: str
    owner_uid: int
    label: str
    status: str
    request: dict[str, Any]
    state: dict[str, Any]
    preview: dict[str, Any] | None
    result: dict[str, Any] | None
    metadata: dict[str, Any]
    error: str | None
    cancel_requested: bool
    created_at: str
    updated_at: str
    lease_owner: str | None
    lease_expires: float | None
    tool_calls_used: int


class SQLiteOperationCatalog:
    """A flexible catalog intended for one database per workflow runtime."""

    def __init__(self, connection: aiosqlite.Connection, *, table: str = "operations"):
        if not _TABLE_NAME.fullmatch(table):
            raise OperationCatalogError("operation table name is invalid")
        self.connection = connection
        self.table = table
        self._tool_call_lock = asyncio.Lock()

    @classmethod
    async def open(
        cls,
        path: Path,
        *,
        table: str = "operations",
        busy_timeout_ms: int = 5_000,
    ) -> SQLiteOperationCatalog:
        if busy_timeout_ms < 0:
            raise OperationCatalogError("busy_timeout_ms must be non-negative")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = await aiosqlite.connect(path)
        connection.row_factory = aiosqlite.Row
        catalog = cls(connection, table=table)
        await catalog.setup(busy_timeout_ms=busy_timeout_ms)
        return catalog

    async def setup(self, *, busy_timeout_ms: int = 5_000) -> None:
        await self.connection.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
        await self.connection.execute("PRAGMA journal_mode=WAL")
        await self.connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table} (
              id TEXT PRIMARY KEY,
              owner_uid INTEGER NOT NULL,
              label TEXT NOT NULL,
              status TEXT NOT NULL,
              request_json TEXT NOT NULL,
              state_json TEXT NOT NULL DEFAULT '{{}}',
              preview_json TEXT,
              result_json TEXT,
              metadata_json TEXT NOT NULL DEFAULT '{{}}',
              error TEXT,
              cancel_requested INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              lease_owner TEXT,
              lease_expires REAL,
              tool_calls_used INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await self.connection.execute(
            f"CREATE INDEX IF NOT EXISTS {self.table}_status_created ON {self.table}(status, created_at)"
        )
        await self.connection.commit()

    async def close(self) -> None:
        await self.connection.close()

    async def create(
        self,
        *,
        operation_id: str,
        owner_uid: int,
        label: str,
        status: str,
        request: Mapping[str, Any],
        state: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> OperationRecord:
        now = _now()
        await self.connection.execute(
            f"""
            INSERT INTO {self.table}
              (id, owner_uid, label, status, request_json, state_json, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                operation_id,
                owner_uid,
                label,
                status,
                _json(request),
                _json(state or {}),
                _json(metadata or {}),
                now,
                now,
            ),
        )
        await self.connection.commit()
        record = await self.get(operation_id)
        assert record is not None
        return record

    async def get(self, operation_id: str) -> OperationRecord | None:
        async with self.connection.execute(
            f"SELECT * FROM {self.table} WHERE id = ?",
            (operation_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return _record(row) if row is not None else None

    async def require_owned(self, operation_id: str, owner_uid: int) -> OperationRecord:
        record = await self.get(operation_id)
        if record is None or record.owner_uid != owner_uid:
            raise OperationNotFoundError("operation was not found for the authenticated local caller")
        return record

    async def update(
        self,
        operation_id: str,
        *,
        status: str | None = None,
        state: Mapping[str, Any] | None = None,
        preview: Mapping[str, Any] | None | object = _UNSET,
        result: Mapping[str, Any] | None | object = _UNSET,
        metadata: Mapping[str, Any] | None = None,
        error: str | None | object = _UNSET,
    ) -> None:
        assignments = ["updated_at = ?"]
        values: list[Any] = [_now()]
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if state is not None:
            assignments.append("state_json = ?")
            values.append(_json(state))
        for column, value in (("preview_json", preview), ("result_json", result)):
            if value is not _UNSET:
                assignments.append(f"{column} = ?")
                values.append(None if value is None else _json(cast(Mapping[str, Any], value)))
        if metadata is not None:
            assignments.append("metadata_json = ?")
            values.append(_json(metadata))
        if error is not _UNSET:
            assignments.append("error = ?")
            values.append(error)
        values.append(operation_id)
        await self.connection.execute(
            f"UPDATE {self.table} SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        await self.connection.commit()

    async def request_cancel(self, operation_id: str, *, status: str | None = None) -> None:
        status_sql = ", status = ?" if status is not None else ""
        values: list[Any] = [_now()]
        if status is not None:
            values.append(status)
        values.append(operation_id)
        await self.connection.execute(
            f"UPDATE {self.table} SET cancel_requested = 1, updated_at = ?{status_sql} WHERE id = ?",
            values,
        )
        await self.connection.commit()

    async def is_cancel_requested(self, operation_id: str) -> bool:
        async with self.connection.execute(
            f"SELECT cancel_requested FROM {self.table} WHERE id = ?",
            (operation_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return bool(row and row[0])

    async def claim_tool_call(self, operation_id: str, limit: int) -> int | None:
        if limit <= 0:
            raise OperationCatalogError("tool-call limit must be positive")
        async with self._tool_call_lock:
            async with self.connection.execute(
                f"""
                UPDATE {self.table}
                SET tool_calls_used = tool_calls_used + 1, updated_at = ?
                WHERE id = ? AND tool_calls_used < ?
                """,
                (_now(), operation_id, limit),
            ) as cursor:
                claimed = cursor.rowcount == 1
            if not claimed:
                await self.connection.commit()
                return None
            async with self.connection.execute(
                f"SELECT tool_calls_used FROM {self.table} WHERE id = ?",
                (operation_id,),
            ) as cursor:
                row = await cursor.fetchone()
            await self.connection.commit()
            assert row is not None
            return limit - int(row[0])

    async def claim(self, operation_id: str, worker_id: str, *, lease_seconds: float = 90.0) -> bool:
        _validate_lease(lease_seconds)
        now = time.time()
        async with self.connection.execute(
            f"""
            UPDATE {self.table} SET lease_owner = ?, lease_expires = ?, updated_at = ?
            WHERE id = ? AND (lease_owner IS NULL OR lease_expires < ? OR lease_owner = ?)
            """,
            (worker_id, now + lease_seconds, _now(), operation_id, now, worker_id),
        ) as cursor:
            claimed = cursor.rowcount == 1
        await self.connection.commit()
        return claimed

    async def renew(self, operation_id: str, worker_id: str, *, lease_seconds: float = 90.0) -> bool:
        _validate_lease(lease_seconds)
        async with self.connection.execute(
            f"""
            UPDATE {self.table} SET lease_expires = ?, updated_at = ?
            WHERE id = ? AND lease_owner = ?
            """,
            (time.time() + lease_seconds, _now(), operation_id, worker_id),
        ) as cursor:
            renewed = cursor.rowcount == 1
        await self.connection.commit()
        return renewed

    async def release(self, operation_id: str, worker_id: str) -> None:
        await self.connection.execute(
            f"""
            UPDATE {self.table} SET lease_owner = NULL, lease_expires = NULL
            WHERE id = ? AND lease_owner = ?
            """,
            (operation_id, worker_id),
        )
        await self.connection.commit()

    async def recoverable(self, terminal_statuses: Collection[str]) -> list[OperationRecord]:
        terminal = sorted(terminal_statuses)
        if not terminal:
            query = f"SELECT * FROM {self.table} ORDER BY created_at"
            parameters: list[str] = []
        else:
            placeholders = ",".join("?" for _ in terminal)
            query = f"SELECT * FROM {self.table} WHERE status NOT IN ({placeholders}) ORDER BY created_at"
            parameters = terminal
        async with self.connection.execute(query, parameters) as cursor:
            rows = await cursor.fetchall()
        return [_record(row) for row in rows]


def _validate_lease(lease_seconds: float) -> None:
    if lease_seconds <= 0:
        raise OperationCatalogError("lease_seconds must be positive")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _record(row: aiosqlite.Row) -> OperationRecord:
    return OperationRecord(
        id=row["id"],
        owner_uid=int(row["owner_uid"]),
        label=row["label"],
        status=row["status"],
        request=json.loads(row["request_json"]),
        state=json.loads(row["state_json"]),
        preview=json.loads(row["preview_json"]) if row["preview_json"] else None,
        result=json.loads(row["result_json"]) if row["result_json"] else None,
        metadata=json.loads(row["metadata_json"]),
        error=row["error"],
        cancel_requested=bool(row["cancel_requested"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        lease_owner=row["lease_owner"],
        lease_expires=row["lease_expires"],
        tool_calls_used=int(row["tool_calls_used"]),
    )
