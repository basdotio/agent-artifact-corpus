"""Per-device state and the process-wide runtime that owns the sessions.

A session wraps one device. Android over adb uses the fast path (Portal HTTP API through an adb
forward, plus adb shell). Every other backend (Portal HTTP-only, iOS, Mobilerun Cloud) goes
through mobilerun-core. Tools use the primitives below and never care which path serves them;
tools that need adb shell call :meth:`DeviceSession.shell`, which reports ``unsupported`` on
backends without adb.
"""

from __future__ import annotations

import asyncio
import time

from .adb import Adb, AdbError, connect_tcp, detect_single_device
from .config import Config
from .coredev import CoreDevice
from .errors import fail
from .ledger import Ledger
from .marks import build_marks, signature
from .models import Mark, Screen
from .parsers.a11y import parse_any_state, parse_screen
from .parsers.packages import App, parse_apps
from .parsers.system import parse_wm_size
from .portal import PortalClient, PortalError
from .targets import Target, resolve_target

APPS_TTL = 60.0
UNREACHABLE_HINT = "is the device listed by `adb devices` and the Mobilerun Portal enabled?"
DOUBLE_TAP_GAP = 0.12
CAMEL_PHONE_KEYS = {
    "package_name": "packageName",
    "activity_name": "activityName",
    "current_app": "currentApp",
    "keyboard_visible": "keyboardVisible",
    "is_editable": "isEditable",
    "focused_element": "focusedElement",
    "bundle_id": "bundleId",
}
KEYCODES = {"home": 3, "back": 4, "enter": 66, "recents": 187, "app_switch": 187, "menu": 82}


