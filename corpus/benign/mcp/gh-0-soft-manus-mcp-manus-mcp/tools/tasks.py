"""Tools for `/v2/task.*` endpoints."""

from __future__ import annotations

from manus_mcp.schemas.tasks import (
    TaskConfirmActionRequest,
    TaskConfirmActionResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskDeleteRequest,
    TaskDeleteResponse,
    TaskDetailQuery,
    TaskDetailResponse,
    TaskListMessagesQuery,
    TaskListMessagesResponse,
    TaskListQuery,
    TaskListResponse,
    TaskSendMessageRequest,
    TaskSendMessageResponse,
    TaskStopRequest,
    TaskStopResponse,
    TaskUpdateRequest,
    TaskUpdateResponse,
)
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_task_create",
    description=(
        "Create a new Manus task. Runs asynchronously; poll manus_task_list_messages or use "
        "manus_task_wait for completion. Supports text/file/voice content parts, connectors, "
        "skills, project scoping, and interactive mode."
    ),
    input_schema=TaskCreateRequest,
    output_schema=TaskCreateResponse,
)
async def task_create(req: TaskCreateRequest, ctx: ToolCtx) -> TaskCreateResponse:
    return await ctx.client.call(
        "POST",
        "/v2/task.create",
        json_body=req,
        response_model=TaskCreateResponse,
        rate_limit_key="task.create",
    )


@manus_tool(
    name="manus_task_detail",
    description=(
        "Get a task's status and metadata. Use manus_task_list_messages for the full "
        "conversation history. Accepts the IM shortcut 'agent-default-main_task'."
    ),
    input_schema=TaskDetailQuery,
    output_schema=TaskDetailResponse,
)
async def task_detail(q: TaskDetailQuery, ctx: ToolCtx) -> TaskDetailResponse:
    return await ctx.client.call(
        "GET",
        "/v2/task.detail",
        params=q.model_dump(exclude_none=True),
        response_model=TaskDetailResponse,
        rate_limit_key="task.detail",
    )


@manus_tool(
    name="manus_task_list",
    description=(
        "List tasks with cursor pagination. scope='agent_subtask' requires agent_id; "
        "scope='project' requires project_id."
    ),
    input_schema=TaskListQuery,
    output_schema=TaskListResponse,
)
async def task_list(q: TaskListQuery, ctx: ToolCtx) -> TaskListResponse:
    return await ctx.client.call(
        "GET",
        "/v2/task.list",
        params=q.model_dump(exclude_none=True),
        response_model=TaskListResponse,
        rate_limit_key="task.list",
    )


@manus_tool(
    name="manus_task_update",
    description="Rename a task or change share visibility / task-list visibility.",
    input_schema=TaskUpdateRequest,
    output_schema=TaskUpdateResponse,
)
async def task_update(req: TaskUpdateRequest, ctx: ToolCtx) -> TaskUpdateResponse:
    return await ctx.client.call(
        "POST",
        "/v2/task.update",
        json_body=req,
        response_model=TaskUpdateResponse,
        rate_limit_key="task.update",
    )


@manus_tool(
    name="manus_task_stop",
    description="Stop a running task. The task can be resumed with manus_task_send_message.",
    input_schema=TaskStopRequest,
    output_schema=TaskStopResponse,
)
async def task_stop(req: TaskStopRequest, ctx: ToolCtx) -> TaskStopResponse:
    return await ctx.client.call(
        "POST",
        "/v2/task.stop",
        json_body=req,
        response_model=TaskStopResponse,
        rate_limit_key="task.stop",
    )


@manus_tool(
    name="manus_task_delete",
    description=(
        "Permanently delete a task. Agent-related tasks (main tasks, subtasks) cannot be deleted."
    ),
    input_schema=TaskDeleteRequest,
    output_schema=TaskDeleteResponse,
)
async def task_delete(req: TaskDeleteRequest, ctx: ToolCtx) -> TaskDeleteResponse:
    return await ctx.client.call(
        "POST",
        "/v2/task.delete",
        json_body=req,
        response_model=TaskDeleteResponse,
        rate_limit_key="task.delete",
    )


@manus_tool(
    name="manus_task_send_message",
    description=(
        "Send a follow-up message to a task. Use this when waiting_for_event_type='messageAskUser' "
        "(NOT manus_task_confirm_action). Accepts the same content structure as manus_task_create."
    ),
    input_schema=TaskSendMessageRequest,
    output_schema=TaskSendMessageResponse,
)
async def task_send_message(req: TaskSendMessageRequest, ctx: ToolCtx) -> TaskSendMessageResponse:
    return await ctx.client.call(
        "POST",
        "/v2/task.sendMessage",
        json_body=req,
        response_model=TaskSendMessageResponse,
        rate_limit_key="task.sendMessage",
    )


@manus_tool(
    name="manus_task_list_messages",
    description=(
        "List task events with cursor pagination. verbose=true includes tool_used, plan_update, "
        "new_plan_step, and explanation events. Inspect status_update events for agent_status."
    ),
    input_schema=TaskListMessagesQuery,
    output_schema=TaskListMessagesResponse,
)
async def task_list_messages(q: TaskListMessagesQuery, ctx: ToolCtx) -> TaskListMessagesResponse:
    return await ctx.client.call(
        "GET",
        "/v2/task.listMessages",
        params=q.model_dump(exclude_none=True),
        response_model=TaskListMessagesResponse,
        rate_limit_key="task.listMessages",
    )


@manus_tool(
    name="manus_task_confirm_action",
    description=(
        "Confirm a pending action. Use when a status_update event reports agent_status='waiting' "
        "with waiting_for_event_type != 'messageAskUser'. Pass event_id from the event and an "
        "input dict matching the event's confirm_input_schema (e.g. {'accept': true} for most "
        "events, {'action': 'select', 'client_id': '...'} for needConnectMyBrowser)."
    ),
    input_schema=TaskConfirmActionRequest,
    output_schema=TaskConfirmActionResponse,
)
async def task_confirm_action(
    req: TaskConfirmActionRequest, ctx: ToolCtx
) -> TaskConfirmActionResponse:
    return await ctx.client.call(
        "POST",
        "/v2/task.confirmAction",
        json_body=req,
        response_model=TaskConfirmActionResponse,
        rate_limit_key="task.confirmAction",
    )
