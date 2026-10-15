from __future__ import annotations

import json
import sqlite3
import time
import uuid

from .config import DATA


class Store:
    def __init__(self, path=None):
        self.path = path or DATA / "sessions.sqlite"
        with self.db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT, value TEXT, updated REAL)"
            )

    def db(self):
        return sqlite3.connect(self.path, timeout=15)

    def put(self, kind: str, value: dict, key: str | None = None) -> dict:
        value = {**value, "id": key or value.get("id") or str(uuid.uuid4())}
        with self.db() as db:
            db.execute(
                "INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?)",
                (value["id"], kind, json.dumps(value), time.time()),
            )
        return value

    def get(self, key: str, kind: str | None = None) -> dict:
        with self.db() as db:
            row = db.execute("SELECT kind, value FROM records WHERE id=?", (key,)).fetchone()
        if not row or (kind and row[0] != kind):
            raise KeyError("Record not found")
        return json.loads(row[1])

    def list(self, kind: str) -> list[dict]:
        with self.db() as db:
            rows = db.execute(
                "SELECT value FROM records WHERE kind=? ORDER BY updated DESC", (kind,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]
