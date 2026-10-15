"""Build numbered targetable marks (set-of-marks) from a parsed :class:`Screen`. Pure functions."""

from __future__ import annotations

import hashlib

from .models import Bounds, Element, Mark, Screen

SYSTEM_UI = "com.android.systemui"
MIN_SIZE = 5
MAX_MARKS = 150
MAX_LABEL = 80


def _descendant_labels(screen: Screen, root: Element) -> list[str]:
    labels: list[str] = []
    for el in screen.elements[root.index + 1 :]:
        if el.depth <= root.depth:
            break
        if el.visible and el.label and el.label not in labels:
            labels.append(el.label)
    return labels


def _kind(el: Element) -> str:
    if el.scrollable and not el.label and not el.editable:
        return "scroll"
    if el.editable:
        return "input"
    if el.checkable:
        return "toggle"
    if el.interactive:
        return "button"
    if el.class_name == "ImageView" and el.description:
        return "image"
    return "text"


def _usable(el: Element, screen: Screen, allow_system_ui: bool) -> bool:
    if not el.visible or el.bounds.width < MIN_SIZE or el.bounds.height < MIN_SIZE:
        return False
    if not el.bounds.intersects(screen.bounds):
        return False
    return allow_system_ui or el.package != SYSTEM_UI


def _is_container(el: Element, screen: Screen) -> bool:
    """A label-less node covering most of the screen is a wrapper, not something to tap."""
    return el.bounds.area > 0.6 * max(1, screen.bounds.area)


def build_marks(screen: Screen, max_marks: int = MAX_MARKS) -> list[Mark]:
    """Interactive nodes and readable text, in reading order, numbered from 1."""
    allow_system_ui = screen.phone.package == SYSTEM_UI
    interactive_boxes: list[tuple[Bounds, str]] = []
    candidates: list[tuple[Element, str]] = []

    for el in screen.elements:
        if not _usable(el, screen, allow_system_ui):
            continue
        label = el.label
        if not label and el.scrollable:
            candidates.append((el, el.short_id or el.class_name))  # scroll host (flag w)
            continue
        if not label and _is_container(el, screen):
            continue  # screen-sized wrappers are not targets
        if not label and el.interactive:
            label = " / ".join(_descendant_labels(screen, el))[:MAX_LABEL]
        if el.interactive:
            interactive_boxes.append((el.bounds, label))
            candidates.append((el, label))
        elif label:
            candidates.append((el, label))

    marks: list[Mark] = []
    for el, label in candidates:
        if (
            not el.interactive
            and not el.scrollable
            and any(box.contains(el.bounds) and label in owner for box, owner in interactive_boxes)
        ):
            continue  # text already represented by the clickable container around it
        marks.append(
            Mark(
                id=0,
                kind=_kind(el),
                label=label[:MAX_LABEL],
                bounds=el.bounds,
                element_index=el.index,
                checked=el.checked if el.checkable else None,
                password=el.password,
                scrollable=el.scrollable,
            )
        )

    marks.sort(key=lambda m: (m.bounds.top, m.bounds.left, m.element_index))
    return [
        Mark(
            id=i,
            kind=m.kind,
            label=m.label,
            bounds=m.bounds,
            element_index=m.element_index,
            checked=m.checked,
            password=m.password,
            scrollable=m.scrollable,
            source=m.source,
            confidence=m.confidence,
        )
        for i, m in enumerate(marks[:max_marks], start=1)
    ]


def signature(screen: Screen, marks: list[Mark]) -> str:
    """Stable fingerprint of what is on screen; used for settle checks and change detection."""
    parts = [screen.phone.package, screen.phone.activity, str(screen.phone.keyboard_visible)]
    parts += [f"{m.kind}|{m.label}|{m.bounds.as_list()}" for m in marks]
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()[:16]


def top_labels(marks: list[Mark], limit: int = 5) -> list[str]:
    seen: list[str] = []
    for m in marks:
        if m.label and m.label not in seen:
            seen.append(m.label)
        if len(seen) >= limit:
            break
    return seen


def has_loading_indicator(screen: Screen) -> bool:
    for el in screen.elements:
        if not el.visible:
            continue
        rid = el.short_id.lower()
        if el.class_name == "ProgressBar" or "progress" in rid or "loading" in rid:
            return True
    return False


def find_marks(marks: list[Mark], query: str) -> list[Mark]:
    """Marks whose label contains ``query`` (case-insensitive), exact matches first."""
    q = query.strip().lower()
    if not q:
        return []
    hits = [m for m in marks if q in m.label.lower()]

    def exact(m: Mark) -> bool:
        return q in [seg.strip().lower() for seg in m.label.split(" / ")]

    return sorted(hits, key=lambda m: (not exact(m), len(m.label)))


def format_marks(marks: list[Mark]) -> str:
    lines = []
    for m in marks:
        extra = ""
        if m.checked is not None:
            extra = " checked" if m.checked else " unchecked"
        cx, cy = m.center
        lines.append(f'{m.id:>3} [{m.kind}] "{m.label}" @({cx},{cy}){extra}')
    return "\n".join(lines)
