"""Read notification rows out of the expanded notification shade's accessibility tree."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Bounds, Element, Screen

ROW_ID = "expandableNotificationRow"
TITLE_IDS = ("title", "notification_title")
TEXT_IDS = ("big_text", "text", "notification_text")
CLEAR_ALL_LABELS = ("clear all", "clear all notifications")


@dataclass(frozen=True)
class ShadeRow:
    bounds: Bounds
    app: str
    title: str
    text: str
    expanded: bool
    expand_button: Element | None
    actions: tuple[Element, ...]
    reply_field: Element | None


def _descendants(screen: Screen, root: Element) -> list[Element]:
    out = []
    for el in screen.elements[root.index + 1 :]:
        if el.depth <= root.depth:
            break
        out.append(el)
    return out


def _first(by_id: dict[str, Element], ids: tuple[str, ...]) -> str:
    for name in ids:
        if name in by_id:
            return by_id[name].label
    return ""


def notification_rows(screen: Screen) -> list[ShadeRow]:
    """Leaf notification rows. Group containers (rows that hold other rows) are skipped."""
    rows = []
    for root in screen.elements:
        if root.short_id != ROW_ID or not root.visible:
            continue
        kids = _descendants(screen, root)
        if any(k.short_id == ROW_ID for k in kids):
            continue  # a collapsed/expanded group header, not a notification itself
        by_id: dict[str, Element] = {}
        for k in kids:
            if k.short_id:
                by_id.setdefault(k.short_id, k)
        expand = by_id.get("expand_button")
        actions = tuple(
            k
            for k in kids
            if k.class_name == "Button"
            and k.clickable
            and k.short_id != "expand_button"
            and k.label
        )
        rows.append(
            ShadeRow(
                bounds=root.bounds,
                app=by_id["app_name_text"].label if "app_name_text" in by_id else "",
                title=_first(by_id, TITLE_IDS),
                text=_first(by_id, TEXT_IDS),
                expanded=bool(expand and expand.label.lower() == "collapse"),
                expand_button=expand,
                actions=actions,
                reply_field=next((k for k in kids if k.editable), None),
            )
        )
    return rows


def find_clear_all(screen: Screen) -> Element | None:
    for el in screen.elements:
        if el.visible and (
            el.short_id == "dismiss_text" or el.label.strip().lower() in CLEAR_ALL_LABELS
        ):
            return el
    return None


def match_row(rows: list[ShadeRow], title: str, text: str = "") -> ShadeRow | None:
    """Row whose title (and, when given, text) matches, case-insensitively."""
    want_title, want_text = title.strip().lower(), text.strip().lower()
    for row in rows:
        if want_title and row.title.strip().lower() != want_title:
            continue
        if want_text and want_text not in row.text.strip().lower():
            continue
        if want_title or want_text:
            return row
    return None
