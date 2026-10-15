"""The mobilerun agent's view of the screen: numbered UI elements and their tap points.

Adapted from droidrun/mobilerun (MIT License, Copyright (c) 2025 Niels Schmidt; see NOTICE):
``mobilerun/tools/filters/concise_filter.py``, ``mobilerun/tools/formatters/indexed_formatter.py``,
``mobilerun/tools/ui/state.py`` and ``mobilerun/tools/helpers/geometry.py``. Indices therefore
match what the mobilerun agent sees for the same Portal state, so ``click(index)`` from a
mobilerun prompt or macro lands on the same element here.
"""

from __future__ import annotations

from typing import Any

MIN_ELEMENT_SIZE = 5
Rect = tuple[int, int, int, int]


# ---- ConciseFilter ----------------------------------------------------------------------
def _rect(node: dict[str, Any]) -> Rect:
    b = node.get("boundsInScreen") or {}
    return (
        int(b.get("left", 0)),
        int(b.get("top", 0)),
        int(b.get("right", 0)),
        int(b.get("bottom", 0)),
    )


def concise_filter(node: dict[str, Any], width: int, height: int, min_size: int) -> dict | None:
    left, top, right, bottom = _rect(node)
    if right <= 0 or bottom <= 0 or left >= width or top >= height:
        return None
    if not (right - left > min_size and bottom - top > min_size):
        return None
    children = []
    for child in node.get("children") or []:
        kept = concise_filter(child, width, height, min_size)
        if kept:
            children.append(kept)
    return {**node, "children": children}


# ---- IndexedFormatter -------------------------------------------------------------------
def rects_overlap(a: Rect, b: Rect) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _parse_bounds(value: str) -> Rect:
    left, top, right, bottom = (int(p) for p in value.split(","))
    return left, top, right, bottom


def _format_node(node: dict[str, Any], index: int) -> dict[str, Any]:
    left, top, right, bottom = _rect(node)
    class_name = node.get("className", "") or ""
    checked = ""
    if node.get("isCheckable"):
        checked = "isChecked=True" if node.get("isChecked") else "isChecked=False"
    return {
        "index": index,
        "resourceId": node.get("resourceId", ""),
        "className": class_name.split(".")[-1] if class_name else "",
        "checkedState": checked,
        "text": node.get("text")
        or node.get("contentDescription")
        or node.get("resourceId")
        or class_name,
        "bounds": f"{left},{top},{right},{bottom}",
        "children": [],
    }


def _add_tap_blockers(siblings: list[tuple[dict[str, Any], dict[str, Any]]]) -> None:
    """Sibling views drawn above an element (same window, higher drawingOrder, touchable)."""
    for raw, formatted in siblings:
        order, window = raw.get("drawingOrder"), raw.get("windowId")
        if not isinstance(order, int) or not isinstance(window, int) or window < 0:
            continue
        bounds = _parse_bounds(formatted["bounds"])
        blockers = []
        for other, candidate in siblings:
            other_order = other.get("drawingOrder")
            if (
                other.get("windowId") != window
                or not isinstance(other_order, int)
                or other_order <= order
                or other.get("isVisibleToUser") is False
                or not (other.get("isClickable") or other.get("isLongClickable"))
            ):
                continue
            if rects_overlap(bounds, _parse_bounds(candidate["bounds"])):
                blockers.append(candidate["bounds"])
        if blockers:
            formatted["tapBlockers"] = blockers


def _flatten(node: dict[str, Any], counter: list[int]) -> list[dict[str, Any]]:
    results = [_format_node(node, counter[0])]
    counter[0] += 1
    siblings = []
    for child in node.get("children") or []:
        descendants = _flatten(child, counter)
        siblings.append((child, descendants[0]))
        results.extend(descendants)
    _add_tap_blockers(siblings)
    return results


