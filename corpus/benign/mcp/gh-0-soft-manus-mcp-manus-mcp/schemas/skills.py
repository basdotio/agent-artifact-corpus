"""Schemas for `/v2/skill.*` endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from manus_mcp.schemas.common import ManusModel, ResponseEnvelope, UnixSeconds

SkillOwnerType = Literal["personal", "official", "team", "project"]


class CreatorInfo(ManusModel):
    model_config = ConfigDict(extra="allow")
    user_id: str | None = None
    name: str | None = None


class SkillRecord(ManusModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    description: str | None = None
    owner_type: SkillOwnerType | None = None
    creator_info: CreatorInfo | None = None
    created_at: UnixSeconds | None = None
    updated_at: UnixSeconds | None = None


class SkillListQuery(ManusModel):
    project_id: str | None = None


class SkillListResponse(ResponseEnvelope):
    data: list[SkillRecord] = []
