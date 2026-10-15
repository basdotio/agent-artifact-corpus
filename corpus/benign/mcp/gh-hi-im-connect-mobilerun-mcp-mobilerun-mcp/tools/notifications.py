"""Reading, acting on and dismissing notifications.

Reading uses ``dumpsys notification``. Acting and dismissing drive the shade UI, because adb
cannot fire a PendingIntent or cancel another app's notification.
"""

from __future__ import annotations

import asyncio

from fastmcp import FastMCP

from ..errors import fail
from ..observe import mutate, settle
from ..parsers.notifications import Notification, parse_notifications
from ..parsers.shade import find_clear_all, match_row, notification_rows
from ..policy import check_app
from ..session import DeviceSession, Runtime
from .common import Device, enforce, get_session


async def dump(session: DeviceSession) -> list[Notification]:
    return parse_notifications(await session.shell("dumpsys notification --noredact", timeout=45))


def select(
    items: list[Notification], key: str | None, package: str | None, title: str | None
) -> Notification:
    pool = [n for n in items if (not key or n.key == key) and (not package or n.package == package)]
    if title:
        pool = [n for n in pool if title.lower() in n.title.lower()]
    if not pool:
        fail(
            "element_not_found",
            "no notification matches",
            "call read_notifications for the current keys",
        )
    if len(pool) > 1 and not key:
        fail(
            "invalid_argument", f"{len(pool)} notifications match; pass key from read_notifications"
        )
    return pool[0]


async def open_shade(session: DeviceSession) -> None:
    await session.shell("cmd statusbar expand-notifications")
    await settle(session.peek, timeout=3.0)


async def close_shade(session: DeviceSession) -> None:
    await session.shell("cmd statusbar collapse")


MAX_DISMISS_STEPS = 25


async def dismiss_rows(session: DeviceSession, targets: list[Notification]) -> None:
    """Swipe target rows off the shade one at a time (tapping 'Clear all' if it is on screen)."""
    wanted = {(n.title, n.text) for n in targets}
    for _ in range(MAX_DISMISS_STEPS):
        screen = await session.capture()
        if screen.phone.package != "com.android.systemui":
            await open_shade(session)
            screen = await session.capture()
        button = find_clear_all(screen) if len(wanted) > 1 else None
        if button is not None:
            cx, cy = button.bounds.center
            await session.tap_xy(cx, cy)
            await asyncio.sleep(0.8)
            return
        row = next(
            (
                r
                for r in notification_rows(screen)
                if (r.title, r.text) in wanted
                or any(r.title == t and (not x or x in r.text) for t, x in wanted)
            ),
            None,
        )
        if row is None:
            return  # nothing left that we can see
        cy = (row.bounds.top + row.bounds.bottom) // 2
        await session.swipe_xy(row.bounds.left + 40, cy, row.bounds.right - 20, cy, 300)
        await asyncio.sleep(0.7)
        wanted.discard((row.title, row.text))
        if not wanted:
            return


def register(mcp: FastMCP, rt: Runtime) -> None:
    @mcp.tool(tags={"read"})
    async def read_notifications(
        package_name: str | None = None,
        include_ongoing: bool = False,
        limit: int = 20,
        package: str | None = None,
        device: Device = None,
    ) -> dict:
        """Current status-bar notifications, newest first, without touching the screen: key,
        app, title, text, action labels. Ongoing ones (music, navigation, downloads) only with
        include_ongoing=true; package_name filters to one app; limit default 20, cap 30.
        With the safety policy on, banking and authenticator notifications are withheld."""
        package = package_name or package
        limit = min(max(limit, 1), 30)
        items = await dump(get_session(rt, device))
        if rt.config.policy != "off":
            items = [n for n in items if check_app(rt.config.policy, n.package).allowed]
        shown = [
            n
            for n in items
            if (not package or n.package == package) and (include_ongoing or not n.ongoing)
        ]
        shown.sort(key=lambda n: n.when_ms, reverse=True)
        return {"count": len(shown), "notifications": [n.to_dict() for n in shown[:limit]]}

    @mcp.tool(tags={"write"})
    async def dismiss_notification(
        key: str | None = None,
        package: str | None = None,
        title: str | None = None,
        clear_all: bool = False,
        device: Device = None,
    ) -> dict:
        """Dismiss one notification (by key, or package/title) or every clearable one."""
        session = get_session(rt, device)
        before = await dump(session)
        if clear_all:
            targets = [n for n in before if n.clearable]
        else:
            target = select(before, key, package, title)
            if not target.clearable:
                fail("not_permitted", f"'{target.title}' is ongoing and cannot be dismissed")
            targets = [target]
        if not targets:
            return {"ok": True, "dismissed": [], "message": "nothing clearable"}

        async def action() -> None:
            await open_shade(session)
            await dismiss_rows(session, targets)
            await close_shade(session)

        result = await mutate(session, action, {"action": "dismiss_notification"})
        after_keys = {n.key for n in await dump(session)}
        gone = [n.key for n in targets if n.key not in after_keys]
        return {
            **result,
            "ok": bool(gone),
            "dismissed": gone,
            "still_present": [n.key for n in targets if n.key in after_keys],
        }

    @mcp.tool(tags={"write"})
    async def notification_action(
        action: str,
        key: str | None = None,
        package: str | None = None,
        title: str | None = None,
        reply_text: str | None = None,
        device: Device = None,
    ) -> dict:
        """Tap one of a notification's own buttons (reply, archive, stop...); reply_text fills an
        inline reply field and sends it. Best-effort: it drives the notification shade."""
        session = get_session(rt, device)
        target = select(await dump(session), key, package, title)
        enforce(check_app(rt.config.policy, target.package))
        labels = [a.lower() for a in target.actions]
        if action.lower() not in labels:
            fail("element_not_found", f"no action '{action}'", f"available: {list(target.actions)}")

        async def sequence() -> None:
            await open_shade(session)
            screen = await session.capture()
            row = match_row(notification_rows(screen), target.title, target.text)
            if row is None:
                fail("element_not_found", "notification row not visible in the shade")
            if not row.expanded and row.expand_button is not None:
                ex, ey = row.expand_button.bounds.center
                await session.tap_xy(ex, ey)
                await settle(session.peek, timeout=2.5)
                screen = await session.capture()
                row = match_row(notification_rows(screen), target.title, target.text) or row
            button = next((b for b in row.actions if b.label.lower() == action.lower()), None)
            if button is None:
                fail("element_not_found", f"button '{action}' not shown on the expanded row")
            bx, by = button.bounds.center
            await session.tap_xy(bx, by)
            if reply_text is not None:
                await settle(session.peek, timeout=3.0)
                await session.portal.input_text(reply_text)
                await session.press("enter")

        return await mutate(
            session, sequence, {"action": "notification_action", "notification": target.title}
        )
