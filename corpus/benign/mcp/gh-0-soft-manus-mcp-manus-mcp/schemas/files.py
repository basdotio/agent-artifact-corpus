"""Schemas for `/v2/file.*` endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from manus_mcp.schemas.common import IntField, ManusModel, ResponseEnvelope, UnixSeconds

FileStatus = Literal["pending", "uploaded", "deleted", "error"]


class FileRecord(ManusModel):
    model_config = ConfigDict(extra="allow")
    id: str
    filename: str | None = None
    status: FileStatus | None = None
    created_at: UnixSeconds | None = None
    bytes: IntField | None = None
    content_type: str | None = None
    expires_at: UnixSeconds | None = None
    error_message: str | None = None


class FileCreateRequest(ManusModel):
    filename: str


class FileCreateResponse(ResponseEnvelope):
    file: FileRecord
    upload_url: str
    upload_expires_at: UnixSeconds | None = None


class FileDetailQuery(ManusModel):
    file_id: str


class FileDetailResponse(ResponseEnvelope):
    file: FileRecord


class FileDeleteRequest(ManusModel):
    file_id: str


class FileDeleteResponse(ResponseEnvelope):
    pass
