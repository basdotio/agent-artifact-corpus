"""How ClickUp responses and failures become MCP results.

Two things worth calling out about the real behavior here (verified, not
assumed):

1. `call_tool` never calls `response.raise_for_status()`. So a non-2xx
   response from ClickUp that still has a JSON body (which is how ClickUp
   reports API errors - e.g. `{"err": "...", "ECODE": "..."}`) is returned
   to the caller as if it were a normal, successful payload. The
   `except httpx.HTTPStatusError` branch exists but nothing in this code
   path raises that exception, so it is effectively unreachable today.
2. What *is* reachable is the generic `except Exception` handler, which
   catches things like a missing required argument (KeyError) or a
   non-JSON response body (json.JSONDecodeError), and turns them into
   `{"error": "Error: ..."}`.

These tests document the real behavior so a future change to this handling
is a deliberate decision, not an accidental regression.
"""
import json

import httpx
import pytest


async def test_unknown_tool_name_returns_a_structured_error(call_tool):
    result = await call_tool("this_tool_does_not_exist", {})
    body = json.loads(result[0].text)
    assert body == {"error": "Unknown tool: this_tool_does_not_exist"}


async def test_missing_required_argument_is_caught_and_reported(call_tool):
    """get_workspace requires workspace_id; omitting it raises a KeyError
    that the outer try/except in call_tool must catch rather than propagate."""
    result = await call_tool("get_workspace", {})
    body = json.loads(result[0].text)
    assert "error" in body
    assert "workspace_id" in body["error"]


async def test_a_clickup_error_body_on_a_4xx_is_passed_through_as_data(
    call_tool, mocked_clickup
):
    """This is the documented gap: raise_for_status() is never called, so a
    401 with a JSON error body from ClickUp comes back looking like success."""
    mocked_clickup.get("/team/9").mock(
        return_value=httpx.Response(
            401, json={"err": "Token invalid", "ECODE": "OAUTH_019"}
        )
    )
    result = await call_tool("get_workspace", {"workspace_id": "9"})
    body = json.loads(result[0].text)
    # No "error" wrapper - the raw ClickUp error envelope is returned as-is.
    assert body == {"err": "Token invalid", "ECODE": "OAUTH_019"}


async def test_non_json_response_body_is_caught_as_a_generic_error(
    call_tool, mocked_clickup
):
    mocked_clickup.get("/team/9").mock(
        return_value=httpx.Response(200, content=b"not json at all")
    )
    result = await call_tool("get_workspace", {"workspace_id": "9"})
    body = json.loads(result[0].text)
    assert "error" in body
    assert body["error"].startswith("Error:")


async def test_successful_response_is_returned_pretty_printed(call_tool, mocked_clickup):
    mocked_clickup.get("/team/9").mock(
        return_value=httpx.Response(200, json={"id": "9", "name": "Acme"})
    )
    result = await call_tool("get_workspace", {"workspace_id": "9"})
    assert len(result) == 1
    assert result[0].type == "text"
    # indent=2 pretty-printing, per the original implementation
    assert result[0].text == json.dumps({"id": "9", "name": "Acme"}, indent=2)


async def test_network_failure_is_caught_as_a_generic_error(call_tool, mocked_clickup):
    mocked_clickup.get("/team/9").mock(side_effect=httpx.ConnectError("boom"))
    result = await call_tool("get_workspace", {"workspace_id": "9"})
    body = json.loads(result[0].text)
    assert "error" in body
    assert "boom" in body["error"]
