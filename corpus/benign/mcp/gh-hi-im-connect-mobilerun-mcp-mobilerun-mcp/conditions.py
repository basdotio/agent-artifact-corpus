"""Screen conditions and change events used by wait_for, verify_action and watch_device_events."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Mark, Screen

_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def screen_text(screen: Screen) -> str:
    """Every visible label on screen, space-joined."""
    return " ".join(e.label for e in screen.elements if e.visible and e.label)


def find_text(screen: Screen, text: str) -> str | None:
    """The label containing ``text`` (whitespace/case-insensitive), or None."""
    want = normalize(text)
    if not want:
        return None
    for element in screen.elements:
        if element.visible and want in normalize(element.label):
            return element.label
    return want and (text if want in normalize(screen_text(screen)) else None) or None


def matches(
    screen: Screen,
    marks: list[Mark],
    *,
    text: str | None = None,
    package: str | None = None,
    activity: str | None = None,
) -> tuple[bool, str]:
    """Do all given conditions hold? Returns (ok, evidence)."""
    evidence = []
    if package is not None:
        if package.lower() not in (screen.phone.package.lower(), screen.phone.app.lower()):
            return False, f"foreground is {screen.phone.package}"
        evidence.append(f"package={screen.phone.package}")
    if activity is not None:
        if normalize(activity) not in normalize(screen.phone.activity):
            return False, f"activity is {screen.phone.activity}"
        evidence.append(f"activity={screen.phone.activity}")
    if text is not None:
        label = find_text(screen, text)
        if label is None:
            return False, f'"{text}" not on screen'
        evidence.append(f'text="{label[:60]}"')
    return bool(evidence), ", ".join(evidence)


@dataclass(frozen=True)
class Snapshot:
    package: str
    activity: str
    keyboard: bool
    signature: str
    count: int


def snapshot_of(screen: Screen, marks: list[Mark], signature: str) -> Snapshot:
    return Snapshot(
        screen.phone.package,
        screen.phone.activity.rsplit(".", 1)[-1],
        screen.phone.keyboard_visible,
        signature,
        len(marks),
    )


def diff_events(prev: Snapshot, cur: Snapshot) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    if (prev.package, prev.activity) != (cur.package, cur.activity):
        events.append(
            {
                "type": "foreground_changed",
                "from": f"{prev.package}/{prev.activity}",
                "to": f"{cur.package}/{cur.activity}",
            }
        )
    if prev.keyboard != cur.keyboard:
        events.append({"type": "keyboard", "visible": cur.keyboard})
    if prev.signature != cur.signature:
        events.append({"type": "screen_changed", "element_count": cur.count})
    return events


def diff_notifications(old_keys: set[str], new_keys: set[str]) -> list[dict[str, object]]:
    return [{"type": "notification_posted", "key": k} for k in sorted(new_keys - old_keys)] + [
        {"type": "notification_removed", "key": k} for k in sorted(old_keys - new_keys)
    ]
