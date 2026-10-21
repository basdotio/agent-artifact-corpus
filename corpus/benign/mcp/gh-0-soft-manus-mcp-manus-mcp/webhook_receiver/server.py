"""Starlette HTTP app that receives Manus webhooks, verifies signatures, and persists them."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from manus_mcp import __version__
from manus_mcp.config import Settings
from manus_mcp.logger import get_logger
from manus_mcp.webhook_receiver.signature import (
    VerificationResult,
    load_public_key,
    verify_signature,
)
from manus_mcp.webhook_receiver.storage import EventStore

_LOG = get_logger("webhook")
_PUBLIC_KEY_TTL_SECONDS = 3600


@dataclass
class _KeyCache:
    pem: str
    expires_at: float


class ManusPublicKeyFetcher:
    """Fetches and caches the Manus webhook public key."""

    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._cache: _KeyCache | None = None

    async def get(self) -> str:
        now = time.time()
        if self._cache and self._cache.expires_at > now:
            return self._cache.pem
        async with httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "x-manus-api-key": self._api_key,
                "User-Agent": f"manus-mcp/{__version__}",
                "Accept": "application/json",
            },
        ) as c:
            resp = await c.get(f"{self._base_url}/v2/webhook.publicKey")
            resp.raise_for_status()
            data = resp.json()
        pem = data.get("public_key")
        if not isinstance(pem, str):
            raise RuntimeError("webhook.publicKey response missing 'public_key'")
        self._cache = _KeyCache(pem=pem, expires_at=now + _PUBLIC_KEY_TTL_SECONDS)
        return pem


def _extract_event_id(body: dict[str, Any]) -> str:
    eid = body.get("event_id")
    if isinstance(eid, str) and eid:
        return eid
    # Fallback: synthesize stable id from timestamp + task_id + type
    parts = [
        str(body.get("event_type") or "unknown"),
        str(body.get("task_detail", {}).get("task_id") or ""),
        str(int(time.time())),
    ]
    return ":".join(parts)


def _extract_task_id(body: dict[str, Any]) -> str | None:
    detail = body.get("task_detail")
    if isinstance(detail, dict):
        tid = detail.get("task_id")
        if isinstance(tid, str):
            return tid
    tid = body.get("task_id")
    return tid if isinstance(tid, str) else None


def create_app(settings: Settings) -> Starlette:
    if not settings.manus_webhook_public_url:
        raise RuntimeError(
            "MANUS_WEBHOOK_PUBLIC_URL must be set to the fully-qualified public URL "
            "that Manus uses to POST webhooks (this is the URL you registered with "
            "manus_webhook_create)."
        )

    store = EventStore(settings.manus_webhook_db_path)
    key_fetcher = ManusPublicKeyFetcher(
        api_key=settings.manus_api_key,
        base_url=settings.manus_base_url,
        timeout=settings.manus_http_timeout,
    )

    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "service": "manus-mcp-webhook", "version": __version__})

    async def receive(request: Request) -> JSONResponse:
        body_bytes = await request.body()
        signature = request.headers.get("x-webhook-signature", "")
        timestamp = request.headers.get("x-webhook-timestamp", "")

        try:
            pem = await key_fetcher.get()
            public_key = load_public_key(pem)
        except Exception as e:
            _LOG.exception("Failed to load Manus public key: %s", e)
            return JSONResponse({"ok": False, "error": "public_key_unavailable"}, status_code=503)

        verification: VerificationResult = verify_signature(
            public_key=public_key,
            signature_b64=signature,
            timestamp=timestamp,
            public_url=settings.manus_webhook_public_url or "",
            body=body_bytes,
        )
        if not verification.valid:
            _LOG.warning("Rejected webhook: %s", verification.reason)
            return JSONResponse(
                {"ok": False, "error": "invalid_signature", "reason": verification.reason},
                status_code=401,
            )

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"ok": False, "error": "body_not_object"}, status_code=400)

        event_id = _extract_event_id(body)
        event_type = str(body.get("event_type") or "unknown")
        task_id = _extract_task_id(body)
        inserted = store.insert(
            event_id=event_id,
            event_type=event_type,
            task_id=task_id,
            body=body,
            headers={
                "x-webhook-signature": signature,
                "x-webhook-timestamp": timestamp,
            },
        )
        if inserted:
            _LOG.info("stored %s event_id=%s task_id=%s", event_type, event_id, task_id)
        else:
            _LOG.info("duplicate event_id=%s (already stored)", event_id)
        return JSONResponse({"ok": True, "event_id": event_id})

    return Starlette(
        routes=[
            Route("/manus/webhook", receive, methods=["POST"]),
            Route("/health", health, methods=["GET"]),
        ]
    )
