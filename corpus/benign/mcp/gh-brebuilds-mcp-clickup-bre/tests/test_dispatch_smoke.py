"""Every one of the 101 tools, dispatched for real.

This is the regression test that matters most for the tools/ package split:
it proves every category module is wired into server.py's dispatcher, that
no tool name accidentally shadows another, and that a minimal valid call for
every tool returns without raising - using only the arguments its own
schema says are required.

All HTTP calls are caught by a catch-all respx route returning a canned
200 response, so this never touches the network and never asserts on
ClickUp's actual response shape (that's covered per-tool in
test_request_building.py). It asserts dispatch resolves to exactly one
TextContent with valid JSON, which is the contract every tool promises.
"""
import json

import httpx
import pytest

from conftest import build_minimal_arguments


def _tool_ids(tools):
    return [t.name for t in tools]


@pytest.fixture
def catch_all_ok(mocked_clickup):
    mocked_clickup.route().mock(
        return_value=httpx.Response(200, json={"ok": True, "id": "abc123"})
    )
    return mocked_clickup


async def test_every_tool_dispatches_without_raising(all_tools, call_tool, catch_all_ok):
    failures = []
    for tool in all_tools:
        args = build_minimal_arguments(tool.inputSchema)
        result = await call_tool(tool.name, args)
        assert isinstance(result, list) and len(result) == 1, (
            f"{tool.name!r} did not return exactly one content item"
        )
        assert result[0].type == "text"
        try:
            json.loads(result[0].text)
        except json.JSONDecodeError:
            failures.append((tool.name, result[0].text[:200]))

    assert not failures, f"non-JSON output for: {failures}"


async def test_no_tool_name_is_handled_by_two_categories(all_tools):
    """A duplicate would mean one category's handler always wins and the
    other's is silently dead code - this is the schema-level version of
    that check, cross-referenced against the live dispatcher below."""
    names = [t.name for t in all_tools]
    assert len(names) == len(set(names))


async def test_dispatch_resolution_matches_exactly_one_category():
    """Ask every category module directly (bypassing server.call_tool's
    short-circuit) and confirm exactly one module claims each tool name."""
    from clickup_mcp.tools import CATEGORIES
    import server

    tools = await server.list_tools()
    for tool in tools:
        claimants = [c.__name__ for c in CATEGORIES if any(t.name == tool.name for t in c.TOOLS)]
        assert len(claimants) == 1, (
            f"{tool.name!r} is declared by {claimants}, expected exactly one"
        )
