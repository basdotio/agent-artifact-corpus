"""Headless CLI; common flags may appear before or after subcommands."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfoNotFoundError

import yaml

from . import __version__
from .config import settings
from .core.importer import apply_import, preview
from .core.store import Conflict, Hub, NotFound


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def parser() -> Parser:
    parser = Parser(prog="hub", description="Local YAML-driven SQLite data hub")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Initialize built-in schemas and apply additive migrations")
    commands.add_parser("tables", help="List tables and row counts")
    schema = commands.add_parser("schema", help="Describe effective schema and sensitivity")
    schema.add_argument("table")
    imp = commands.add_parser("import", help="Preview mappings; use --yes to write validated rows")
    imp.add_argument("path")
    imp.add_argument("--table", required=True)
    imp.add_argument("--map")
    imp.add_argument("--sheet")
    imp.add_argument("--dry-run", action="store_true")
    imp.add_argument("--yes", action="store_true")
    imp.add_argument("--expected-sha1")
    query = commands.add_parser("query", help="Read masked rows with safe comparisons")
    query.add_argument("table")
    query.add_argument("--where")
    query.add_argument("--fields")
    query.add_argument("--search")
    query.add_argument("--limit", type=int, default=50)
    query.add_argument("--offset", type=int, default=0)
    for command in ("add", "update"):
        child = commands.add_parser(command, help="Write a record and audit it")
        child.add_argument("table")
        if command == "update":
            child.add_argument("id")
            child.add_argument("--expected-updated-at")
        child.add_argument("--data", required=True, help="JSON object of business fields")
    delete = commands.add_parser("delete", help="Delete a row, preserving reversible audit history")
    delete.add_argument("table")
    delete.add_argument("id")
    delete.add_argument("--yes", action="store_true")
    history = commands.add_parser("history", help="Read masked change history")
    history.add_argument("--table")
    history.add_argument("--row-id")
    history.add_argument("--limit", type=int, default=100)
    revert = commands.add_parser("revert", help="Reverse a change if no later write conflicts")
    revert.add_argument("change_id")
    revert.add_argument("--yes", action="store_true")
    due = commands.add_parser("due", help="Read upcoming and overdue document/important dates")
    due.add_argument("--within", default="30d")
    export = commands.add_parser("export", help="Export a table as masked JSON or CSV")
    export.add_argument("table")
    export.add_argument("--format", choices=["json", "csv"], default="json")
    export.add_argument("--out", required=True)
    export.add_argument("--where")
    export.add_argument("--search")
    export.add_argument("--utf8", action="store_true")
    backup = commands.add_parser(
        "backup", help="Write a dated ZIP of database and effective schemas"
    )
    backup.add_argument("--out")
    serve = commands.add_parser("serve", help="Start local Web and REST API")
    serve.add_argument("--host", choices=["127.0.0.1", "localhost", "::1"], default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8766)
    commands.add_parser("mcp", help="Run official FastMCP over stdio")
    return parser


def execute(args: argparse.Namespace, hub: Hub, actor: str, reveal: bool) -> Any:
    cmd = args.command
    if cmd == "init":
        return {"database": str(hub.path), "schemas": str(hub.schema_dir), "tables": hub.tables()}
    if cmd == "tables":
        return hub.tables()
    if cmd == "schema":
        return hub.describe(args.table, reveal)
    if cmd == "import":
        mapping = json.loads(Path(args.map).read_text(encoding="utf-8")) if args.map else None
        if args.dry_run or not args.yes:
            return preview(hub, args.path, args.table, mapping, args.sheet, reveal)
        return apply_import(
            hub, args.path, args.table, mapping, args.sheet, True, actor, args.expected_sha1
        )
    if cmd == "query":
        return hub.query(
            args.table,
            args.where,
            args.fields.split(",") if args.fields else None,
            args.limit,
            args.offset,
            args.search,
            reveal,
        )
    if cmd == "add":
        return hub.insert(args.table, json.loads(args.data), actor, reveal)
    if cmd == "update":
        return hub.update(
            args.table, args.id, json.loads(args.data), actor, reveal, args.expected_updated_at
        )
    if cmd == "delete":
        return hub.delete(args.table, args.id, args.yes, actor)
    if cmd == "history":
        return hub.history(args.table, args.row_id, args.limit, reveal)
    if cmd == "revert":
        return hub.revert(args.change_id, args.yes, actor, reveal)
    if cmd == "due":
        return hub.due(args.within, reveal)
    if cmd == "export":
        return hub.export(
            args.table, args.out, args.format, args.where, reveal, not args.utf8, args.search
        )
    if cmd == "backup":
        return hub.backup(args.out)
    raise ValueError(f"unsupported command: {cmd}")


def main(argv: list[str] | None = None) -> int:
    try:
        common = Parser(add_help=False, allow_abbrev=False)
        for option in ("data-dir", "schema-dir", "config", "actor"):
            common.add_argument("--" + option)
        for option in ("json", "quiet", "version", "reveal", "progress"):
            common.add_argument("--" + option, action="store_true")
        global_args, remaining = common.parse_known_args(sys.argv[1:] if argv is None else argv)
        if global_args.version:
            print(__version__)
            return 0
        if not remaining or remaining == ["--help"]:
            parser().print_help()
            print(
                "\nGlobal: --data-dir DIR --schema-dir DIR --config TOML --actor NAME --json --quiet --reveal --progress --version"
            )
            return 0
        args = parser().parse_args(remaining)
        config = settings(global_args.data_dir, global_args.config, global_args.schema_dir)
        hub = Hub(config["data_dir"], config["schema_dir"], config["timezone"])
        actor = global_args.actor or config["actor"]
        if args.command == "serve":
            import uvicorn

            from .web.app import create_app

            uvicorn.run(create_app(hub, config["token"]), host=args.host, port=args.port)
            return 0
        if args.command == "mcp":
            from .mcp_server import create_server

            create_server(hub, actor).run(transport="stdio")
            return 0
        if global_args.progress:
            print(f"Running {args.command}...", file=sys.stderr)
        data = execute(args, hub, actor, global_args.reveal)
        if global_args.json or not global_args.quiet:
            print(
                json.dumps(
                    {"ok": True, "data": data, "warnings": []}, ensure_ascii=False, default=str
                )
            )
        return 0
    except NotFound as exc:
        return failure("NOT_FOUND", str(exc), 3)
    except (Conflict, sqlite3.IntegrityError) as exc:
        return failure("CONFLICT", str(exc), 2)
    except (ValueError, TypeError, KeyError, yaml.YAMLError, ZoneInfoNotFoundError) as exc:
        return failure("INVALID_ARGUMENT", str(exc), 2)
    except (OSError, sqlite3.Error) as exc:
        return failure("IO_ERROR", str(exc), 1)


def failure(code: str, message: str, status: int) -> int:
    print(
        json.dumps({"ok": False, "error": {"code": code, "message": message}}, ensure_ascii=False)
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
