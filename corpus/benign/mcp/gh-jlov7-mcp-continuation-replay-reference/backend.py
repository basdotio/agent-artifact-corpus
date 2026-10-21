"""Harmless local issue-record backend.

Deliberately **not** idempotent: every `create_issue` call inserts a new row.
That is the whole point. If the backend deduplicated, a duplicate effect would
be invisible and the experiment would measure nothing.

No payments, no external services, no identity provider. SQLite only.
"""

from __future__ import annotations

import math
import sqlite3
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

__all__ = [
    "ApplyResult",
    "Compensation",
    "Issue",
    "IssueStore",
    "OperationAuthorityExpired",
    "OperationConflict",
    "OperationEvent",
    "OperationIdentity",
    "OperationInProgress",
    "OperationRecord",
    "OperationRetentionExpired",
    "Watcher",
    "WatcherInsertFailed",
]


@dataclass(frozen=True, slots=True)
class Issue:
    id: int
    title: str
    body: str


@dataclass(frozen=True, slots=True)
class Watcher:
    id: int
    issue_id: int
    name: str


@dataclass(frozen=True, slots=True)
class Compensation:
    id: int
    issue_id: int
    kind: str
    outcome: str


@dataclass(frozen=True, slots=True)
class OperationIdentity:
    """Identity used for dispatch and later reconciliation."""

    operation_id: str
    principal: str
    backend: str


@dataclass(frozen=True, slots=True)
class OperationRecord:
    identity: OperationIdentity
    request_fingerprint: str
    state: str
    effect_id: int | None
    result: str | None
    issued_at: float
    authority_expires_at: float | None
    replay_expires_at: float | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class OperationEvent:
    id: int
    operation_id: str
    step: str
    outcome: str
    error_type: str | None


@dataclass(frozen=True, slots=True)
class ApplyResult:
    effect_id: int
    result: str
    replayed: bool
    state: str = "applied"


class WatcherInsertFailed(RuntimeError):
    """The issue committed but the watcher row did not — a partial effect."""


class OperationConflict(RuntimeError):
    """An operation id was reused outside its original equivalence binding."""


class OperationInProgress(RuntimeError):
    """The operation exists but has no terminal result yet."""


class OperationAuthorityExpired(RuntimeError):
    """The operation's authority deadline passed before this write attempt."""


class OperationRetentionExpired(RuntimeError):
    """The replay deadline passed; the retained operation is a tombstone."""


