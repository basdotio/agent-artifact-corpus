"""Tools for `/v2/usage.*` endpoints."""

from __future__ import annotations

from manus_mcp.schemas.usage import (
    UsageListQuery,
    UsageListResponse,
    UsageTeamLogQuery,
    UsageTeamLogResponse,
    UsageTeamStatisticQuery,
    UsageTeamStatisticResponse,
)
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_usage_list",
    description="List the current user's credit history at session granularity (newest first).",
    input_schema=UsageListQuery,
    output_schema=UsageListResponse,
)
async def usage_list(q: UsageListQuery, ctx: ToolCtx) -> UsageListResponse:
    return await ctx.client.call(
        "GET",
        "/v2/usage.list",
        params=q.model_dump(exclude_none=True),
        response_model=UsageListResponse,
        rate_limit_key="usage.list",
    )


@manus_tool(
    name="manus_usage_team_statistic",
    description=(
        "Daily team credit consumption totals. Team accounts only; members see only their own "
        "totals. Optional start_date / end_date filter (Unix seconds)."
    ),
    input_schema=UsageTeamStatisticQuery,
    output_schema=UsageTeamStatisticResponse,
)
async def usage_team_statistic(
    q: UsageTeamStatisticQuery, ctx: ToolCtx
) -> UsageTeamStatisticResponse:
    return await ctx.client.call(
        "GET",
        "/v2/usage.teamStatistic",
        params=q.model_dump(exclude_none=True),
        response_model=UsageTeamStatisticResponse,
        rate_limit_key="usage.teamStatistic",
    )


@manus_tool(
    name="manus_usage_team_log",
    description=(
        "Per-user team statistics (task counts + credit totals). Team accounts only; members "
        "see only their own row. Enterprise teams have T+1 latency."
    ),
    input_schema=UsageTeamLogQuery,
    output_schema=UsageTeamLogResponse,
)
async def usage_team_log(q: UsageTeamLogQuery, ctx: ToolCtx) -> UsageTeamLogResponse:
    return await ctx.client.call(
        "GET",
        "/v2/usage.teamLog",
        params=q.model_dump(exclude_none=True),
        response_model=UsageTeamLogResponse,
        rate_limit_key="usage.teamLog",
    )
