"""Helpers shared by tool modules."""

from __future__ import annotations

from ..errors import fail
from ..policy import Decision
from ..session import DeviceSession, Runtime

Device = str | None


def get_session(rt: Runtime, device: Device) -> DeviceSession:
    return rt.session(device)


def enforce(decision: Decision) -> None:
    if not decision.allowed:
        fail(
            "policy_blocked",
            f"{decision.category}: {decision.reason}",
            "this is a safety block; ask the user to do this part themselves",
        )


async def guard_foreground(rt: Runtime, session: DeviceSession) -> None:
    """Refuse gestures while a sensitive app is in the foreground (policy standard/strict)."""
    from ..policy import check_app

    if rt.config.policy == "off":
        return
    screen = await session.capture()
    enforce(check_app(rt.config.policy, screen.phone.package, screen.phone.app))


def check_point(session_size: tuple[int, int], x: int, y: int) -> None:
    width, height = session_size
    if not (0 <= x < width and 0 <= y < height):
        fail("invalid_argument", f"({x},{y}) is outside the {width}x{height} screen")
