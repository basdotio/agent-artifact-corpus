"""Output and progress reporting.

One rule: **stdout carries the payload and nothing else.**

Every pre-0.2 analyzer printed its progress chatter to stdout ahead of the
JSON, so ``python boundary_detector.py . > out.json`` produced a file that
would not parse. The MCP server carried a `redirect_stdout` shim purely to work
around it; the CLI got no such courtesy. Progress goes to stderr here, which
makes the shim unnecessary and piping work.
"""

from __future__ import annotations

import dataclasses
import enum
import json
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

__all__ = ["Reporter", "to_jsonable", "dumps", "write_output"]


class Reporter:
    """Progress messages, always on stderr, silenced by ``--quiet``."""

    def __init__(self, *, quiet: bool = False, stream: TextIO | None = None) -> None:
        self.quiet = quiet
        self._stream = stream if stream is not None else sys.stderr

    def step(self, message: str) -> None:
        if not self.quiet:
            print(message, file=self._stream, flush=True)

    def warn(self, message: str) -> None:
        # Warnings survive --quiet: they explain why output looks thin.
        print(f"warning: {message}", file=self._stream, flush=True)

    def sub(self, message: str) -> None:
        self.step(f"  {message}")


def to_jsonable(obj: Any) -> Any:
    """Convert dataclasses, sets, Paths and enums into JSON-safe values.

    Sets are sorted rather than listed in iteration order, so identical input
    produces byte-identical output -- diffable, cacheable, and testable.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_jsonable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(to_jsonable(v) for v in obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def dumps(data: Any, *, compact: bool = False) -> str:
    return json.dumps(
        to_jsonable(data),
        indent=None if compact else 2,
        separators=(",", ":") if compact else None,
        sort_keys=False,
        ensure_ascii=False,
    )


def write_output(
    text: str,
    destination: str | Path | None,
    reporter: Reporter,
    *,
    summary: Callable[[], str] | None = None,
) -> None:
    """Write to a file, or to stdout when no destination is given."""
    if destination:
        path = Path(destination)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        reporter.step(f"wrote {path} ({len(text):,} chars)")
        if summary:
            reporter.sub(summary())
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
