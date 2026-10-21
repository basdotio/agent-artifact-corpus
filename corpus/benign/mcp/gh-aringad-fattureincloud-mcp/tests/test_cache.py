import os
import time
from datetime import timedelta

import pytest

import cache


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("FIC_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("FIC_CACHE_DISABLED", raising=False)
    yield tmp_path


def test_put_and_get(tmp_cache):
    cache.put("clients", 12345, [{"id": 1, "name": "Acme"}])
    assert cache.get("clients", 12345) == [{"id": 1, "name": "Acme"}]


def test_get_miss_no_file(tmp_cache):
    assert cache.get("clients", 12345) is None


def test_ttl_expired(tmp_cache):
    cache.put("clients", 12345, [{"id": 1}])
    path = tmp_cache / "12345" / "clients.json"
    old = time.time() - 3600 * 25
    os.utime(path, (old, old))
    assert cache.get("clients", 12345, ttl=timedelta(hours=24)) is None


def test_multi_company_isolation(tmp_cache):
    cache.put("clients", 100, [{"name": "A"}])
    cache.put("clients", 200, [{"name": "B"}])
    assert cache.get("clients", 100) == [{"name": "A"}]
    assert cache.get("clients", 200) == [{"name": "B"}]


def test_disabled_blocks_get(tmp_cache, monkeypatch):
    cache.put("clients", 100, [{"name": "A"}])
    monkeypatch.setenv("FIC_CACHE_DISABLED", "1")
    assert cache.get("clients", 100) is None


def test_disabled_blocks_put(tmp_cache, monkeypatch):
    monkeypatch.setenv("FIC_CACHE_DISABLED", "1")
    cache.put("clients", 100, [{"name": "A"}])
    monkeypatch.delenv("FIC_CACHE_DISABLED", raising=False)
    assert cache.get("clients", 100) is None


def test_invalidate(tmp_cache):
    cache.put("clients", 100, [{"name": "A"}])
    cache.invalidate("clients", 100)
    assert cache.get("clients", 100) is None


def test_invalidate_all(tmp_cache):
    cache.put("clients", 100, [{"name": "A"}])
    cache.put("cost_centers", 100, [{"id": 1}])
    cache.invalidate_all(100)
    assert cache.get("clients", 100) is None
    assert cache.get("cost_centers", 100) is None


def test_cached_decorator_hit(tmp_cache):
    calls = {"n": 0}

    @cache.cached("clients", ttl=timedelta(hours=24))
    def fetch(company_id):
        calls["n"] += 1
        return [{"id": 1}]

    fetch(company_id=100)
    fetch(company_id=100)
    fetch(company_id=100)
    assert calls["n"] == 1


def test_cached_decorator_per_company(tmp_cache):
    calls = {"n": 0}

    @cache.cached("clients", ttl=timedelta(hours=24))
    def fetch(company_id):
        calls["n"] += 1
        return [{"company": company_id}]

    fetch(company_id=100)
    fetch(company_id=200)
    fetch(company_id=100)
    assert calls["n"] == 2


def test_cached_decorator_disabled(tmp_cache, monkeypatch):
    monkeypatch.setenv("FIC_CACHE_DISABLED", "1")
    calls = {"n": 0}

    @cache.cached("clients", ttl=timedelta(hours=24))
    def fetch(company_id):
        calls["n"] += 1
        return [{"id": 1}]

    fetch(company_id=100)
    fetch(company_id=100)
    assert calls["n"] == 2


def test_cached_decorator_passes_args_and_kwargs(tmp_cache):
    @cache.cached("scoped", ttl=timedelta(hours=24))
    def fetch(prefix, company_id, suffix=""):
        return f"{prefix}-{company_id}-{suffix}"

    assert fetch("p", company_id=100, suffix="s") == "p-100-s"
    assert fetch("ignored", company_id=100, suffix="ignored") == "p-100-s"
