"""Waiting, watching and verifying: wait_for, watch_device_events, validate_action, verify_action."""

from __future__ import annotations

import asyncio
import time

from fastmcp import FastMCP

from .. import ocr as ocr_mod
from ..conditions import (
    diff_events,
    diff_notifications,
    matches,
    normalize,
    screen_text,
    snapshot_of,
)
from ..errors import fail
from ..marks import has_loading_indicator, signature, top_labels
from ..observe import build_observation
from ..parsers.notifications import parse_notifications
from ..parsers.packages import resolve_app
from ..policy import check_app, check_text
from ..session import DeviceSession, Runtime
from ..shell import view_args
from .apps import resolve_component
from .common import Device, get_session

MAX_WATCH_SECONDS = 30.0
NOTIFICATION_POLL = 2.0
ACTIONS = ("tap", "double_tap", "long_press", "swipe", "type_text", "launch_app", "open_deeplink")


async def poll_until(session: DeviceSession, check, timeout: float, interval: float):
    """Poll the screen until ``check(screen, marks)`` returns a truthy value or time runs out."""
    deadline = time.monotonic() + timeout
    while True:
        screen, marks, sig = await session.peek()
        found = check(screen, marks)
        if found or time.monotonic() >= deadline:
            return found, screen, marks, sig
        await asyncio.sleep(interval)


