"""Tools for `/v2/file.*` endpoints (low-level). The composite upload is in composite.py."""

from __future__ import annotations

from manus_mcp.schemas.files import (
    FileCreateRequest,
    FileCreateResponse,
    FileDeleteRequest,
    FileDeleteResponse,
    FileDetailQuery,
    FileDetailResponse,
)
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_file_create",
    description=(
        "Create a file record and get a presigned S3 upload URL. You must PUT the bytes to "
        "upload_url within 3 minutes. Prefer manus_file_upload which performs the full flow "
        "(create + PUT + wait-until-uploaded) in one call."
    ),
    input_schema=FileCreateRequest,
    output_schema=FileCreateResponse,
)
async def file_create(req: FileCreateRequest, ctx: ToolCtx) -> FileCreateResponse:
    return await ctx.client.call(
        "POST",
        "/v2/file.upload",
        json_body=req,
        response_model=FileCreateResponse,
        rate_limit_key="file.upload",
    )


@manus_tool(
    name="manus_file_detail",
    description="Get a file's metadata including upload status, size, and expiration.",
    input_schema=FileDetailQuery,
    output_schema=FileDetailResponse,
)
async def file_detail(q: FileDetailQuery, ctx: ToolCtx) -> FileDetailResponse:
    return await ctx.client.call(
        "GET",
        "/v2/file.detail",
        params=q.model_dump(exclude_none=True),
        response_model=FileDetailResponse,
        rate_limit_key="file.detail",
    )


@manus_tool(
    name="manus_file_delete",
    description=(
        "Delete a file. Files auto-delete 48 hours after upload, so manual deletion is optional."
    ),
    input_schema=FileDeleteRequest,
    output_schema=FileDeleteResponse,
)
async def file_delete(req: FileDeleteRequest, ctx: ToolCtx) -> FileDeleteResponse:
    return await ctx.client.call(
        "POST",
        "/v2/file.delete",
        json_body=req,
        response_model=FileDeleteResponse,
        rate_limit_key="file.delete",
    )
