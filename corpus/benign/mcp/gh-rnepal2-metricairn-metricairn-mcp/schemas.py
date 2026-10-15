"""Public MCP schemas; the API remains the authority for validation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Dimension = Literal[
    "path",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "device",
    "browser",
    "os",
    "country",
    "event",
]


class AnalyticsFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Dimension
    values: list[str] = Field(min_length=1, max_length=30)


class AnalyticsPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: Literal["pageviews", "visitors", "sessions", "events", "event_count"] = "pageviews"
    event_name: str | None = Field(default=None, min_length=1, max_length=200)
    mode: Literal["total", "timeseries", "breakdown"] = "total"
    dimension: Dimension | None = None
    interval: Literal["day", "hour"] = "day"
    filters: list[AnalyticsFilter] = Field(default_factory=list, max_length=10)
    date_from: str | None = None
    date_to: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
