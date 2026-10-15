"""Noninteractive pte command line; structured results on stdout."""

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path

from . import __version__
from .core.errors import PDFError, failure, success
from .core.extract import extract_tables, inspect_pdf, render_page
from .core.templates import Templates


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PDFError("invalid_arguments", message, 2)


def global_first(args: list[str]) -> list[str]:
    globals_, remaining = [], []
    index = 0
    while index < len(args):
        item = args[index]
        if item == "--":
            remaining.extend(args[index:])
            break
        if item in {"--data-dir", "--config"}:
            globals_.append(item)
            index += 1
            if index < len(args):
                globals_.append(args[index])
        elif item in {"--json", "--quiet", "--version", "--progress"} or item.startswith(
            ("--data-dir=", "--config=")
        ):
            globals_.append(item)
        else:
            remaining.append(item)
        index += 1
    return globals_ + remaining


def add_options(command: argparse.ArgumentParser) -> None:
    command.add_argument("--pages")
    command.add_argument("--engine", choices=["auto", "plumber", "camelot"], default="auto")
    command.add_argument("--ocr", action="store_true")
    command.add_argument("--merge-pages", action="store_true")
    command.add_argument("--fill-merged", choices=["none", "down", "right"], default="none")
    command.add_argument("--header-rows", type=int, default=1)
    command.add_argument("--area", help="x0,top,x1,bottom in PDF points, top-left origin")
    command.add_argument("--columns", help="Comma-separated x coordinates, including outer edges")
    command.add_argument("--trim-top", type=float, default=0)
    command.add_argument("--trim-bottom", type=float, default=0)
    command.add_argument("--exclude-text", action="append", default=[])
    command.add_argument("--keep-numbers", action="store_true")
    command.add_argument(
        "--compare", action="store_true", help="Compare plumber and Camelot raw tables"
    )
    command.add_argument("--camelot-flavor", choices=["lattice", "stream"], default="lattice")


def parser() -> Parser:
    root = Parser(description="Local PDF tables with geometric review and provenance")
    root.add_argument("--data-dir")
    root.add_argument("--config")
    root.add_argument("--json", action="store_true")
    root.add_argument("--quiet", action="store_true")
    root.add_argument("--progress", action="store_true")
    root.add_argument("--version", action="store_true")
    commands = root.add_subparsers(dest="command")
    extract = commands.add_parser("extract")
    extract.add_argument("path")
    extract.add_argument("--out", help="Output directory; omit to return JSON tables only")
    extract.add_argument("--format", choices=["csv", "xlsx", "json"], default="csv")
    extract.add_argument("--utf8", action="store_true", help="CSV without Excel BOM")
    add_options(extract)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("path")
    render = commands.add_parser("render")
    render.add_argument("path")
    render.add_argument("--page", type=int, default=1)
    render.add_argument("--scale", type=float, default=1.5)
    render.add_argument("--out", required=True)
    template = commands.add_parser("template")
    sub = template.add_subparsers(dest="template_command", required=True)
    save = sub.add_parser("save")
    save.add_argument("name")
    save.add_argument("--from-file", help="Load options from JSON instead of flags")
    save.add_argument("--yes", action="store_true", help="Replace an existing template")
    add_options(save)
    sub.add_parser("list")
    show = sub.add_parser("show")
    show.add_argument("name")
    delete = sub.add_parser("delete")
    delete.add_argument("name")
    delete.add_argument("--yes", action="store_true")
    apply = sub.add_parser("apply")
    apply.add_argument("name")
    apply.add_argument("paths", nargs="+")
    apply.add_argument("--out", required=True)
    apply.add_argument("--format", choices=["csv", "xlsx", "json"], default="csv")
    export = commands.add_parser("export")
    export.add_argument("--format", choices=["json", "csv"], default="json")
    export.add_argument("--out", required=True)
    export.add_argument("--utf8", action="store_true")
    importing = commands.add_parser("import")
    importing.add_argument("path")
    backup = commands.add_parser("backup")
    backup.add_argument("--out")
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8766)
    serve.add_argument("--pdf", help="Initial local PDF shown in the review UI")
    commands.add_parser("mcp")
    return root


def options(args: argparse.Namespace) -> dict:
    result = {
        name: getattr(args, name)
        for name in (
            "pages",
            "engine",
            "ocr",
            "merge_pages",
            "fill_merged",
            "header_rows",
            "trim_top",
            "trim_bottom",
            "exclude_text",
            "compare",
            "camelot_flavor",
        )
    }
    result["normalize_numbers"] = not args.keep_numbers
    for name in ("area", "columns"):
        result[name] = (
            [float(value) for value in getattr(args, name).split(",")]
            if getattr(args, name)
            else None
        )
    return result


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(global_first(list(sys.argv[1:] if argv is None else argv)))
        if args.version:
            print(json.dumps(success({"version": __version__})))
            return 0
        if not args.command:
            raise PDFError("invalid_arguments", "A subcommand is required; use --help", 2)
        config = {}
        if args.config:
            with Path(args.config).open("rb") as file:
                config = tomllib.load(file)
        directory = args.data_dir or os.getenv("PTE_DATA_DIR") or config.get("data_dir", "data")
        if args.command == "extract":
            progress = (
                (lambda text: print(text, file=sys.stderr))
                if args.progress and not args.quiet
                else None
            )
            result = extract_tables(
                args.path,
                out=args.out,
                format=args.format,
                bom=not args.utf8,
                progress=progress,
                **options(args),
            )
        elif args.command == "inspect":
            result = inspect_pdf(args.path)
        elif args.command == "render":
            output = Path(args.out)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(render_page(args.path, args.page, args.scale))
            result = {"path": str(output.resolve())}
        elif args.command in {"template", "export", "import", "backup"}:
            store = Templates(directory, config.get("timezone", "Asia/Shanghai"))
            if args.command == "template":
                if args.template_command == "save":
                    selected = (
                        json.loads(Path(args.from_file).read_text())
                        if args.from_file
                        else options(args)
                    )
                    result = store.save(args.name, selected, replace=args.yes)
                elif args.template_command == "list":
                    result = store.list()
                elif args.template_command == "show":
                    result = {"name": args.name, "options": store.get(args.name)}
                elif args.template_command == "delete":
                    result = store.delete(args.name, args.yes)
                else:
                    result = store.apply(args.name, args.paths, args.out, args.format)
            elif args.command == "export":
                result = store.export(args.out, args.format, not args.utf8)
            elif args.command == "import":
                result = store.import_file(args.path)
            else:
                result = store.backup(args.out)
        elif args.command == "serve":
            from .web.server import serve

            serve(args.host, args.port, args.pdf, args.quiet)
            return 0
        else:
            from .mcp_server import build_server

            build_server().run(transport="stdio")
            return 0
        print(json.dumps(success(result), ensure_ascii=False, allow_nan=False))
        return 0
    except PDFError as error:
        print(json.dumps(failure(error)))
        return error.exit_code
    except FileNotFoundError as error:
        print(json.dumps(failure(PDFError("not_found", str(error), 3))))
        return 3
    except (ValueError, TypeError, KeyError) as error:
        print(json.dumps(failure(PDFError("invalid_input", str(error), 2))))
        return 2
    except OSError as error:
        print(json.dumps(failure(PDFError("operation_failed", str(error)))))
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
