"""Navigate a page and wait until the NEW document has loaded (not the one being replaced)."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

from .cdp import CdpError

ORIGIN = "performance.timeOrigin"
STATE = (
    f"({{title: document.title, url: location.href, ready: document.readyState, origin: {ORIGIN}}})"
)


class Client(Protocol):
    async def send(
        self, method: str, params: dict[str, Any] | None = None, timeout: float = ...
    ) -> dict: ...

    async def evaluate(self, expression: str, timeout: float = ...) -> Any: ...


def strip_fragment(url: str) -> str:
    return url.split("#", 1)[0]


async def navigate(
    client: Client, url: str, timeout: float = 15.0, wait: bool = True, interval: float = 0.3
) -> dict[str, Any]:
    """Go to ``url``; returns {title, url, ready}. Raises CdpError when the load fails.

    A page that is already ``complete`` when the command returns is usually the old document, so
    the wait requires a different ``performance.timeOrigin`` (a new document) unless the target
    differs from the current URL only by its fragment (a same-document navigation).
    """
    try:
        before = await client.evaluate(STATE)
    except CdpError:
        before = {}
    reply = await client.send("Page.navigate", {"url": url}, timeout=timeout)
    if reply.get("errorText"):
        raise CdpError(f"navigation failed: {reply['errorText']}")
    same_document = bool(before) and strip_fragment(before.get("url", "")) == strip_fragment(url)
    wants_blank = url.startswith("about:")
    deadline = time.monotonic() + timeout
    info: dict[str, Any] = {}
    while wait and time.monotonic() < deadline:
        try:
            info = await client.evaluate(STATE)
        except CdpError:
            info = {}  # the old document is being torn down
        else:
            fresh = same_document or info.get("origin") != before.get("origin")
            # a cold browser first commits an interim about:blank document: not our page yet
            interim = info.get("url") in ("about:blank", "") and not wants_blank
            if info.get("ready") == "complete" and fresh and not interim:
                break
        await asyncio.sleep(interval)
    if not info:
        info = await client.evaluate(STATE)
    return {"title": info.get("title"), "url": info.get("url"), "ready": info.get("ready")}
