"""Official FastMCP v1 adapter with explicit side effects and masking defaults."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import settings
from .core.store import Conflict, Hub, NotFound


def response(function: Callable[..., Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        return {"ok": True, "data": function(*args, **kwargs), "warnings": []}
    except NotFound as exc:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": str(exc)}}
    except (Conflict, sqlite3.IntegrityError) as exc:
        return {"ok": False, "error": {"code": "CONFLICT", "message": str(exc)}}
    except (ValueError, TypeError) as exc:
        return {"ok": False, "error": {"code": "INVALID_ARGUMENT", "message": str(exc)}}
    except (OSError, sqlite3.Error) as exc:
        return {"ok": False, "error": {"code": "IO_ERROR", "message": str(exc)}}


def create_server(hub: Hub, actor: str = "mcp") -> FastMCP:
    server = FastMCP("personal-data-hub")

    @server.tool()
    def list_tables() -> dict[str, Any]:
        """Read available table names, labels, columns and row counts."""
        return response(hub.tables)

    @server.tool()
    def describe_table(table: str, reveal: bool = False) -> dict[str, Any]:
        """Read effective YAML schema; sensitive default values are masked unless reveal=true."""
        return response(hub.describe, table, reveal)

    @server.tool()
    def query_rows(
        table: str,
        where: str | None = None,
        fields: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        reveal: bool = False,
    ) -> dict[str, Any]:
        """Read rows, masked by default. where: FIELD OP VALUE joined by AND.

        Supported operators: = != > < >= <= ~. Values are parameterized. Limit 1..10000.
        reveal=true explicitly exposes sensitive fields and enables filtering them.
        """
        return response(hub.query, table, where, fields, limit, offset, search, reveal)

    @server.tool()
    def insert_row(table: str, data: dict[str, Any], reveal: bool = False) -> dict[str, Any]:
        """WRITE: insert schema-validated business fields and an audit event; result is masked by default."""
        return response(hub.insert, table, data, actor, reveal)

    @server.tool()
    def update_row(
        table: str,
        id: str,
        data: dict[str, Any],
        reveal: bool = False,
        expected_updated_at: str | None = None,
    ) -> dict[str, Any]:
        """WRITE: update supplied fields and audit before/after values. Omitted fields survive.

        Optional expected_updated_at rejects stale edits. Back up before overwriting useful data.
        """
        return response(hub.update, table, id, data, actor, reveal, expected_updated_at)

    @server.tool()
    def delete_row(table: str, id: str, confirm: bool = False) -> dict[str, Any]:
        """DELETE: remove a record only with confirm=true, preserving its reversible audit snapshot.

        Back up first. Audit history retains deleted sensitive data.
        """
        return response(hub.delete, table, id, confirm, actor)

    @server.tool()
    def list_due_items(within: str = "30d", reveal: bool = False) -> dict[str, Any]:
        """Read upcoming and overdue documents/important dates, within a duration such as 30d."""
        return response(hub.due, within, reveal)

    @server.tool()
    def get_history(
        table: str | None = None, row_id: str | None = None, limit: int = 100, reveal: bool = False
    ) -> dict[str, Any]:
        """Read change history with field-sensitive masking for both before/after snapshots."""
        return response(hub.history, table, row_id, limit, reveal)

    return server


def main() -> None:
    config = settings()
    create_server(Hub(config["data_dir"], config["schema_dir"], config["timezone"])).run(
        transport="stdio"
    )


if __name__ == "__main__":
    main()
