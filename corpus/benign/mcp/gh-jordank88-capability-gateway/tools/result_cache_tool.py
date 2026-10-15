"""
result_cache_tool.py — tool "result_cache" (the registry name needn't match
the module name): admin surface over _result_cache.py, the shared
gateway-level TTL result cache.

Lets "refresh that number" / "how stale is this?" be normal tool calls:

Modes
-----
stats        Entry counts (total/fresh/expired, per-tool), hit totals,
             default TTL, DB path.
invalidate   Drop entries. tool+args → one entry; tool alone → all entries
             for that tool; neither → everything.
prune        Delete only expired entries (housekeeping; safe anytime).

Usage (CLI)
-----------
  python tools/result_cache_tool.py '{"mode": "stats"}'
  python tools/result_cache_tool.py '{"mode": "invalidate", "tool": "my_report"}'
  python tools/result_cache_tool.py '{"mode": "prune"}'
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for _utils
from _utils import read_args, emit, ok, fail
import _result_cache as _rc


def run(arguments: dict) -> dict:
    mode = (arguments.get("mode") or "stats").strip().lower()

    if mode == "stats":
        return ok(**_rc.stats())

    if mode == "invalidate":
        tool = (arguments.get("tool") or "").strip() or None
        args = arguments.get("args")
        if args is not None and not isinstance(args, dict):
            return fail("'args' must be an object (the original tool args)", "BAD_ARGS")
        if args is not None and not tool:
            return fail("'args' requires 'tool' (args alone can't identify an entry)", "BAD_ARGS")
        deleted = _rc.invalidate(tool, args)
        return ok(deleted=deleted, tool=tool, scoped_to_args=args is not None)

    if mode == "prune":
        return ok(pruned=_rc.prune())

    return fail(f"Unknown mode '{mode}'. Use stats | invalidate | prune.", "BAD_MODE")


if __name__ == "__main__":
    emit(run(read_args({"mode": "stats"})))
