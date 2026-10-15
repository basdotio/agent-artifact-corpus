"""
Unit tests for _result_cache.py — the shared TTL result cache used by the
gateway's run_tool and by tools that cache internally. These tests define the
library's contract.
"""

import concurrent.futures
import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import _result_cache as rc  # noqa: E402




@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setattr(rc, "_DB_PATH", tmp_path / "rc.db")
    monkeypatch.setattr(rc, "DEFAULT_TTL_S", 3600)


def _age_row(tool: str, args: dict, seconds: float) -> None:
    conn = sqlite3.connect(str(rc._DB_PATH))
    conn.execute("UPDATE results SET cached_at = cached_at - ? WHERE cache_key=?",
                 (seconds, rc.cache_key(tool, args)))
    conn.commit()
    conn.close()


GOOD = {"success": True, "count": 1234}


class TestRoundTrip:
    def test_miss_then_hit(self):
        assert rc.get("my_report", {"mode": "active_stores"}) is None
        assert rc.put("my_report", {"mode": "active_stores"}, GOOD) is True
        hit = rc.get("my_report", {"mode": "active_stores"})
        assert hit["count"] == 1234
        assert hit["_from_cache"] is True
        assert isinstance(hit["_cache_age_s"], int)
        assert hit["_cached_at"] <= time.time()

    def test_stored_copy_is_clean_of_prior_cache_tags(self):
        tainted = {**GOOD, "_from_cache": True, "_cache_age_s": 999,
                   "_cached_at": 1.0}
        rc.put("t", {}, tainted)
        hit = rc.get("t", {})
        assert hit["_cache_age_s"] < 999  # re-tagged for THIS entry, not replayed
        conn = sqlite3.connect(str(rc._DB_PATH))
        stored = json.loads(conn.execute("SELECT result_json FROM results").fetchone()[0])
        conn.close()
        assert "_from_cache" not in stored and "_cache_age_s" not in stored

    def test_hit_count_increments(self):
        rc.put("t", {}, GOOD)
        rc.get("t", {})
        rc.get("t", {})
        assert rc.stats()["total_hits"] == 2


class TestKeySemantics:
    def test_tool_name_participates(self):
        rc.put("tool_a", {"x": 1}, GOOD)
        assert rc.get("tool_b", {"x": 1}) is None

    def test_meta_args_are_stripped(self):
        rc.put("t", {"mode": "m"}, GOOD)
        assert rc.get("t", {"mode": "m", "force_refresh": True,
                            "timeout_s": 300, "debug": True}) is not None

    def test_data_args_are_not_stripped(self):
        rc.put("t", {"mode": "m"}, GOOD)
        assert rc.get("t", {"mode": "m", "as_of": "2026-07-01"}) is None

    def test_key_is_order_insensitive(self):
        assert rc.cache_key("t", {"a": 1, "b": 2}) == rc.cache_key("t", {"b": 2, "a": 1})

    def test_none_args_equal_empty(self):
        assert rc.cache_key("t", None) == rc.cache_key("t", {})


class TestStoragePolicy:
    def test_failure_is_never_stored(self):
        assert rc.put("t", {}, {"success": False, "error": "boom"}) is False
        assert rc.get("t", {}) is None

    def test_missing_success_is_never_stored(self):
        assert rc.put("t", {}, {"count": 5}) is False

    def test_non_dict_is_never_stored(self):
        assert rc.put("t", {}, "just a string") is False

    def test_image_payloads_are_never_stored(self):
        assert rc.put("t", {}, {**GOOD, "_image_b64": "AAAA"}) is False

    def test_disabled_cache_neither_reads_nor_writes(self, monkeypatch):
        monkeypatch.setattr(rc, "DEFAULT_TTL_S", 0)
        assert rc.put("t", {}, GOOD) is False
        assert rc.get("t", {}) is None


