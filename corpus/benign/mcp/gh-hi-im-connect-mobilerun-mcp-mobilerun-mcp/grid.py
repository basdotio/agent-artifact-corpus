"""Text views of the screen in AURA's formats.

- :func:`render_grid` - read_screen: the screen drawn as a character grid of boxes (som_id and
  label inside), an IDLE/BUSY header, a table of actionable elements (som, in, flg, label),
  off-screen text, and an ESCALATE line when the accessibility tree cannot describe the screen.
- :func:`element_entries` - perceive_screen's ``e`` array: ``[cx, cy, name, flags]`` per som_id.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Element, Mark, Screen

COLS = 72
MAX_ROWS = 64
FRAME_FRACTION = 0.9
MIN_ELEMENTS = 3
MIN_LABELED = 0.3
CANVAS_CLASSES = ("WebView", "SurfaceView", "TextureView", "GLSurfaceView", "MapView")


def element_of(screen: Screen, mark: Mark) -> Element | None:
    if 0 <= mark.element_index < len(screen.elements):
        return screen.elements[mark.element_index]
    return None


def grid_flags(mark: Mark, el: Element | None) -> str:
    """read_screen flags: * tappable, e input, S scroll, c/o toggle on/off, l long-press, d disabled."""
    flags = ""
    if mark.kind == "input":
        flags += "e"
    elif mark.kind == "toggle":
        flags += "c" if mark.checked else "o"
    elif mark.kind == "button" or (el is not None and el.clickable):
        flags += "*"
    if mark.scrollable:
        flags += "S"
    if el is not None and el.long_clickable:
        flags += "l"
    if el is not None and not el.enabled:
        flags += "d"
    return flags or "-"


def entry_flags(mark: Mark, el: Element | None) -> str:
    """perceive_screen flags: e c o d f l ? w."""
    flags = ""
    if mark.kind == "input":
        flags += "e"
    if mark.kind == "toggle":
        flags += "c" if mark.checked else "o"
    if el is not None:
        if not el.enabled:
            flags += "d"
        if el.focused:
            flags += "f"
        if el.long_clickable:
            flags += "l"
    if mark.source == "vision" and mark.confidence < 0.5:
        flags += "?"
    if mark.kind == "scroll":
        flags += "w"
    return flags


def element_entries(screen: Screen, marks: list[Mark]) -> list[list]:
    out = []
    for mark in marks:
        cx, cy = mark.center
        entry: list = [cx, cy]
        flags = entry_flags(mark, element_of(screen, mark))
        if mark.label or flags:
            entry.append(mark.label)
        if flags:
            entry.append(flags)
        out.append(entry)
    return out


def offscreen_text(screen: Screen, limit: int = 20) -> list[str]:
    seen: list[str] = []
    for el in screen.elements:
        if not el.label or el.bounds.width <= 0 or el.bounds.height <= 0:
            continue
        if el.bounds.intersects(screen.bounds):
            continue
        label = el.label.strip().replace("|", "/")[:40]
        if label and label not in seen:
            seen.append(label)
        if len(seen) >= limit:
            break
    return seen


def escalate_reason(screen: Screen, marks: list[Mark]) -> str | None:
    for el in screen.elements:
        if (
            el.visible
            and el.class_name in CANVAS_CLASSES
            and el.bounds.area > 0.4 * screen.bounds.area
        ):
            return f"a {el.class_name} fills most of the screen; its content is not in the tree"
    if len(marks) < MIN_ELEMENTS:
        return (
            f"only {len(marks)} elements in the tree; the screen is probably drawn, not described"
        )
    labeled = sum(1 for m in marks if m.label.strip())
    if labeled / max(1, len(marks)) < MIN_LABELED:
        return "most elements have no label (icon-only or custom-drawn controls)"
    return None


@dataclass
class _Row:
    som: int
    parent: int | None
    flags: str
    label: str
    on_grid: bool = False


def _contains(outer: Mark, inner: Mark) -> bool:
    return outer.bounds.contains(inner.bounds) and outer.bounds != inner.bounds


def render_grid(screen: Screen, marks: list[Mark], idle: bool, settled: bool) -> str:
    width, height = max(1, screen.width), max(1, screen.height)
    rows_n = min(MAX_ROWS, max(12, round(COLS * height / width / 2)))
    sx, sy = COLS / width, rows_n / height
    canvas = [[" "] * (COLS + 1) for _ in range(rows_n + 1)]
    screen_area = width * height

    # group marks sharing exact bounds: the first id draws, the rest count as +k
    groups: dict[tuple, list[Mark]] = {}
    for m in marks:
        groups.setdefault(tuple(m.bounds.as_list()), []).append(m)

    rows: dict[int, _Row] = {}
    for m in marks:
        parents = [o for o in marks if _contains(o, m)]
        parent = min(parents, key=lambda o: o.bounds.area).id if parents else None
        rows[m.id] = _Row(m.id, parent, grid_flags(m, element_of(screen, m)), m.label)

    frames = 0
    boxes = 0
    for bounds, group in sorted(groups.items(), key=lambda kv: -kv[1][0].bounds.area):
        lead = group[0]
        if lead.bounds.area >= FRAME_FRACTION * screen_area:
            frames += 1
            continue
        boxes += 1
        x1 = max(0, min(COLS, round(bounds[0] * sx)))
        y1 = max(0, min(rows_n, round(bounds[1] * sy)))
        x2 = max(x1 + 1, min(COLS, round(bounds[2] * sx)))
        y2 = max(y1, min(rows_n, round(bounds[3] * sy)))
        for x in range(x1, x2 + 1):
            canvas[y1][x] = "-"
            canvas[y2][x] = "-"
        for y in range(y1, y2 + 1):
            canvas[y][x1] = "|"
            canvas[y][x2] = "|"
        for x, y in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
            canvas[y][x] = "+"
        tag = str(lead.id) + (f"+{len(group) - 1}" if len(group) > 1 else "")
        inner = x2 - x1 - 1
        text_row = y1 + 1 if y2 - y1 >= 2 else y1
        start = x1 + 1
        label = lead.label.replace("\n", " ").strip()
        text = f"{tag} {label}".rstrip()
        if len(text) <= inner:
            rows[lead.id].on_grid = bool(label)
        else:
            text = tag[: max(0, inner)]
        for i, ch in enumerate(text[: max(0, inner)]):
            canvas[text_row][start + i] = ch

    rendered: list[str] = []
    for row in ("".join(r).rstrip() for r in canvas):
        if not row and rendered and not rendered[-1]:
            continue  # collapse empty bands to one blank line
        rendered.append(row)
    grid = "\n".join(rendered).strip("\n")
    status = "IDLE" if idle else "BUSY"
    if not settled:
        status += " (still moving when the settle cap expired)"
    header = (
        f"SCREEN {width}x{height}  {screen.phone.package or '?'}  {status}  "
        f"{len(marks)} elements in {boxes} boxes"
    )
    if frames:
        header += f"  ({frames} full-screen frame(s) not drawn)"
    lines = [
        header,
        "numbers are som_id; N+k = N plus k more sharing those bounds; `in` = som_id of the "
        "smallest element containing this one; labels are drawn on the grid, listed below only "
        "when they would not fit",
        grid,
        "",
        "som  in   flg  label (only if not on the grid)",
    ]
    for row in sorted(rows.values(), key=lambda r: r.som):
        if row.flags == "-" and row.on_grid:
            continue
        parent = str(row.parent) if row.parent is not None else "-"
        label = "" if row.on_grid else row.label
        lines.append(f"{row.som:<5}{parent:<5}{row.flags:<5}{label}".rstrip())
    off = offscreen_text(screen)
    if off:
        lines += [
            "",
            "OFFSCREEN (exists but not visible; no som_id, cannot be tapped): " + " | ".join(off),
        ]
    reason = escalate_reason(screen, marks)
    if reason:
        lines += ["", f"ESCALATE to perceive_screen — {reason}"]
    return "\n".join(lines)
