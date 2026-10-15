"""Gestures, typing and hardware keys."""

from __future__ import annotations

from fastmcp import FastMCP

from ..errors import fail
from ..marks import find_marks
from ..observe import mutate, settle
from ..policy import check_text
from ..session import DeviceSession, Runtime
from .common import Device, check_point, enforce, get_session, guard_foreground

DEFAULT_SWIPE_MS = 300
DEFAULT_LONG_PRESS_MS = 1000  # AURA's default; mobilerun-core callers pass ms=800 explicitly
SCROLL_MS = 500
SCROLL_TOP_MARGIN = 120
SCROLL_BOTTOM_MARGIN = 140


def scroll_vector(direction: str, region: tuple[int, int, int, int], amount: float):
    """(x1, y1, x2, y2) finger path that scrolls the content ``direction`` by ``amount`` of the region."""
    left, top, right, bottom = region
    cx, cy = (left + right) // 2, (top + bottom) // 2
    dx = int((right - left) * min(max(amount, 0.1), 0.9) / 2)
    dy = int((bottom - top) * min(max(amount, 0.1), 0.9) / 2)
    return {
        "down": (cx, cy + dy, cx, cy - dy),
        "up": (cx, cy - dy, cx, cy + dy),
        "right": (cx + dx, cy, cx - dx, cy),
        "left": (cx - dx, cy, cx + dx, cy),
    }[direction]


async def tap_point(session: DeviceSession, x: int, y: int, stealth: bool = False) -> None:
    if stealth:
        await session.core.call("tap", x, y, stealth=True)
    else:
        await session.tap_xy(x, y)


async def index_point(session: DeviceSession, index: int) -> tuple[int, int, dict]:
    """Tap point for a mobilerun-agent element index (see get_state)."""
    from ..agentui import element_coords

    if not session.agent_elements:
        await session.agent_state()
    try:
        x, y = element_coords(session.agent_elements, index, session.agent_size)
    except ValueError as exc:
        fail("element_not_found", str(exc), "call get_state for current indices")
    element = next(e for e in session.agent_elements if e["index"] == index)
    return x, y, {"target": {"index": index, "text": element["text"]}}


