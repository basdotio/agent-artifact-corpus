"""Async HTTP client for the Manus API v2."""

from __future__ import annotations

import json
from typing import Any, Literal, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from manus_mcp import __version__
from manus_mcp.client.errors import ManusApiError, ManusNetworkError
from manus_mcp.client.rate_limiter import RateLimiter
from manus_mcp.client.retry import RetryPolicy, sleep_with_cancel
from manus_mcp.logger import get_logger

T = TypeVar("T", bound=BaseModel)

_LOG = get_logger("client")


def _rate_key_from_path(path: str) -> str:
    """Extract `task.create` from `/v2/task.create` for limiter lookup."""
    stripped = path.strip("/")
    if stripped.startswith("v2/"):
        stripped = stripped[3:]
    # Drop anything after the dot-name if there are additional segments.
    return stripped.split("/", 1)[0]


def _safe_request_id(payload: Any) -> str | None:
    if isinstance(payload, dict):
        rid = payload.get("request_id")
        if isinstance(rid, str):
            return rid
    return None


def _coerce_error(payload: Any, http_status: int) -> ManusApiError:
    """Map a response body to ManusApiError."""
    if isinstance(payload, dict):
        err = payload.get("error")
        request_id = _safe_request_id(payload)
        if isinstance(err, dict):
            code = str(err.get("code") or "unknown_error")
            message = str(err.get("message") or "Manus API returned an error")
            return ManusApiError(
                code=code, message=message, http_status=http_status, request_id=request_id
            )
        # ok=false without nested error
        if payload.get("ok") is False:
            return ManusApiError(
                code="unknown_error",
                message=str(payload.get("message") or "Manus API returned ok=false"),
                http_status=http_status,
                request_id=request_id,
            )
    return ManusApiError(
        code=f"http_{http_status}",
        message=f"Unexpected response: {json.dumps(payload)[:200] if payload is not None else '<empty>'}",
        http_status=http_status,
    )


class ManusClient:
    """Thin, typed wrapper around Manus REST endpoints."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.manus.ai",
        timeout: float = 60.0,
        rate_limiter: RateLimiter | None = None,
        retry_policy: RetryPolicy | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be a non-empty string")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._rate_limiter = rate_limiter or RateLimiter()
        self._retry = retry_policy or RetryPolicy()
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "x-manus-api-key": api_key,
                "User-Agent": f"manus-mcp/{__version__}",
                "Accept": "application/json",
            },
            transport=transport,
        )

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ManusClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def call(
        self,
        method: Literal["GET", "POST"],
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: BaseModel | dict[str, Any] | None = None,
        response_model: type[T],
        rate_limit_key: str | None = None,
        idempotent: bool | None = None,
    ) -> T:
        """Make an authenticated call, retry on 429/5xx, parse envelope into response_model."""
        key = rate_limit_key or _rate_key_from_path(path)
        if idempotent is None:
            idempotent = method == "GET"

        body: dict[str, Any] | None
        if isinstance(json_body, BaseModel):
            body = json_body.model_dump(mode="json", exclude_none=True, by_alias=True)
        else:
            body = json_body

        # Strip None values from query params.
        clean_params: dict[str, Any] | None = None
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}

        attempt_429 = 0
        attempt_5xx = 0
        attempt_net = 0

        while True:
            await self._rate_limiter.acquire(key)
            try:
                response = await self._client.request(method, path, params=clean_params, json=body)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                attempt_net += 1
                if attempt_net > self._retry.max_attempts_network or not idempotent:
                    raise ManusNetworkError(f"{type(e).__name__}: {e}", original=e) from e
                delay = self._retry.backoff_delay(attempt_net)
                _LOG.warning("%s %s network error (%s), retrying in %.2fs", method, path, e, delay)
                await sleep_with_cancel(delay)
                continue

            status = response.status_code
            try:
                parsed: Any = response.json() if response.content else None
            except ValueError:
                parsed = None

            if status == 429:
                self._rate_limiter.note_server_429(key)
                attempt_429 += 1
                if attempt_429 > self._retry.max_attempts_429:
                    raise _coerce_error(parsed, status)
                hint = None
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        hint = float(retry_after)
                    except ValueError:
                        hint = None
                delay = self._retry.backoff_delay(attempt_429, server_hint=hint)
                _LOG.warning("%s %s rate-limited, retrying in %.2fs", method, path, delay)
                await sleep_with_cancel(delay)
                continue

            if 500 <= status < 600:
                attempt_5xx += 1
                if attempt_5xx > self._retry.max_attempts_5xx or not idempotent:
                    raise _coerce_error(parsed, status)
                delay = self._retry.backoff_delay(attempt_5xx)
                _LOG.warning("%s %s http %d, retrying in %.2fs", method, path, status, delay)
                await sleep_with_cancel(delay)
                continue

            if not (200 <= status < 300):
                raise _coerce_error(parsed, status)

            if not isinstance(parsed, dict):
                raise ManusApiError(
                    code="invalid_response",
                    message=f"Expected JSON object, got {type(parsed).__name__}",
                    http_status=status,
                )

            if parsed.get("ok") is False:
                raise _coerce_error(parsed, status)

            try:
                validated = response_model.model_validate(parsed)
            except ValidationError as e:
                raise ManusApiError(
                    code="invalid_response",
                    message=f"Response did not match {response_model.__name__}: {e}",
                    http_status=status,
                    request_id=_safe_request_id(parsed),
                ) from e
            _LOG.debug(
                "manus %s %s status=%d request_id=%s",
                method,
                path,
                status,
                _safe_request_id(parsed) or "-",
            )
            return validated

    async def put_raw(
        self,
        url: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """PUT raw bytes to a presigned URL (e.g. S3). Does NOT send the API key."""
        attempt = 0
        while True:
            try:
                # Use a bare client (no base_url, no auth) for absolute URL PUT.
                async with httpx.AsyncClient(timeout=self._client.timeout) as raw:
                    resp = await raw.put(
                        url,
                        content=data,
                        headers={"Content-Type": content_type},
                    )
            except (httpx.TimeoutException, httpx.TransportError) as e:
                attempt += 1
                if attempt > self._retry.max_attempts_network:
                    raise ManusNetworkError(f"PUT failed: {e}", original=e) from e
                await sleep_with_cancel(self._retry.backoff_delay(attempt))
                continue
            if 200 <= resp.status_code < 300:
                return
            if 500 <= resp.status_code < 600:
                attempt += 1
                if attempt > self._retry.max_attempts_5xx:
                    raise ManusApiError(
                        code=f"upload_http_{resp.status_code}",
                        message=f"Upload failed with status {resp.status_code}",
                        http_status=resp.status_code,
                    )
                await sleep_with_cancel(self._retry.backoff_delay(attempt))
                continue
            raise ManusApiError(
                code=f"upload_http_{resp.status_code}",
                message=f"Upload failed: {resp.text[:200] if resp.text else 'no body'}",
                http_status=resp.status_code,
            )