def register(mcp: FastMCP, rt: Runtime) -> None:
    @mcp.tool(tags={"read"})
    async def wait_for(
        condition: str | None = None,
        timeout_ms: int | None = None,
        poll_interval_ms: int | None = None,
        text: str | None = None,
        package: str | None = None,
        activity: str | None = None,
        gone: bool = False,
        timeout: float | None = None,
        interval: float | None = None,
        device: Device = None,
    ) -> dict:
        """LONG waits only (downloads, uploads, processing, status changes); gestures already
        settle. With text / package / activity: wait until that is on screen (gone=true: until it
        disappears). Otherwise wait until loading finishes (no progress bar or "Loading" text) and
        the screen is still; condition is echoed back, you judge the returned state.
        Timeouts: timeout_ms (default 5000, max 30000) / poll_interval_ms (default 500, min 100),
        or timeout / interval in seconds."""
        session = get_session(rt, device)
        started = time.monotonic()
        explicit = text is not None or package is not None or activity is not None
        if timeout_ms is not None:
            limit = min(max(timeout_ms, 0), 30000) / 1000
        elif timeout is not None:
            limit = min(timeout, 120.0)
        else:
            limit = 15.0 if explicit else 5.0
        step = max(poll_interval_ms or 500, 100) / 1000 if interval is None else interval
        if explicit:

            def check(screen, marks):
                ok, evidence = matches(screen, marks, text=text, package=package, activity=activity)
                return evidence or True if (not ok if gone else ok) else None
        else:
            last: dict[str, str] = {}

            def check(screen, marks):
                sig = signature(screen, marks)
                still = last.get("sig") == sig
                last["sig"] = sig
                return "loaded" if still and not has_loading_indicator(screen) else None

        found, screen, marks, sig = await poll_until(session, check, limit, step)
        return {
            "ok": bool(found),
            **({"condition": condition} if condition else {}),
            "gone": gone,
            "timed_out": not found,
            "elapsed": round(time.monotonic() - started, 2),
            "evidence": found if isinstance(found, str) else "",
            "observation": build_observation("", screen, marks, sig, True),
        }

    @mcp.tool(tags={"read"})
    async def watch_device_events(
        timeout_seconds: float | None = None,
        max_events: int = 50,
        duration: float | None = None,
        interval: float = 0.5,
        kinds: list[str] | None = None,
        device: Device = None,
    ) -> dict:
        """Collect device events for up to timeout_seconds (default 10, max 30), returning early
        once max_events (default 50) arrive: foreground app, keyboard, screen content,
        notifications posted/removed. kinds filters: foreground, keyboard, screen, notifications."""
        session = get_session(rt, device)
        wanted = set(kinds or ["foreground", "keyboard", "screen", "notifications"])
        if not session.has_adb:
            wanted.discard("notifications")  # read from dumpsys
        seconds = timeout_seconds if timeout_seconds is not None else duration
        duration = min(max(10.0 if seconds is None else seconds, 0.5), MAX_WATCH_SECONDS)
        events: list[dict] = []
        screen, marks, sig = await session.peek()
        prev = snapshot_of(screen, marks, sig)
        keys = (
            {
                n.key
                for n in parse_notifications(
                    await session.shell("dumpsys notification --noredact", timeout=45)
                )
            }
            if "notifications" in wanted
            else set()
        )
        start = last_notification_poll = time.monotonic()
        while time.monotonic() - start < duration:
            await asyncio.sleep(interval)
            screen, marks, sig = await session.peek()
            cur = snapshot_of(screen, marks, sig)
            for event in diff_events(prev, cur):
                kind = {
                    "foreground_changed": "foreground",
                    "keyboard": "keyboard",
                    "screen_changed": "screen",
                }[str(event["type"])]
                if kind in wanted:
                    events.append({"t": round(time.monotonic() - start, 2), **event})
            prev = cur
            if (
                "notifications" in wanted
                and time.monotonic() - last_notification_poll >= NOTIFICATION_POLL
            ):
                last_notification_poll = time.monotonic()
                now_keys = {
                    n.key
                    for n in parse_notifications(
                        await session.shell("dumpsys notification --noredact", timeout=45)
                    )
                }
                for event in diff_notifications(keys, now_keys):
                    events.append({"t": round(time.monotonic() - start, 2), **event})
                keys = now_keys
            if len(events) >= max_events:
                events = events[:max_events]
                break
        return {
            "duration": round(time.monotonic() - start, 2),
            "count": len(events),
            "events": events,
        }

    @mcp.tool(tags={"read"})
    async def validate_action(
        gesture_type: str | None = None,
        target: str | None = None,
        action: str | None = None,
        x: int | None = None,
        y: int | None = None,
        som_id: int | None = None,
        text: str | None = None,
        package: str | None = None,
        app_name: str | None = None,
        uri: str | None = None,
        device: Device = None,
    ) -> dict:
        """Pre-check a planned action against the safety policy (and, for our action set, that
        its target exists) without doing it. gesture_type is the action (tap, type_text,
        launch_app, open_deeplink, ...); target is the app name/package, deep-link URI or text
        you plan to use. Returns allowed=false with a category for blocked apps and text."""
        action = action or gesture_type
        if not action:
            fail("invalid_argument", "give gesture_type")
        mode = rt.config.policy
        if target is not None:
            if action in ("type_text", "type", "type_secret"):
                text = text if text is not None else target
            elif (
                action in ("open_deeplink", "open_deep_link", "resolve_deeplink") or "://" in target
            ):
                uri = uri or target
            else:
                app_name = app_name or target
        if action not in ACTIONS:
            decision = check_text(mode, target or "") if target else None
            if decision is None or decision.allowed:
                decision = check_app(mode, target or "", target or "") if target else decision
            blocked = bool(decision and not decision.allowed)
            return {
                "allowed": not blocked,
                "valid": not blocked,
                "problems": [f"policy_blocked: {decision.category}"] if blocked else [],
                "category": decision.category if blocked else "",
                "message": decision.reason if blocked else "",
                "policy": {
                    "mode": mode,
                    "blocked": blocked,
                    "category": decision.category if blocked else "",
                },
            }
        session = get_session(rt, device)
        problems: list[str] = []
        blocked = None
        if action in ("tap", "double_tap", "long_press", "swipe"):
            if som_id is not None:
                try:
                    mark = session.get_mark(som_id)
                    x, y = mark.center
                except Exception as exc:  # stale/unknown ids are reported, not raised
                    problems.append(str(exc))
            if x is not None and y is not None:
                width, height = await session.screen_size()
                if not (0 <= x < width and 0 <= y < height):
                    problems.append(f"({x},{y}) is outside the {width}x{height} screen")
            elif som_id is None:
                problems.append("give x and y, or a som_id")
            screen = await session.capture()
            blocked = check_app(mode, screen.phone.package, screen.phone.app)
        elif action == "type_text":
            if text is None:
                problems.append("text is required")
            else:
                screen = await session.capture()
                field = next((e for e in screen.elements if e.focused and e.editable), None)
                if field is None:
                    problems.append("no editable field is focused")
                blocked = check_text(
                    mode,
                    text,
                    " ".join(filter(None, (field.hint, field.description, field.short_id)))
                    if field
                    else "",
                    bool(field and field.password),
                )
        elif action == "launch_app":
            apps = await session.apps()
            match = next((a for a in apps if a.package == package), None)
            if match is None and app_name:
                match, _ = resolve_app(app_name, apps)
            if match is None:
                problems.append("no single installed app matches")
            else:
                blocked = check_app(mode, match.package, match.label)
        else:
            if not uri:
                problems.append("uri is required")
            else:
                component = await resolve_component(session, view_args(uri, package))
                if not component:
                    problems.append(f"no app handles {uri}")
                else:
                    blocked = check_app(mode, component.split("/")[0])
        if blocked is not None and not blocked.allowed:
            problems.append(f"policy_blocked: {blocked.category}")
        is_blocked = bool(blocked and not blocked.allowed)
        return {
            "allowed": not is_blocked,
            "valid": not problems,
            "problems": problems,
            "category": blocked.category if is_blocked else "",
            "message": blocked.reason if is_blocked else "",
            "policy": {
                "mode": mode,
                "blocked": bool(blocked and not blocked.allowed),
                "category": blocked.category if blocked else "",
            },
        }

    @mcp.tool(tags={"read"})
    async def verify_action(
        expected: str,
        kind: str = "text",
        timeout: float = 3.0,
        use_ocr: bool = False,
        device: Device = None,
    ) -> dict:
        """Check an outcome against the live screen. kind: text (visible), gone (not visible),
        app (foreground package or name), activity, changed (the last action changed the screen)."""
        if kind not in ("text", "gone", "app", "activity", "changed"):
            fail("invalid_argument", "kind must be text, gone, app, activity or changed")
        session = get_session(rt, device)
        if kind == "changed":
            last = session.last_observation or {}
            return {
                "verified": bool(last.get("screen_changed")),
                "evidence": "from the last action's observation",
            }

        def check(screen, marks):
            if kind == "app":
                ok, ev = matches(screen, marks, package=expected)
            elif kind == "activity":
                ok, ev = matches(screen, marks, activity=expected)
            else:
                ok, ev = matches(screen, marks, text=expected)
                ok = ok if kind == "text" else not ok
            return ev or True if ok else None

        found, screen, marks, sig = await poll_until(session, check, timeout, 0.4)
        state = build_observation("", screen, marks, sig, True)
        state["top_labels"] = top_labels(marks, 10)
        state.pop("screen_changed", None)
        if not found and kind == "text" and use_ocr and ocr_mod.available():
            lines = await ocr_mod.run_tesseract(await session.screenshot())
            haystack = normalize(" ".join(line.text for line in lines))
            if normalize(expected) in haystack:
                return {
                    "verified": True,
                    "evidence": "found by OCR",
                    "expected": expected,
                    "state": state,
                }
        return {
            "expected": expected,
            "state": state,
            "verified": bool(found),
            "evidence": found if isinstance(found, str) else "",
            "foreground": screen.phone.package,
            "visible_text": screen_text(screen)[:300] if not found else "",
        }
