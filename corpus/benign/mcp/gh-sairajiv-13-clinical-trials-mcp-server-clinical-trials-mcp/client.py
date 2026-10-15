"""Async client for the ClinicalTrials.gov API v2.

One job: turn HTTP calls into parsed JSON, and turn HTTP failures into the
error types in :mod:`clinical_trials_mcp.errors`. Successful GET responses
are kept in a small in-memory cache keyed by the full request, because an
LLM session tends to ask about the same study several times in a row.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from .config import Settings
from .errors import (
    StudyNotFoundError,
    UpstreamDataError,
    UpstreamError,
    UpstreamUnavailableError,
)

USER_AGENT = "clinical-trials-mcp-server/0.1.0"
RETRY_BASE_DELAY_SECONDS = 0.25


class TrialsClient:
    """Client for the ClinicalTrials.gov API v2 (no API key required)."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings or Settings.from_env()
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        # cache key -> (expiry monotonic timestamp, payload)
        self._cache: dict[str, tuple[float, Any]] = {}

    # -- lifecycle ----------------------------------------------------------

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=self._settings.timeout_seconds,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                transport=self._transport,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> TrialsClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    # -- public API ----------------------------------------------------------

    async def search_studies(self, params: dict[str, str]) -> dict[str, Any]:
        """Run a study search. ``params`` are raw API v2 query parameters."""
        query = {"format": "json", "countTotal": "true", **params}
        return await self._get_json("/studies", query)

    async def get_study(self, nct_id: str) -> dict[str, Any]:
        """Fetch one study by NCT number. Raises StudyNotFoundError on 404."""
        try:
            return await self._get_json(f"/studies/{nct_id}", {"format": "json"})
        except UpstreamError as exc:
            if exc.status_code == 404:
                raise StudyNotFoundError(nct_id) from exc
            raise

    # -- internals -----------------------------------------------------------

    def _cache_key(self, path: str, params: dict[str, str]) -> str:
        parts = "&".join(f"{key}={params[key]}" for key in sorted(params))
        return f"{path}?{parts}"

    async def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        ttl = self._settings.cache_ttl_seconds
        key = self._cache_key(path, params)
        if ttl > 0:
            cached = self._cache.get(key)
            if cached is not None and cached[0] > time.monotonic():
                return cached[1]

        payload = await self._request_with_retries(path, params)

        if ttl > 0:
            self._cache[key] = (time.monotonic() + ttl, payload)
        return payload

    async def _request_with_retries(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        attempts = 1 + self._settings.max_retries
        http = await self._http()
        for attempt in range(attempts):
            last = attempt == attempts - 1
            try:
                response = await http.get(path, params=params)
            except httpx.HTTPError as exc:  # timeouts, DNS, connection resets
                if last:
                    raise UpstreamUnavailableError(attempts) from exc
                await asyncio.sleep(RETRY_BASE_DELAY_SECONDS * (2**attempt))
                continue
            if response.status_code >= 500:
                if last:
                    raise UpstreamUnavailableError(attempts)
                await asyncio.sleep(RETRY_BASE_DELAY_SECONDS * (2**attempt))
                continue
            if response.status_code >= 400:
                raise UpstreamError(response.status_code)
            try:
                payload = response.json()
            except ValueError as exc:
                raise UpstreamDataError() from exc
            if not isinstance(payload, dict):
                raise UpstreamDataError()
            return payload
        raise UpstreamUnavailableError(attempts)  # pragma: no cover - unreachable
