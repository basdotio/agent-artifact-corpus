"""Tests for result_cache_tool.py — admin interface (stats/invalidate/prune)
over _result_cache.py.

Relies on the autouse `_isolate_caches` fixture in conftest.py, which points
_result_cache._DB_PATH at a per-test temp DB — safe to exercise directly.
"""

import sys
import time
from pathlib import Path

import pytest

_TOOLS_DIR = Path(__file__).parent.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from tools import result_cache_tool  # noqa: E402
import _result_cache as _rc  # noqa: E402


class TestStats:
    def test_stats_on_empty_cache(self):
        result = result_cache_tool.run({"mode": "stats"})
        assert result["success"] is True
        assert result["entries"] == 0
        assert result["tools"] == {}

    def test_stats_reflects_populated_entries(self):
        _rc.put("my_report", {"mode": "active_stores"}, {"success": True, "count": 5})
        _rc.put("my_report", {"mode": "conversions"}, {"success": True, "count": 1})
        _rc.put("reference_lookup", {"q": "fireball"}, {"success": True, "text": "..."})

        result = result_cache_tool.run({"mode": "stats"})
        assert result["success"] is True
        assert result["entries"] == 3
        assert result["tools"]["my_report"] == 2
        assert result["tools"]["reference_lookup"] == 1
        assert result["fresh_entries"] == 3


class TestInvalidate:
    def test_invalidate_single_entry_by_tool_and_args(self):
        _rc.put("my_report", {"mode": "active_stores"}, {"success": True, "count": 5})
        _rc.put("my_report", {"mode": "conversions"}, {"success": True, "count": 1})

        result = result_cache_tool.run({
            "mode": "invalidate", "tool": "my_report", "args": {"mode": "active_stores"},
        })
        assert result["success"] is True
        assert result["deleted"] == 1
        assert result["scoped_to_args"] is True
        remaining = result_cache_tool.run({"mode": "stats"})
        assert remaining["tools"]["my_report"] == 1

    def test_invalidate_all_entries_for_a_tool(self):
        _rc.put("my_report", {"mode": "active_stores"}, {"success": True, "count": 5})
        _rc.put("my_report", {"mode": "conversions"}, {"success": True, "count": 1})
        _rc.put("reference_lookup", {"q": "fireball"}, {"success": True, "text": "..."})

        result = result_cache_tool.run({"mode": "invalidate", "tool": "my_report"})
        assert result["deleted"] == 2
        assert result["scoped_to_args"] is False
        remaining = result_cache_tool.run({"mode": "stats"})
        assert "my_report" not in remaining["tools"]
        assert remaining["tools"]["reference_lookup"] == 1

    def test_args_without_tool_is_rejected(self):
        result = result_cache_tool.run({"mode": "invalidate", "args": {"mode": "x"}})
        assert result["success"] is False
        assert result["error_code"] == "BAD_ARGS"

    def test_args_must_be_an_object(self):
        result = result_cache_tool.run({"mode": "invalidate", "tool": "my_report", "args": "not-a-dict"})
        assert result["success"] is False
        assert result["error_code"] == "BAD_ARGS"


class TestPrune:
    def test_prune_removes_only_expired_entries(self):
        _rc.put("my_report", {"mode": "active_stores"}, {"success": True, "count": 5}, ttl_s=100)
        _rc.put("my_report", {"mode": "conversions"}, {"success": True, "count": 1}, ttl_s=100)

        # Age one entry past its TTL directly in the DB.
        import sqlite3
        conn = sqlite3.connect(str(_rc._DB_PATH))
        conn.execute(
            "UPDATE results SET cached_at = cached_at - 200 WHERE cache_key = ?",
            (_rc.cache_key("my_report", {"mode": "active_stores"}),),
        )
        conn.commit()
        conn.close()

        result = result_cache_tool.run({"mode": "prune"})
        assert result["success"] is True
        assert result["pruned"] == 1
        remaining = result_cache_tool.run({"mode": "stats"})
        assert remaining["entries"] == 1


class TestUnknownMode:
    def test_unknown_mode_fails(self):
        result = result_cache_tool.run({"mode": "bogus"})
        assert result["success"] is False
        assert result["error_code"] == "BAD_MODE"
