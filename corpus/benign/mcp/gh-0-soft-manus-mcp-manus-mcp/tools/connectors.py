"""Tools for `/v2/connector.*` endpoints."""

from __future__ import annotations

from manus_mcp.schemas.connectors import ConnectorListQuery, ConnectorListResponse
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_connector_list",
    description=(
        "List all connectors installed in the account. Use the returned IDs in the connectors "
        "array of manus_task_create / manus_task_send_message."
    ),
    input_schema=ConnectorListQuery,
    output_schema=ConnectorListResponse,
)
async def connector_list(q: ConnectorListQuery, ctx: ToolCtx) -> ConnectorListResponse:
    return await ctx.client.call(
        "GET",
        "/v2/connector.list",
        response_model=ConnectorListResponse,
        rate_limit_key="connector.list",
    )
