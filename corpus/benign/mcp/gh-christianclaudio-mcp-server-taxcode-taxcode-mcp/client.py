"""Asynchronous HTTP client with connection pooling, retries, and path sanitization."""

import asyncio
import random
import urllib.parse
from typing import Any
from urllib.parse import urlparse

import httpx

from taxcode_mcp import __version__
from taxcode_mcp.config import settings
from taxcode_mcp.errors import (
    AuthenticationError,
    RateLimitError,
    ResourceNotFoundError,
    TemplateError,
    redact_secrets,
)
from taxcode_mcp.ssrf import SSRFValidationError, validate_outbound_url, validate_resolved_host


def _legacy_base_url_message(exc: SSRFValidationError) -> str:
    """Map shared SSRF errors onto the base-URL messages callers already match."""
    host = exc.hostname or ""
    if exc.reason in {"scheme", "insecure_http"}:
        return "Only HTTPS is permitted for base URL."
    if exc.reason == "missing_hostname":
        return "Invalid base URL: missing hostname."
    if exc.reason == "blocked_hostname":
        return f"Blocked internal/loopback hostname in base URL: {host}"
    if exc.reason == "allowlist":
        return f"Hostname '{host}' is not in allowed hosts allowlist."
    if exc.reason == "blocked_ip":
        return f"Blocked private/reserved IP address in base URL: {host}"
    return str(exc)


def _validate_base_url(
    url: str,
    allowed_hosts_str: str | None = None,
    check_dns: bool = False,
) -> str:
    """Validate a config-controlled base URL via the shared SSRF helper.

    Template base URLs stay HTTPS-only. Blank input falls back to the configured
    default. DNS rebinding checks stay opt-in here and always run again at
    request time inside ``SSRFSafeAsyncTransport``.
    """
    if not url:
        return settings.BASE_URL.rstrip("/")

    allowed_raw = allowed_hosts_str if allowed_hosts_str is not None else settings.ALLOWED_HOSTS
    allowed_hosts = allowed_raw if allowed_raw.strip() else None
    try:
        validated = validate_outbound_url(url, allowed_hosts=allowed_hosts)
    except SSRFValidationError as exc:
        raise ValueError(_legacy_base_url_message(exc)) from exc

    if check_dns:
        hostname = urlparse(validated).hostname
        if hostname is not None:
            _validate_hostname_dns(hostname)
    return validated.rstrip("/")


def _validate_hostname_dns(hostname: str) -> None:
    """Validate resolved DNS IP addresses to defend against private IP binding and DNS rebinding."""
    try:
        validate_resolved_host(hostname)
    except SSRFValidationError as exc:
        if exc.reason == "dns_failure":
            raise ValueError(f"Could not resolve hostname in base URL: {hostname}") from exc
        if exc.resolved_ip is not None:
            raise ValueError(
                f"Blocked hostname '{hostname}' resolving to private/reserved IP: {exc.resolved_ip}"
            ) from exc
        if exc.reason == "blocked_ip":
            raise ValueError(f"Blocked private/reserved IP address: {hostname}") from exc
        raise ValueError(str(exc)) from exc


class SSRFSafeAsyncTransport(httpx.AsyncHTTPTransport):
    """Async HTTP transport enforcing DNS destination validation at request connection time."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Validate destination hostname via worker thread before dispatching HTTP request."""
        hostname = request.url.host
        if hostname:
            try:
                await asyncio.to_thread(_validate_hostname_dns, hostname)
            except ValueError as exc:
                raise TemplateError(
                    f"SSRF validation blocked request to {hostname}: {exc}"
                ) from exc
        return await super().handle_async_request(request)


class TemplateClient:
    """Hardened async client for interacting with upstream APIs."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        raw_url = (base_url or settings.BASE_URL).rstrip("/")
        self.base_url = _validate_base_url(raw_url, check_dns=False)
        self.api_key = api_key or settings.API_KEY
        self.timeout = timeout if timeout is not None else settings.TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.MAX_RETRIES
        self._custom_client = http_client
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        """Retrieve or initialize persistent AsyncClient pool."""
        if self._custom_client is not None:
            return self._custom_client
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/json",
                "User-Agent": f"mcp-server-taxcode/{__version__}",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            transport = SSRFSafeAsyncTransport(
                verify=True,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(self.timeout),
                transport=transport,
            )
        return self._client

    async def close(self) -> None:
        """Close underlying connection pool."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def sanitize_path_param(self, segment: str) -> str:
        """Encode path parameters to prevent directory traversal and path injection."""
        return urllib.parse.quote(str(segment), safe="").replace("..", "%2E%2E")

    @staticmethod
    def extract_list(container: Any, key: str | None = None) -> list[Any]:
        """Safely extract a list from a polymorphic upstream JSON response or field."""
        if key is not None:
            target = container.get(key) if isinstance(container, dict) else None
        else:
            target = container
        return target if isinstance(target, list) else []

    @staticmethod
    def extract_dict(container: Any, key: str | None = None) -> dict[str, Any]:
        """Safely extract a dictionary from a polymorphic upstream JSON response or field."""
        if key is not None:
            target = container.get(key) if isinstance(container, dict) else None
        else:
            target = container
        return target if isinstance(target, dict) else {}

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute request with exponential backoff and randomized jitter."""
        client = await self.get_client()
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                )

                if response.status_code in (401, 403):
                    raise AuthenticationError(f"HTTP {response.status_code}: {response.text}")
                if response.status_code == 404:
                    raise ResourceNotFoundError(f"HTTP 404: Resource at '{path}' not found.")
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        backoff = (2**attempt) + random.uniform(0.1, 0.5)
                        await asyncio.sleep(backoff)
                        continue
                    raise RateLimitError("HTTP 429: Rate limit exceeded after retries.")

                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        backoff = (2**attempt) + random.uniform(0.1, 0.5)
                        await asyncio.sleep(backoff)
                        continue
                    raise TemplateError(f"HTTP {response.status_code}: Upstream server error.")

                response.raise_for_status()
                if not response.content:
                    return {}
                return response.json()  # type: ignore[no-any-return]

            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    await asyncio.sleep((2**attempt) + random.uniform(0.1, 0.5))
                    continue

        raise TemplateError(f"Request failed: {redact_secrets(str(last_exception))}")
