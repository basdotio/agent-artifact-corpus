"""Schemas for `/v2/project.*` endpoints."""

from __future__ import annotations

from pydantic import ConfigDict

from manus_mcp.schemas.common import ManusModel, ResponseEnvelope, UnixSeconds


class ProjectRecord(ManusModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    created_at: UnixSeconds | None = None
    instruction: str | None = None


class ProjectCreateRequest(ManusModel):
    name: str
    instruction: str | None = None


class ProjectCreateResponse(ResponseEnvelope):
    project: ProjectRecord


class ProjectListQuery(ManusModel):
    pass


class ProjectListResponse(ResponseEnvelope):
    data: list[ProjectRecord] = []
