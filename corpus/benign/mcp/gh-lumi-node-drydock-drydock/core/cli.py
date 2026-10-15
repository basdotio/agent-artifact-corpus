"""Shared CLI machinery: one flag vocabulary for every analyzer.

Pre-0.2 the eight analyzers split 4/4 on their own convention -- four defaulted
to JSON and took ``--markdown``, four defaulted to markdown and took ``--json``
-- while the README stated "JSON-first: all tools default to JSON". One of the
markdown-default tools also registered a ``--markdown`` flag it never read, so
the documented ``--output deps.json`` wrote markdown into a ``.json`` file.

Flags are built here from each analyzer's `Option` declarations, so every tool
gets the identical core vocabulary and cannot disagree with the docs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from .output import Reporter, dumps, write_output
from .registry import Analyzer, AnalysisContext, Option
from .walker import WalkPolicy

__all__ = ["build_parser", "run_analyzer", "EXIT_OK", "EXIT_ERROR", "EXIT_USAGE"]

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def build_parser(analyzer: Analyzer, *, prog: str | None = None) -> argparse.ArgumentParser:
    """Build an argparse parser for `analyzer` with the shared vocabulary."""
    parser = argparse.ArgumentParser(
        prog=prog or f"drydock {analyzer.name}",
        description=analyzer.description.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", help="Path to the project root")
    add_common_arguments(parser)
    add_options(parser, analyzer.options)
    return parser


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """The flags every analyzer has, spelled the same way every time."""
    out = parser.add_argument_group("output")
    out.add_argument("--output", "-o", metavar="FILE",
                     help="Write to FILE instead of stdout")
    out.add_argument("--markdown", "-m", action="store_true",
                     help="Render as Markdown (default: JSON)")
    out.add_argument("--compact", "-c", action="store_true",
                     help="Compact JSON, no indentation")
    out.add_argument("--quiet", "-q", action="store_true",
                     help="Suppress progress output on stderr")

    scope = parser.add_argument_group("scope")
    scope.add_argument("--no-tests", dest="include_tests", action="store_false",
                       default=True,
                       help="Exclude files classified as tests from the analysis")
    scope.add_argument("--max-files", type=_positive_int, default=None, metavar="N",
                       help="Stop after N files (partial results are flagged)")
    scope.add_argument("--skip-dir", action="append", default=[], metavar="NAME",
                       help="Additional directory name to skip (repeatable)")
    scope.add_argument("--follow-symlinks", action="store_true",
                       help="Follow symlinked directories (cycle-guarded)")


def add_options(parser: argparse.ArgumentParser, options: Sequence[Option]) -> None:
    """Render an analyzer's `Option` declarations as argparse flags."""
    if not options:
        return
    group = parser.add_argument_group("analyzer options")
    for opt in options:
        kwargs: dict[str, Any] = {"help": opt.help, "default": opt.default,
                                  "dest": opt.name}
        if opt.type is bool:
            kwargs["action"] = "store_true" if not opt.default else "store_false"
            kwargs.pop("default", None)
            kwargs["default"] = opt.default
        else:
            kwargs["type"] = _bounded(opt) if opt.type is int else opt.type
            if opt.choices:
                kwargs["choices"] = list(opt.choices)
            kwargs["metavar"] = opt.name.upper().replace("_", "-")
        group.add_argument(*opt.flags, **kwargs)


def _positive_int(raw: str) -> int:
    """A file limit below 1 can only be a mistake; 0 would analyse nothing."""
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expects an integer, got {raw!r}")
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {value}")
    return value


def _bounded(opt: Option):
    """argparse type that rejects out-of-range numbers with a clear message.

    A negative limit is always a mistake, and silently honouring it produced
    empty analyses that looked like real results.
    """
    def parse(raw: str) -> int:
        try:
            value = int(raw)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{opt.flag} expects an integer, got {raw!r}")
        low = opt.minimum if opt.minimum is not None else 0
        if value < low:
            raise argparse.ArgumentTypeError(
                f"{opt.flag} must be >= {low}, got {value}"
            )
        if opt.maximum is not None and value > opt.maximum:
            raise argparse.ArgumentTypeError(
                f"{opt.flag} must be <= {opt.maximum}, got {value}"
            )
        return value
    parse.__name__ = "int"
    return parse


def policy_from_args(args: argparse.Namespace) -> WalkPolicy:
    policy = WalkPolicy(
        include_tests=getattr(args, "include_tests", True),
        max_files=getattr(args, "max_files", None),
        follow_symlinks=getattr(args, "follow_symlinks", False),
    )
    extra = getattr(args, "skip_dir", None)
    if extra:
        policy = policy.with_extra_skips(extra)
    return policy


def run_analyzer(analyzer: Analyzer, argv: Sequence[str] | None = None,
                 *, prog: str | None = None) -> int:
    """Parse `argv`, run `analyzer`, emit output, return a process exit code.

    Exit status is meaningful: 0 only when the analysis actually succeeded.
    The old `context_compiler` caught every per-section failure into an
    ``{"error": ...}`` blob, printed "ready for AI agent consumption" and
    exited 0 even when all six sections had failed, which made it useless as a
    CI gate.
    """
    parser = build_parser(analyzer, prog=prog)
    args = parser.parse_args(argv)
    reporter = Reporter(quiet=args.quiet)

    root = Path(args.project_path)
    if not root.exists():
        print(f"error: project path not found: {root}", file=sys.stderr)
        return EXIT_USAGE
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return EXIT_USAGE

    ctx = AnalysisContext(root, policy=policy_from_args(args), reporter=reporter)
    opts = {opt.name: getattr(args, opt.name) for opt in analyzer.options}

    reporter.step(f"drydock {analyzer.name}: {ctx.root}")
    try:
        result = analyzer.run(ctx, **opts)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except KeyboardInterrupt:  # pragma: no cover
        print("interrupted", file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:
        print(f"error: {analyzer.name} failed: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return EXIT_ERROR

    text = analyzer.to_markdown(result) if args.markdown else dumps(
        result, compact=args.compact
    )
    write_output(text, args.output, reporter)

    return EXIT_ERROR if _has_failures(result) else EXIT_OK


def _has_failures(result: Mapping[str, Any]) -> bool:
    """True if the analyzer reported a hard failure anywhere in its result."""
    if not isinstance(result, Mapping):
        return False
    if result.get("error"):
        return True
    errors = result.get("errors")
    if isinstance(errors, (list, tuple)) and errors:
        return True
    sections = result.get("sections")
    if isinstance(sections, Mapping):
        failed = [k for k, v in sections.items()
                  if isinstance(v, Mapping) and v.get("error")]
        # A compiled context is a failure only when nothing at all succeeded.
        return len(failed) == len(sections) and bool(sections)
    return False
