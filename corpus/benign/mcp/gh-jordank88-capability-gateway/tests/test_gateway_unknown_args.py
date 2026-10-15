"""test_gateway_unknown_args.py — run_tool rejects arguments a tool doesn't take.

jsonschema on its own accepts properties a schema doesn't declare, so without
this check a call carrying a wrong argument runs anyway with that argument
silently ignored — e.g. dry_run=true sent to a tool with no dry-run mode runs
it for real, and hours=4 sent to a tool that takes `minutes` runs with the
default. Both look like successes.

Uses fake tools injected into the registry, and stubs dispatch to explode so
a rejection that leaks through to a tool fails loudly instead of running it.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gateway_server as gw  # noqa: E402
from _registry import _TOOLS  # noqa: E402

_TIMER = {
    "module": "unused", "description": "test-only timer",
    "input_schema": {"type": "object", "properties": {
        "mode": {"type": "string"}, "minutes": {"type": "integer"},
    }},
}
_SITE_SYNC = {
    "module": "unused", "description": "test-only sync A",
    "input_schema": {"type": "object", "properties": {"site_number": {"type": "string"}}},
}
_FACILITY_SYNC = {
    "module": "unused", "description": "test-only sync B",
    "input_schema": {"type": "object", "properties": {"facility_id": {"type": "integer"}}},
}


@pytest.fixture(autouse=True)
def fake_tools(monkeypatch):
    """timer in its own group; two sibling sync tools sharing a group."""
    monkeypatch.setitem(_TOOLS, "timer", _TIMER)
    monkeypatch.setitem(_TOOLS, "site_sync", _SITE_SYNC)
    monkeypatch.setitem(_TOOLS, "facility_sync", _FACILITY_SYNC)
    monkeypatch.setitem(gw.CAPABILITIES, "fake-time", {"description": "d", "tools": ["timer"]})
    monkeypatch.setitem(gw.CAPABILITIES, "fake-sync",
                        {"description": "d", "tools": ["site_sync", "facility_sync"]})


@pytest.fixture
def no_dispatch(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("a rejected call must never reach the tool")
    monkeypatch.setattr(gw, "_call_tool", boom)


@pytest.fixture
def dispatched(monkeypatch):
    seen = {}

    def fake_call(name, args):
        seen["args"] = args
        return json.dumps({"success": True})
    monkeypatch.setattr(gw, "_call_tool", fake_call)
    monkeypatch.setattr(gw, "_log_audit", lambda *a, **k: None)
    return seen


def _run(name, args):
    out, _ = gw._run_tool_raw(name, args)
    return json.loads(out)


class TestRejection:
    def test_dry_run_on_a_tool_without_one_is_refused_with_warning(self, no_dispatch):
        r = _run("site_sync", {"site_number": "42", "dry_run": True})
        assert r["success"] is False
        assert r["error_code"] == "UNKNOWN_ARGUMENT"
        assert r["unknown_args"] == ["dry_run"]
        assert "has no dry_run mode" in r["warning"]
        assert r["suggestions"]["dry_run"] == {}, "dry_run is generic -- no tool guesses"

    def test_wrong_unit_lists_the_real_arguments(self, no_dispatch):
        r = _run("timer", {"mode": "start", "hours": 4})
        assert r["unknown_args"] == ["hours"]
        assert "minutes" in r["valid_args"]
        assert "minutes" in r["error"], "the message itself must show what the tool takes"

    def test_typo_suggests_the_right_argument(self, no_dispatch):
        r = _run("timer", {"mode": "start", "minute": 30})
        assert r["suggestions"]["minute"]["did_you_mean_arg"][0] == "minutes"
        assert "did you mean 'minutes'" in r["error"]

    def test_distinctive_arg_points_at_the_sibling_that_owns_it(self, no_dispatch):
        r = _run("site_sync", {"site_number": "42", "facility_id": 123})
        assert r["suggestions"]["facility_id"]["did_you_mean_tool"] == ["facility_sync"]
        assert "did you mean to use facility_sync" in r["error"]

    def test_tool_hints_never_cross_capability_groups(self, no_dispatch):
        r = _run("timer", {"mode": "start", "facility_id": 123})
        assert "did_you_mean_tool" not in r["suggestions"]["facility_id"]

    def test_all_unknown_args_reported_at_once(self, no_dispatch):
        r = _run("timer", {"mode": "start", "hours": 4, "dry_run": True})
        assert r["unknown_args"] == ["dry_run", "hours"]
        assert "warning" in r


class TestAllowed:
    def test_declared_args_pass(self, dispatched):
        assert _run("timer", {"mode": "start", "minutes": 5})["success"] is True

    def test_gateway_force_refresh_is_never_unknown(self, dispatched):
        assert _run("timer", {"mode": "start", "force_refresh": True})["success"] is True

    def test_tolerated_undeclared_key_passes(self, dispatched, monkeypatch):
        monkeypatch.setitem(gw._UNDECLARED_ARGS_TOLERATED, "timer", frozenset({"legacy"}))
        assert _run("timer", {"mode": "start", "legacy": 1})["success"] is True

    def test_tolerance_is_per_key_not_per_tool(self, no_dispatch, monkeypatch):
        monkeypatch.setitem(gw._UNDECLARED_ARGS_TOLERATED, "timer", frozenset({"legacy"}))
        assert _run("timer", {"mode": "start", "dry_run": True})["error_code"] == "UNKNOWN_ARGUMENT"

    def test_explicit_additional_properties_opts_out(self, dispatched, monkeypatch):
        spec = dict(_TIMER)
        spec["input_schema"] = {**spec["input_schema"], "additionalProperties": True}
        monkeypatch.setitem(_TOOLS, "timer", spec)
        assert _run("timer", {"mode": "start", "anything": 1})["success"] is True


class TestPlaceholders:
    def test_placeholder_value_is_refused(self, no_dispatch):
        r = _run("site_sync", {"site_number": "dummy_123"})
        assert r["success"] is False
        assert r["error_field"] == "site_number"

    def test_filename_lookalike_is_not_a_placeholder(self, dispatched):
        assert _run("site_sync", {"site_number": "example.json"})["success"] is True


class TestToleranceListStaysHonest:
    def test_every_tolerated_tool_exists(self):
        assert set(gw._UNDECLARED_ARGS_TOLERATED) <= set(_TOOLS)

    def test_no_tolerated_key_is_already_declared(self):
        # Once a key is declared in _registry.py, delete it from the list.
        for tool, keys in gw._UNDECLARED_ARGS_TOLERATED.items():
            declared = set(_TOOLS[tool]["input_schema"].get("properties") or {})
            assert not (keys & declared), f"{tool}: {sorted(keys & declared)} now declared"
