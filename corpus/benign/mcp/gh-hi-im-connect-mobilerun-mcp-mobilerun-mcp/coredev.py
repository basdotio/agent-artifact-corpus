"""Async facade over mobilerun-core's (synchronous) ``Device``.

mobilerun-core is droidrun's canonical control API: one ``Device`` for local Android over adb,
Android Portal HTTP-only, iOS (mobilerun-ios / ios-portal) and Mobilerun Cloud. Calls run in a
worker thread, serialized per device because the underlying connections are not thread-safe.
"""

from __future__ import annotations

import asyncio
import base64
import threading
from pathlib import Path
from typing import Any

from .errors import fail
from .targets import CLOUD, CORE_BACKEND, Target


class CoreDevice:
    """``session`` (Android over adb only) routes core through :class:`FastAndroidConnection`."""

    def __init__(
        self, target: Target, cloud_api_key: str | None = None, session: Any = None
    ) -> None:
        self.target = target
        self._cloud_api_key = cloud_api_key
        self._session = session
        self._loop: asyncio.AbstractEventLoop | None = None
        self._device: Any = None
        self._lock = threading.Lock()

    def _connect(self) -> Any:
        if self._device is None:
            from mobilerun_core import Device, Mobilerun

            from .fastconn import FastAndroidConnection, allow_all

            if self._session is not None and self.target.has_adb:
                self._device = Device(FastAndroidConnection(self._session, self._loop), allow_all)
                return self._device

            kwargs: dict[str, Any] = {"backend": CORE_BACKEND[self.target.kind]}
            if self.target.url:
                kwargs["url"] = self.target.url
            if self.target.token:
                kwargs["token"] = self.target.token
            device_id = None if self.target.url and self.target.kind != CLOUD else self.target.id
            self._device = Mobilerun(
                bearer=self._cloud_api_key or None, hitl_gate=allow_all
            ).connect(device_id, **kwargs)
        return self._device

    def _invoke(self, method: str, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            device = self._connect()
            return getattr(device, method)(*args, **kwargs)

    async def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Run ``Device.<method>`` off the event loop; map core errors to tool errors."""
        self._loop = self._loop or asyncio.get_running_loop()
        try:
            return await asyncio.to_thread(self._invoke, method, *args, **kwargs)
        except Exception as exc:  # mobilerun-core raises many types; surface them uniformly
            name = type(exc).__name__
            if name == "UnsupportedOperation" or isinstance(exc, NotImplementedError):
                fail("unsupported", f"{method} is not supported on {self.target.kind}: {exc}")
            if isinstance(exc, (ValueError, TypeError)):
                fail("invalid_argument", f"{method}: {exc}")
            fail("device_unreachable", f"{self.target.id}: {method} failed: {name}: {exc}")

    async def capabilities(self) -> dict[str, Any]:
        self._loop = self._loop or asyncio.get_running_loop()

        def read() -> dict[str, Any]:
            with self._lock:
                return dict(self._connect().capabilities)

        return await asyncio.to_thread(read)

    async def screenshot_png(self, hide_overlay: bool = False) -> bytes:
        """PNG bytes from ``Device.screenshot`` (base64 on local backends, a temp file on cloud)."""
        value = await self.call("screenshot", hide_overlay=hide_overlay)
        if isinstance(value, bytes):
            return value
        text = str(value)
        path = Path(text)
        if len(text) < 1024 and path.is_file():
            return path.read_bytes()
        return base64.b64decode(text)
