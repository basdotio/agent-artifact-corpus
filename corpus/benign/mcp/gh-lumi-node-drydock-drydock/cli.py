"""``drydock`` command-line entry point.

Subcommands are generated from the analyzer registry, so a third-party
analyzer installed via the ``drydock.analyzers`` entry point appears in
``drydock --help`` with no changes here.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__
from .core.cli import EXIT_OK, EXIT_USAGE, run_analyzer
from .core.registry import available

__all__ = ["main"]


def _print_analyzers() -> None:
    rows = [(name, a.summary) for name, a in available().items()]
    width = max((len(n) for n, _ in rows), default=0)
    print("Analyzers:")
    for name, summary in rows:
        print(f"  {name.ljust(width)}  {summary}")


def _print_languages() -> None:
    from .langs import language_registry

    rows = language_registry().support_matrix()
    width = max((len(r["language"]) for r in rows), default=0)
    print("Languages:")
    for row in rows:
        print(f"  {row['language'].ljust(width)}  {row['fidelity']:<6} {row['extensions']}")


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(f"drydock {__version__} — analyze, decompose and reconstruct codebases\n")
        print("Usage: drydock <analyzer> <project_path> [options]")
        print("       drydock <analyzer> --help")
        print("       drydock extract <project_path> [selection] [options]")
        print("       drydock extract --help")
        print("       drydock catalog <subcommand> [options]")
        print("       drydock catalog --help")
        print("       drydock list | languages | mcp\n")
        _print_analyzers()
        print()
        print("Also: `drydock mcp` runs the MCP server over stdio.")
        return EXIT_OK

    command, rest = argv[0], argv[1:]

    if command in ("-V", "--version", "version"):
        print(f"drydock {__version__}")
        return EXIT_OK

    if command == "list":
        _print_analyzers()
        return EXIT_OK

    if command == "languages":
        _print_languages()
        return EXIT_OK

    if command == "mcp":
        from .mcp import serve

        return serve(rest)

    if command == "extract":
        from .extract.cli import main as extract_main

        return extract_main(rest)

    if command == "catalog":
        from .catalog.cli import main as catalog_main

        return catalog_main(rest)

    analyzers = available()
    analyzer = analyzers.get(command)
    if analyzer is None:
        print(f"error: unknown analyzer '{command}'", file=sys.stderr)
        print(f"available: {', '.join(analyzers)}", file=sys.stderr)
        return EXIT_USAGE

    return run_analyzer(analyzer, rest, prog=f"drydock {command}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
