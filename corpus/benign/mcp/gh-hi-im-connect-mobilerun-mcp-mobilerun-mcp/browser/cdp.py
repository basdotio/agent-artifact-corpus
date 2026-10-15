"""Minimal Chrome DevTools Protocol client over a websocket (no Playwright)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from websockets.asyncio.client import ClientConnection, connect

DEFAULT_TIMEOUT = 15.0
MAX_MESSAGE = 32 * 1024 * 1024


class CdpError(RuntimeError):
    """The browser answered a command with an error, or the connection dropped."""


class CdpClient:
    def __init__(self, ws: ClientConnection) -> None:
        self._ws = ws
        self._next_id = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._waiters: dict[str, list[asyncio.Future[dict[str, Any]]]] = {}
        self._reader = asyncio.create_task(self._read_loop())
        self.closed = False

    @classmethod
    async def connect(cls, url: str, timeout: float = 10.0) -> CdpClient:
        try:
            ws = await connect(url, max_size=MAX_MESSAGE, open_timeout=timeout, ping_interval=None)
        except (OSError, TimeoutError) as exc:
            raise CdpError(f"cannot connect to {url}: {exc}") from exc
        return cls(ws)

    async def _read_loop(self) -> None:
        try:
            async for raw in self._ws:
                message = json.loads(raw)
                if "id" in message:
                    future = self._pending.pop(message["id"], None)
                    if future and not future.done():
                        future.set_result(message)
                elif "method" in message:
                    for future in self._waiters.pop(message["method"], []):
                        if not future.done():
                            future.set_result(message.get("params", {}))
        except Exception:  # connection closed or bad frame: fail everything still waiting
            pass
        finally:
            self.closed = True
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(CdpError("connection closed"))
            self._pending.clear()

    async def send(
        self, method: str, params: dict[str, Any] | None = None, timeout: float = DEFAULT_TIMEOUT
    ) -> dict[str, Any]:
        if self.closed:
            raise CdpError("connection closed")
        self._next_id += 1
        message_id = self._next_id
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[message_id] = future
        await self._ws.send(
            json.dumps({"id": message_id, "method": method, "params": params or {}})
        )
        try:
            reply = await asyncio.wait_for(future, timeout)
        except TimeoutError as exc:
            self._pending.pop(message_id, None)
            raise CdpError(f"{method} timed out after {timeout}s") from exc
        if "error" in reply:
            raise CdpError(f"{method}: {reply['error'].get('message', reply['error'])}")
        return reply.get("result", {})

    async def wait_event(self, name: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._waiters.setdefault(name, []).append(future)
        try:
            return await asyncio.wait_for(future, timeout)
        except TimeoutError as exc:
            raise CdpError(f"event {name} not seen within {timeout}s") from exc

    async def evaluate(
        self, expression: str, timeout: float = DEFAULT_TIMEOUT, await_promise: bool = False
    ) -> Any:
        """Evaluate JS and return its value (JSON-serializable results only)."""
        result = await self.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": await_promise},
            timeout,
        )
        if "exceptionDetails" in result:
            details = result["exceptionDetails"]
            text = (details.get("exception") or {}).get("description") or details.get(
                "text", "error"
            )
            raise CdpError(f"page script failed: {text}")
        return (result.get("result") or {}).get("value")

    async def close(self) -> None:
        self.closed = True
        await self._ws.close()
        self._reader.cancel()


def parse_targets(text: str) -> list[dict[str, Any]]:
    """DevTools ``/json`` output; WebViews put raw control characters in titles, so parse leniently."""
    try:
        data = json.loads(text, strict=False)
    except json.JSONDecodeError:
        return []
    return [t for t in data if isinstance(t, dict)] if isinstance(data, list) else []
