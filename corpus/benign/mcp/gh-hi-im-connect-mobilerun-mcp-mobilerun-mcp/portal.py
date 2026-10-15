"""Thin client for the Mobilerun Portal.

Fast path: the Portal's local HTTP server through an adb forward (bearer token from the content
provider). Fallback: the Portal content provider over ``adb shell content`` when HTTP is off.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any

import httpx

from .adb import Adb, AdbError
from .parsers.content import extract_token, parse_content_output, unwrap

PORTAL_PACKAGE = "com.mobilerun.portal"
PORTAL_REMOTE = "tcp:8080"
PROVIDER = f"content://{PORTAL_PACKAGE}"


class PortalError(RuntimeError):
    """The Portal is unreachable or answered with an error."""


class PortalClient:
    def __init__(self, adb: Adb) -> None:
        self._adb = adb
        self._token: str | None = None
        self._base: str | None = None
        self._http_ok = False
        self._connected = False
        self._http = httpx.AsyncClient(timeout=15.0)

    @property
    def transport(self) -> str:
        return "http" if self._http_ok else "content_provider"

    async def close(self) -> None:
        await self._http.aclose()

    async def _fetch_token(self) -> str | None:
        raw = await self._adb.shell(f"content query --uri {PROVIDER}/auth_token", check=False)
        return extract_token(parse_content_output(raw))

    async def _ensure_forward(self) -> str:
        for local, remote in await self._adb.forward_list():
            if remote == PORTAL_REMOTE and local.startswith("tcp:"):
                return f"http://127.0.0.1:{local.split(':')[1]}"
        port = await self._adb.forward(PORTAL_REMOTE)
        return f"http://127.0.0.1:{port}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def _http_ping(self) -> bool:
        try:
            resp = await self._http.get(f"{self._base}/ping", headers=self._headers(), timeout=5.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def connect(self) -> None:
        """(Re)establish the transport: forward, token, and enable the HTTP server if needed."""
        self._token = await self._fetch_token()
        self._base = await self._ensure_forward()
        self._http_ok = await self._http_ping()
        if not self._http_ok:
            await self._adb.shell(
                f"content insert --uri {PROVIDER}/toggle_socket_server --bind enabled:b:true",
                check=False,
            )
            await asyncio.sleep(1.0)
            self._token = await self._fetch_token() or self._token
            self._http_ok = await self._http_ping()
        self._connected = True

    async def _ensure(self) -> None:
        if not self._connected:
            await self.connect()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in (1, 2):
            await self._ensure()
            try:
                resp = await self._http.request(
                    method, f"{self._base}{path}", headers=self._headers(), **kwargs
                )
            except httpx.TransportError as exc:
                if attempt == 2:
                    raise PortalError(f"Portal unreachable: {exc}") from exc
                self._connected = False  # forward may have died; rebuild and retry once
                continue
            if resp.status_code in (401, 403) and attempt == 1:
                self._token = await self._fetch_token()
                continue
            return resp
        raise PortalError("Portal request failed")

    async def ping(self) -> dict[str, Any]:
        await self._ensure()
        if self._http_ok:
            resp = await self._request("GET", "/ping")
            if resp.status_code != 200:
                raise PortalError(f"ping failed: HTTP {resp.status_code}")
            return {"status": "ok", "transport": "http", **_as_dict(resp.json())}
        await self.state()  # content-provider health check
        return {"status": "ok", "transport": "content_provider"}

    async def state(self) -> dict[str, Any]:
        """Accessibility tree plus phone state (keys ``a11y_tree`` and ``phone_state``)."""
        await self._ensure()
        if self._http_ok:
            resp = await self._request("GET", "/state_full")
            if resp.status_code != 200:
                raise PortalError(f"state_full failed: HTTP {resp.status_code}")
            data = unwrap(resp.json())
        else:
            raw = await self._adb.shell(
                f"content query --uri {PROVIDER}/state_full", timeout=20, check=False
            )
            data = parse_content_output(raw)
        if not isinstance(data, dict) or "error" in data:
            raise PortalError(f"state_full returned an unusable payload: {str(data)[:120]}")
        return data

    async def screenshot(self, hide_overlay: bool = False) -> bytes:
        """PNG bytes; falls back to adb screencap when the Portal endpoint is unavailable."""
        await self._ensure()
        if self._http_ok:
            params = {"hideOverlay": "true"} if hide_overlay else None
            resp = await self._request("GET", "/screenshot", params=params)
            if resp.status_code == 200:
                body = resp.json()
                encoded = unwrap(body) if body.get("status") == "success" else None
                if isinstance(encoded, str):
                    return base64.b64decode(encoded)
        try:
            return await self._adb.exec_out("screencap", "-p")
        except AdbError as exc:
            raise PortalError(f"screenshot failed: {exc}") from exc

    async def input_text(self, text: str, clear: bool = False) -> None:
        await self._ensure()
        encoded = base64.b64encode(text.encode()).decode()
        if self._http_ok:
            resp = await self._request(
                "POST", "/keyboard/input", json={"base64_text": encoded, "clear": clear}
            )
            if resp.status_code == 200:
                return
        flag = "true" if clear else "false"
        await self._adb.shell(
            f'content insert --uri "{PROVIDER}/keyboard/input" '
            f'--bind base64_text:s:"{encoded}" --bind clear:b:{flag}'
        )

    async def action(self, name: str, **payload: Any) -> str:
        """POST /action/<name>: accessibility-service gestures (tap, swipe, global, key)."""
        resp = await self._request("POST", f"/action/{name}", json=payload)
        try:
            body = resp.json()
        except ValueError as exc:
            raise PortalError(f"action {name}: unreadable response") from exc
        if body.get("status") != "success":
            raise PortalError(f"action {name}: {body.get('error', 'failed')}")
        return str(body.get("result", ""))

    async def tap(self, x: int, y: int) -> None:
        await self.action("tap", x=x, y=y)

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        await self.action("swipe", startX=x1, startY=y1, endX=x2, endY=y2, duration=duration_ms)

    async def apps(self) -> list[dict[str, Any]]:
        """Installed apps: dicts with packageName, label, isSystemApp."""
        raw = await self._adb.shell(f"content query --uri {PROVIDER}/packages", timeout=60)
        data = parse_content_output(raw)
        if isinstance(data, dict):
            data = data.get("packages")
        return data if isinstance(data, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {"value": value}
