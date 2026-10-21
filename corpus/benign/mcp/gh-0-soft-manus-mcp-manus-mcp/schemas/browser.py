"""Schemas for `/v2/browser.*` endpoints."""

from __future__ import annotations

from pydantic import ConfigDict

from manus_mcp.schemas.common import ManusModel, ResponseEnvelope


class BrowserClient(ManusModel):
    model_config = ConfigDict(extra="allow")
    client_id: str
    client_name: str | None = None
    ua: str | None = None


class BrowserOnlineListQuery(ManusModel):
    pass


class BrowserOnlineListResponse(ResponseEnvelope):
    data: list[BrowserClient] = []
