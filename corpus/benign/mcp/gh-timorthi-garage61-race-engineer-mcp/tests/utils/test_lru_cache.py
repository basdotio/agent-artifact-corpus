"""Tests for utils.lru_cache.LRUCache."""

import pandas as pd
import pytest

from utils.lru_cache import LRUCache


@pytest.fixture
def cache() -> LRUCache:
    return LRUCache(maxsize=3)


def _df(value: float) -> pd.DataFrame:
    """Minimal single-value DataFrame for use as a cache payload."""
    return pd.DataFrame({"v": [value]})


class TestLRUCacheGet:
    def test_miss_returns_none(self, cache: LRUCache) -> None:
        assert cache.get("missing") is None

    def test_hit_returns_stored_value(self, cache: LRUCache) -> None:
        df = _df(1.0)
        cache.put("a", df)
        result = cache.get("a")
        assert result is df  # same object, not a copy

    def test_get_promotes_to_most_recent(self, cache: LRUCache) -> None:
        cache.put("a", _df(1.0))
        cache.put("b", _df(2.0))
        cache.put("c", _df(3.0))

        # Access "a" so it becomes most-recently-used.
        cache.get("a")

        # Adding a fourth entry should evict "b" (now the LRU), not "a".
        cache.put("d", _df(4.0))

        assert cache.get("b") is None
        assert cache.get("a") is not None


class TestLRUCachePut:
    def test_evicts_lru_when_full(self, cache: LRUCache) -> None:
        cache.put("a", _df(1.0))
        cache.put("b", _df(2.0))
        cache.put("c", _df(3.0))
        cache.put("d", _df(4.0))  # should evict "a"

        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("c") is not None
        assert cache.get("d") is not None

    def test_reput_existing_key_does_not_grow_cache(self, cache: LRUCache) -> None:
        cache.put("a", _df(1.0))
        cache.put("b", _df(2.0))
        cache.put("a", _df(99.0))  # update, not insert

        # Cache should still only contain 2 unique keys.
        assert len(cache._data) == 2

    def test_reput_existing_key_updates_value(self, cache: LRUCache) -> None:
        cache.put("a", _df(1.0))
        new_df = _df(99.0)
        cache.put("a", new_df)

        assert cache.get("a") is new_df

    def test_reput_existing_key_promotes_to_most_recent(self, cache: LRUCache) -> None:
        cache.put("a", _df(1.0))
        cache.put("b", _df(2.0))
        cache.put("c", _df(3.0))

        # Re-put "a" so it becomes most-recently-used.
        cache.put("a", _df(1.0))

        # Adding a fourth entry should evict "b", not "a".
        cache.put("d", _df(4.0))

        assert cache.get("b") is None
        assert cache.get("a") is not None
