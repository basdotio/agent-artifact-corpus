"""Tools for `/v2/website.*` endpoints."""

from __future__ import annotations

from manus_mcp.schemas.website import (
    WebsiteListCheckpointsQuery,
    WebsiteListCheckpointsResponse,
    WebsitePublishRequest,
    WebsitePublishResponse,
    WebsiteStatusQuery,
    WebsiteStatusResponse,
)
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_website_status",
    description=(
        "Get a website's publish status, live URLs, and visibility. Provide exactly one of "
        "task_id or website_id."
    ),
    input_schema=WebsiteStatusQuery,
    output_schema=WebsiteStatusResponse,
)
async def website_status(q: WebsiteStatusQuery, ctx: ToolCtx) -> WebsiteStatusResponse:
    return await ctx.client.call(
        "GET",
        "/v2/website.status",
        params=q.model_dump(exclude_none=True),
        response_model=WebsiteStatusResponse,
        rate_limit_key="website.status",
    )


@manus_tool(
    name="manus_website_list_checkpoints",
    description=(
        "List all checkpoints of a website (newest first). Match published_version_id against "
        "data[].version_id to find the live checkpoint."
    ),
    input_schema=WebsiteListCheckpointsQuery,
    output_schema=WebsiteListCheckpointsResponse,
)
async def website_list_checkpoints(
    q: WebsiteListCheckpointsQuery, ctx: ToolCtx
) -> WebsiteListCheckpointsResponse:
    return await ctx.client.call(
        "GET",
        "/v2/website.listCheckpoints",
        params=q.model_dump(exclude_none=True),
        response_model=WebsiteListCheckpointsResponse,
        rate_limit_key="website.listCheckpoints",
    )


@manus_tool(
    name="manus_website_publish",
    description=(
        "Deploy the latest checkpoint of a website. Async — poll manus_website_status until "
        "publish_status becomes 'published' or 'failed', or use manus_website_publish_and_wait "
        "for an all-in-one call."
    ),
    input_schema=WebsitePublishRequest,
    output_schema=WebsitePublishResponse,
)
async def website_publish(req: WebsitePublishRequest, ctx: ToolCtx) -> WebsitePublishResponse:
    return await ctx.client.call(
        "POST",
        "/v2/website.publish",
        json_body=req,
        response_model=WebsitePublishResponse,
        rate_limit_key="website.publish",
    )
