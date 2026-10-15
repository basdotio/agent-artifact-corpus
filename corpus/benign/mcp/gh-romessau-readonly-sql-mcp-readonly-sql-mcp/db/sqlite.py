"""Read-only SQLite adapter."""

from __future__ import annotations

import re
import sqlite3
import time
from contextlib import suppress
from pathlib import Path

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from readonly_sql_mcp.db.base import (
    ColumnInfo,
    ForeignKeyInfo,
    IndexInfo,
    QueryResult,
    TableDescription,
    TableInfo,
)
from readonly_sql_mcp.security import is_pragma_name

_SQLITE_MAGIC = b"SQLite format 3\x00"
_LEADING_UNSAFE = re.compile(
    r"^(?:\s|--[^\n]*(?:\n|$)|/\*.*?\*/)*(ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE | re.DOTALL,
)


class DatabaseError(Exception):
    """A safe database error suitable for returning to clients."""


class QueryTimeoutError(DatabaseError):
    """The database stopped a query after its configured time budget."""


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _reject_connection_escapes(sql: str) -> None:
    """Block ATTACH, DETACH, and PRAGMA even when the AST validator is skipped."""
    if _LEADING_UNSAFE.match(sql) is not None:
        raise DatabaseError("query could not be executed")
    try:
        statements = [
            statement
            for statement in parse(sql, read="sqlite")
            if statement and not isinstance(statement, exp.Semicolon)
        ]
    except (ParseError, ValueError):
        return
    for statement in statements:
        if isinstance(statement, (exp.Attach, exp.Detach, exp.Pragma)):
            raise DatabaseError("query could not be executed")
        if (
            statement.find(exp.Attach) is not None
            or statement.find(exp.Detach) is not None
            or statement.find(exp.Pragma) is not None
        ):
            raise DatabaseError("query could not be executed")
        for table in statement.find_all(exp.Table):
            relation_name = table.name
            if isinstance(table.this, exp.Func):
                relation_name = (
                    table.this.name if isinstance(table.this, exp.Anonymous) else table.this.key
                )
            if is_pragma_name(relation_name):
                raise DatabaseError("query could not be executed")


class SQLiteAdapter:
    """SQLite implementation that opens an existing database read-only."""

    def __init__(self, database_path: Path, timeout_ms: int = 5_000) -> None:
        path = database_path.expanduser().resolve()
        if not path.is_file():
            raise DatabaseError("database file does not exist")
        try:
            with path.open("rb") as database_file:
                header = database_file.read(16)
        except OSError:
            raise DatabaseError("unable to open database") from None
        if header != _SQLITE_MAGIC:
            raise DatabaseError("unable to open database")
        try:
            self._connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
            self._connection.execute("PRAGMA query_only = ON")
        except sqlite3.Error:
            raise DatabaseError("unable to open database") from None
        self._connection.row_factory = sqlite3.Row
        self._timeout_ms = timeout_ms

    def list_tables(self) -> list[TableInfo]:
        """List user tables and views with available planner estimates."""
        try:
            objects = self._connection.execute(
                "SELECT name, type FROM sqlite_schema "
                "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            estimates: dict[str, int] = {}
            has_stats = self._connection.execute(
                "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'sqlite_stat1'"
            ).fetchone()
            if has_stats:
                for row in self._connection.execute("SELECT tbl, stat FROM sqlite_stat1"):
                    first = str(row["stat"]).split()[0]
                    if first.isdigit():
                        name = str(row["tbl"])
                        value = int(first)
                        previous = estimates.get(name)
                        estimates[name] = value if previous is None else max(previous, value)
            return [
                TableInfo(
                    name=str(row["name"]),
                    type=str(row["type"]),
                    row_count=estimates.get(str(row["name"])),
                )
                for row in objects
            ]
        except sqlite3.Error:
            raise DatabaseError("database metadata could not be read") from None

    def describe_table(self, name: str) -> TableDescription:
        """Return columns, foreign keys, and indexes for a table or view."""
        try:
            found = self._connection.execute(
                "SELECT 1 FROM sqlite_schema "
                "WHERE name = ? AND type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'",
                (name,),
            ).fetchone()
            if found is None:
                raise DatabaseError("table or view not found")
            quoted = _quote_identifier(name)
            columns: list[ColumnInfo] = [
                ColumnInfo(
                    name=str(row["name"]),
                    type=str(row["type"]),
                    nullable=not bool(row["notnull"]) and not bool(row["pk"]),
                    primary_key=bool(row["pk"]),
                )
                for row in self._connection.execute(f"PRAGMA table_info({quoted})")
            ]
            foreign_keys: list[ForeignKeyInfo] = [
                ForeignKeyInfo(
                    column=str(row["from"]),
                    referenced_table=str(row["table"]),
                    referenced_column=str(row["to"]),
                )
                for row in self._connection.execute(f"PRAGMA foreign_key_list({quoted})")
            ]
            indexes: list[IndexInfo] = []
            for row in self._connection.execute(f"PRAGMA index_list({quoted})"):
                index_name = str(row["name"])
                index_columns = [
                    str(column["name"])
                    for column in self._connection.execute(
                        f"PRAGMA index_info({_quote_identifier(index_name)})"
                    )
                ]
                indexes.append(
                    IndexInfo(name=index_name, unique=bool(row["unique"]), columns=index_columns)
                )
            return TableDescription(
                name=name, columns=columns, foreign_keys=foreign_keys, indexes=indexes
            )
        except DatabaseError:
            raise
        except sqlite3.Error:
            raise DatabaseError("database metadata could not be read") from None

    def run_query(self, sql: str, row_limit: int) -> QueryResult:
        """Execute SQL with a time budget and bounded result materialization."""
        if row_limit < 1:
            raise DatabaseError("row limit must be positive")
        _reject_connection_escapes(sql)
        deadline = time.monotonic() + self._timeout_ms / 1_000
        self._connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1_000)
        try:
            cursor = self._connection.execute(sql)
            columns = [item[0] for item in cursor.description or []]
            raw_rows = cursor.fetchmany(row_limit + 1)
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc).lower():
                raise QueryTimeoutError("query exceeded the configured time limit") from None
            raise DatabaseError("query could not be executed") from None
        except sqlite3.Error:
            raise DatabaseError("query could not be executed") from None
        finally:
            self._connection.set_progress_handler(None, 0)
            with suppress(sqlite3.Error):
                self._connection.execute("PRAGMA query_only = ON")
        truncated = len(raw_rows) > row_limit
        rows = [list(row) for row in raw_rows[:row_limit]]
        message = f"Result truncated at {row_limit} rows." if truncated else None
        return QueryResult(columns=columns, rows=rows, truncated=truncated, message=message)

    def close(self) -> None:
        """Close the database connection."""
        self._connection.close()

    def __enter__(self) -> SQLiteAdapter:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
