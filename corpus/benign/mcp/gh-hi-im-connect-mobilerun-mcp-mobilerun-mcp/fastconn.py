"""mobilerun-core ``Connection`` for Android over adb, served by this server's fast transport.

mobilerun-core's ``Device`` implements droidrun's canonical control API (find_nodes, tap_text,
scroll_until, wait_for_* ...) on top of a small ``Connection`` protocol. This subclass keeps
core's own adb connection for everything it does not override, and swaps the hot paths
(UI tree, taps, swipes, screenshots, keys, plain typing) for the Portal HTTP API through an adb
forward, which is ~50x faster than core's per-call adb round trips. It also fills in operations
core-local does not offer on local devices: clipboard, runtime permissions, deep links and
JavaScript in the foreground browser page.

Every method runs in a worker thread (see :mod:`coredev`) and bridges back to the server's
event loop for the async session calls.
"""

from __future__ import annotations

import asyncio
import base64
from typing import TYPE_CHECKING, Any

from mobilerun_core.connection import KEY_CODES
from mobilerun_core.connection.framework import MobilerunLocalAndroidAdb, _normalize_tree

from .shell import q

if TYPE_CHECKING:
    from .session import DeviceSession

EXTRA_ACTIONS = {
    "get_clipboard",
    "set_clipboard",
    "grant_permission",
    "open_deep_link",
    "execute_script",
}
BRIDGE_TIMEOUT = 120.0


class FastAndroidConnection(MobilerunLocalAndroidAdb):
    def __init__(self, session: DeviceSession, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(session.serial)
        self._session = session
        self._main = loop

    def _await(self, coro: Any, timeout: float = BRIDGE_TIMEOUT) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._main).result(timeout)

    @property
    def capabilities(self) -> dict[str, Any]:
        caps = super().capabilities
        caps["actions"] = sorted(set(caps["actions"]) | EXTRA_ACTIONS)
        caps["transport"] = "mobilerun-mcp fast path (Portal HTTP over adb forward)"
        return caps

    # ---- hot paths ---------------------------------------------------------------------
    def ui(self, *, filter: bool = True) -> Any:
        return _normalize_tree(self._await(self._session.raw_state()), platform="android")

    def screenshot(self, *, hide_overlay: bool = False) -> str:
        return base64.b64encode(self._await(self._session.screenshot())).decode("ascii")

    def tap(self, x: int, y: int, *, stealth: bool = True) -> None:
        self._await(self._session.tap_xy(int(x), int(y)))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, ms: int = 300) -> None:
        self._await(self._session.swipe_xy(int(x1), int(y1), int(x2), int(y2), int(ms)))

    def type(
        self, text: str, *, clear: bool = False, wpm: int | None = None, stealth: bool = True
    ) -> None:
        if stealth:
            super().type(text, clear=clear, wpm=wpm, stealth=True)  # core's Gboard key tapping
            return
        self._await(self._session.input_text(text, clear))

    def key(self, name_or_code: str | int) -> None:
        code = (
            name_or_code
            if isinstance(name_or_code, int)
            else KEY_CODES.get(str(name_or_code).lower())
        )
        if code is None:
            super().key(name_or_code)
            return
        self._await(self._session.shell(f"input keyevent {int(code)}"))

    # ---- operations core-local lacks on local devices ----------------------------------
    def get_clipboard(self) -> str:
        return self._await(self._session.portal.action("clipboard/get"))

    def set_clipboard(self, value: str) -> None:
        encoded = base64.b64encode(value.encode()).decode()
        self._await(self._session.portal.action("clipboard/set", text_base64=encoded))

    def grant_permission(self, package: str, permission: str) -> None:
        out = self._await(
            self._session.shell(f"pm grant {q(package)} {q(permission)}", check=False)
        )
        if out.strip():
            raise ValueError(out.strip()[:300])

    def open_deep_link(
        self, deep_link: str, *, package_name: str | None = None, action: str | None = None
    ) -> None:
        args = f"-a {q(action or 'android.intent.action.VIEW')} -d {q(deep_link)}"
        if package_name:
            args += f" -p {q(package_name)}"
        out = self._await(self._session.shell(f"am start {args}", check=False))
        if "Error" in out or "Exception" in out:
            raise ValueError(out.strip().splitlines()[-1][:300])

    def execute_script(self, js: str) -> Any:
        return self._await(evaluate_in_browser(self._session, js))


async def evaluate_in_browser(session: DeviceSession, js: str) -> Any:
    """Evaluate ``js`` in the on-device browser page (the ``scratch`` browser session)."""
    from .browser.cdp import CdpError
    from .tools.browser import manager

    try:
        attached = await manager(session).attach("scratch")
        return await attached.client.evaluate(js)
    except CdpError as exc:
        raise ValueError(f"execute_script: {exc}") from exc


def allow_all(action: str, args: dict[str, Any]) -> None:
    """HITL gate for MCP use: the calling agent is the approver; policy.py does the gating."""
    return None