class IssueStore:
    """Append-only issue records. Small on purpose — no ORM, no migrations."""

    def __init__(self, path: str = ":memory:", *, backend_id: str | None = None) -> None:
        if path != ":memory:" and not backend_id:
            raise ValueError("backend_id is required for a file-backed store")
        requested_backend = backend_id or f"sqlite:memory:{uuid4()}"
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        try:
            # Serialize first-use schema and binding before either process can write.
            self._conn.execute("BEGIN IMMEDIATE")
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS store_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._conn.execute(
                "INSERT OR IGNORE INTO store_metadata (key, value) VALUES ('backend_id', ?)",
                (requested_backend,),
            )
            row = self._conn.execute(
                "SELECT value FROM store_metadata WHERE key = 'backend_id'"
            ).fetchone()
            if row is None or row["value"] != requested_backend:
                raise ValueError(
                    f"database is bound to backend_id {row['value'] if row else None!r}, "
                    f"not {requested_backend!r}"
                )
            self.backend_id = requested_backend
            self._create_schema()
        except BaseException:
            self._conn.rollback()
            self._conn.close()
            raise

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body  TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT NOT NULL,
                step         TEXT NOT NULL,
                outcome      TEXT NOT NULL,
                error_type   TEXT,
                created_at   TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchers (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER NOT NULL REFERENCES issues(id),
                name     TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compensations (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER NOT NULL REFERENCES issues(id),
                kind     TEXT NOT NULL,
                outcome  TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                operation_id       TEXT NOT NULL,
                principal          TEXT NOT NULL,
                backend            TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                state              TEXT NOT NULL CHECK (state IN ('in_progress', 'applied', 'partial')),
                effect_id          INTEGER REFERENCES issues(id),
                result             TEXT,
                issued_at          REAL,
                authority_expires_at REAL,
                replay_expires_at  REAL,
                created_at         TEXT NOT NULL,
                updated_at         TEXT NOT NULL,
                PRIMARY KEY (operation_id, principal, backend)
            )
            """
        )
        columns = {
            str(row["name"])
            for row in self._conn.execute("PRAGMA table_info(operations)").fetchall()
        }
        for name, kind in (
            ("issued_at", "REAL"),
            ("authority_expires_at", "REAL"),
            ("replay_expires_at", "REAL"),
        ):
            if name not in columns:
                self._conn.execute(f"ALTER TABLE operations ADD COLUMN {name} {kind}")
        self._conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def apply_issue_once(
        self,
        identity: OperationIdentity,
        *,
        request_fingerprint: str,
        title: str,
        body: str,
        issued_at: float | None = None,
        authority_expires_at: float | None = None,
        replay_expires_at: float | None = None,
        now_epoch: float | None = None,
        fault_hook: Callable[[str], None] | None = None,
    ) -> ApplyResult:
        """Atomically apply one issue effect or replay its stored result.

        The operation id is globally bound to principal, backend, and request
        fingerprint. SQLite's immediate transaction serializes competing writers,
        so concurrent identical attempts cannot both dispatch the effect.
        """
        if identity.backend != self.backend_id:
            raise OperationConflict(
                f"operation backend {identity.backend!r} does not match {self.backend_id!r}"
            )
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            rows = self._conn.execute(
                """SELECT operation_id, principal, backend, request_fingerprint,
                          state, effect_id, result, issued_at, authority_expires_at,
                          replay_expires_at, created_at, updated_at
                   FROM operations WHERE operation_id = ?""",
                (identity.operation_id,),
            ).fetchall()
            if rows:
                row = rows[0]
                same_binding = (
                    row["principal"] == identity.principal
                    and row["backend"] == identity.backend
                    and row["request_fingerprint"] == request_fingerprint
                )
                if not same_binding:
                    raise OperationConflict(
                        "operation_id is already bound to a different principal, backend, "
                        "or request fingerprint"
                    )
                self._check_deadlines(row, now_epoch)
                if row["state"] == "partial" and row["effect_id"] is not None:
                    self._conn.commit()
                    return ApplyResult(
                        effect_id=int(row["effect_id"]),
                        result=str(row["result"] or "partial"),
                        replayed=True,
                        state="partial",
                    )
                if row["state"] != "applied" or row["effect_id"] is None or row["result"] is None:
                    raise OperationInProgress(
                        f"operation {identity.operation_id!r} is {row['state']}"
                    )
                self._conn.commit()
                return ApplyResult(
                    effect_id=int(row["effect_id"]), result=str(row["result"]), replayed=True
                )

            now = self._now()
            effective_issued_at = issued_at if issued_at is not None else (now_epoch or 0.0)
            self._validate_timing(
                issued_at=issued_at,
                authority_expires_at=authority_expires_at,
                replay_expires_at=replay_expires_at,
                now_epoch=now_epoch,
            )
            self._check_new_deadlines(
                now_epoch,
                authority_expires_at=authority_expires_at,
                replay_expires_at=replay_expires_at,
            )
            self._conn.execute(
                """INSERT INTO operations
                   (operation_id, principal, backend, request_fingerprint, state,
                    effect_id, result, issued_at, authority_expires_at,
                    replay_expires_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'in_progress', NULL, NULL, ?, ?, ?, ?, ?)""",
                (
                    identity.operation_id,
                    identity.principal,
                    identity.backend,
                    request_fingerprint,
                    effective_issued_at,
                    authority_expires_at,
                    replay_expires_at,
                    now,
                    now,
                ),
            )
            if fault_hook is not None:
                fault_hook("after-ledger-insert")
            cur = self._conn.execute(
                "INSERT INTO issues (title, body) VALUES (?, ?)", (title, body)
            )
            if fault_hook is not None:
                fault_hook("after-issue-insert")
            effect_id = cur.lastrowid
            assert effect_id is not None
            result = f"created {int(effect_id)}"
            self._conn.execute(
                """UPDATE operations
                   SET state = 'applied', effect_id = ?, result = ?, updated_at = ?
                   WHERE operation_id = ? AND principal = ? AND backend = ?""",
                (
                    int(effect_id),
                    result,
                    self._now(),
                    identity.operation_id,
                    identity.principal,
                    identity.backend,
                ),
            )
            self._conn.commit()
            return ApplyResult(effect_id=int(effect_id), result=result, replayed=False)
        except BaseException:
            # Cleanup also covers in-process cancellation and interruption.
            # Roll back only the current transaction, then preserve the signal.
            with suppress(sqlite3.Error):
                self._conn.rollback()
            raise

    @staticmethod
    def _validate_timing(
        *,
        issued_at: float | None,
        authority_expires_at: float | None,
        replay_expires_at: float | None,
        now_epoch: float | None,
    ) -> None:
        values = {
            "issued_at": issued_at,
            "authority_expires_at": authority_expires_at,
            "replay_expires_at": replay_expires_at,
            "now_epoch": now_epoch,
        }
        for name, value in values.items():
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if now_epoch is None and any(
            value is not None for value in (issued_at, authority_expires_at, replay_expires_at)
        ):
            raise ValueError("now_epoch is required for a bounded operation")
        if issued_at is not None:
            if now_epoch is not None and now_epoch < issued_at:
                raise ValueError("now_epoch cannot precede issued_at")
            if authority_expires_at is not None and authority_expires_at <= issued_at:
                raise ValueError("authority_expires_at must follow issued_at")
            if replay_expires_at is not None and replay_expires_at <= issued_at:
                raise ValueError("replay_expires_at must follow issued_at")

    @staticmethod
    def _check_new_deadlines(
        now_epoch: float | None,
        *,
        authority_expires_at: float | None,
        replay_expires_at: float | None,
    ) -> None:
        if now_epoch is None:
            return
        if not math.isfinite(now_epoch):
            raise ValueError("now_epoch must be finite")
        for name, value in (
            ("authority_expires_at", authority_expires_at),
            ("replay_expires_at", replay_expires_at),
        ):
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if authority_expires_at is not None and now_epoch >= authority_expires_at:
            raise OperationAuthorityExpired("operation authority has expired")
        if replay_expires_at is not None and now_epoch >= replay_expires_at:
            raise OperationRetentionExpired("operation replay retention has expired")

    @classmethod
    def _check_deadlines(cls, row: sqlite3.Row, now_epoch: float | None) -> None:
        if now_epoch is None and (
            row["authority_expires_at"] is not None or row["replay_expires_at"] is not None
        ):
            raise ValueError("now_epoch is required to replay a bounded operation")
        cls._check_new_deadlines(
            now_epoch,
            authority_expires_at=(
                float(row["authority_expires_at"])
                if row["authority_expires_at"] is not None
                else None
            ),
            replay_expires_at=(
                float(row["replay_expires_at"]) if row["replay_expires_at"] is not None else None
            ),
        )

    def apply_partial_issue_once(
        self,
        identity: OperationIdentity,
        *,
        request_fingerprint: str,
        title: str,
        body: str,
        watcher: str,
        issued_at: float,
        authority_expires_at: float,
        replay_expires_at: float,
        now_epoch: float,
        watcher_operation: Callable[[sqlite3.Connection, int, str], None],
        compensation_operation: Callable[[sqlite3.Connection, int], None],
        fault_hook: Callable[[str], None] | None = None,
    ) -> ApplyResult:
        """Commit a first effect, then preserve a failed second step and compensation.

        This is a deliberately bounded partial-effect model for case 12. The
        issue is committed with an in-progress ledger row. The absent watcher,
        failed compensation record, and terminal partial state are then committed
        without rewriting or repeating the first effect.
        """
        if identity.backend != self.backend_id:
            raise OperationConflict(
                f"operation backend {identity.backend!r} does not match {self.backend_id!r}"
            )
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                """SELECT operation_id, principal, backend, request_fingerprint,
                          state, effect_id, result, issued_at, authority_expires_at,
                          replay_expires_at, created_at, updated_at
                   FROM operations WHERE operation_id = ?""",
                (identity.operation_id,),
            ).fetchone()
            if row is not None:
                if (
                    row["principal"] != identity.principal
                    or row["backend"] != identity.backend
                    or row["request_fingerprint"] != request_fingerprint
                ):
                    raise OperationConflict(
                        "operation_id is already bound to a different principal, backend, "
                        "or request fingerprint"
                    )
                self._check_deadlines(row, now_epoch)
                if row["state"] not in {"partial", "applied"} or row["effect_id"] is None:
                    raise OperationInProgress(
                        f"operation {identity.operation_id!r} is {row['state']}"
                    )
                self._conn.commit()
                return ApplyResult(
                    effect_id=int(row["effect_id"]),
                    result=str(row["result"] or "partial"),
                    replayed=True,
                    state=str(row["state"]),
                )

            self._check_new_deadlines(
                now_epoch,
                authority_expires_at=authority_expires_at,
                replay_expires_at=replay_expires_at,
            )
            self._validate_timing(
                issued_at=issued_at,
                authority_expires_at=authority_expires_at,
                replay_expires_at=replay_expires_at,
                now_epoch=now_epoch,
            )
            stamp = self._now()
            self._conn.execute(
                """INSERT INTO operations
                   (operation_id, principal, backend, request_fingerprint, state,
                    effect_id, result, issued_at, authority_expires_at,
                    replay_expires_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'in_progress', NULL, NULL, ?, ?, ?, ?, ?)""",
                (
                    identity.operation_id,
                    identity.principal,
                    identity.backend,
                    request_fingerprint,
                    issued_at,
                    authority_expires_at,
                    replay_expires_at,
                    stamp,
                    stamp,
                ),
            )
            cur = self._conn.execute(
                "INSERT INTO issues (title, body) VALUES (?, ?)", (title, body)
            )
            effect_id = cur.lastrowid
            assert effect_id is not None
            self._conn.execute(
                """UPDATE operations SET effect_id = ?, updated_at = ?
                   WHERE operation_id = ? AND principal = ? AND backend = ?""",
                (
                    int(effect_id),
                    self._now(),
                    identity.operation_id,
                    identity.principal,
                    identity.backend,
                ),
            )
            self._conn.commit()

            if fault_hook is not None:
                fault_hook("after-partial-first-commit")

            self._record_operation_event(identity.operation_id, "watcher", "attempted")
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                watcher_operation(self._conn, int(effect_id), watcher)
                self._conn.execute(
                    """INSERT INTO operation_events
                       (operation_id, step, outcome, error_type, created_at)
                       VALUES (?, 'watcher', 'succeeded', NULL, ?)""",
                    (identity.operation_id, self._now()),
                )
                result = f"created {int(effect_id)} with watcher"
                self._conn.execute(
                    """UPDATE operations SET state = 'applied', result = ?, updated_at = ?
                       WHERE operation_id = ? AND principal = ? AND backend = ?""",
                    (
                        result,
                        self._now(),
                        identity.operation_id,
                        identity.principal,
                        identity.backend,
                    ),
                )
                self._conn.commit()
                return ApplyResult(
                    effect_id=int(effect_id), result=result, replayed=False, state="applied"
                )
            except Exception as watcher_error:  # noqa: BLE001 - injected operation boundary
                with suppress(sqlite3.Error):
                    self._conn.rollback()
                self._record_operation_event(
                    identity.operation_id,
                    "watcher",
                    "failed",
                    error_type=type(watcher_error).__name__,
                )

            self._record_operation_event(identity.operation_id, "rollback_issue", "attempted")
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                compensation_operation(self._conn, int(effect_id))
                self._conn.execute(
                    """INSERT INTO operation_events
                       (operation_id, step, outcome, error_type, created_at)
                       VALUES (?, 'rollback_issue', 'succeeded', NULL, ?)""",
                    (identity.operation_id, self._now()),
                )
                self._conn.execute(
                    "INSERT INTO compensations (issue_id, kind, outcome) VALUES (?, ?, ?)",
                    (int(effect_id), "rollback_issue", "succeeded"),
                )
                self._conn.execute(
                    """UPDATE operations SET state = 'partial', result = ?, updated_at = ?
                       WHERE operation_id = ? AND principal = ? AND backend = ?""",
                    (
                        f"partial {int(effect_id)}; watcher failed; rollback succeeded",
                        self._now(),
                        identity.operation_id,
                        identity.principal,
                        identity.backend,
                    ),
                )
                self._conn.commit()
            except Exception as compensation_error:  # noqa: BLE001 - injected operation boundary
                with suppress(sqlite3.Error):
                    self._conn.rollback()
                error_type = type(compensation_error).__name__
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    """INSERT INTO operation_events
                       (operation_id, step, outcome, error_type, created_at)
                       VALUES (?, 'rollback_issue', 'failed', ?, ?)""",
                    (identity.operation_id, error_type, self._now()),
                )
                self._conn.execute(
                    "INSERT INTO compensations (issue_id, kind, outcome) VALUES (?, ?, ?)",
                    (int(effect_id), "rollback_issue", f"failed:{error_type}"),
                )
                result = f"partial {int(effect_id)}; watcher failed; rollback failed"
                self._conn.execute(
                    """UPDATE operations SET state = 'partial', result = ?, updated_at = ?
                       WHERE operation_id = ? AND principal = ? AND backend = ?""",
                    (
                        result,
                        self._now(),
                        identity.operation_id,
                        identity.principal,
                        identity.backend,
                    ),
                )
                self._conn.commit()
                return ApplyResult(
                    effect_id=int(effect_id), result=result, replayed=False, state="partial"
                )

            # A successful compensation is still an unresolved partial outcome:
            # it cannot erase the committed first effect's historical identity.
            result = f"partial {int(effect_id)}; watcher failed; rollback succeeded"
            return ApplyResult(
                effect_id=int(effect_id), result=result, replayed=False, state="partial"
            )
        except BaseException:
            # Cleanup also covers in-process cancellation and interruption.
            # Roll back only the current transaction, then preserve the signal.
            with suppress(sqlite3.Error):
                self._conn.rollback()
            raise

    def operation_record(self, identity: OperationIdentity) -> OperationRecord | None:
        row = self._conn.execute(
            """SELECT operation_id, principal, backend, request_fingerprint,
                      state, effect_id, result, issued_at, authority_expires_at,
                      replay_expires_at, created_at, updated_at
               FROM operations
               WHERE operation_id = ? AND principal = ? AND backend = ?""",
            (identity.operation_id, identity.principal, identity.backend),
        ).fetchone()
        if row is None:
            return None
        return OperationRecord(
            identity=identity,
            request_fingerprint=str(row["request_fingerprint"]),
            state=str(row["state"]),
            effect_id=int(row["effect_id"]) if row["effect_id"] is not None else None,
            result=str(row["result"]) if row["result"] is not None else None,
            issued_at=(float(row["issued_at"]) if row["issued_at"] is not None else 0.0),
            authority_expires_at=(
                float(row["authority_expires_at"])
                if row["authority_expires_at"] is not None
                else None
            ),
            replay_expires_at=(
                float(row["replay_expires_at"]) if row["replay_expires_at"] is not None else None
            ),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _record_operation_event(
        self, operation_id: str, step: str, outcome: str, *, error_type: str | None = None
    ) -> None:
        self._conn.execute("BEGIN IMMEDIATE")
        self._conn.execute(
            """INSERT INTO operation_events
               (operation_id, step, outcome, error_type, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (operation_id, step, outcome, error_type, self._now()),
        )
        self._conn.commit()

    def operation_events(self, operation_id: str) -> list[OperationEvent]:
        rows = self._conn.execute(
            """SELECT id, operation_id, step, outcome, error_type
               FROM operation_events WHERE operation_id = ? ORDER BY id""",
            (operation_id,),
        ).fetchall()
        return [
            OperationEvent(
                id=int(row["id"]),
                operation_id=str(row["operation_id"]),
                step=str(row["step"]),
                outcome=str(row["outcome"]),
                error_type=str(row["error_type"]) if row["error_type"] is not None else None,
            )
            for row in rows
        ]

    def create_issue(self, title: str, body: str = "") -> int:
        """Insert a new issue and return its id.

        NOT idempotent by design. Calling this twice creates two issues.
        """
        cur = self._conn.execute("INSERT INTO issues (title, body) VALUES (?, ?)", (title, body))
        self._conn.commit()
        rowid = cur.lastrowid
        assert rowid is not None
        return int(rowid)

    def get_issue(self, issue_id: int) -> Issue | None:
        row = self._conn.execute(
            "SELECT id, title, body FROM issues WHERE id = ?", (issue_id,)
        ).fetchone()
        return Issue(id=row["id"], title=row["title"], body=row["body"]) if row else None

    def issues_with_title(self, title: str) -> list[Issue]:
        rows = self._conn.execute(
            "SELECT id, title, body FROM issues WHERE title = ? ORDER BY id", (title,)
        ).fetchall()
        return [Issue(id=r["id"], title=r["title"], body=r["body"]) for r in rows]

    def issues_with_body(self, body: str) -> list[Issue]:
        rows = self._conn.execute(
            "SELECT id, title, body FROM issues WHERE body = ? ORDER BY id", (body,)
        ).fetchall()
        return [Issue(id=r["id"], title=r["title"], body=r["body"]) for r in rows]

    def create_issue_with_watcher(
        self,
        title: str,
        body: str,
        watcher: str,
        *,
        fail_watcher: bool = False,
    ) -> int:
        """Two sub-effects: the issue, then a watcher row on it.

        With `fail_watcher=True` the issue **commits** and the watcher insert
        raises — leaving a `partial` effect observable through read-back. That
        partial state is what case 12 exists to preserve, not to paper over.
        """
        issue_id = self.create_issue(title, body)
        if fail_watcher:
            raise WatcherInsertFailed(
                f"issue {issue_id} committed but watcher {watcher!r} was not applied"
            )
        self._conn.execute(
            "INSERT INTO watchers (issue_id, name) VALUES (?, ?)", (issue_id, watcher)
        )
        self._conn.commit()
        return issue_id

    def record_compensation(self, issue_id: int, kind: str, outcome: str) -> int:
        """Record a compensation as its OWN identity row.

        Never rewrites the original operation: the issue row is preserved
        exactly as it happened. The compensation is a separate effect with a
        separate outcome.
        """
        cur = self._conn.execute(
            "INSERT INTO compensations (issue_id, kind, outcome) VALUES (?, ?, ?)",
            (issue_id, kind, outcome),
        )
        self._conn.commit()
        rowid = cur.lastrowid
        assert rowid is not None
        return int(rowid)

    def watchers_for(self, issue_id: int) -> list[Watcher]:
        rows = self._conn.execute(
            "SELECT id, issue_id, name FROM watchers WHERE issue_id = ? ORDER BY id",
            (issue_id,),
        ).fetchall()
        return [Watcher(id=r["id"], issue_id=r["issue_id"], name=r["name"]) for r in rows]

    def compensations_for(self, issue_id: int) -> list[Compensation]:
        rows = self._conn.execute(
            "SELECT id, issue_id, kind, outcome FROM compensations WHERE issue_id = ? ORDER BY id",
            (issue_id,),
        ).fetchall()
        return [
            Compensation(id=r["id"], issue_id=r["issue_id"], kind=r["kind"], outcome=r["outcome"])
            for r in rows
        ]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS n FROM issues").fetchone()["n"])

    def operation_count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS n FROM operations").fetchone()["n"])

    def reset(self) -> None:
        self._conn.execute("DELETE FROM watchers")
        self._conn.execute("DELETE FROM compensations")
        self._conn.execute("DELETE FROM operations")
        self._conn.execute("DELETE FROM operation_events")
        self._conn.execute("DELETE FROM issues")
        self._conn.execute(
            """DELETE FROM sqlite_sequence
               WHERE name IN ('issues', 'watchers', 'compensations', 'operation_events')"""
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
