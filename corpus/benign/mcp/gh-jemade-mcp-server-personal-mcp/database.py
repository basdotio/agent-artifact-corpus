"""Transactional task storage and bounded, read-only SQL access."""

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path


def now():
    return datetime.now(UTC).isoformat()


def clean_text(value, name, maximum=500):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be non-empty and at most {maximum} characters")
    return value.strip()


def due(value):
    if value is not None:
        date.fromisoformat(value)
    return value


class TaskStore:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'todo'
                      CHECK(status IN ('todo','in_progress','done')),
                    priority TEXT NOT NULL DEFAULT 'medium'
                      CHECK(priority IN ('low','medium','high')),
                    due_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1))
                );
                CREATE INDEX IF NOT EXISTS tasks_status_due ON tasks(archived,status,due_date);
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL REFERENCES tasks(id),
                    action TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL
                );
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def event(db, task_id, action, details):
        db.execute(
            "INSERT INTO task_events(task_id,action,details,created_at) VALUES (?,?,?,?)",
            (task_id, action, json.dumps(details), now()),
        )

    def create(self, title, description="", priority="medium", due_date=None):
        title = clean_text(title, "title")
        if len(description) > 10000:
            raise ValueError("description exceeds 10000 characters")
        if priority not in ("low", "medium", "high"):
            raise ValueError("invalid priority")
        due(due_date)
        stamp = now()
        with self.connection() as db:
            result = db.execute(
                """
                INSERT INTO tasks(title,description,priority,due_date,created_at,updated_at)
                VALUES (?,?,?,?,?,?)
            """,
                (title, description, priority, due_date, stamp, stamp),
            )
            task_id = result.lastrowid
            self.event(db, task_id, "created", {"title": title})
            return dict(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

    def get(self, task_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise ValueError("task not found")
            return dict(row)

    def list(
        self,
        status=None,
        priority=None,
        search=None,
        due_before=None,
        include_archived=False,
        limit=50,
        offset=0,
    ):
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("limit must be 1..100 and offset nonnegative")
        conditions, args = [], []
        if not include_archived:
            conditions.append("archived=0")
        for column, value, choices in [
            ("status", status, ("todo", "in_progress", "done")),
            ("priority", priority, ("low", "medium", "high")),
        ]:
            if value is not None:
                if value not in choices:
                    raise ValueError(f"invalid {column}")
                conditions.append(f"{column}=?")
                args.append(value)
        if search is not None:
            conditions.append(
                "(instr(lower(title),lower(?))>0 OR instr(lower(description),lower(?))>0)"
            )
            args.extend([clean_text(search, "search"), search])
        if due_before:
            conditions.append("due_date <= ?")
            args.append(due(due_before))
        where = " AND ".join(conditions) or "1=1"
        with self.connection() as db:
            total = db.execute(f"SELECT count(*) FROM tasks WHERE {where}", args).fetchone()[0]
            rows = db.execute(
                f"""SELECT * FROM tasks WHERE {where}
                ORDER BY due_date IS NULL, due_date, id LIMIT ? OFFSET ?""",
                [*args, limit, offset],
            ).fetchall()
        return {
            "tasks": [dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(rows) < total,
        }

    def update(self, task_id, expected_version, changes):
        allowed = {"title", "description", "status", "priority", "due_date"}
        if not changes or set(changes) - allowed:
            raise ValueError("provide supported fields only")
        if "title" in changes:
            changes["title"] = clean_text(changes["title"], "title")
        if "description" in changes and (
            not isinstance(changes["description"], str) or len(changes["description"]) > 10000
        ):
            raise ValueError("invalid description")
        for field, choices in [
            ("status", ("todo", "in_progress", "done")),
            ("priority", ("low", "medium", "high")),
        ]:
            if field in changes and changes[field] not in choices:
                raise ValueError(f"invalid {field}")
        if "due_date" in changes:
            due(changes["due_date"])
        with self.connection() as db:
            sets = ",".join(f"{key}=?" for key in changes)
            changed = db.execute(
                f"""UPDATE tasks SET {sets},updated_at=?,version=version+1
                WHERE id=? AND version=? AND archived=0""",
                [*changes.values(), now(), task_id, expected_version],
            ).rowcount
            if not changed:
                raise ValueError(
                    "task missing, archived or version conflict; fetch before retrying"
                )
            self.event(db, task_id, "updated", changes)
            return dict(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

    def archive(self, task_id, expected_version, archived=True):
        with self.connection() as db:
            changed = db.execute(
                """UPDATE tasks SET archived=?,updated_at=?,version=version+1
                WHERE id=? AND version=?""",
                (int(archived), now(), task_id, expected_version),
            ).rowcount
            if not changed:
                raise ValueError("task missing or version conflict")
            self.event(db, task_id, "archived" if archived else "restored", {})
            return dict(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

    def history(self, task_id):
        self.get(task_id)
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM task_events WHERE task_id=? ORDER BY id DESC LIMIT 100",
                    (task_id,),
                )
            ]


class ReadOnlySQL:
    """Only allowlisted tables, ordinary SELECT operations and approved scalar functions."""

    FUNCTIONS = frozenset(
        {
            "count",
            "sum",
            "avg",
            "min",
            "max",
            "coalesce",
            "ifnull",
            "nullif",
            "lower",
            "upper",
            "length",
            "substr",
            "substring",
            "trim",
            "ltrim",
            "rtrim",
            "abs",
            "round",
            "date",
            "datetime",
            "strftime",
            "julianday",
            "unixepoch",
            "replace",
            "instr",
            "like",
            "glob",
            "typeof",
            "total",
        }
    )

    def __init__(self, path, tables):
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise ValueError("query database does not exist")
        self.tables = frozenset(tables)
        if not self.tables:
            raise ValueError("configure at least one allowed table")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=2)
        db.execute("PRAGMA query_only=ON")
        db.enable_load_extension(False)
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1_000_000)
        db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 10_000)
        try:
            yield db
        finally:
            db.close()

    def schema(self):
        with self.connection() as db:
            found = {}
            for name, kind, sql in db.execute(
                "SELECT name,type,sql FROM sqlite_master WHERE type IN ('table','view')"
            ):
                if name in self.tables and kind == "table":
                    # PRAGMA table_info accepts a quoted identifier; names originate in schema.
                    escaped = name.replace('"', '""')
                    cols = db.execute(f'PRAGMA table_info("{escaped}")').fetchall()
                    found[name] = {
                        "ddl": sql,
                        "columns": [
                            {
                                "name": c[1],
                                "type": c[2],
                                "not_null": bool(c[3]),
                                "primary_key": bool(c[5]),
                            }
                            for c in cols
                        ],
                    }
            return found

    def query(self, sql, parameters=None, max_rows=100):
        if not 1 <= max_rows <= 200:
            raise ValueError("max_rows must be 1..200")
        if len(sql) > 10000:
            raise ValueError("SQL exceeds 10000 characters")
        tables = set(self.schema())

        def authorize(action, arg1, arg2, database, trigger):
            if action == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if (
                action == sqlite3.SQLITE_READ
                and (database == "main" or (database is None and arg2 == ""))
                and arg1 in tables
            ):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in self.FUNCTIONS:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        with self.connection() as db:
            db.set_authorizer(authorize)
            deadline = time.monotonic() + 1.0
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            try:
                cursor = db.execute(sql, parameters or [])
                if cursor.description is None:
                    raise ValueError("only result-returning read queries are supported")
                rows = cursor.fetchmany(max_rows + 1)
                # Bound tool output even when each row has unusually large TEXT fields.
                result, size, truncated = [], 0, len(rows) > max_rows
                for row in rows[:max_rows]:
                    converted = [v.hex() if isinstance(v, bytes) else v for v in row]
                    size += len(json.dumps(converted))
                    if size > 100_000:
                        truncated = True
                        break
                    result.append(converted)
                return {
                    "columns": [col[0] for col in cursor.description],
                    "rows": result,
                    "returned_rows": len(result),
                    "truncated": truncated,
                }
            except sqlite3.Error as error:
                raise ValueError(f"query rejected or failed: {error}") from error
