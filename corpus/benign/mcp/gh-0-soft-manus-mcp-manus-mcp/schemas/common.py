"""Shared pydantic primitives."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _coerce_int(v: Any) -> Any:
    """Accept both strings and numbers from the API; coerce to int."""
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            return int(float(s))
    if isinstance(v, float):
        return int(v)
    return v


# Timestamps and numeric IDs often arrive as strings from the Manus API.
UnixSeconds = Annotated[int, BeforeValidator(_coerce_int)]
IntField = Annotated[int, BeforeValidator(_coerce_int)]


class ManusModel(BaseModel):
    """Base model: forbid unknown keys on request inputs but tolerate extras on responses."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=False)


class ResponseEnvelope(ManusModel):
    """Every Manus response starts with `ok` + `request_id`."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    ok: Literal[True] = True
    request_id: str | None = None


class PaginationQuery(ManusModel):
    """Standard cursor-based pagination query."""

    limit: int | None = Field(default=None, ge=1, le=200)
    cursor: str | None = None


class DatedPaginationQuery(PaginationQuery):
    """Pagination + date-range filter used by usage endpoints."""

    start_date: int | None = Field(default=None, description="Unix timestamp in seconds")
    end_date: int | None = Field(default=None, description="Unix timestamp in seconds")
