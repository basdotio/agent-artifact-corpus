"""Tools for `/v2/skill.*` endpoints."""

from __future__ import annotations

from manus_mcp.schemas.skills import SkillListQuery, SkillListResponse
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_skill_list",
    description=(
        "List available skills. Provide project_id to include project-specific skills "
        "in addition to global user skills."
    ),
    input_schema=SkillListQuery,
    output_schema=SkillListResponse,
)
async def skill_list(q: SkillListQuery, ctx: ToolCtx) -> SkillListResponse:
    return await ctx.client.call(
        "GET",
        "/v2/skill.list",
        params=q.model_dump(exclude_none=True),
        response_model=SkillListResponse,
        rate_limit_key="skill.list",
    )
