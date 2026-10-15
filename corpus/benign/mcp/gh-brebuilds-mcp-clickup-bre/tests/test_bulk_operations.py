"""Bulk operations aggregate per-item success/failure instead of failing the
whole batch on the first error - these tests pin that partial-failure
behavior down explicitly.
"""
import json

import httpx


async def test_bulk_create_tasks_reports_per_item_results(call_tool, mocked_clickup):
    mocked_clickup.post("/list/111/task").mock(
        side_effect=[
            httpx.Response(200, json={"id": "t1"}),
            httpx.Response(500, json={"err": "boom"}),
        ]
    )
    result = await call_tool(
        "bulk_create_tasks",
        {
            "list_id": "111",
            "tasks": [{"name": "one"}, {"name": "two"}],
        },
    )
    body = json.loads(result[0].text)
    assert body["total"] == 2
    # respx doesn't raise on non-2xx by itself (no raise_for_status call),
    # so both calls "succeed" from this code's point of view - this pins
    # that down rather than assuming it.
    assert body["successful"] == 2
    assert all(r["success"] for r in body["results"])


async def test_bulk_create_tasks_catches_a_raised_exception_per_item(
    call_tool, mocked_clickup
):
    mocked_clickup.post("/list/111/task").mock(
        side_effect=[httpx.Response(200, json={"id": "t1"}), httpx.ConnectError("down")]
    )
    result = await call_tool(
        "bulk_create_tasks",
        {"list_id": "111", "tasks": [{"name": "one"}, {"name": "two"}]},
    )
    body = json.loads(result[0].text)
    assert body["total"] == 2
    assert body["successful"] == 1
    assert body["results"][0]["success"] is True
    assert body["results"][1]["success"] is False
    assert "down" in body["results"][1]["error"]


async def test_bulk_update_tasks_pops_id_and_puts_the_rest(call_tool, mocked_clickup):
    route = mocked_clickup.put("/task/t1").mock(
        return_value=httpx.Response(200, json={"id": "t1"})
    )
    result = await call_tool(
        "bulk_update_tasks",
        {"tasks": [{"id": "t1", "status": "done"}]},
    )
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body == {"status": "done"}
    body = json.loads(result[0].text)
    assert body["results"][0]["task_id"] == "t1"
    assert body["successful"] == 1


async def test_bulk_delete_tasks_reports_success_count(call_tool, mocked_clickup):
    mocked_clickup.delete("/task/t1").mock(return_value=httpx.Response(200))
    mocked_clickup.delete("/task/t2").mock(return_value=httpx.Response(200))
    result = await call_tool("bulk_delete_tasks", {"task_ids": ["t1", "t2"]})
    body = json.loads(result[0].text)
    assert body["total"] == 2
    assert body["successful"] == 2
    assert {r["task_id"] for r in body["results"]} == {"t1", "t2"}