def register(mcp: FastMCP, rt: Runtime) -> None:
    async def resolve_point(session, x, y, som_id, index=None) -> tuple[int, int, dict]:
        if som_id is not None:
            mark = session.get_mark(som_id)
            cx, cy = mark.center
            return cx, cy, {"target": {"som_id": som_id, "label": mark.label}}
        if index is not None:
            return await index_point(session, index)
        if x is None or y is None:
            fail("invalid_argument", "give x and y, a som_id, or an index")
        check_point(await session.screen_size(), x, y)
        return x, y, {"target": {"x": x, "y": y}}

    @mcp.tool(tags={"write"})
    async def tap(
        x: int | None = None,
        y: int | None = None,
        som_id: int | None = None,
        stealth: bool = False,
        device: Device = None,
    ) -> dict:
        """Tap at (x, y) or at the center of a numbered mark (som_id from perceive_screen /
        read_screen). stealth=true uses mobilerun-core's humanized tap."""
        session = get_session(rt, device)
        await guard_foreground(rt, session)
        cx, cy, info = await resolve_point(session, x, y, som_id)
        return await mutate(
            session, lambda: tap_point(session, cx, cy, stealth), {"action": "tap", **info}
        )

    @mcp.tool(tags={"write"})
    async def double_tap(
        x: int | None = None, y: int | None = None, som_id: int | None = None, device: Device = None
    ) -> dict:
        """Double-tap at (x, y) or a mark."""
        session = get_session(rt, device)
        await guard_foreground(rt, session)
        cx, cy, info = await resolve_point(session, x, y, som_id)
        return await mutate(
            session, lambda: session.double_tap_xy(cx, cy), {"action": "double_tap", **info}
        )

    @mcp.tool(tags={"write"})
    async def long_press(
        x: int | None = None,
        y: int | None = None,
        som_id: int | None = None,
        index: int | None = None,
        duration_ms: int | None = None,
        ms: int | None = None,
        device: Device = None,
    ) -> dict:
        """Press and hold at (x, y), a mark (som_id) or a get_state element (index).
        Hold time: duration_ms or ms (default 1000)."""
        session = get_session(rt, device)
        await guard_foreground(rt, session)
        cx, cy, info = await resolve_point(session, x, y, som_id, index)
        hold = duration_ms or ms or DEFAULT_LONG_PRESS_MS
        return await mutate(
            session,
            lambda: session.long_press_xy(cx, cy, hold),
            {"action": "long_press", "duration_ms": hold, **info},
        )

    @mcp.tool(tags={"write"})
    async def long_press_at(x: int, y: int, device: Device = None) -> dict:
        """Long press at (x, y) (mobilerun agent action)."""
        return await long_press(x=x, y=y, device=device)

    async def do_swipe(device, x1, y1, x2, y2, ms, action="swipe") -> dict:
        session = get_session(rt, device)
        await guard_foreground(rt, session)
        size = await session.screen_size()
        for px, py in ((x1, y1), (x2, y2)):
            check_point(size, px, py)
        return await mutate(
            session,
            lambda: session.swipe_xy(x1, y1, x2, y2, ms),
            {"action": action, "from": [x1, y1], "to": [x2, y2], "duration_ms": ms},
        )

    @mcp.tool(tags={"write"})
    async def swipe(
        x1: int | None = None,
        y1: int | None = None,
        x2: int | None = None,
        y2: int | None = None,
        duration_ms: int | None = None,
        ms: int | None = None,
        coordinate: list[int] | None = None,
        coordinate2: list[int] | None = None,
        duration: float | None = None,
        device: Device = None,
    ) -> dict:
        """Swipe from (x1, y1) to (x2, y2) over duration_ms / ms (default 300).
        mobilerun agent form: coordinate=[x, y], coordinate2=[x, y], duration in seconds."""
        if coordinate is not None or coordinate2 is not None:
            if not (coordinate and coordinate2 and len(coordinate) == 2 and len(coordinate2) == 2):
                fail("invalid_argument", "coordinate and coordinate2 must be [x, y] lists")
            x1, y1 = coordinate
            x2, y2 = coordinate2
            duration = 1.0 if duration is None and duration_ms is None and ms is None else duration
        if None in (x1, y1, x2, y2):
            fail("invalid_argument", "give x1, y1, x2, y2 (or coordinate and coordinate2)")
        hold = (
            duration_ms
            or ms
            or (int(duration * 1000) if duration is not None else DEFAULT_SWIPE_MS)
        )
        return await do_swipe(device, x1, y1, x2, y2, hold)

    async def do_scroll(
        direction: str, amount: float, som_id: int | None, device: Device, ms: int = SCROLL_MS
    ) -> dict:
        session = get_session(rt, device)
        await guard_foreground(rt, session)
        width, height = await session.screen_size()
        if som_id is not None:
            b = session.get_mark(som_id).bounds
            region = (b.left, b.top, b.right, b.bottom)
        else:
            region = (0, 0, width, height)
        x1, y1, x2, y2 = scroll_vector(direction, region, amount)
        return await mutate(
            session,
            lambda: session.swipe_xy(x1, y1, x2, y2, ms),
            {"action": f"scroll_{direction}"},
        )

    @mcp.tool(tags={"write"})
    async def scroll_down(
        amount: float = 0.5, som_id: int | None = None, device: Device = None
    ) -> dict:
        """Scroll the content down (reveal what is below): a centered swipe over half the screen
        (amount), or inside a scrollable mark (som_id)."""
        return await do_scroll("down", amount, som_id, device)

    @mcp.tool(tags={"write"})
    async def scroll_up(
        amount: float = 0.5, som_id: int | None = None, device: Device = None
    ) -> dict:
        """Scroll the content up (reveal what is above)."""
        return await do_scroll("up", amount, som_id, device)

    @mcp.tool(tags={"write"})
    async def scroll_left(
        amount: float = 0.5, som_id: int | None = None, device: Device = None
    ) -> dict:
        """Scroll the content left (reveal what is to the left)."""
        return await do_scroll("left", amount, som_id, device)

    @mcp.tool(tags={"write"})
    async def scroll_right(
        amount: float = 0.5, som_id: int | None = None, device: Device = None
    ) -> dict:
        """Scroll the content right (reveal what is to the right)."""
        return await do_scroll("right", amount, som_id, device)

    @mcp.tool(tags={"write"})
    async def scroll(
        direction: str,
        distance: float = 0.5,
        ms: int = DEFAULT_SWIPE_MS,
        verify: bool = False,
        device: Device = None,
    ) -> dict:
        """Scroll the content in direction (up | down | left | right) by distance (fraction of
        the screen). verify=true reports whether the screen actually moved (mobilerun-core)."""
        if direction not in ("down", "up", "left", "right"):
            fail("invalid_argument", "direction must be down, up, left or right")
        result = await do_scroll(direction, distance, None, device, ms)
        result["action"] = "scroll"
        if verify:
            result["moved"] = result["post_action_observation"]["screen_changed"]
        return result

    async def scroll_until_text(session, text, direction, max_scrolls) -> dict:
        width, height = await session.screen_size()
        region = (0, SCROLL_TOP_MARGIN, width, height - SCROLL_BOTTOM_MARGIN)
        vector = scroll_vector(direction, region, 0.6)
        async with session.lock:
            last_sig = ""
            for scrolls in range(max_scrolls + 1):
                _, marks = await session.perceive()
                hits = find_marks(marks, text)
                if hits:
                    return {
                        "ok": True,
                        "found": True,
                        "scrolls": scrolls,
                        "mark": hits[0].to_dict(),
                    }
                if session.signature == last_sig:
                    break  # the screen stopped changing: end of the list
                last_sig = session.signature
                if scrolls < max_scrolls:
                    await session.swipe_xy(*vector, 600)
                    await settle(session.peek)  # let the fling finish so the next tap is a tap
        return {
            "ok": True,
            "found": False,
            "message": f'"{text}" not found while scrolling {direction}',
        }

    @mcp.tool(tags={"write"})
    async def scroll_to(
        x1: int | None = None,
        y1: int | None = None,
        x2: int | None = None,
        y2: int | None = None,
        duration_ms: int = DEFAULT_SWIPE_MS,
        text: str | None = None,
        direction: str = "down",
        max_scrolls: int = 8,
        device: Device = None,
    ) -> dict:
        """Two modes. With x1, y1, x2, y2: drag the content from one point to the other (precise
        scroll, AURA). With text: scroll in direction until an element containing text is
        visible and return its mark."""
        if text is None:
            if None in (x1, y1, x2, y2):
                fail("invalid_argument", "give x1, y1, x2, y2, or text")
            return await do_swipe(device, x1, y1, x2, y2, duration_ms, action="scroll_to")
        if direction not in ("down", "up", "left", "right"):
            fail("invalid_argument", "direction must be down, up, left or right")
        session = get_session(rt, device)
        await guard_foreground(rt, session)
        return await scroll_until_text(session, text, direction, max_scrolls)

    async def focused_field(session):
        screen = await session.capture()
        return next((e for e in screen.elements if e.focused and e.editable), None)

    async def enter_text(
        session,
        text: str,
        clear: bool,
        submit: bool,
        action: str,
        stealth: bool = False,
        wpm: int | None = None,
    ) -> dict:
        focused = await focused_field(session)
        hint = " ".join(
            filter(None, (focused.hint, focused.description, focused.short_id) if focused else ())
        )
        enforce(check_text(rt.config.policy, text, hint, bool(focused and focused.password)))
        note = (
            {}
            if focused
            else {"warning": "no editable field appears focused; typing may go nowhere"}
        )

        async def act() -> None:
            if stealth:
                await session.core.call("type", text, clear=clear, wpm=wpm, stealth=True)
            else:
                await session.input_text(text, clear)
            if submit:
                await session.press("enter")

        return await mutate(session, act, {"action": action, "chars": len(text), **note})

    async def focus(session, som_id=None, index=None) -> None:
        cx, cy, _ = await resolve_point(session, None, None, som_id, index)
        await mutate(session, lambda: tap_point(session, cx, cy), {"action": "focus"})

    @mcp.tool(tags={"write"})
    async def type_text(
        text: str,
        clear: bool = False,
        submit: bool = False,
        som_id: int | None = None,
        device: Device = None,
    ) -> dict:
        """Type into the focused field (tap it first, or pass som_id). submit presses Enter after."""
        session = get_session(rt, device)
        if som_id is not None:
            await focus(session, som_id=som_id)
        return await enter_text(session, text, clear, submit, "type_text")

    @mcp.tool(tags={"write"})
    async def type(
        text: str,
        index: int | None = None,
        clear: bool = False,
        wpm: int | None = None,
        stealth: bool = False,
        device: Device = None,
    ) -> dict:
        """Type text (mobilerun). index taps that get_state element first; stealth=true types
        key by key like a person (mobilerun-core), at wpm words per minute."""
        session = get_session(rt, device)
        if index is not None and index != -1:
            await focus(session, index=index)
        return await enter_text(session, text, clear, False, "type", stealth, wpm)

    async def press_key(name: str, action: str, device: Device) -> dict:
        session = get_session(rt, device)
        return await mutate(session, lambda: session.press(name), {"action": action})

    @mcp.tool(tags={"write"})
    async def press_home(device: Device = None) -> dict:
        """Press the Home button."""
        return await press_key("home", "press_home", device)

    @mcp.tool(tags={"write"})
    async def press_back(device: Device = None) -> dict:
        """Press Back (also closes the keyboard without leaving the screen)."""
        return await press_key("back", "press_back", device)

    @mcp.tool(tags={"write"})
    async def press_enter(device: Device = None) -> dict:
        """Press Enter (submits search bars and forms)."""
        return await press_key("enter", "press_enter", device)

    @mcp.tool(tags={"write"})
    async def open_recent_apps(device: Device = None) -> dict:
        """Open the recent-apps overview."""
        return await press_key("recents", "open_recent_apps", device)

    @mcp.tool(tags={"write"})
    async def key(name_or_code: str | int, device: Device = None) -> dict:
        """Press a key by mobilerun-core name (back, home, menu, enter, delete, escape, tab, space,
        search, page_up, page_down, volume_up, volume_down, wakeup, media_play_pause, ...) or by
        Android keycode number."""
        session = get_session(rt, device)
        if isinstance(name_or_code, int) or str(name_or_code).isdigit():
            code = int(name_or_code)
            if session.has_adb:
                act = lambda: session.shell(f"input keyevent {code}")  # noqa: E731
            else:
                act = lambda: session.core.call("key", code)  # noqa: E731
        else:
            act = lambda: session.press(str(name_or_code))  # noqa: E731
        return await mutate(session, act, {"action": "key", "key": name_or_code})
