"""Request-building tests.

These exercise the actual URL, query params and JSON bodies each tool sends
to the ClickUp API - the part that's easy to get subtly wrong (e.g. the
`statuses[]` array-param convention ClickUp's API expects, or which of
list_id/folder_id/space_id wins when more than one is supplied).

All HTTP traffic is intercepted by respx; nothing here reaches the network.
"""
import json

import httpx
import pytest


async def test_get_tasks_prefers_list_id_over_folder_and_space(call_tool, mocked_clickup):
    route = mocked_clickup.get("/list/111/task").mock(
        return_value=httpx.Response(200, json={"tasks": []})
    )
    result = await call_tool(
        "get_tasks",
        {"list_id": "111", "folder_id": "222", "space_id": "333"},
    )
    assert route.called
    assert json.loads(result[0].text) == {"tasks": []}


async def test_get_tasks_falls_back_to_folder_id(call_tool, mocked_clickup):
    route = mocked_clickup.get("/folder/222/task").mock(
        return_value=httpx.Response(200, json={"tasks": []})
    )
    result = await call_tool("get_tasks", {"folder_id": "222"})
    assert route.called
    assert json.loads(result[0].text) == {"tasks": []}


async def test_get_tasks_falls_back_to_space_id(call_tool, mocked_clickup):
    route = mocked_clickup.get("/space/333/task").mock(
        return_value=httpx.Response(200, json={"tasks": []})
    )
    result = await call_tool("get_tasks", {"space_id": "333"})
    assert route.called


async def test_get_tasks_requires_a_container_id(call_tool, mocked_clickup):
    """No list_id/folder_id/space_id at all - the code returns a structured
    error instead of calling the API, and must not make any HTTP request."""
    result = await call_tool("get_tasks", {})
    body = json.loads(result[0].text)
    assert "error" in body
    assert "list_id, folder_id, or space_id" in body["error"]


async def test_get_tasks_sends_array_params_with_bracket_suffix(call_tool, mocked_clickup):
    """ClickUp's API expects repeated array params as e.g. statuses[]=open,
    not a bare `statuses` key with a JSON-encoded list."""
    route = mocked_clickup.get("/list/111/task").mock(
        return_value=httpx.Response(200, json={"tasks": []})
    )
    await call_tool(
        "get_tasks",
        {
            "list_id": "111",
            "statuses": ["open", "in progress"],
            "assignees": ["42"],
            "tags": ["urgent"],
        },
    )
    assert route.called
    sent = route.calls.last.request.url.params
    assert sent.get_list("statuses[]") == ["open", "in progress"]
    assert sent.get_list("assignees[]") == ["42"]
    assert sent.get_list("tags[]") == ["urgent"]
    # plain (non-array) keys must NOT be present
    assert "statuses" not in sent


async def test_get_tasks_forwards_date_filter_params(call_tool, mocked_clickup):
    route = mocked_clickup.get("/list/111/task").mock(
        return_value=httpx.Response(200, json={"tasks": []})
    )
    await call_tool(
        "get_tasks",
        {"list_id": "111", "due_date_gt": 1000, "date_updated_lt": 2000},
    )
    sent = route.calls.last.request.url.params
    assert sent.get("due_date_gt") == "1000"
    assert sent.get("date_updated_lt") == "2000"


async def test_search_tasks_sends_team_id_query_and_page(call_tool, mocked_clickup):
    route = mocked_clickup.get("/task").mock(
        return_value=httpx.Response(200, json={"tasks": []})
    )
    await call_tool(
        "search_tasks", {"team_id": "9", "query": "invoice", "page": 2}
    )
    sent = route.calls.last.request.url.params
    assert sent.get("team_id") == "9"
    assert sent.get("query") == "invoice"
    assert sent.get("page") == "2"


async def test_create_task_only_forwards_allowed_fields(call_tool, mocked_clickup):
    """create_task should pass through the documented optional fields and
    silently ignore anything not in its allow-list, rather than forwarding
    the arguments dict verbatim."""
    route = mocked_clickup.post("/list/111/task").mock(
        return_value=httpx.Response(200, json={"id": "t1"})
    )
    await call_tool(
        "create_task",
        {
            "list_id": "111",
            "name": "Ship the thing",
            "priority": 1,
            "not_a_real_field": "should be dropped",
        },
    )
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body["name"] == "Ship the thing"
    assert sent_body["priority"] == 1
    assert "not_a_real_field" not in sent_body
    assert "list_id" not in sent_body  # path param, not body


async def test_update_task_builds_partial_update_body(call_tool, mocked_clickup):
    route = mocked_clickup.put("/task/t1").mock(
        return_value=httpx.Response(200, json={"id": "t1"})
    )
    await call_tool("update_task", {"task_id": "t1", "status": "done"})
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body == {"status": "done"}


async def test_get_spaces_forwards_archived_flag(call_tool, mocked_clickup):
    route = mocked_clickup.get("/team/9/space").mock(
        return_value=httpx.Response(200, json={"spaces": []})
    )
    await call_tool("get_spaces", {"workspace_id": "9", "archived": True})
    sent = route.calls.last.request.url.params
    assert sent.get("archived") == "true"


async def test_get_spaces_omits_archived_when_not_supplied(call_tool, mocked_clickup):
    route = mocked_clickup.get("/team/9/space").mock(
        return_value=httpx.Response(200, json={"spaces": []})
    )
    await call_tool("get_spaces", {"workspace_id": "9"})
    sent = route.calls.last.request.url.params
    assert "archived" not in sent


async def test_get_time_entries_forwards_optional_filters(call_tool, mocked_clickup):
    route = mocked_clickup.get("/team/9/time_entries").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    await call_tool(
        "get_time_entries",
        {"team_id": "9", "start_date": 100, "end_date": 200, "space_id": "5"},
    )
    sent = route.calls.last.request.url.params
    assert sent.get("team_id") == "9"
    assert sent.get("start_date") == "100"
    assert sent.get("end_date") == "200"
    assert sent.get("space_id") == "5"


async def test_get_task_forwards_optional_query_params(call_tool, mocked_clickup):
    route = mocked_clickup.get("/task/t1").mock(
        return_value=httpx.Response(200, json={"id": "t1"})
    )
    await call_tool(
        "get_task",
        {"task_id": "t1", "team_id": "9", "include_subtasks": True},
    )
    sent = route.calls.last.request.url.params
    assert sent.get("team_id") == "9"
    assert sent.get("include_subtasks") == "true"
