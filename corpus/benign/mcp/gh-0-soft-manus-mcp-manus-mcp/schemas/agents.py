"""Schemas for `/v2/agent.*` endpoints."""

from __future__ import annotations

from pydantic import ConfigDict

from manus_mcp.schemas.common import ManusModel, ResponseEnvelope


class AgentRecord(ManusModel):
    model_config = ConfigDict(extra="allow")
    id: str
    task_id: str | None = None
    nickname: str | None = None
    about: str | None = None


class AgentListQuery(ManusModel):
    pass


class AgentListResponse(ResponseEnvelope):
    data: list[AgentRecord] = []


class AgentDetailQuery(ManusModel):
    agent_id: str


class AgentDetailResponse(ResponseEnvelope):
    agent: AgentRecord


class AgentUpdateRequest(ManusModel):
    agent_id: str
    nickname: str | None = None
    about: str | None = None


class AgentUpdateResponse(ResponseEnvelope):
    agent: AgentRecord
