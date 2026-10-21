"""SQLite store: patients, vitals history, proposals, flags and the audit log.

Nothing in here decides anything clinical. It records what was proposed, who
confirmed it, and every tool call with inputs, outputs and timestamps.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
  id TEXT PRIMARY KEY,
  card_json TEXT NOT NULL,
  arrived_at TEXT NOT NULL,
  registered_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vitals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  source TEXT NOT NULL,
  vitals_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS proposals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  colour TEXT NOT NULL,
  tews INTEGER NOT NULL,
  sources_json TEXT NOT NULL,
  rationale TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  decided_at TEXT,
  clinician TEXT,
  final_colour TEXT,
  note TEXT
);
CREATE TABLE IF NOT EXISTS flags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL,
  proposal_id INTEGER
);
CREATE TABLE IF NOT EXISTS blind_calls (
  proposal_id INTEGER PRIMARY KEY,
  patient_id TEXT NOT NULL,
  clinician TEXT NOT NULL,
  colour TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL,
  tool TEXT NOT NULL,
  input_json TEXT NOT NULL,
  output_json TEXT NOT NULL,
  ok INTEGER NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_path() -> Path:
    return Path(os.environ.get("TRIAGE_DB", "triage.db"))


MIGRATIONS = [  # (table, column, type): added to databases made by older versions
    ("flags", "closed_at", "TEXT"),
    ("flags", "closed_by", "TEXT"),
    ("patients", "seen_at", "TEXT"),
    ("patients", "seen_by", "TEXT"),
]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    for table, col, kind in MIGRATIONS:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {kind}")
    return conn


def get_setting(key: str, default: str = "") -> str:
    with connect() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with connect() as c:
        c.execute("INSERT INTO settings (key, value) VALUES (?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def blind_call(proposal_id: int) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM blind_calls WHERE proposal_id=?", (proposal_id,)).fetchone()
    return dict(row) if row else None


def log(actor: str, tool: str, inputs: dict, output: object, ok: bool) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO audit (ts, actor, tool, input_json, output_json, ok) VALUES (?,?,?,?,?,?)",
            (now(), actor, tool, json.dumps(inputs, default=str), json.dumps(output, default=str), int(ok)),
        )


def get_patient(patient_id: str) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    if not row:
        return None
    return {"id": row["id"], "card": json.loads(row["card_json"]), "arrived_at": row["arrived_at"]}


def latest_vitals(patient_id: str) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM vitals WHERE patient_id=? ORDER BY id DESC LIMIT 1", (patient_id,)
        ).fetchone()
    if not row:
        return None
    return {"id": row["id"], "recorded_at": row["recorded_at"], "source": row["source"],
            "vitals": json.loads(row["vitals_json"])}


def add_vitals(patient_id: str, vitals: dict, source: str) -> int:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO vitals (patient_id, recorded_at, source, vitals_json) VALUES (?,?,?,?)",
            (patient_id, now(), source, json.dumps(vitals)),
        )
        return cur.lastrowid


def current_confirmed(patient_id: str) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM proposals WHERE patient_id=? AND status IN ('approved','overridden','nurse_set') "
            "ORDER BY id DESC LIMIT 1",
            (patient_id,),
        ).fetchone()
    return dict(row) if row else None


def pending_for(patient_id: str) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM proposals WHERE patient_id=? AND status='pending' ORDER BY id", (patient_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def open_flags(patient_id: str | None = None) -> list[dict]:
    q = "SELECT * FROM flags WHERE status='open'"
    args: tuple = ()
    if patient_id:
        q += " AND patient_id=?"
        args = (patient_id,)
    with connect() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY id", args).fetchall()]


def audit_for(patient_id: str) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM audit WHERE input_json LIKE ? OR output_json LIKE ? ORDER BY id",
            (f"%{patient_id}%", f'%"patient_id": "{patient_id}"%'),
        ).fetchall()
    return [dict(r) for r in rows]


def pending_all() -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT * FROM proposals WHERE status='pending' ORDER BY id").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["sources"] = json.loads(d.pop("sources_json"))
        out.append(d)
    return out
