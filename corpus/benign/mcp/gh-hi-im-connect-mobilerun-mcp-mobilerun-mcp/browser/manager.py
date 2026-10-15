"""Find DevTools sockets on the device, forward them to the host and attach CDP sessions."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from ..errors import fail
from ..parsers.system import parse_devtools_sockets
from .cdp import CdpClient, CdpError, parse_targets

if TYPE_CHECKING:
    from ..session import DeviceSession

SHELL_PACKAGE = "org.chromium.webview_shell"
SHELL_ACTIVITY = f"{SHELL_PACKAGE}/.WebViewBrowserActivity"
SOCKET_WAIT = 20.0


@dataclass(frozen=True)
class Target:
    id: str
    title: str
    url: str
    socket: str
    package: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "title": self.title, "url": self.url, "app": self.package}


@dataclass
class Attached:
    client: CdpClient
    target: Target
    port: int


class BrowserManager:
    def __init__(self, session: DeviceSession) -> None:
        self._s = session
        self._ports: dict[str, int] = {}
        self._attached: dict[str, Attached] = {}
        self._http = httpx.AsyncClient(timeout=8.0)
        self.generations: dict[str, tuple[int, int]] = {}  # session -> (page signature, generation)
        self.tabs: dict[str, list[str]] = {}  # scratch-browser virtual tabs (inactive URLs)
        self.handoffs: dict[str, dict] = {}

    # ---- discovery ---------------------------------------------------------------------
    async def _packages(self, pids: list[int]) -> dict[int, str]:
        if not pids:
            return {}
        loop = " ".join(str(p) for p in pids)
        out = await self._s.shell(
            f"for p in {loop}; do echo \"$p $(tr '\\0' ' ' </proc/$p/cmdline 2>/dev/null)\"; done",
            check=False,
        )
        names = {}
        for line in out.splitlines():
            head, _, rest = line.partition(" ")
            if head.isdigit():
                names[int(head)] = rest.strip().split(":")[0].split(" ")[0] or "unknown"
        return names

    async def sockets(self) -> list[tuple[str, int, str]]:
        raw = await self._s.shell(
            "cat /proc/net/unix | grep -o '@[a-z_]*devtools_remote[_0-9a-z]*'", check=False
        )
        socks = [(n, p) for n, p in parse_devtools_sockets(raw) if p is not None]
        packages = await self._packages([p for _, p in socks])
        return [(name, pid, packages.get(pid, "unknown")) for name, pid in socks]

    async def _port(self, socket_name: str) -> int:
        if socket_name not in self._ports:
            self._ports[socket_name] = await self._s.adb.forward(f"localabstract:{socket_name}")
        return self._ports[socket_name]

    async def targets(self) -> list[Target]:
        found: list[Target] = []
        for name, _pid, package in await self.sockets():
            try:
                port = await self._port(name)
                resp = await self._http.get(f"http://127.0.0.1:{port}/json")
            except (httpx.HTTPError, OSError):
                self._ports.pop(name, None)
                continue
            for t in parse_targets(resp.text):
                if t.get("type") == "page":
                    found.append(
                        Target(
                            str(t.get("id", "")),
                            str(t.get("title", "")),
                            str(t.get("url", "")),
                            name,
                            package,
                        )
                    )
        return found

    async def ensure_shell(self) -> None:
        """Start the on-device browser (WebView Browser Tester) if it is not running."""
        if any(package == SHELL_PACKAGE for _, _, package in await self.sockets()):
            return
        await self._s.shell(f"am start -n {SHELL_ACTIVITY}")
        deadline = time.monotonic() + SOCKET_WAIT
        while time.monotonic() < deadline:
            await asyncio.sleep(0.7)
            if any(package == SHELL_PACKAGE for _, _, package in await self.sockets()):
                await asyncio.sleep(0.8)  # let the first page target appear
                return
        fail(
            "timeout",
            "the on-device browser did not expose a DevTools socket",
            "is WebView Browser Tester installed?",
        )

    # ---- attach ------------------------------------------------------------------------
    async def attach(
        self, name: str = "default", target_id: str | None = None, app: str | None = None
    ) -> Attached:
        cached = self._attached.get(name)
        if cached and not cached.client.closed and target_id is None and app is None:
            return cached
        if not target_id and not app:
            await self.ensure_shell()
        targets = await self.targets()
        chosen = next(
            (
                t
                for t in targets
                if (target_id and t.id == target_id)
                or (app and t.package == app)
                or (not target_id and not app and t.package == SHELL_PACKAGE)
            ),
            None,
        )
        if chosen is None:
            listing = [t.to_dict() for t in targets]
            fail(
                "element_not_found",
                "no matching browser page",
                f"open pages: {listing}" if listing else "no pages are open",
            )
        port = await self._port(chosen.socket)
        try:
            client = await CdpClient.connect(f"ws://127.0.0.1:{port}/devtools/page/{chosen.id}")
        except CdpError as exc:
            fail("device_unreachable", str(exc))
        if cached:
            await cached.client.close()
        attached = Attached(client, chosen, port)
        self._attached[name] = attached
        return attached

    def sessions(self) -> dict[str, dict[str, str]]:
        return {n: a.target.to_dict() for n, a in self._attached.items() if not a.client.closed}

    async def detach(self, name: str) -> bool:
        attached = self._attached.pop(name, None)
        if attached is None:
            return False
        if not attached.client.closed:
            await attached.client.close()
        return True

    async def close(self) -> None:
        for name in list(self._attached):
            await self.detach(name)
        for port in self._ports.values():
            await self._s.adb.remove_forward(f"tcp:{port}")
        self._ports.clear()
        await self._http.aclose()
