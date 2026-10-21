"""Schemas for `/v2/usage.*` endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field

from manus_mcp.schemas.common import IntField, ManusModel, ResponseEnvelope, UnixSeconds

UsageType = Literal["cost", "refund", "grant"]


class CollaborateInfo(ManusModel):
    model_config = ConfigDict(extra="allow")
    user_id: str | None = None
    user_name: str | None = None
    credits: IntField | None = None


class UsageRecord(ManusModel):
    model_config = ConfigDict(extra="allow")
    task_id: str | None = None
    title: str | None = None
    credits: IntField | None = None
    created_at: UnixSeconds | None = None
    type: UsageType | None = None
    collaborate_infos: list[CollaborateInfo] | None = None


class UsageListQuery(ManusModel):
    limit: int | None = Field(default=None, ge=1, le=100)
    cursor: str | None = None


class UsageListResponse(ResponseEnvelope):
    data: list[UsageRecord] = []
    has_more: bool | None = None
    next_cursor: str | None = None


class TeamDailyStatistic(ManusModel):
    model_config = ConfigDict(extra="allow")
    date: UnixSeconds
    credits: IntField


class UsageTeamStatisticQuery(ManusModel):
    start_date: int | None = None
    end_date: int | None = None


class UsageTeamStatisticResponse(ResponseEnvelope):
    data: list[TeamDailyStatistic] = []


class TeamLogEntry(ManusModel):
    model_config = ConfigDict(extra="allow")
    user_id: str | None = None
    user_name: str | None = None
    email: str | None = None
    task_count: IntField | None = None
    credits: IntField | None = None


class UsageTeamLogQuery(ManusModel):
    limit: int | None = Field(default=None, ge=1, le=100)
    cursor: str | None = None
    start_date: int | None = None
    end_date: int | None = None
    sort_by: Literal["task_count", "credits"] | None = None
    is_asc: bool | None = None


class UsageTeamLogResponse(ResponseEnvelope):
    data: list[TeamLogEntry] = []
    has_more: bool | None = None
    next_cursor: str | None = None