class TestTtl:
    def test_expired_entry_misses(self):
        rc.put("t", {}, GOOD, ttl_s=60)
        _age_row("t", {}, 61)
        assert rc.get("t", {}) is None

    def test_entry_within_ttl_serves(self):
        rc.put("t", {}, GOOD, ttl_s=60)
        _age_row("t", {}, 30)
        hit = rc.get("t", {})
        assert hit is not None and hit["_cache_age_s"] >= 30

    def test_default_ttl_applies_when_unspecified(self):
        rc.put("t", {}, GOOD)  # stored with DEFAULT_TTL_S=3600
        _age_row("t", {}, 3000)
        assert rc.get("t", {}) is not None
        _age_row("t", {}, 700)  # total ~3700 > 3600
        assert rc.get("t", {}) is None

    def test_caller_ttl_bound_overrides_stored_ttl(self):
        rc.put("t", {}, GOOD, ttl_s=3600)
        _age_row("t", {}, 120)
        assert rc.get("t", {}) is not None            # stored TTL: fresh
        assert rc.get("t", {}, ttl_s=60) is None      # caller bound: too old

    def test_ttl_zero_entry_never_serves(self):
        rc.put("t", {}, GOOD, ttl_s=0)
        assert rc.get("t", {}) is None

    def test_put_refreshes_clock_and_resets_hits(self):
        rc.put("t", {}, GOOD, ttl_s=60)
        rc.get("t", {})
        _age_row("t", {}, 50)
        rc.put("t", {}, {"success": True, "count": 5678}, ttl_s=60)
        hit = rc.get("t", {})
        assert hit["count"] == 5678 and hit["_cache_age_s"] < 50
        assert rc.stats()["total_hits"] == 1  # reset on overwrite


class TestInvalidateAndPrune:
    def test_invalidate_one_entry(self):
        rc.put("t", {"a": 1}, GOOD)
        rc.put("t", {"a": 2}, GOOD)
        assert rc.invalidate("t", {"a": 1}) == 1
        assert rc.get("t", {"a": 1}) is None
        assert rc.get("t", {"a": 2}) is not None

    def test_invalidate_whole_tool(self):
        rc.put("t1", {"a": 1}, GOOD)
        rc.put("t1", {"a": 2}, GOOD)
        rc.put("t2", {}, GOOD)
        assert rc.invalidate("t1") == 2
        assert rc.get("t2", {}) is not None

    def test_invalidate_everything(self):
        rc.put("t1", {}, GOOD)
        rc.put("t2", {}, GOOD)
        assert rc.invalidate() == 2
        assert rc.stats()["entries"] == 0

    def test_prune_removes_only_expired(self):
        rc.put("old", {}, GOOD, ttl_s=60)
        rc.put("new", {}, GOOD, ttl_s=3600)
        _age_row("old", {}, 120)
        assert rc.prune() == 1
        assert rc.stats()["entries"] == 1
        assert rc.get("new", {}) is not None


class TestStats:
    def test_stats_shape(self):
        rc.put("t1", {"a": 1}, GOOD, ttl_s=60)
        rc.put("t1", {"a": 2}, GOOD, ttl_s=60)
        rc.put("t2", {}, GOOD, ttl_s=60)
        _age_row("t1", {"a": 1}, 120)
        s = rc.stats()
        assert s["entries"] == 3
        assert s["fresh_entries"] == 2 and s["expired_entries"] == 1
        assert s["tools"] == {"t1": 2, "t2": 1}
        assert s["default_ttl_s"] == 3600


class TestConcurrency:
    def test_parallel_put_get_is_safe(self):
        """8 threads × mixed put/get on overlapping keys — mirrors the
        gateway's ThreadPoolExecutor(max_workers=8). Must not raise, and
        every stored entry must be readable and internally consistent."""
        def worker(i: int) -> None:
            for j in range(25):
                key_args = {"k": j % 5}
                rc.put("concurrent", key_args,
                       {"success": True, "value": f"{i}-{j}"})
                hit = rc.get("concurrent", key_args)
                if hit is not None:
                    assert hit["success"] is True and "value" in hit

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker, i) for i in range(8)]
            for f in futures:
                f.result()  # surfaces any exception

        assert rc.stats()["entries"] == 5  # 5 distinct keys survive
