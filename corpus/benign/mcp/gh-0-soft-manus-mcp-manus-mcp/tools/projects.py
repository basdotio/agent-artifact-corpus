"""Tools for `/v2/project.*` endpoints."""

from __future__ import annotations

from manus_mcp.schemas.projects import (
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectListQuery,
    ProjectListResponse,
)
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_project_create",
    description=(
        "Create a new project with an optional default instruction that will be applied to "
        "every task created with this project_id."
    ),
    input_schema=ProjectCreateRequest,
    output_schema=ProjectCreateResponse,
)
async def project_create(req: ProjectCreateRequest, ctx: ToolCtx) -> ProjectCreateResponse:
    return await ctx.client.call(
        "POST",
        "/v2/project.create",
        json_body=req,
        response_model=ProjectCreateResponse,
        rate_limit_key="project.create",
    )


@manus_tool(
    name="manus_project_list",
    description="List all projects visible to the current user.",
    input_schema=ProjectListQuery,
    output_schema=ProjectListResponse,
)
async def project_list(q: ProjectListQuery, ctx: ToolCtx) -> ProjectListResponse:
    return await ctx.client.call(
        "GET",
        "/v2/project.list",
        response_model=ProjectListResponse,
        rate_limit_key="project.list",
    )
