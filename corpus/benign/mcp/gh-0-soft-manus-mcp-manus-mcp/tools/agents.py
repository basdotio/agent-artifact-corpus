"""Tools for `/v2/agent.*` endpoints."""

from __future__ import annotations

from manus_mcp.schemas.agents import (
    AgentDetailQuery,
    AgentDetailResponse,
    AgentListQuery,
    AgentListResponse,
    AgentUpdateRequest,
    AgentUpdateResponse,
)
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_agent_list",
    description="List all agents in the account.",
    input_schema=AgentListQuery,
    output_schema=AgentListResponse,
)
async def agent_list(q: AgentListQuery, ctx: ToolCtx) -> AgentListResponse:
    return await ctx.client.call(
        "GET",
        "/v2/agent.list",
        response_model=AgentListResponse,
        rate_limit_key="agent.list",
    )


@manus_tool(
    name="manus_agent_detail",
    description=(
        "Get an agent's details including nickname and description. "
        "The 'agent-default' shortcut works only when your account has a configured "
        "IM agent; otherwise this returns 'not_found'. Use manus_agent_list to "
        "discover real agent_ids if 'agent-default' is rejected."
    ),
    input_schema=AgentDetailQuery,
    output_schema=AgentDetailResponse,
)
async def agent_detail(q: AgentDetailQuery, ctx: ToolCtx) -> AgentDetailResponse:
    return await ctx.client.call(
        "GET",
        "/v2/agent.detail",
        params=q.model_dump(exclude_none=True),
        response_model=AgentDetailResponse,
        rate_limit_key="agent.detail",
    )


@manus_tool(
    name="manus_agent_update",
    description="Update an agent's nickname and/or description.",
    input_schema=AgentUpdateRequest,
    output_schema=AgentUpdateResponse,
)
async def agent_update(req: AgentUpdateRequest, ctx: ToolCtx) -> AgentUpdateResponse:
    return await ctx.client.call(
        "POST",
        "/v2/agent.update",
        json_body=req,
        response_model=AgentUpdateResponse,
        rate_limit_key="agent.update",
    )
