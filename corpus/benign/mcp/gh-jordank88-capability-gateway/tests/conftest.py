"""
Shared test fixtures.

    pytest tests/ -q
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch, tmp_path):
    """Point every on-disk store at a per-test temp file.

    A safety net, not a convenience. Without it, a test that runs a cacheable
    tool writes into the REAL result cache — and the dangerous version is a
    test with a mocked tool parking fabricated results there under a 16h TTL,
    where a later live question gets them served back as though they were
    real. Add any store your own tools persist to (token caches especially).

    Tests that inspect a store's internals can still monkeypatch _DB_PATH
    themselves; a later assignment wins over this one.
    """
    import _result_cache
    from tools import audit_log

    monkeypatch.setattr(_result_cache, "_DB_PATH", tmp_path / "tool_result_cache.db")
    monkeypatch.setattr(audit_log, "_DB_PATH", tmp_path / "audit_log.db")


@pytest.fixture(autouse=True)
def _isolate_keyring(monkeypatch):
    """Give every test an empty in-memory keyring instead of the real one, so
    a test exercising a "credential missing" path can never find a real
    secret in the OS vault and go on to make a real authenticated call."""
    import types

    store: dict = {}
    fake = types.ModuleType("keyring")
    fake.get_password = lambda service, key: store.get((service, key))
    fake.set_password = lambda service, key, value: store.__setitem__((service, key), value)
    monkeypatch.setitem(sys.modules, "keyring", fake)
    import _utils
    monkeypatch.setattr(_utils, "_keyring_available", None)
