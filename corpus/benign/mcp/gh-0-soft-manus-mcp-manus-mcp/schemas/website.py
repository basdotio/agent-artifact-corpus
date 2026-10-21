"""Schemas for `/v2/website.*` endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, model_validator

from manus_mcp.schemas.common import ManusModel, ResponseEnvelope, UnixSeconds

PublishStatus = Literal["unpublished", "publishing", "published", "failed"]
WebsiteVisibility = Literal["public", "team", "private"]
CheckpointStatus = Literal["pending", "success", "failed", "unspecified"]


class _WebsiteTarget(ManusModel):
    """Helper: exactly one of task_id / website_id must be provided."""

    task_id: str | None = None
    website_id: str | None = None

    @model_validator(mode="after")
    def _one_of(self) -> _WebsiteTarget:
        if (self.task_id is None) == (self.website_id is None):
            raise ValueError("Exactly one of task_id or website_id must be provided")
        return self


class WebsiteStatusQuery(_WebsiteTarget):
    pass


class WebsiteStatusResponse(ResponseEnvelope):
    website_id: str
    publish_status: PublishStatus
    site_urls: list[str] = []
    version_id: str | None = None
    status_updated_at: UnixSeconds | None = None
    visibility: WebsiteVisibility | None = None


class Checkpoint(ManusModel):
    model_config = ConfigDict(extra="allow")
    version_id: str
    message: str | None = None
    status: CheckpointStatus | None = None
    created_at: UnixSeconds | None = None


class WebsiteListCheckpointsQuery(_WebsiteTarget):
    pass


class WebsiteListCheckpointsResponse(ResponseEnvelope):
    website_id: str
    data: list[Checkpoint] = []
    published_version_id: str | None = None


class WebsitePublishRequest(_WebsiteTarget):
    visibility: WebsiteVisibility | None = None


class WebsitePublishResponse(ResponseEnvelope):
    website_id: str
    version_id: str
