"""SQLite storage and versioned schema; no appliance or approval decisions."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from backend.domain import InputError

DEFAULT_DB = Path(__file__).resolve().parents[1] / ".local" / "homeresolve.sqlite3"

SCHEMA = (
    """CREATE TABLE repair_proposals (
        proposal_id TEXT PRIMARY KEY NOT NULL,
        household_id TEXT NOT NULL CHECK(length(trim(household_id)) BETWEEN 1 AND 80),
        appliance_id TEXT NOT NULL,
        issue_description TEXT NOT NULL CHECK(length(trim(issue_description)) BETWEEN 1 AND 2000),
        warranty_evaluation_snapshot TEXT NOT NULL CHECK(json_valid(warranty_evaluation_snapshot)),
        supporting_evidence_references TEXT NOT NULL CHECK(json_valid(supporting_evidence_references)),
        purchase_evidence_snapshot TEXT NOT NULL CHECK(json_valid(purchase_evidence_snapshot)),
        request_json TEXT NOT NULL CHECK(json_valid(request_json)),
        status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        idempotency_key TEXT NOT NULL CHECK(length(trim(idempotency_key)) BETWEEN 1 AND 120),
        UNIQUE(household_id, idempotency_key), UNIQUE(proposal_id, household_id)
    )""",
    """CREATE TABLE repair_cases (
        case_id TEXT PRIMARY KEY NOT NULL,
        proposal_id TEXT NOT NULL UNIQUE,
        household_id TEXT NOT NULL,
        appliance_id TEXT NOT NULL, issue_description TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status = 'open'),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(case_id, proposal_id, household_id),
        FOREIGN KEY(proposal_id, household_id) REFERENCES repair_proposals(proposal_id, household_id)
    )""",
    """CREATE TABLE audit_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id TEXT NOT NULL, proposal_id TEXT NOT NULL, case_id TEXT,
        event_type TEXT NOT NULL CHECK(event_type IN ('proposal_prepared','proposal_approved','proposal_rejected','case_created')),
        event_timestamp TEXT NOT NULL,
        metadata_json TEXT NOT NULL CHECK(json_valid(metadata_json)),
        FOREIGN KEY(proposal_id, household_id) REFERENCES repair_proposals(proposal_id, household_id),
        FOREIGN KEY(case_id, proposal_id, household_id) REFERENCES repair_cases(case_id, proposal_id, household_id)
    )""",
    """CREATE TRIGGER proposal_starts_pending BEFORE INSERT ON repair_proposals
        WHEN NEW.status != 'pending' BEGIN SELECT RAISE(ABORT, 'proposal must start pending'); END""",
    """CREATE TRIGGER proposal_terminal BEFORE UPDATE OF status ON repair_proposals
        WHEN OLD.status != 'pending' AND NEW.status != OLD.status
        BEGIN SELECT RAISE(ABORT, 'terminal proposal state'); END""",
    """CREATE TRIGGER case_requires_approval BEFORE INSERT ON repair_cases
        WHEN NOT EXISTS (SELECT 1 FROM repair_proposals p WHERE p.proposal_id=NEW.proposal_id
          AND p.household_id=NEW.household_id AND p.status='approved'
          AND p.appliance_id=NEW.appliance_id AND p.issue_description=NEW.issue_description)
        BEGIN SELECT RAISE(ABORT, 'case requires matching approved proposal'); END""",
    "CREATE INDEX audit_proposal ON audit_events(household_id, proposal_id, event_id)",
)


class RepairRepository:
    """Each operation owns a fresh connection. Writes serialize before reading state."""

    def __init__(self, path: Path = DEFAULT_DB) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                for statement in SCHEMA:
                    connection.execute(statement)
                connection.execute("PRAGMA user_version = 1")
            elif version != 1:
                raise ValueError(f"Unsupported database schema version {version}; expected 1.")

    @contextmanager
    def transaction(self, *, write: bool = True) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def record(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        for field in ("warranty_evaluation_snapshot", "supporting_evidence_references",
                      "purchase_evidence_snapshot", "request_json", "metadata_json"):
            if field in result:
                result[field] = json.loads(result[field])
        return result

    def get(self, connection: sqlite3.Connection, kind: str, household: str, identifier: str) -> dict[str, Any]:
        # Table/column names are internal allow-listed constants, never caller SQL.
        table, key = {"proposal": ("repair_proposals", "proposal_id"), "case": ("repair_cases", "case_id")}[kind]
        row = connection.execute(f"SELECT * FROM {table} WHERE household_id=? AND {key}=?",
                                 (household, identifier)).fetchone()
        if row is None:
            raise InputError(f"Unknown {kind} in this household: {identifier}")
        return self.record(row)

    def proposal_by_key(self, connection: sqlite3.Connection, household: str, key: str) -> dict[str, Any] | None:
        row = connection.execute("SELECT * FROM repair_proposals WHERE household_id=? AND idempotency_key=?",
                                 (household, key)).fetchone()
        return self.record(row) if row is not None else None

    def case_for_proposal(self, connection: sqlite3.Connection, household: str, proposal_id: str) -> dict[str, Any] | None:
        row = connection.execute("SELECT * FROM repair_cases WHERE household_id=? AND proposal_id=?",
                                 (household, proposal_id)).fetchone()
        return self.record(row) if row is not None else None

    @staticmethod
    def set_proposal_status(connection: sqlite3.Connection, household: str, proposal_id: str,
                            status: str, now: str) -> None:
        connection.execute("UPDATE repair_proposals SET status=?,updated_at=? WHERE household_id=? AND proposal_id=?",
                           (status, now, household, proposal_id))

    def cases(self, connection: sqlite3.Connection, household: str) -> list[dict[str, Any]]:
        return [self.record(row) for row in connection.execute(
            "SELECT * FROM repair_cases WHERE household_id=? ORDER BY created_at,case_id", (household,))]

    def proposals(self, connection: sqlite3.Connection, household: str) -> list[dict[str, Any]]:
        return [self.record(row) for row in connection.execute(
            "SELECT * FROM repair_proposals WHERE household_id=? ORDER BY created_at,proposal_id", (household,))]

    def events(self, connection: sqlite3.Connection, household: str, proposal_id: str) -> list[dict[str, Any]]:
        return [self.record(row) for row in connection.execute(
            "SELECT * FROM audit_events WHERE household_id=? AND proposal_id=? ORDER BY event_id", (household, proposal_id))]

    @staticmethod
    def insert(connection: sqlite3.Connection, table: str, values: dict[str, Any]) -> None:
        if table not in {"repair_proposals", "repair_cases", "audit_events"}:
            raise ValueError("Invalid internal table")
        columns = ",".join(values)
        connection.execute(f"INSERT INTO {table} ({columns}) VALUES ({','.join('?' for _ in values)})",
                           tuple(values.values()))
