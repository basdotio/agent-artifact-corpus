"""MCP tools for reading events from the webhook store."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from manus_mcp.config import load_settings
from manus_mcp.schemas.common import ManusModel, ResponseEnvelope
from manus_mcp.tools.registry import ToolCtx, manus_tool
from manus_mcp.webhook_receiver.storage import EventStore, StoredEvent


def _store() -> EventStore:
    # Re-read settings each call so the path can change without restart during dev.
    return EventStore(load_settings().manus_webhook_db_path)


class _EventDTO(ManusModel):
    model_config = ConfigDict(extra="allow")
    event_id: str
    event_type: str
    task_id: str | None = None
    received_at: int
    body: dict[str, Any]
    headers: dict[str, str]


def _to_dto(e: StoredEvent) -> _EventDTO:
    return _EventDTO(
        event_id=e.event_id,
        event_type=e.event_type,
        task_id=e.task_id,
        received_at=e.received_at,
        body=e.body,
        headers=e.headers,
    )


class WebhookEventsListRequest(ManusModel):
    event_type: str | None = None
    task_id: str | None = None
    since_received_at: int | None = Field(
        default=None, description="Unix seconds. Only events strictly newer are returned."
    )
    limit: int = Field(default=50, ge=1, le=500)
    order: str = Field(default="desc", pattern="^(asc|desc)$")


class WebhookEventsListResponse(ResponseEnvelope):
    data: list[_EventDTO]
    count: int


@manus_tool(
    name="manus_webhook_events_list",
    description=(
        "List webhook events received by the local webhook receiver. Filter by event_type "
        "('task_created' / 'task_stopped') and/or task_id. Requires the webhook receiver to be "
        "running (see manus-mcp-webhook)."
    ),
    input_schema=WebhookEventsListRequest,
    output_schema=WebhookEventsListResponse,
)
async def webhook_events_list(
    req: WebhookEventsListRequest, _ctx: ToolCtx
) -> WebhookEventsListResponse:
    store = _store()
    events = store.list(
        event_type=req.event_type,
        task_id=req.task_id,
        since_received_at=req.since_received_at,
        limit=req.limit,
        order=req.order,
    )
    dtos = [_to_dto(e) for e in events]
    return WebhookEventsListResponse(data=dtos, count=len(dtos))


class WebhookEventsGetRequest(ManusModel):
    event_id: str


class WebhookEventsGetResponse(ResponseEnvelope):
    event: _EventDTO | None = None


@manus_tool(
    name="manus_webhook_events_get",
    description="Fetch a single webhook event by event_id.",
    input_schema=WebhookEventsGetRequest,
    output_schema=WebhookEventsGetResponse,
)
async def webhook_events_get(
    req: WebhookEventsGetRequest, _ctx: ToolCtx
) -> WebhookEventsGetResponse:
    e = _store().get(req.event_id)
    return WebhookEventsGetResponse(event=_to_dto(e) if e else None)


class WebhookEventsClearRequest(ManusModel):
    before_received_at: int | None = Field(
        default=None, description="Unix seconds. Delete events strictly older than this."
    )
    event_type: str | None = None
    task_id: str | None = None


class WebhookEventsClearResponse(ResponseEnvelope):
    deleted: int


@manus_tool(
    name="manus_webhook_events_clear",
    description=(
        "Delete webhook events from the local store. Provide any combination of filters; no "
        "filters = delete everything."
    ),
    input_schema=WebhookEventsClearRequest,
    output_schema=WebhookEventsClearResponse,
)
async def webhook_events_clear(
    req: WebhookEventsClearRequest, _ctx: ToolCtx
) -> WebhookEventsClearResponse:
    n = _store().clear(
        before_received_at=req.before_received_at,
        event_type=req.event_type,
        task_id=req.task_id,
    )
    return WebhookEventsClearResponse(deleted=n)
