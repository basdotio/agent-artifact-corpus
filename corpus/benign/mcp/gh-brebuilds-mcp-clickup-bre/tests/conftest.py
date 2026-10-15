"""Shared pytest fixtures.

CLICKUP_API_TOKEN must be set before `clickup_mcp.client` (or the legacy
`server` module) is imported anywhere, because that module validates the
token at import time. This file is collected before any test module in the
same directory, so setting it here — at module scope, not inside a fixture —
guarantees it happens first.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("CLICKUP_API_TOKEN", "test-token-not-real")

# Make the repo root importable (so `import server` and `import clickup_mcp`
# work regardless of where pytest is invoked from).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
import respx
import httpx

import server  # noqa: E402  (import after sys.path/env setup above)


@pytest.fixture
def app():
    """The MCP Server instance under test."""
    return server.app


@pytest.fixture
def call_tool():
    """server.call_tool, the top-level dispatcher."""
    return server.call_tool


@pytest.fixture
async def all_tools():
    """Every registered Tool schema, as returned by list_tools()."""
    return await server.list_tools()


@pytest.fixture
def mocked_clickup():
    """A respx router pre-scoped to the ClickUp API base URL.

    Individual tests add their own `.route(...)` expectations to this
    router; nothing is mocked by default so an unexpected call fails loudly
    instead of silently returning 200.
    """
    with respx.mock(
        base_url="https://api.clickup.com/api/v2", assert_all_called=False
    ) as router:
        yield router


def build_minimal_arguments(schema: dict) -> dict:
    """Build the smallest argument dict that satisfies a tool's `required` list.

    Used by schema/dispatch smoke tests that need *a* valid call for every
    tool without hand-writing 101 fixtures. Only fills required fields —
    optional fields are intentionally left out so each test only proves what
    the schema actually demands.
    """
    props = schema.get("properties", {})
    required = schema.get("required", [])
    args = {}
    for key in required:
        prop = props.get(key, {})
        prop_type = prop.get("type")
        if prop_type == "string":
            args[key] = "test_value"
        elif prop_type in ("integer", "number"):
            args[key] = 1
        elif prop_type == "boolean":
            args[key] = True
        elif prop_type == "array":
            items = prop.get("items", {})
            item_type = items.get("type") if isinstance(items, dict) else None
            if item_type == "integer":
                args[key] = [1]
            elif item_type == "object":
                args[key] = [{"id": "1"}]
            else:
                args[key] = ["test_value"]
        elif prop_type == "object":
            args[key] = {}
        else:
            args[key] = "test_value"
    return args
