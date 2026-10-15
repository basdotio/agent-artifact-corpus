"""
Tests for the gateway's opt-in result-cache wiring
(gateway_server._run_tool_raw + the CACHEABLE_TOOLS allowlist validation).

Complements tests/test_result_cache.py (the library's own contract) — here
we test the GATEWAY's behavior: allowlist gating, force_refresh plumbing,
audit tagging, and that non-allowlisted tools are never cached.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import gateway_server  # noqa: E402
import _result_cache as rc  # noqa: E402
from _capabilities import CACHEABLE_TOOLS  # noqa: E402




class CallToolSpy:
    """Replaces gateway_server._call_tool. Counts real dispatches per tool
    (audit_log calls are recorded but answered separately)."""

    def __init__(self, result: dict | None = None):
        self.dispatches: list[str] = []
        self.audit_tags: list[list] = []
        self.result = result or {"success": True, "count": 1234}

    def __call__(self, name: str, args: dict) -> str:
        if name == "audit_log":
            self.audit_tags.append(args.get("tags", []))
            return json.dumps({"success": True})
        self.dispatches.append(name)
        return json.dumps(self.result)


@pytest.fixture
def gw(monkeypatch, tmp_path):
    monkeypatch.setattr(rc, "_DB_PATH", tmp_path / "rc.db")
    monkeypatch.setattr(rc, "DEFAULT_TTL_S", 3600)
    spy = CallToolSpy()
    monkeypatch.setattr(gateway_server, "_call_tool", spy)
    # A fake cacheable tool, so tests don't depend on any real tool's schema
    monkeypatch.setitem(gateway_server._TOOLS, "fake_cached", {
        "module": "does_not_matter",
        "cache_ttl_s": 3600,
        "description": "test-only",
        "input_schema": {"type": "object", "properties": {"mode": {"type": "string"}}},
    })
    monkeypatch.setitem(gateway_server._TOOLS, "fake_uncached", {
        "module": "does_not_matter",
        "description": "test-only",
        "input_schema": {"type": "object", "properties": {"mode": {"type": "string"}}},
    })
    return spy


def _run(name, args=None, **kw):
    result_json, _ = gateway_server._run_tool_raw(name, args or {}, **kw)
    return json.loads(result_json)


class TestGatewayCaching:
    def test_first_call_dispatches_then_second_hits_cache(self, gw):
        first = _run("fake_cached", {"mode": "m"})
        second = _run("fake_cached", {"mode": "m"})
        assert gw.dispatches == ["fake_cached"]  # exactly one real run
        assert "_from_cache" not in first
        assert second["_from_cache"] is True and second["count"] == 1234

    def test_cache_hit_is_audit_tagged(self, gw):
        _run("fake_cached", {"mode": "m"})
        _run("fake_cached", {"mode": "m"})
        assert ["auto", "success"] in gw.audit_tags
        assert ["auto", "cache_hit"] in gw.audit_tags

    def test_force_refresh_param_redispatches_and_updates_cache(self, gw):
        _run("fake_cached", {"mode": "m"})
        gw.result = {"success": True, "count": 5678}
        refreshed = _run("fake_cached", {"mode": "m"}, force_refresh=True)
        assert len(gw.dispatches) == 2
        assert refreshed["count"] == 5678
        # The forced result replaced the cached entry
        after = _run("fake_cached", {"mode": "m"})
        assert after["_from_cache"] is True and after["count"] == 5678

    def test_force_refresh_inside_args_also_works(self, gw):
        _run("fake_cached", {"mode": "m"})
        _run("fake_cached", {"mode": "m", "force_refresh": True})
        assert len(gw.dispatches) == 2

    def test_force_refresh_propagates_into_args_when_declared(self, monkeypatch, gw):
        """REGRESSION: tools that cache INTERNALLY own the only cache
        their callers see. A
        gateway-only force_refresh left their internal cache untouched, so
        asking for live numbers silently returned stale ones. Tools opt in
        by declaring force_refresh in their input_schema."""
        seen: list[dict] = []

        def spy_call(name, args):
            if name == "audit_log":  # not the tool call we're inspecting
                return json.dumps({"success": True})
            seen.append(args)
            return json.dumps({"success": True, "count": 1})

        monkeypatch.setitem(gateway_server._TOOLS, "internally_cached", {
            "module": "m", "description": "d",
            "input_schema": {"type": "object", "properties": {
                "mode": {"type": "string"},
                "force_refresh": {"type": "boolean"},
            }},
        })
        monkeypatch.setattr(gateway_server, "_call_tool", spy_call)
        _run("internally_cached", {"mode": "m"}, force_refresh=True)
        assert seen[-1].get("force_refresh") is True

    def test_force_refresh_not_injected_when_undeclared(self, monkeypatch, gw):
        """Tools that don't declare it must not receive a surprise kwarg."""
        seen: list[dict] = []

        def spy_call(name, args):
            if name == "audit_log":
                return json.dumps({"success": True})
            seen.append(args)
            return json.dumps({"success": True})

        monkeypatch.setattr(gateway_server, "_call_tool", spy_call)
        _run("fake_uncached", {"mode": "m"}, force_refresh=True)
        assert "force_refresh" not in seen[-1]

    def test_args_variants_cache_separately(self, gw):
        _run("fake_cached", {"mode": "a"})
        _run("fake_cached", {"mode": "b"})
        assert len(gw.dispatches) == 2

    def test_non_allowlisted_tool_is_never_cached(self, gw):
        _run("fake_uncached", {"mode": "m"})
        _run("fake_uncached", {"mode": "m"})
        assert gw.dispatches == ["fake_uncached", "fake_uncached"]

    def test_failure_is_not_cached(self, gw):
        gw.result = {"success": False, "error": "boom"}
        _run("fake_cached", {"mode": "m"})
        gw.result = {"success": True, "count": 1}
        result = _run("fake_cached", {"mode": "m"})
        assert len(gw.dispatches) == 2  # failure didn't satisfy the second call
        assert "_from_cache" not in result

    def test_unknown_tool_still_errors_cleanly(self, gw):
        result = _run("definitely_not_a_tool")
        assert result["success"] is False


class TestAllowlistValidation:
    def test_current_registry_is_in_sync(self):
        errors = gateway_server._validate_capabilities()
        assert errors == []

    def test_cache_ttl_without_allowlist_membership_fails(self, monkeypatch):
        monkeypatch.setitem(gateway_server._TOOLS, "sneaky_tool", {
            "module": "sneaky", "cache_ttl_s": 60,
            "description": "d", "input_schema": {"type": "object"},
        })
        errors = gateway_server._validate_capabilities()
        assert any("sneaky_tool" in e and "CACHEABLE_TOOLS" in e for e in errors)

    def test_bad_ttl_value_fails(self, monkeypatch):
        monkeypatch.setitem(gateway_server._TOOLS, "bad_ttl_tool", {
            "module": "bad", "cache_ttl_s": -5,
            "description": "d", "input_schema": {"type": "object"},
        })
        errors = gateway_server._validate_capabilities()
        assert any("bad_ttl_tool" in e and "positive int" in e for e in errors)

    def test_every_allowlisted_tool_really_exists_with_ttl(self):
        for name in CACHEABLE_TOOLS:
            assert name in gateway_server._TOOLS
            assert isinstance(gateway_server._TOOLS[name].get("cache_ttl_s"), int)
