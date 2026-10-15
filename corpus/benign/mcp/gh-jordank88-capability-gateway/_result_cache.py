"""
_result_cache.py — shared TTL result cache for tool runs.

NOT a tool (no run()). A shared library, same pattern as _utils.py: the
gateway wires it into run_tool for MCP-invoked calls, and a tool that other
tools import directly (bypassing the gateway) can call it itself from inside
run(). One storage, one key scheme, so a gateway-path call and an
internal-import call round-trip through the same cache row.

Storage: .cache/tool_result_cache.db (SQLite, WAL mode — gateway calls run
in a ThreadPoolExecutor and internal callers may be a separate process, so
concurrent readers/writers are the normal case, not an edge case).

Policy:
  * Opt-in only — nothing is cached unless the caller asks for it.
  * Default TTL 16 hours ("run a report every day, get updated numbers");
    RESULT_CACHE_TTL env var overrides; 0 disables read AND write globally.
  * Only success:true results are ever stored. Never failures, never
    results carrying _image_b64 (huge, and captures are point-in-time).
  * Raw args are never stored — only their hash plus a redacted preview
    (args can contain secrets; same lesson as the gateway audit log).
  * Cross-session sharing is by design: the DB outlives any one process.

Usage:
    import _result_cache as rc

    cached = rc.get("my_report", args)          # None on miss/expired
    if cached is None:
        result = _do_real_work(args)
        rc.put("my_report", args, result)       # no-op unless success:true
    rc.invalidate(tool="my_report")             # or invalidate() for all
    rc.stats()
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / ".cache" / "tool_result_cache.db"

# Default TTL: 16 hours — same-day repeats hit cache, a daily report is
# always fresh. RESULT_CACHE_TTL=0 disables the cache entirely.
DEFAULT_TTL_S = int(os.environ.get("RESULT_CACHE_TTL", 16 * 3600))

# Gateway/meta args that never identify the data being asked for.
_META_ARGS = frozenset({"force_refresh", "timeout_s", "debug"})

# Redaction for the stored args preview (mirrors gateway_server._summarize —
# kept local to avoid importing the gateway from a shared library).
_REDACT_KEY_HINTS = ("password", "secret", "token", "credential", "key")


def _redacted_preview(args: dict, max_len: int = 200) -> str:
    if not isinstance(args, dict):
        s = str(args)
        return s[:max_len] + ("..." if len(s) > max_len else "")
    safe = {
        k: ("<redacted>" if any(h in k.lower() for h in _REDACT_KEY_HINTS) else v)
        for k, v in args.items()
    }
    s = json.dumps(safe, default=str)
    return s[:max_len] + ("..." if len(s) > max_len else "")


def cache_key(tool: str, args: dict) -> str:
    """sha256 of tool name + canonical (sorted, meta-stripped) args."""
    relevant = {k: v for k, v in (args or {}).items() if k not in _META_ARGS}
    payload = json.dumps(relevant, sort_keys=True, default=str)
    return hashlib.sha256(f"{tool}\n{payload}".encode()).hexdigest()


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            cache_key    TEXT PRIMARY KEY,
            tool         TEXT NOT NULL,
            args_preview TEXT,
            result_json  TEXT NOT NULL,
            cached_at    REAL NOT NULL,
            ttl_s        INTEGER NOT NULL,
            hit_count    INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_results_tool ON results(tool)")
    return conn


def get(tool: str, args: dict, ttl_s: int | None = None) -> dict | None:
    """
    Return the cached result for (tool, args) if present and fresh, else None.

    ttl_s=None (normal case) uses the TTL the entry was stored with.
    Passing ttl_s applies a caller-side freshness bound instead — an entry
    older than the caller's bound misses even if its stored TTL says fresh.
    Returned dicts are tagged _from_cache=true, _cached_at, _cache_age_s.
    """
    if DEFAULT_TTL_S <= 0:
        return None
    try:
        conn = _conn()
    except Exception:
        return None  # cache must never break the real call
    try:
        row = conn.execute(
            "SELECT * FROM results WHERE cache_key=?", (cache_key(tool, args),)
        ).fetchone()
        if row is None:
            return None
        age = time.time() - row["cached_at"]
        effective_ttl = ttl_s if ttl_s is not None else row["ttl_s"]
        if effective_ttl <= 0 or age > effective_ttl:
            return None
        try:
            result = json.loads(row["result_json"])
        except Exception:
            return None
        conn.execute(
            "UPDATE results SET hit_count=hit_count+1 WHERE cache_key=?",
            (row["cache_key"],),
        )
        conn.commit()
        result["_from_cache"] = True
        result["_cached_at"] = row["cached_at"]
        result["_cache_age_s"] = int(age)
        return result
    except Exception:
        return None
    finally:
        conn.close()


def put(tool: str, args: dict, result: dict, ttl_s: int | None = None) -> bool:
    """
    Store a result. Returns True if stored, False if skipped (failure
    results, image payloads, cache disabled, or any storage error — all
    silently non-fatal by design: caching must never break the real call).
    """
    if DEFAULT_TTL_S <= 0:
        return False
    if not isinstance(result, dict) or result.get("success") is not True:
        return False
    if "_image_b64" in result:
        return False
    # Store a clean copy — cache-metadata tags from a prior layer must not
    # be re-served as if they described THIS entry.
    clean = {k: v for k, v in result.items()
             if k not in ("_from_cache", "_cached_at", "_cache_age_s")}
    try:
        payload = json.dumps(clean, default=str)
    except Exception:
        return False
    try:
        conn = _conn()
    except Exception:
        return False
    try:
        conn.execute(
            "INSERT INTO results (cache_key, tool, args_preview, result_json, cached_at, ttl_s, hit_count) "
            "VALUES (?,?,?,?,?,?,0) "
            "ON CONFLICT(cache_key) DO UPDATE SET args_preview=excluded.args_preview, "
            "result_json=excluded.result_json, cached_at=excluded.cached_at, "
            "ttl_s=excluded.ttl_s, hit_count=0",
            (cache_key(tool, args), tool, _redacted_preview(args), payload,
             time.time(), ttl_s if ttl_s is not None else DEFAULT_TTL_S),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def invalidate(tool: str | None = None, args: dict | None = None) -> int:
    """
    Remove entries. args+tool → that one entry; tool alone → all entries for
    that tool; neither → everything. Returns number of rows deleted.
    """
    try:
        conn = _conn()
    except Exception:
        return 0
    try:
        if tool and args is not None:
            cur = conn.execute("DELETE FROM results WHERE cache_key=?",
                               (cache_key(tool, args),))
        elif tool:
            cur = conn.execute("DELETE FROM results WHERE tool=?", (tool,))
        else:
            cur = conn.execute("DELETE FROM results")
        conn.commit()
        return cur.rowcount
    except Exception:
        return 0
    finally:
        conn.close()


def stats() -> dict:
    """Entry counts (total + per-tool), hits, and freshness snapshot."""
    try:
        conn = _conn()
    except Exception:
        return {"entries": 0, "tools": {}, "total_hits": 0, "fresh_entries": 0}
    try:
        now = time.time()
        rows = conn.execute(
            "SELECT tool, cached_at, ttl_s, hit_count FROM results"
        ).fetchall()
        tools: dict[str, int] = {}
        fresh = 0
        hits = 0
        for r in rows:
            tools[r["tool"]] = tools.get(r["tool"], 0) + 1
            hits += r["hit_count"]
            if now - r["cached_at"] <= r["ttl_s"]:
                fresh += 1
        return {
            "entries": len(rows),
            "fresh_entries": fresh,
            "expired_entries": len(rows) - fresh,
            "total_hits": hits,
            "tools": dict(sorted(tools.items())),
            "default_ttl_s": DEFAULT_TTL_S,
            "db_path": str(_DB_PATH),
        }
    except Exception:
        return {"entries": 0, "tools": {}, "total_hits": 0, "fresh_entries": 0}
    finally:
        conn.close()


def prune() -> int:
    """Delete expired entries. Returns rows removed. Safe to run anytime."""
    try:
        conn = _conn()
    except Exception:
        return 0
    try:
        cur = conn.execute(
            "DELETE FROM results WHERE ? - cached_at > ttl_s", (time.time(),)
        )
        conn.commit()
        return cur.rowcount
    except Exception:
        return 0
    finally:
        conn.close()
