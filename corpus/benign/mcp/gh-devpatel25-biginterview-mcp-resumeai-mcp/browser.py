"""Playwright persistent-context lifecycle, human_delay, snapshots (PLAN.md §6, §12)."""

import asyncio
import functools
import json
import os
import random
import socket
from html.parser import HTMLParser
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from . import storage
from .config import Settings, private_dir
from .schemas import ToolError


class ProfileInUseError(ToolError):
    """Another browser (e.g. login.py) holds the persistent profile (§6.1, §13 profile_in_use)."""

    def __init__(self, profile: Path):
        super().__init__(
            "profile_in_use",
            "The browser profile is in use (is scripts/login.py running?).",  # no local path: §7.0 no PII
            "Close the other browser / login script, then retry.",
        )


def profile_in_use(profile_dir: Path) -> bool:
    """True if a live Chrome process holds `profile_dir`.

    Chrome marks an open profile with a `SingletonLock` symlink pointing at
    "<hostname>-<pid>". A lock whose pid is dead is stale and Chrome clears it itself.
    """
    lock = profile_dir / "SingletonLock"
    if not os.path.lexists(lock):
        return False
    try:
        host, _, pid = os.readlink(lock).rpartition("-")
        pid_num = int(pid)
    except (OSError, ValueError):
        return True  # unreadable lock: assume held rather than risk corrupting the profile
    if pid_num <= 0:
        return True  # os.kill(0|-n) would signal a process group; treat as unreadable
    if host != socket.gethostname():
        return True  # can't check a pid on another host
    try:
        os.kill(pid_num, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OverflowError):
        return True  # OverflowError: pid out of range → unreadable lock
    return True


_pw: Playwright | None = None
_ctx: BrowserContext | None = None
_init_lock = asyncio.Lock()  # serializes launch: concurrent callers must not start two browsers
_site_lock = asyncio.Lock()  # one tool at a time: all tools drive the same page (§12: one scan in flight)


def site_operation(fn):
    """Run a site-touching tool exclusively. Inner helpers (read_feedback, …) must not re-acquire it."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        async with _site_lock:
            return await fn(*args, **kwargs)
    return wrapper


async def ensure_context(settings: Settings, headless: bool | None = None) -> BrowserContext:
    """Return the shared persistent context, launching it on first use."""
    global _pw, _ctx
    async with _init_lock:
        if _ctx is not None:
            return _ctx
        private_dir(settings.data_dir)  # profile usually lives inside it; parents get default perms
        profile = private_dir(settings.profile_dir)
        if profile_in_use(profile):
            raise ProfileInUseError(profile)
        pw = await async_playwright().start()
        try:
            ctx = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                headless=settings.headless if headless is None else headless,
                channel=settings.browser_channel,
            )
        except BaseException:
            await pw.stop()
            raise
        ctx.set_default_timeout(settings.nav_timeout_ms)
        _pw, _ctx = pw, ctx
        return ctx


async def close_context() -> None:
    global _pw, _ctx
    async with _init_lock:
        if _ctx is not None:
            await _ctx.close()
            _ctx = None
        if _pw is not None:
            await _pw.stop()
            _pw = None


async def new_page(settings: Settings, headless: bool | None = None) -> Page:
    ctx = await ensure_context(settings, headless)
    return ctx.pages[0] if ctx.pages else await ctx.new_page()


async def goto(page: Page, settings: Settings, path: str) -> None:
    await page.goto(settings.base_url + path, wait_until="domcontentloaded")


async def human_delay(settings: Settings) -> None:
    """Random pause between UI actions (§12: 2–5 s by default)."""
    await asyncio.sleep(random.uniform(settings.human_delay_min_s, settings.human_delay_max_s))


async def snapshot(page: Page, settings: Settings, name: str) -> Path:
    return storage.save_snapshot(settings, name, await page.content())


class _PropsFinder(HTMLParser):
    def __init__(self, app: str):
        super().__init__()
        self.app, self.props = app, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.props is None and a.get("data-react-class") == self.app:
            self.props = a.get("data-react-props")


def react_props(html: str, app: str) -> dict:
    """The JSON props of the portal's React app `app` (§9 amendment 2026-09-28). ValueError if absent."""
    finder = _PropsFinder(app)
    finder.feed(html)
    if finder.props is None:
        raise ValueError(f"{app} props not found")
    props = json.loads(finder.props)
    if not isinstance(props, dict):
        raise TypeError(f"{app} props is not an object")
    return props
