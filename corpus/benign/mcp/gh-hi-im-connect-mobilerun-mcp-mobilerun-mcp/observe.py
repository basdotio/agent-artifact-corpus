"""Settle-then-observe: every mutating action returns what the screen looks like afterwards."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .marks import has_loading_indicator, top_labels
from .models import Mark, Screen
from .policy import check_app


def is_sensitive(screen: Screen) -> bool:
    """Banking / payment / authenticator app in the foreground (independent of policy mode)."""
    return not check_app("standard", screen.phone.package, screen.phone.app).allowed


Capture = Callable[[], Awaitable[tuple[Screen, list[Mark], str]]]
Ready = Callable[[Screen, str], bool]

SCROLL_ACTIONS = {"scroll_up", "scroll_down", "scroll_left", "scroll_right", "scroll_to", "scroll"}
HINT_SCROLL = (
    "Settled after the scroll. top_labels only covers the top of the screen: call read_screen to "
    "see what is in view now before concluding the list has ended or the item is missing. "
    "Earlier som_ids are stale."
)
HINT_DEFAULT = (
    "Settled after the action. Judge the result from this observation and plan the next step; "
    "wait_for is not needed just to check. Earlier som_ids are stale: read_screen before tapping "
    "a new element by som_id, perceive_screen when you need to see the screen."
)
HINT_SENSITIVE = (
    "A banking, payment or authenticator app is in the foreground: its content is withheld and "
    "taps or reads inside it are blocked. press_back or press_home to leave it and ask the user "
    "to do this step."
)
INITIAL_DELAY = 0.3
POLL_INTERVAL = 0.25
SETTLE_TIMEOUT = 3.0


async def settle(
    capture: Capture,
    *,
    timeout: float = SETTLE_TIMEOUT,
    interval: float = POLL_INTERVAL,
    delay: float = INITIAL_DELAY,
    ready: Ready | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[Screen, list[Mark], str, bool]:
    """Poll until two consecutive captures agree and ``ready`` (default: a foreground app exists)
    accepts them. Returns (screen, marks, signature, settled)."""
    ready = ready or (lambda screen, _sig: bool(screen.phone.package))
    await sleep(delay)
    deadline = clock() + timeout
    screen, marks, sig = await capture()
    while clock() < deadline:
        await sleep(interval)
        screen2, marks2, sig2 = await capture()
        if sig2 == sig and ready(screen2, sig2):
            return screen2, marks2, sig2, True
        screen, marks, sig = screen2, marks2, sig2
    return screen, marks, sig, False


def seen_before_note(actions_ago: int) -> str:
    when = "1 action ago" if actions_ago == 1 else f"{actions_ago} actions ago"
    return (
        f"Same screen as {when}. Unless you meant to come back, you may be going in circles: "
        "try a different path."
    )


def build_observation(
    before_signature: str, screen: Screen, marks: list[Mark], signature: str, settled: bool
) -> dict[str, Any]:
    return {
        "foreground_app": screen.phone.app or screen.phone.package,
        "package": screen.phone.package,
        "activity": screen.phone.activity.rsplit(".", 1)[-1],
        "element_count": len(marks),
        "keyboard_visible": screen.phone.keyboard_visible,
        "top_labels": top_labels(marks),
        "screen_changed": bool(before_signature) and before_signature != signature,
        "loading_indicator_present": has_loading_indicator(screen),
        "settled": settled,
    }


async def mutate(
    session: Any,
    action: Callable[[], Awaitable[None]],
    result: dict[str, Any] | None = None,
    *,
    settle_timeout: float = SETTLE_TIMEOUT,
    expect_change: bool = False,
    expect_package: str | None = None,
) -> dict[str, Any]:
    """Run ``action`` under the device lock, wait for the screen to settle, report the change.

    ``expect_package`` (launches, deep links) finishes once that app, or any other app that
    replaced the previous one, is in the foreground: cold starts can take ~20s on a slow box, but
    an already-foreground target returns at once. ``expect_change`` waits for any screen change."""
    started = time.monotonic()
    async with session.lock:
        before_screen, _, before = await session.peek()
        before_package = before_screen.phone.package
        await action()
        session.invalidate_marks()

        def ready(screen: Screen, sig: str) -> bool:
            package = screen.phone.package
            if not package:
                return False
            if expect_package:
                return package == expect_package or package != before_package
            return not expect_change or sig != before

        screen, marks, sig, settled = await settle(
            session.peek, timeout=settle_timeout, ready=ready
        )
        observation = build_observation(before, screen, marks, sig, settled)
        observation["settle_ms"] = int((time.monotonic() - started) * 1000)
        if not settled:
            observation["screen_changed_confidence"] = "low"
        session.action_count += 1
        session.last_action_at = time.monotonic()
        last = session.seen_at.get(sig)
        if last is not None and observation["screen_changed"]:
            observation["seen_before"] = seen_before_note(session.action_count - last)
        session.seen_at[sig] = session.action_count
        name = str((result or {}).get("action", ""))
        observation["sensitive_foreground"] = is_sensitive(screen)
        if observation["sensitive_foreground"]:
            observation["hint"] = HINT_SENSITIVE
            if getattr(getattr(session, "config", None), "policy", "off") != "off":
                for key in (
                    "element_count",
                    "top_labels",
                    "keyboard_visible",
                    "loading_indicator_present",
                ):
                    observation.pop(key, None)
        else:
            observation["hint"] = HINT_SCROLL if name in SCROLL_ACTIONS else HINT_DEFAULT
        session.signature = sig
        session.last_observation = observation
    return {"ok": True, **(result or {}), "post_action_observation": observation}
