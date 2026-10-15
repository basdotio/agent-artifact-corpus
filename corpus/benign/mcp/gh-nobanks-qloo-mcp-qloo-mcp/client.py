"""Async HTTP client for the Qloo Taste AI API.

Only the endpoints and parameters documented in the project PRD are used.
The API key is read from the QLOO_API_KEY environment variable and is never
logged, echoed, or included in any error message.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from .schemas import (
    GetDemographicsInput,
    GetInsightsInput,
    GetTasteAnalysisInput,
    ListAudiencesInput,
    SearchEntitiesInput,
    SearchTagsInput,
)

QLOO_API_URL_DEFAULT = "https://hackathon.api.qloo.com"
QLOO_API_KEY_ENV = "QLOO_API_KEY"
QLOO_API_URL_ENV = "QLOO_API_URL"
QLOO_TIMEOUT_ENV = "QLOO_TIMEOUT_SECONDS"

DEMOGRAPHICS_TYPE = "urn:demographics"
TAG_TYPE = "urn:tag"


class QlooAPIError(Exception):
    """Raised when the Qloo API returns a non-2xx response or a network error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_stringify(item) for item in value)
    return str(value)


def _clean_params(params: dict[str, Any]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        if isinstance(value, (list, tuple)) and len(value) == 0:
            continue
        cleaned[key] = _stringify(value)
    return cleaned


class QlooClient:
    """Thin async wrapper around the Qloo REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        resolved_key = api_key if api_key is not None else os.environ.get(QLOO_API_KEY_ENV, "")
        resolved_key = (resolved_key or "").strip()
        if not resolved_key:
            raise ValueError("QLOO_API_KEY environment variable is required")
        self._api_key = resolved_key

        resolved_url = base_url if base_url is not None else os.environ.get(QLOO_API_URL_ENV)
        resolved_url = (resolved_url or QLOO_API_URL_DEFAULT).strip()
        self._base_url = resolved_url.rstrip("/")

        if timeout is not None:
            self._timeout = float(timeout)
        else:
            raw_timeout = os.environ.get(QLOO_TIMEOUT_ENV)
            try:
                self._timeout = float(raw_timeout) if raw_timeout else 30.0
            except (TypeError, ValueError):
                self._timeout = 30.0

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout(self) -> float:
        return self._timeout

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self._api_key,
            "Accept": "application/json",
        }

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        query = _clean_params(params)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as http:
                response = await http.get(url, params=query, headers=self._headers())
        except httpx.HTTPError as exc:
            raise QlooAPIError(f"Network error: {exc}") from exc

        if response.status_code < 200 or response.status_code >= 300:
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = response.text
            raise QlooAPIError(
                f"Qloo API error {response.status_code}",
                response.status_code,
                body,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise QlooAPIError("Qloo API returned a non-JSON response") from exc
        if not isinstance(payload, dict):
            raise QlooAPIError("Qloo API returned an unexpected response shape")
        return payload

    async def search_entities(self, inp: SearchEntitiesInput) -> dict[str, Any]:
        params: dict[str, Any] = {
            "query": inp.query,
            "types": list(inp.types),
            "take": inp.take,
            "page": inp.page,
            "filter.location": inp.location,
            "filter.radius": inp.radius_miles,
        }
        return await self._get("/search", params)

    async def search_tags(self, inp: SearchTagsInput) -> dict[str, Any]:
        params: dict[str, Any] = {
            "filter.query": inp.query,
            "filter.tag.types": list(inp.tag_types),
            "filter.parents.types": list(inp.parent_types),
            "take": inp.take,
            "page": inp.page,
        }
        return await self._get("/v2/tags", params)

    async def list_audiences(self, inp: ListAudiencesInput) -> dict[str, Any]:
        params: dict[str, Any] = {
            "filter.audience.types": list(inp.audience_types),
            "take": inp.take,
            "page": inp.page,
        }
        return await self._get("/v2/audiences", params)

    async def get_insights(self, inp: GetInsightsInput) -> dict[str, Any]:
        params: dict[str, Any] = {
            "filter.type": inp.entity_type,
            "signal.interests.entities": list(inp.entity_ids),
            "signal.interests.tags": list(inp.tag_ids),
            "signal.demographics.audiences": list(inp.audience_ids),
            "signal.demographics.age": inp.age,
            "signal.demographics.gender": inp.gender,
            "signal.location.query": inp.signal_location,
            "filter.location.query": inp.filter_location,
            "filter.tags": list(inp.filter_tag_ids),
            "filter.popularity.min": inp.popularity_min,
            "take": inp.take,
            "page": inp.page,
        }
        if inp.explain:
            params["feature.explainability"] = True
        return await self._get("/v2/insights", params)

    async def get_demographics(self, inp: GetDemographicsInput) -> dict[str, Any]:
        params: dict[str, Any] = {
            "filter.type": DEMOGRAPHICS_TYPE,
            "signal.interests.entities": list(inp.entity_ids),
            "signal.interests.tags": list(inp.tag_ids),
        }
        return await self._get("/v2/insights", params)

    async def get_taste_analysis(self, inp: GetTasteAnalysisInput) -> dict[str, Any]:
        params: dict[str, Any] = {
            "filter.type": TAG_TYPE,
            "signal.interests.entities": list(inp.entity_ids),
            "signal.interests.tags": list(inp.tag_ids),
            "signal.demographics.audiences": list(inp.audience_ids),
            "signal.location.query": inp.location,
            "filter.tag.types": list(inp.tag_types),
            "filter.parents.types": list(inp.parent_types),
            "take": inp.take,
        }
        return await self._get("/v2/insights", params)