class DeviceSession:
    def __init__(self, target: Target | str, config: Config) -> None:
        self.target = target if isinstance(target, Target) else resolve_target(target)
        self.serial = self.target.id
        self.config = config
        self.adb: Adb | None = Adb(self.serial, config.adb_bin) if self.target.has_adb else None
        self.portal: PortalClient | None = PortalClient(self.adb) if self.adb else None
        self.core = CoreDevice(self.target, config.cloud_api_key, self)
        self.lock = asyncio.Lock()
        self.ledger = Ledger()
        self.screen: Screen | None = None
        self.marks: list[Mark] = []
        self.marks_stale = True
        self.signature = ""
        self.last_observation: dict[str, object] | None = None
        self.last_action_at = 0.0
        self.last_look_at = 0.0
        self.action_count = 0
        self.seen_at: dict[str, int] = {}  # screen signature -> action_count when last seen
        self.agent_elements: list[dict] = []  # mobilerun-agent indexed elements (get_state)
        self.agent_size: tuple[int, int] | None = None
        self._apps: list[App] = []
        self._apps_at = 0.0
        self._connected = False
        self.browser = None  # BrowserManager, created on first browser tool call

    @property
    def has_adb(self) -> bool:
        return self.adb is not None

    # ---- connectivity ------------------------------------------------------------------
    async def ensure_connected(self) -> None:
        if self._connected:
            return
        if self.adb is not None:
            try:
                await connect_tcp(self.serial, self.config.adb_bin)
                await self.portal.connect()
            except (AdbError, PortalError) as exc:
                fail("device_unreachable", f"{self.serial}: {exc}", UNREACHABLE_HINT)
        else:
            await self.core.capabilities()  # connects, raising device_unreachable on failure
        self._connected = True

    def _lost(self, exc: Exception):
        self._connected = False
        fail("device_unreachable", f"{self.serial}: {exc}", UNREACHABLE_HINT)

    def require_adb(self, feature: str) -> Adb:
        if self.adb is None:
            fail(
                "unsupported",
                f"{feature} needs adb, but {self.serial} is a {self.target.kind} device",
                "use an Android device over adb for this tool",
            )
        return self.adb

    async def shell(self, command: str, timeout: float = 30.0, check: bool = True) -> str:
        adb = self.require_adb("this tool")
        await self.ensure_connected()
        try:
            return await adb.shell(command, timeout=timeout, check=check)
        except AdbError as exc:
            self._lost(exc)

    # ---- gestures ----------------------------------------------------------------------
    # Accessibility gestures via the Portal are preferred: they work on surfaces (the notification
    # shade) that ignore injected `input` events, and skip a process launch per gesture.
    async def _portal_gesture(self, call) -> bool:
        await self.ensure_connected()
        if self.portal is None or self.portal.transport != "http":
            return False
        try:
            await call()
            return True
        except PortalError:
            return False

    async def tap_xy(self, x: int, y: int) -> None:
        if self.adb is None:
            await self.core.call("tap", x, y, stealth=False)
            return
        if not await self._portal_gesture(lambda: self.portal.tap(x, y)):
            await self.shell(f"input tap {x} {y}")

    async def swipe_xy(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        if self.adb is None:
            await self.core.call("swipe", x1, y1, x2, y2, ms=duration_ms)
            return
        if not await self._portal_gesture(lambda: self.portal.swipe(x1, y1, x2, y2, duration_ms)):
            await self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    async def long_press_xy(self, x: int, y: int, duration_ms: int = 1000) -> None:
        if self.adb is None:
            await self.core.call("long_press", x, y, ms=duration_ms)
            return
        await self.swipe_xy(x, y, x, y, duration_ms)

    async def double_tap_xy(self, x: int, y: int) -> None:
        # Back-to-back accessibility gestures cancel each other (the page sees one click); a short
        # gap keeps the pair inside the double-tap window (verified: 2 clicks + a dblclick).
        if self.adb is None:
            await self.core.call("tap", x, y, stealth=False)
            await asyncio.sleep(DOUBLE_TAP_GAP)
            await self.core.call("tap", x, y, stealth=False)
            return
        if await self._portal_gesture(lambda: self.portal.tap(x, y)):
            await asyncio.sleep(DOUBLE_TAP_GAP)
            if await self._portal_gesture(lambda: self.portal.tap(x, y)):
                return
        await self.shell(f"input tap {x} {y} & input tap {x} {y} & wait")

    async def input_text(self, text: str, clear: bool = False) -> None:
        if self.adb is None:
            await self.core.call("type", text, clear=clear, stealth=False)
            return
        await self.ensure_connected()
        try:
            await self.portal.input_text(text, clear)
        except (AdbError, PortalError) as exc:
            self._lost(exc)

    async def press(self, button: str) -> None:
        """home | back | enter | recents | menu, or any mobilerun-core key name."""
        name = button.lower()
        if self.adb is None:
            await self.core.call("key", "app_switch" if name == "recents" else name)
            return
        code = KEYCODES.get(name)
        if code is None:
            await self.core.call("key", name)
            return
        await self.shell(f"input keyevent {code}")

    async def start_app(self, package: str, activity: str | None = None) -> None:
        await self.core.call("start_app", package, activity=activity)

    # ---- perception --------------------------------------------------------------------
    async def raw_state(self) -> dict:
        await self.ensure_connected()
        if self.adb is None:
            state = dict(await self.core.call("ui", filter=False))
            phone = state.get("phone_state")
            if isinstance(phone, dict):  # core renames Portal keys to snake_case; restore them
                state["phone_state"] = {CAMEL_PHONE_KEYS.get(k, k): v for k, v in phone.items()}
            return state
        try:
            return await self.portal.state()
        except (AdbError, PortalError) as exc:
            self._lost(exc)

    async def capture(self) -> Screen:
        state = await self.raw_state()
        if self.adb is not None:
            self.screen = parse_screen(state)
        else:
            size = None
            if self.target.platform == "ios":
                size = tuple(await self.core.call("screen_size"))
            self.screen = parse_any_state(state, size)
        return self.screen

    async def perceive(self, max_marks: int = 150) -> tuple[Screen, list[Mark]]:
        """Fresh screen plus numbered marks; the marks become the current (valid) ids."""
        screen = await self.capture()
        marks = build_marks(screen, max_marks)
        self.marks, self.marks_stale = marks, False
        self.signature = signature(screen, marks)
        self.last_look_at = time.monotonic()
        return screen, marks

    async def peek(self) -> tuple[Screen, list[Mark], str]:
        """Capture without touching the id table (used for settle polling)."""
        screen = await self.capture()
        marks = build_marks(screen)
        return screen, marks, signature(screen, marks)

    def invalidate_marks(self) -> None:
        self.marks_stale = True
        self.agent_elements = []

    async def agent_state(self) -> str:
        """Index the screen the way the mobilerun agent does; returns its formatted text."""
        from .agentui import index_state

        state = await self.raw_state()
        text, elements = index_state(state)
        if not elements:  # non-Portal tree (iOS): number the parsed elements in the same order
            screen = await self.capture()
            elements = [
                {
                    "index": i,
                    "resourceId": e.resource_id,
                    "className": e.class_name,
                    "checkedState": (f"isChecked={e.checked}" if e.checkable else ""),
                    "text": e.text or e.description or e.resource_id or e.class_name,
                    "bounds": f"{e.bounds.left},{e.bounds.top},{e.bounds.right},{e.bounds.bottom}",
                    "children": [],
                }
                for i, e in enumerate(
                    (
                        e
                        for e in screen.elements
                        if e.bounds.right - e.bounds.left > 5 and e.bounds.bottom - e.bounds.top > 5
                    ),
                    start=1,
                )
            ]
            from .agentui import SCHEMA, _element_lines

            text = f"Current Clickable UI elements:\n{SCHEMA}:\n{_element_lines(elements)}"
        self.agent_elements = elements
        self.agent_size = await self.screen_size()
        return text

    def get_mark(self, som_id: int) -> Mark:
        if not self.marks:
            fail("unknown_som_id", "no screen has been perceived yet", "call perceive_screen first")
        if self.marks_stale:
            fail(
                "stale_som_id",
                f"som_id {som_id} belongs to a screen that has since changed",
                "call perceive_screen or read_screen again and use the new ids",
            )
        for mark in self.marks:
            if mark.id == som_id:
                return mark
        fail("unknown_som_id", f"no mark with id {som_id}", f"valid ids are 1..{len(self.marks)}")

    async def screenshot(self) -> bytes:
        await self.ensure_connected()
        if self.adb is None:
            return await self.core.screenshot_png()
        try:
            return await self.portal.screenshot()
        except (AdbError, PortalError) as exc:
            self._lost(exc)

    async def screen_size(self) -> tuple[int, int]:
        if self.screen is not None:
            return self.screen.width, self.screen.height
        if self.adb is None:
            width, height = await self.core.call("screen_size")
            return int(width), int(height)
        size = parse_wm_size(await self.shell("wm size"))
        return size or (720, 1280)

    # ---- apps --------------------------------------------------------------------------
    async def apps(self, refresh: bool = False) -> list[App]:
        if refresh or not self._apps or time.monotonic() - self._apps_at > APPS_TTL:
            await self.ensure_connected()
            if self.adb is None:
                raw = await self.core.call("list_apps", include_system_apps=True)
                self._apps = [
                    App(
                        package=str(a.get("package_name") or a.get("packageName") or ""),
                        label=str(a.get("label") or ""),
                        system=bool(a.get("is_system_app") or a.get("isSystemApp")),
                        version=str(a.get("version_name") or ""),
                    )
                    for a in raw
                    if a.get("package_name") or a.get("packageName")
                ]
            else:
                try:
                    self._apps = parse_apps(await self.portal.apps())
                except (AdbError, PortalError) as exc:
                    self._lost(exc)
            self._apps_at = time.monotonic()
        return self._apps


class Runtime:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._sessions: dict[str, DeviceSession] = {}
        self._default = ""
        self.local_tasks = None  # tools.tasks.LocalTasks

    def default_device(self) -> str:
        """MOBILERUN_DEVICE, else the only attached adb device; anything else is an error."""
        if not self._default:
            self._default = self.config.device or detect_single_device(self.config.adb_bin) or ""
        if not self._default:
            fail(
                "device_unreachable",
                "no device selected",
                "set MOBILERUN_DEVICE=<adb serial | ios | cloud:<uuid> | http://portal> "
                "or attach exactly one adb device",
            )
        return self._default

    def session(self, device: str | None = None) -> DeviceSession:
        name = device or self.default_device()
        if name not in self._sessions:
            self._sessions[name] = DeviceSession(resolve_target(name), self.config)
        return self._sessions[name]

    async def drop(self, name: str) -> None:
        session = self._sessions.pop(name, None)
        if session is not None:
            if session.browser is not None:
                await session.browser.close()
            if session.portal is not None:
                await session.portal.close()

    async def aclose(self) -> None:
        for session in self._sessions.values():
            if session.browser is not None:
                await session.browser.close()
            if session.portal is not None:
                await session.portal.close()
