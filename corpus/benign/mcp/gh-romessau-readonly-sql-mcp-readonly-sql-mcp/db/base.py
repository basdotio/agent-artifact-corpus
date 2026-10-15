"""Shared database adapter contracts."""

from __future__ import annotations

from typing import Protocol

from typing_extensions import TypedDict


class ColumnInfo(TypedDict):
    name: str
    type: str
    nullable: bool
    primary_key: bool


class ForeignKeyInfo(TypedDict):
    column: str
    referenced_table: str
    referenced_column: str


class IndexInfo(TypedDict):
    name: str
    unique: bool
    columns: list[str]


class TableInfo(TypedDict):
    name: str
    type: str
    row_count: int | None


class TableDescription(TypedDict):
    name: str
    columns: list[ColumnInfo]
    foreign_keys: list[ForeignKeyInfo]
    indexes: list[IndexInfo]


class QueryResult(TypedDict):
    columns: list[str]
    rows: list[list[object]]
    truncated: bool
    message: str | None


class DatabaseAdapter(Protocol):
    """Operations exposed by a read-only database backend."""

    def list_tables(self) -> list[TableInfo]: ...

    def describe_table(self, name: str) -> TableDescription: ...

    def run_query(self, sql: str, row_limit: int) -> QueryResult: ...

    def close(self) -> None: ...
