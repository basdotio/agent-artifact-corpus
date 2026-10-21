"""Schemas for `/v2/webhook.*` endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from manus_mcp.schemas.common import ManusModel, ResponseEnvelope, UnixSeconds

WebhookStatus = Literal["active", "inactive"]


class WebhookRecord(ManusModel):
    model_config = ConfigDict(extra="allow")
    id: str
    url: str
    status: WebhookStatus | None = None
    created_at: UnixSeconds | None = None


class WebhookCreateRequest(ManusModel):
    url: str


class WebhookCreateResponse(ResponseEnvelope):
    webhook: WebhookRecord


class WebhookListQuery(ManusModel):
    pass


class WebhookListResponse(ResponseEnvelope):
    data: list[WebhookRecord] = []


class WebhookDeleteRequest(ManusModel):
    webhook_id: str


class WebhookDeleteResponse(ResponseEnvelope):
    pass


class WebhookPublicKeyQuery(ManusModel):
    pass


class WebhookPublicKeyResponse(ResponseEnvelope):
    public_key: str
    algorithm: str | None = None
