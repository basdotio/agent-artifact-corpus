"""Exact provider requests with a small, inspectable transport envelope."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

import httpx


ENDPOINTS = {
    "context": {
        "search": "/v1/web/search",
        "scrape": "/v1/web/scrape",
    },
    "exa": {
        "search": "/search",
        "contents": "/contents",
    },
    "firecrawl": {
        "search": "/v2/search",
        "scrape": "/v2/scrape",
    },
    "parallel": {
        "search": "/v1/search",
        "extract": "/v1/extract",
    },
}

BASE_URLS = {
    "context": "https://api.context.dev",
    "exa": "https://api.exa.ai",
    "firecrawl": "https://api.firecrawl.dev",
    "parallel": "https://api.parallel.ai",
}

KEY_NAMES = {
    "context": "CONTEXT_API_KEY",
    "exa": "EXA_API_KEY",
    "firecrawl": "FIRECRAWL_API_KEY",
    "parallel": "PARALLEL_API_KEY",
}


@dataclass(frozen=True)
class ToolResult:
    provider: str
    operation: str
    endpoint: str
    started_at: str
    elapsed_ms: float
    request: dict[str, Any]
    status_code: int | None
    response: Any
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResearchClient:
    """Call provider APIs without hiding cache controls, errors, or source data.

    No automatic retries, truncation, grading, or cross-provider normalization.
    A caller can compare like operations while retaining the actual wire payload.
    """

    def __init__(
        self,
        *,
        keys: Mapping[str, str] | None = None,
        timeout: float = 90.0,
        base_urls: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.keys = dict(keys or {})
        self.base_urls = {
            provider: os.environ.get(f"WEB_RESEARCH_{provider.upper()}_BASE_URL", url)
            for provider, url in BASE_URLS.items()
        } | dict(base_urls or {})
        self.http = httpx.Client(timeout=timeout, transport=transport)

    def __enter__(self) -> ResearchClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.http.close()

    def call(self, provider: str, operation: str, request: Mapping[str, Any]) -> ToolResult:
        if provider not in ENDPOINTS or operation not in ENDPOINTS[provider]:
            raise ValueError(f"Unsupported provider operation: {provider}.{operation}")
        if not isinstance(request, Mapping):
            raise TypeError("request must be a JSON object")
        key = self.keys.get(provider) or os.environ.get(KEY_NAMES[provider])
        if not key:
            raise ValueError(f"Set {KEY_NAMES[provider]} before calling {provider}")
        payload = dict(request)
        endpoint = self.base_urls[provider].rstrip("/") + ENDPOINTS[provider][operation]
        headers = {"Content-Type": "application/json"}
        if provider in ("context", "firecrawl"):
            headers["Authorization"] = f"Bearer {key}"
        else:
            headers["x-api-key"] = key
        started_at = datetime.now(timezone.utc).isoformat()
        start = time.perf_counter()
        status_code: int | None = None
        response_body: Any = None
        error: str | None = None
        try:
            response = self.http.post(endpoint, json=payload, headers=headers)
            status_code = response.status_code
            try:
                response_body = response.json()
            except ValueError:
                response_body = response.text
            if response.is_error:
                error = f"HTTP {status_code}"
        except httpx.RequestError as exc:
            error = type(exc).__name__ + ": " + str(exc)
        return ToolResult(
            provider=provider,
            operation=operation,
            endpoint=endpoint,
            started_at=started_at,
            elapsed_ms=round((time.perf_counter() - start) * 1000, 3),
            request=payload,
            status_code=status_code,
            response=response_body,
            error=error,
        )
