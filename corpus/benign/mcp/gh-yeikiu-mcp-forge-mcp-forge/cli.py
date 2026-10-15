"""Command line interface: ``mcp-forge new`` / ``doctor`` / ``templates``."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .doctor import format_report, run_checks
from .scaffold import available_templates, generate

PRO_HINT = (
    "Pro pack (extra templates, conformance suite, CI, hardening guide): "
    "https://github.com/yeikiu/mcp-forge#pro"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-forge",
        description="Build and check Model Context Protocol servers in Python.",
    )
    parser.add_argument("--version", action="version", version=f"mcp-forge {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="generate a new MCP server project")
    new.add_argument("name", help="project name, e.g. weather-mcp")
    new.add_argument("-t", "--template", default="basic", help="template to use (default: basic)")
    new.add_argument("-o", "--out", default=".", help="where to create the project")
    new.add_argument("-d", "--description", default="An MCP server built with mcp-forge.")
    new.add_argument("-a", "--author", default="")
    new.add_argument("--force", action="store_true", help="write into a non-empty directory")

    doctor = sub.add_parser("doctor", help="run a protocol check-up against an MCP server")
    doctor.add_argument("server_command", nargs=argparse.REMAINDER,
                        help="the server command, e.g. -- python server.py")
    doctor.add_argument("--cwd", default=None, help="working directory for the server")
    doctor.add_argument("--env", action="append", default=[], metavar="KEY=VALUE",
                        help="extra environment variable for the server (repeatable)")
    doctor.add_argument("--timeout", type=float, default=20.0)

    sub.add_parser("templates", help="list available templates")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "templates":
        for name in available_templates():
            print(name)
        print(f"\n{PRO_HINT}")
        return 0

    if args.command == "new":
        try:
            files = generate(
                args.name,
                Path(args.out).resolve(),
                template=args.template,
                description=args.description,
                author=args.author,
                force=args.force,
            )
        except (FileNotFoundError, FileExistsError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        root = Path(args.out).resolve()
        for path in files:
            print(f"  created {path.relative_to(root)}")
        print(f"\n{len(files)} files written. Next:")
        print(f"  cd {Path(files[0]).parent.name if len(files) == 1 else args.name}")
        print('  pip install -e ".[dev]" && pytest -q')
        return 0

    if args.command == "doctor":
        command = [part for part in args.server_command if part != "--"]
        if not command:
            print("error: give me a server command, e.g. mcp-forge doctor -- python server.py",
                  file=sys.stderr)
            return 2
        env = dict(os.environ)
        for pair in args.env:
            key, _, value = pair.partition("=")
            env[key] = value
        checks = run_checks(command, cwd=args.cwd, env=env, timeout=args.timeout)
        print(format_report(command, checks))
        return 1 if any(c.status == "fail" for c in checks) else 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
