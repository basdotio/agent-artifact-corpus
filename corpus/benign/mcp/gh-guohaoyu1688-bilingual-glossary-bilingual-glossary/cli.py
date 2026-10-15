"""Noninteractive CLI with stable JSON envelopes."""

import argparse
import json
import os
import sqlite3
import sys
import tomllib
from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException

from . import __version__
from .core.checker import Checker
from .core.store import Glossary, GlossError


def ok(data):
    return {"ok": True, "data": data, "warnings": []}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise GlossError(message, "ARGUMENT_ERROR")


def parser():
    p = Parser(description="Offline bilingual terminology manager")
    p.add_argument("--data-dir")
    p.add_argument("--config")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--version", action="store_true")
    commands = p.add_subparsers(dest="command")
    add = commands.add_parser("add")
    add.add_argument("--file")
    add.add_argument("--record")
    update = commands.add_parser("update")
    update.add_argument("id")
    update.add_argument("--record", required=True)
    update.add_argument("--expected-updated-at")
    delete = commands.add_parser("delete")
    delete.add_argument("id")
    delete.add_argument("--yes", action="store_true")
    listing = commands.add_parser("list")
    listing.add_argument("--domain")
    listing.add_argument("--status", choices=["draft", "approved"])
    show = commands.add_parser("show")
    show.add_argument("id")
    imp = commands.add_parser("import")
    imp.add_argument("path")
    imp.add_argument("--replace", action="store_true")
    imp.add_argument("--yes", action="store_true")
    export = commands.add_parser("export")
    export.add_argument("--format", choices=["json", "csv", "tbx"], default="json")
    export.add_argument("--out", required=True)
    export.add_argument("--domain")
    export.add_argument("--kb", action="store_true")
    export.add_argument("--no-bom", action="store_true")
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--domain")
    search.add_argument("--lang", choices=["zh", "en"])
    search.add_argument("--limit", type=int, default=10)
    for name in ["check", "fix"]:
        check = commands.add_parser(name)
        check.add_argument("paths", nargs="+")
        check.add_argument("--lang", choices=["zh", "en"])
        check.add_argument("--domain")
        check.add_argument("--write", action="store_true")
        if name == "check":
            check.add_argument("--pair")
            check.add_argument("--fix", action="store_true")
    prompt = commands.add_parser("prompt")
    prompt.add_argument("--text", required=True)
    prompt.add_argument("--domain")
    commands.add_parser("backup")
    commands.add_parser("mcp")
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8872)
    return p


def globals_first(argv):
    front, rest = [], []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in {"--data-dir", "--config"}:
            if i + 1 == len(argv):
                raise GlossError(f"{token} requires a value")
            front += argv[i : i + 2]
            i += 2
        elif token in {"--json", "--quiet", "--version"} or token.startswith(
            ("--data-dir=", "--config=")
        ):
            front.append(token)
            i += 1
        else:
            rest.append(token)
            i += 1
    return front + rest


def main(argv=None):
    raw = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in raw
    try:
        args = parser().parse_args(globals_first(raw))
        code = 0
        if args.version:
            data = {"version": __version__}
        else:
            settings = {}
            if args.config:
                path = Path(args.config)
                if not path.is_file():
                    raise GlossError("Configuration not found", "NOT_FOUND", 3)
                settings = tomllib.loads(path.read_text()).get("gloss", {})
            glossary = Glossary(
                args.data_dir or os.getenv("GLOSS_DATA_DIR") or settings.get("data_dir", "./data"),
                settings.get("timezone", "Asia/Shanghai"),
            )
            checker = Checker(glossary)
            match args.command:
                case "add":
                    if bool(args.file) == bool(args.record):
                        raise GlossError("Use exactly one of --file and --record")
                    data = glossary.add(
                        json.loads(Path(args.file).read_text())
                        if args.file
                        else json.loads(args.record)
                    )
                case "update":
                    data = glossary.update(
                        args.id, json.loads(args.record), args.expected_updated_at
                    )
                case "delete":
                    data = glossary.delete(args.id, args.yes)
                case "list":
                    data = glossary.list(args.domain, args.status)
                case "show":
                    data = glossary.get(args.id)
                case "import":
                    data = glossary.import_file(args.path, args.replace, args.yes)
                case "export":
                    data = glossary.export(
                        args.out, args.format, args.domain, args.kb, not args.no_bom
                    )
                case "search":
                    data = glossary.search(args.query, args.domain, args.lang, args.limit)
                case "check" | "fix":
                    if args.command == "fix" or args.fix:
                        data = checker.fix(args.paths, args.write, args.lang, args.domain)
                    else:
                        if args.write:
                            raise GlossError("--write requires --fix")
                        issues = [
                            issue
                            for path in args.paths
                            for issue in checker.check_file(path, args.pair, args.lang, args.domain)
                        ]
                        data = {"passed": not issues, "issues": issues}
                        code = 1 if issues else 0
                case "prompt":
                    data = checker.prompt(Path(args.text).read_text(encoding="utf-8"), args.domain)
                case "backup":
                    data = glossary.backup()
                case "mcp":
                    from .mcp_server import create_server

                    create_server(glossary).run(transport="stdio")
                    return 0
                case "serve":
                    import uvicorn

                    from .web.app import create_app

                    uvicorn.run(create_app(glossary), host=args.host, port=args.port)
                    return 0
                case _:
                    raise GlossError("A command is required", "ARGUMENT_ERROR")
        if json_mode:
            print(json.dumps(ok(data), ensure_ascii=False))
        elif not args.quiet:
            print(
                data["prompt"]
                if args.command == "prompt"
                else json.dumps(data, ensure_ascii=False, indent=2)
            )
        return code
    except GlossError as exc:
        error = {"ok": False, "error": {"code": exc.code, "message": str(exc)}}
        code = exc.exit_code
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        sqlite3.Error,
        DefusedXmlException,
        ParseError,
    ) as exc:
        error = {"ok": False, "error": {"code": "OPERATION_FAILED", "message": str(exc)}}
        code = 1
    print(json.dumps(error), file=sys.stdout if json_mode else sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
