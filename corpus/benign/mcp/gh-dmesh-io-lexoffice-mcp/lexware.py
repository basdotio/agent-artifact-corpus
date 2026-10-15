"""Thin async client for the Lexware (formerly lexoffice) public API."""

import asyncio
import json
import logging
import time
from types import TracebackType
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.lexware.io"
DEFAULT_APP_URL = "https://app.lexware.de"
# Lexware allows 2 requests per second across all endpoints; keep a small buffer.
MIN_REQUEST_INTERVAL_SECONDS = 0.55
MAX_RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 35.0


class LexwareError(Exception):
    """Raised when the Lexware API responds with a non success status."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"Lexware API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message


def describe_error(response: httpx.Response) -> str:
    """Extract a human readable message from the different Lexware error formats."""
    try:
        body = response.json()
    except json.JSONDecodeError:
        return response.text.strip() or response.reason_phrase

    if not isinstance(body, dict):
        return json.dumps(body, ensure_ascii=False)

    # Legacy format used by contacts, files and vouchers.
    if issues := body.get("IssueList"):
        return "; ".join(
            f"{issue.get('i18nKey')} ({issue.get('source')})" if issue.get("source") else str(issue.get("i18nKey"))
            for issue in issues
        )

    # Current format used by sales voucher endpoints such as invoices.
    parts = [str(body["message"])] if body.get("message") else []
    for detail in body.get("details") or []:
        field = detail.get("field")
        text = detail.get("message") or detail.get("violation")
        parts.append(f"{field}: {text}" if field else str(text))
    return "; ".join(parts) or json.dumps(body, ensure_ascii=False)


class LexwareClient:
    """Async Lexware API client with client side throttling and 429 retries."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )
        self._throttle_lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def create_invoice(self, payload: dict[str, Any], finalize: bool) -> dict[str, Any]:
        params = {"finalize": "true"} if finalize else None
        return await self._request("POST", "/v1/invoices", json=payload, params=params)

    async def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/invoices/{invoice_id}")

    async def find_contacts(self, filters: dict[str, str], page: int, size: int) -> dict[str, Any]:
        params = {**filters, "page": str(page), "size": str(size)}
        return await self._request("GET", "/v1/contacts", params=params)

    async def _throttle(self) -> None:
        async with self._throttle_lock:
            wait = self._last_request_at + MIN_REQUEST_INTERVAL_SECONDS - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            await self._throttle()
            response = await self._http.request(method, path, **kwargs)
            # A 429 guarantees the call was not executed, so retrying is safe even for POST.
            # Other errors (e.g. 500/504) are not retried to avoid creating duplicate invoices.
            if response.status_code == 429 and attempt < MAX_RATE_LIMIT_RETRIES:
                backoff = RATE_LIMIT_BACKOFF_SECONDS * 2**attempt
                logger.warning("Lexware rate limit hit on %s %s, retrying in %ss", method, path, backoff)
                await asyncio.sleep(backoff)
                continue
            if response.is_error:
                raise LexwareError(response.status_code, describe_error(response))
            return response.json()
        raise AssertionError("unreachable")