def _phone_state_text(phone: dict[str, Any]) -> str:
    app, package = phone.get("currentApp", ""), phone.get("packageName", "")
    focused = phone.get("focusedElement") or {}
    lines = ["**Current Phone State:**"]
    if app and package:
        lines.append(f"• **App:** {app} ({package})")
    elif app or package:
        lines.append(f"• **App:** {app or package}")
    lines.append(f"• **Keyboard:** {'Visible' if phone.get('isEditable') else 'Hidden'}")
    lines.append(f"• **Focused Element:** '{focused.get('text', '') if focused else ''}'")
    return "\n".join(lines)


def _element_lines(elements: list[dict[str, Any]]) -> str:
    lines = []
    for e in elements:
        parts = [f"{e['index']}."]
        if e["className"]:
            parts.append(e["className"] + ":")
        details = [f'"{v}"' for v in (e["resourceId"], e["text"]) if v]
        if details:
            parts.append(", ".join(details))
        if e["checkedState"]:
            parts.append(f"; {e['checkedState']}")
        parts.append(f"- ({e['bounds']})")
        lines.append(" ".join(parts))
    return "\n".join(lines)


SCHEMA = "'index. className: resourceId; checkedState, text - bounds(x1,y1,x2,y2)'"


def index_state(state: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """(formatted text, flat element list) for a Portal ``state_full`` payload."""
    ctx = state.get("device_context") or {}
    screen = ctx.get("screen_bounds") or {}
    params = ctx.get("filtering_params") or {}
    tree = state.get("a11y_tree")
    filtered = (
        concise_filter(
            tree,
            int(screen.get("width", 1080)),
            int(screen.get("height", 2400)),
            int(params.get("min_element_size", MIN_ELEMENT_SIZE)),
        )
        if isinstance(tree, dict)
        else None
    )
    elements = _flatten(filtered, [1]) if filtered else []
    body = _element_lines(elements) if elements else "No UI elements found"
    text = (
        f"{_phone_state_text(state.get('phone_state') or {})}\n\n"
        f"Current Clickable UI elements:\n{SCHEMA}:\n{body}"
    )
    return text, elements


# ---- tap point (UIState.get_element_coords) --------------------------------------------
def find_uncovered_point(bounds: Rect, blockers: list[Rect]) -> tuple[int, int] | None:
    """Center of the largest part of ``bounds`` not covered by any blocker."""
    regions = [bounds] if bounds[0] < bounds[2] and bounds[1] < bounds[3] else []
    for blocker in blockers:
        remaining = []
        for left, top, right, bottom in regions:
            bl, bt = max(left, blocker[0]), max(top, blocker[1])
            br, bb = min(right, blocker[2]), min(bottom, blocker[3])
            if bl >= br or bt >= bb:
                remaining.append((left, top, right, bottom))
                continue
            for region in (
                (left, top, right, bt),
                (left, bb, right, bottom),
                (left, bt, bl, bb),
                (br, bt, right, bb),
            ):
                if region[0] < region[2] and region[1] < region[3]:
                    remaining.append(region)
        regions = remaining
    if not regions:
        return None
    left, top, right, bottom = max(regions, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
    return (left + right) // 2, (top + bottom) // 2


def element_coords(
    elements: list[dict[str, Any]], index: int, screen: tuple[int, int] | None = None
) -> tuple[int, int]:
    """Tap point for ``index``; raises ValueError like mobilerun does."""
    element = next((e for e in elements if e["index"] == index), None)
    if element is None:
        indices = [str(e["index"]) for e in elements]
        shown = ", ".join(indices[:20]) + (
            f"... and {len(indices) - 20} more" if len(indices) > 20 else ""
        )
        raise ValueError(f"No element found with index {index}. Available indices: {shown}")
    left, top, right, bottom = _parse_bounds(element["bounds"])
    x, y = (left + right) // 2, (top + bottom) // 2
    blockers = [_parse_bounds(b) for b in element.get("tapBlockers", [])]
    if not any(bl <= x < br and bt <= y < bb for bl, bt, br, bb in blockers):
        return x, y
    if screen:
        left, top = max(0, left), max(0, top)
        right, bottom = min(screen[0], right), min(screen[1], bottom)
    clear = find_uncovered_point((left, top, right, bottom), blockers)
    if clear is None:
        raise ValueError(f"No clear tap point for element {index}")
    return clear
