"""Transactional SQLite records, masking, audit and conflict-aware reversal."""

from __future__ import annotations

import copy
import csv
import io
import json
import re
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from .filters import parse_where
from .schema import MASK, META, TYPES, identifier, load_schemas, merge_schema


class NotFound(LookupError):
    """A requested table, row or change does not exist."""


class Conflict(ValueError):
    """An operation would conflict with a later write or existing unique key."""


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def decimal_compare(left: Any, right: Any) -> int | None:
    if left is None or right is None:
        return None
    a, b = Decimal(str(left)), Decimal(str(right))
    return (a > b) - (a < b)


class Hub:
    def __init__(
        self,
        data_dir: str | Path = "data",
        schema_dir: str | Path | None = None,
        timezone: str = "Asia/Shanghai",
    ) -> None:
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "hub.db"
        self.schema_dir = (
            Path(schema_dir).expanduser().resolve() if schema_dir else self.data_dir / "schemas"
        )
        self.schema_dir.mkdir(parents=True, exist_ok=True)
        self.timezone = timezone
        ZoneInfo(timezone)
        builtin = Path(__file__).parents[1] / "builtin_schemas"
        for source in builtin.glob("*.yaml"):
            destination = self.schema_dir / source.name
            if not destination.exists():
                shutil.copyfile(source, destination)
        self.schemas: dict[str, dict[str, Any]] = {}
        self.migrate()

    @contextmanager
    def connect(self, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.create_function("decimal_compare", 2, decimal_compare, deterministic=True)
        try:
            if write:
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        """Add tables/columns only; persisted schemas retain removed columns and sensitivity."""
        discovered = load_schemas(self.schema_dir)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS schema_registry(table_name TEXT PRIMARY KEY, schema_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS changes(id TEXT PRIMARY KEY, table_name TEXT NOT NULL,
                    row_id TEXT NOT NULL, op TEXT NOT NULL, before_json TEXT, after_json TEXT,
                    actor TEXT NOT NULL, at TEXT NOT NULL, reverses TEXT, reverted_by TEXT);
                CREATE INDEX IF NOT EXISTS changes_row ON changes(table_name,row_id,at);
                CREATE TABLE IF NOT EXISTS imports(id TEXT PRIMARY KEY, file TEXT NOT NULL, sha1 TEXT NOT NULL,
                    table_name TEXT NOT NULL, rows_in INTEGER NOT NULL, rows_upserted INTEGER NOT NULL, at TEXT NOT NULL);
            """)
        with self.connect(write=True) as conn:
            stored = {
                row["table_name"]: json.loads(row["schema_json"])
                for row in conn.execute("SELECT * FROM schema_registry")
            }
            effective = dict(stored)
            for table, current in discovered.items():
                previous = stored.get(table)
                schema = merge_schema(previous, current) if previous else current
                physical = "h_" + table
                if previous is None:
                    definitions = [
                        "id TEXT PRIMARY KEY",
                        "created_at TEXT NOT NULL",
                        "updated_at TEXT NOT NULL",
                        "source_file TEXT NOT NULL",
                        "actor TEXT NOT NULL",
                    ]
                    definitions += [
                        f'"{name}" {TYPES[options["type"]]}'
                        for name, options in schema["columns"].items()
                    ]
                    conn.execute(f'CREATE TABLE "{physical}" ({",".join(definitions)})')
                    if schema["unique"]:
                        keys = ",".join('"' + key + '"' for key in schema["unique"])
                        conn.execute(f'CREATE UNIQUE INDEX "u_{table}" ON "{physical}" ({keys})')
                else:
                    for name, options in schema["columns"].items():
                        if name in previous["columns"]:
                            continue
                        count = conn.execute(f'SELECT count(*) FROM "{physical}"').fetchone()[0]
                        if options.get("required") and count and options.get("default") is None:
                            raise ValueError(
                                f"{table}.{name}: new required columns need a default when rows exist"
                            )
                        conn.execute(
                            f'ALTER TABLE "{physical}" ADD COLUMN "{name}" {TYPES[options["type"]]}'
                        )
                        if "default" in options:
                            value = self._coerce(name, options["default"], options)
                            records = conn.execute(f'SELECT * FROM "{physical}"').fetchall()
                            for record in records:
                                before = dict(record)
                                after = {
                                    **before,
                                    name: value,
                                    "updated_at": now(),
                                    "actor": "schema:migration",
                                }
                                conn.execute(
                                    f'UPDATE "{physical}" SET "{name}"=?,updated_at=?,actor=? WHERE id=?',
                                    (value, after["updated_at"], after["actor"], record["id"]),
                                )
                                self._audit(
                                    conn,
                                    table,
                                    record["id"],
                                    "update",
                                    before,
                                    after,
                                    "schema:migration",
                                )
                conn.execute(
                    "INSERT OR REPLACE INTO schema_registry VALUES (?,?)",
                    (table, json.dumps(schema, ensure_ascii=False)),
                )
                effective[table] = schema
            self.schemas = effective

    def _schema(self, table: str) -> dict[str, Any]:
        identifier(table)
        if table not in self.schemas:
            raise NotFound(f"unknown table: {table}")
        return self.schemas[table]

    def describe(self, table: str, reveal: bool = False) -> dict[str, Any]:
        schema = copy.deepcopy(self._schema(table))
        if not reveal:
            for options in schema["columns"].values():
                if options.get("sensitive") and "default" in options:
                    options["default"] = MASK
        schema["metadata_fields"] = sorted(META)
        return schema

    def tables(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [
                {
                    "table": table,
                    "label": schema["label"],
                    "rows": conn.execute(f'SELECT count(*) FROM "h_{table}"').fetchone()[0],
                    "columns": len(schema["columns"]),
                }
                for table, schema in sorted(self.schemas.items())
            ]

    def mask(
        self, table: str, row: dict[str, Any] | None, reveal: bool = False
    ) -> dict[str, Any] | None:
        if row is None:
            return None
        result = dict(row)
        for name, options in self._schema(table)["columns"].items():
            if name in result and result[name] is not None:
                if options.get("sensitive") and not reveal:
                    result[name] = MASK
                elif options["type"] == "boolean":
                    result[name] = bool(result[name])
        return result

    def _coerce(self, name: str, value: Any, options: dict[str, Any]) -> Any:
        if value is None or value == "":
            if options.get("required"):
                raise ValueError(f"required field is missing: {name}")
            return None
        if value == MASK:
            raise ValueError(
                f"masked placeholder cannot be written to field: {name}; use an explicit value or omit it"
            )
        kind = options["type"]
        try:
            if kind == "integer":
                if (
                    isinstance(value, bool)
                    or Decimal(str(value)) != Decimal(str(value)).to_integral_value()
                ):
                    raise ValueError
                return int(Decimal(str(value)))
            if kind == "decimal":
                number = Decimal(str(value))
                if not number.is_finite():
                    raise ValueError
                return format(number, "f")
            if kind == "boolean":
                if value in (True, 1, "true", "True", "1"):
                    return 1
                if value in (False, 0, "false", "False", "0"):
                    return 0
                raise ValueError
            if kind == "date":
                if isinstance(value, datetime):
                    return value.date().isoformat()
                return date.fromisoformat(str(value)).isoformat()
            if kind == "datetime":
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo(self.timezone))
                return dt.astimezone(UTC).isoformat()
            if not isinstance(value, (str, int, float, Decimal, date)):
                raise ValueError
            return str(value)
        except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
            raise ValueError(f"invalid {kind} value for field: {name}") from exc

    def _prepare(self, table: str, data: dict[str, Any], partial: bool = False) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("record data must be a JSON object")
        schema = self._schema(table)
        unknown = set(data) - set(schema["columns"])
        if unknown:
            raise ValueError("unknown or protected fields: " + ", ".join(sorted(unknown)))
        result = {}
        for name, options in schema["columns"].items():
            if partial and name not in data:
                continue
            value = data.get(name, options.get("default"))
            if name in schema["unique"] and (value is None or value == ""):
                raise ValueError(f"unique key is required: {name}")
            result[name] = self._coerce(name, value, options)
        return result

    @staticmethod
    def _actor(actor: str) -> None:
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor must be a non-empty string")

    def _get(self, conn: sqlite3.Connection, table: str, row_id: str) -> dict[str, Any]:
        self._schema(table)
        row = conn.execute(f'SELECT * FROM "h_{table}" WHERE id=?', (row_id,)).fetchone()
        if row is None:
            raise NotFound("record not found")
        return dict(row)

    def get(self, table: str, row_id: str, reveal: bool = False) -> dict[str, Any]:
        with self.connect() as conn:
            return self.mask(table, self._get(conn, table, row_id), reveal)

    def _audit(
        self,
        conn: sqlite3.Connection,
        table: str,
        row_id: str,
        op: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        actor: str,
        reverses: str | None = None,
    ) -> str:
        self._actor(actor)
        change = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO changes VALUES (?,?,?,?,?,?,?,?,?,NULL)",
            (
                change,
                table,
                row_id,
                op,
                json.dumps(before, ensure_ascii=False) if before is not None else None,
                json.dumps(after, ensure_ascii=False) if after is not None else None,
                actor,
                now(),
                reverses,
            ),
        )
        return change

    def _insert(
        self,
        conn: sqlite3.Connection,
        table: str,
        data: dict[str, Any],
        actor: str,
        source_file: str = "",
        *,
        row_id: str | None = None,
        created_at: str | None = None,
        reverses: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        self._actor(actor)
        values = self._prepare(table, data)
        at = now()
        values = {
            "id": row_id or str(uuid.uuid4()),
            "created_at": created_at or at,
            "updated_at": at,
            "source_file": source_file,
            "actor": actor,
            **values,
        }
        columns = ",".join('"' + key + '"' for key in values)
        conn.execute(
            f'INSERT INTO "h_{table}" ({columns}) VALUES ({",".join("?" for _ in values)})',
            list(values.values()),
        )
        change = self._audit(conn, table, values["id"], "insert", None, values, actor, reverses)
        return values, change

    def insert(
        self, table: str, data: dict[str, Any], actor: str = "cli", reveal: bool = False
    ) -> dict[str, Any]:
        with self.connect(write=True) as conn:
            row, change = self._insert(conn, table, data, actor)
        return {"row": self.mask(table, row, reveal), "change_id": change}

    def _update(
        self,
        conn: sqlite3.Connection,
        table: str,
        row_id: str,
        data: dict[str, Any],
        actor: str,
        source_file: str | None = None,
        expected_updated_at: str | None = None,
        reverses: str | None = None,
    ) -> tuple[dict[str, Any], str | None]:
        before = self._get(conn, table, row_id)
        if expected_updated_at is not None and before["updated_at"] != expected_updated_at:
            raise Conflict("record changed since it was read; refresh before editing")
        values = self._prepare(table, data, partial=True)
        if not values:
            raise ValueError("provide at least one field to update")
        if all(before[name] == value for name, value in values.items()) and source_file in {
            None,
            before["source_file"],
        }:
            return before, None
        after = {**before, **values, "updated_at": now(), "actor": actor}
        if source_file is not None:
            after["source_file"] = source_file
        self._actor(actor)
        columns = [name for name in after if name != "id"]
        conn.execute(
            f'UPDATE "h_{table}" SET {",".join(chr(34) + name + chr(34) + "=?" for name in columns)} WHERE id=?',
            [after[name] for name in columns] + [row_id],
        )
        change = self._audit(conn, table, row_id, "update", before, after, actor, reverses)
        return after, change

    def update(
        self,
        table: str,
        row_id: str,
        data: dict[str, Any],
        actor: str = "cli",
        reveal: bool = False,
        expected_updated_at: str | None = None,
    ) -> dict[str, Any]:
        with self.connect(write=True) as conn:
            row, change = self._update(
                conn, table, row_id, data, actor, expected_updated_at=expected_updated_at
            )
        return {
            "row": self.mask(table, row, reveal),
            "change_id": change,
            "unchanged": change is None,
        }

    def _delete(
        self,
        conn: sqlite3.Connection,
        table: str,
        row_id: str,
        actor: str,
        reverses: str | None = None,
    ) -> str:
        before = self._get(conn, table, row_id)
        conn.execute(f'DELETE FROM "h_{table}" WHERE id=?', (row_id,))
        return self._audit(conn, table, row_id, "delete", before, None, actor, reverses)

    def delete(
        self, table: str, row_id: str, confirm: bool = False, actor: str = "cli"
    ) -> dict[str, Any]:
        if confirm is not True:
            raise ValueError("delete requires confirm=true or --yes; back up first")
        with self.connect(write=True) as conn:
            change = self._delete(conn, table, row_id, actor)
        return {"id": row_id, "deleted": True, "change_id": change}

    def query(
        self,
        table: str,
        where: str | None = None,
        fields: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        reveal: bool = False,
    ) -> list[dict[str, Any]]:
        schema = self._schema(table)
        all_columns = {**{key: {"type": "text"} for key in META}, **schema["columns"]}
        selected = fields or list(all_columns)
        if any(name not in all_columns for name in selected):
            raise ValueError("requested field is not in the schema")
        if (
            type(limit) is not int
            or not 1 <= limit <= 10000
            or type(offset) is not int
            or offset < 0
        ):
            raise ValueError("limit must be 1..10000 and offset must be nonnegative")
        condition, params = parse_where(where, all_columns, reveal=reveal)
        conditions = [condition] if condition else []
        if search:
            searchable = [
                name
                for name, opts in schema["columns"].items()
                if opts["type"] == "text" and (reveal or not opts.get("sensitive"))
            ]
            if not searchable:
                return []
            conditions.append(
                "(" + " OR ".join('"' + name + "\" LIKE ? ESCAPE '\\'" for name in searchable) + ")"
            )
            needle = (
                "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            )
            params.extend([needle] * len(searchable))
        names = ",".join('"' + name + '"' for name in selected)
        sql = (
            f'SELECT {names} FROM "h_{table}"'
            + (" WHERE " + " AND ".join(conditions) if conditions else "")
            + " ORDER BY created_at,id LIMIT ? OFFSET ?"
        )
        with self.connect() as conn:
            rows = conn.execute(sql, [*params, limit, offset]).fetchall()
        return [self.mask(table, dict(row), reveal) for row in rows]

    def history(
        self,
        table: str | None = None,
        row_id: str | None = None,
        limit: int = 100,
        reveal: bool = False,
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= 10000:
            raise ValueError("history limit must be 1..10000")
        conditions, args = [], []
        if table:
            self._schema(table)
            conditions.append("table_name=?")
            args.append(table)
        if row_id:
            conditions.append("row_id=?")
            args.append(row_id)
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM changes"
                + (" WHERE " + " AND ".join(conditions) if conditions else "")
                + " ORDER BY at DESC,id DESC LIMIT ?",
                [*args, limit],
            ).fetchall()
        result = []
        for row in rows:
            entry = dict(row)
            entry["table"] = entry.pop("table_name")
            for side in ("before", "after"):
                raw = entry.pop(side + "_json")
                entry[side] = self.mask(entry["table"], json.loads(raw) if raw else None, reveal)
            result.append(entry)
        return result

    def revert(
        self, change_id: str, confirm: bool = False, actor: str = "cli", reveal: bool = False
    ) -> dict[str, Any]:
        """Invert a change only if no later state conflicts; each inverse is itself audited."""
        if confirm is not True:
            raise ValueError("revert requires confirm=true or --yes; back up first")
        with self.connect(write=True) as conn:
            change = conn.execute("SELECT * FROM changes WHERE id=?", (change_id,)).fetchone()
            if not change:
                raise NotFound("change not found")
            if change["reverted_by"]:
                raise Conflict("change has already been reverted")
            table, row_id = change["table_name"], change["row_id"]
            before = json.loads(change["before_json"]) if change["before_json"] else None
            after = json.loads(change["after_json"]) if change["after_json"] else None
            if change["op"] in {"insert", "update"}:
                current = self._get(conn, table, row_id)
                # Add-only migrations may introduce extra columns; compare recorded fields.
                if any(current.get(key) != value for key, value in after.items()):
                    raise Conflict("a later change conflicts with this revert")
            if change["op"] == "insert":
                inverse = self._delete(conn, table, row_id, actor, change_id)
                row = None
            elif change["op"] == "update":
                data = {
                    name: before.get(name)
                    for name in self.schemas[table]["columns"]
                    if name in before
                }
                row, inverse = self._update(
                    conn,
                    table,
                    row_id,
                    data,
                    actor,
                    source_file=before["source_file"],
                    reverses=change_id,
                )
            else:
                if conn.execute(f'SELECT 1 FROM "h_{table}" WHERE id=?', (row_id,)).fetchone():
                    raise Conflict("deleted record ID has been reused")
                data = {
                    name: before.get(name)
                    for name in self.schemas[table]["columns"]
                    if name in before
                }
                row, inverse = self._insert(
                    conn,
                    table,
                    data,
                    actor,
                    before["source_file"],
                    row_id=row_id,
                    created_at=before["created_at"],
                    reverses=change_id,
                )
            conn.execute("UPDATE changes SET reverted_by=? WHERE id=?", (inverse, change_id))
        return {"reverted": change_id, "change_id": inverse, "row": self.mask(table, row, reveal)}

    def due(self, within: str = "30d", reveal: bool = False) -> list[dict[str, Any]]:
        if not re.fullmatch(r"\d+d", within) or int(within[:-1]) > 36500:
            raise ValueError("within must be a duration such as 30d, at most 36500d")
        today = datetime.now(ZoneInfo(self.timezone)).date()
        end = today + timedelta(days=int(within[:-1]))
        results = []
        with self.connect() as conn:
            for table, schema in self.schemas.items():
                for field in schema["due_fields"]:
                    if schema["columns"][field].get("sensitive") and not reveal:
                        continue
                    rows = conn.execute(
                        f'SELECT * FROM "h_{table}" WHERE "{field}"<=? ORDER BY "{field}"',
                        (end.isoformat(),),
                    ).fetchall()
                    for row in rows:
                        results.append(
                            {
                                "table": table,
                                "field": field,
                                "due_date": row[field],
                                "days_remaining": (date.fromisoformat(row[field]) - today).days,
                                "row": self.mask(table, dict(row), reveal),
                            }
                        )
        return sorted(
            results, key=lambda item: (item["due_date"], item["table"], item["row"]["id"])
        )

    def export_text(
        self,
        table: str,
        format: str = "json",
        where: str | None = None,
        reveal: bool = False,
        bom: bool = True,
        search: str | None = None,
    ) -> tuple[str, int]:
        if format not in {"json", "csv"}:
            raise ValueError("export format must be json or csv")
        items = []
        offset = 0
        while True:
            batch = self.query(
                table, where=where, reveal=reveal, limit=10000, offset=offset, search=search
            )
            items.extend(batch)
            if len(batch) < 10000:
                break
            offset += len(batch)
        if format == "json":
            return json.dumps(items, ensure_ascii=False, indent=2), len(items)
        output = io.StringIO(newline="")
        fields = [
            "id",
            *self._schema(table)["columns"],
            "created_at",
            "updated_at",
            "source_file",
            "actor",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)
        return ("\ufeff" if bom else "") + output.getvalue(), len(items)

    def export(
        self,
        table: str,
        out: str | Path,
        format: str = "json",
        where: str | None = None,
        reveal: bool = False,
        bom: bool = True,
        search: str | None = None,
    ) -> dict[str, Any]:
        path = Path(out).expanduser().resolve()
        if path == self.path or str(path).startswith(str(self.path) + "-"):
            raise ValueError("export cannot overwrite the database or its WAL files")
        content, count = self.export_text(table, format, where, reveal, bom, search)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
        return {"path": str(path), "count": count, "masked": not reveal}

    def backup(self, out: str | Path | None = None) -> dict[str, Any]:
        stamp = datetime.now(ZoneInfo(self.timezone)).strftime("%Y%m%d_%H%M%S_%f")
        path = (
            Path(out).expanduser().resolve()
            if out
            else self.data_dir / "backups" / f"backup_{stamp}.zip"
        )
        if path == self.path or str(path).startswith(str(self.path) + "-"):
            raise ValueError("backup cannot overwrite the database or its WAL files")
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "hub.db"
            with self.connect() as conn, sqlite3.connect(db) as target:
                conn.backup(target)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(db, "hub.db")
                for name, schema in self.schemas.items():
                    archive.writestr(
                        f"schemas/{name}.yaml",
                        yaml.safe_dump(schema, sort_keys=False, allow_unicode=True),
                    )
                archive.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "version": "0.1.1",
                            "created_at": now(),
                            "timezone": self.timezone,
                            "contains_unmasked_private_data": True,
                        }
                    ),
                )
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "contains_unmasked_private_data": True,
        }
