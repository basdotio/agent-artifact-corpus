"""Schemas for `/v2/connector.*` endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from manus_mcp.schemas.common import ManusModel, ResponseEnvelope

ConnectorType = Literal["builtin", "byok", "mcp"]


class ConnectorRecord(ManusModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str | None = None
    type: ConnectorType | None = None
    description: str | None = None
    category: str | None = None


class ConnectorListQuery(ManusModel):
    pass


class ConnectorListResponse(ResponseEnvelope):
    data: list[ConnectorRecord] = []
