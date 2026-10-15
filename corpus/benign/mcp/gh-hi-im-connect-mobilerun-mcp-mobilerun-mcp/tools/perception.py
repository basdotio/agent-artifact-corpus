"""Seeing the screen: numbered marks, annotated screenshots, the raw tree, plain screenshots."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from mcp.types import TextContent

from .. import ocr as ocr_mod
from ..annotate import annotate
from ..errors import fail
from ..grid import element_entries, offscreen_text, render_grid
from ..marks import format_marks, has_loading_indicator
from ..models import Mark, Screen
from ..observe import settle
from ..session import DeviceSession, Runtime
from .common import Device, get_session

SPARSE_INTERACTIVE = 3
TREE_LIMIT = 300
SHOT_DIR = Path(tempfile.gettempdir()) / "mobilerun-mcp"


def render_tree(screen: Screen, max_depth: int = 8, limit: int = TREE_LIMIT) -> str:
    """Indented text tree: only visible nodes that carry a label, are interactive, or scroll."""
    keep = [
        e
        for e in screen.elements
        if e.visible and e.depth <= max_depth and (e.label or e.interactive or e.scrollable)
    ]
    lines = []
    for e in keep[:limit]:
        flags = "".join(
            f
            for f, on in (
                ("C", e.clickable),
                ("L", e.long_clickable),
                ("E", e.editable),
                ("S", e.scrollable),
                ("K", e.checkable),
                ("P", e.password),
            )
            if on
        )
        label = f' "{e.label[:60]}"' if e.label else ""
        ident = f" #{e.short_id}" if e.short_id else ""
        b = e.bounds
        lines.append(
            f"{'  ' * e.depth}{e.class_name}{ident}{label} [{flags}] ({b.left},{b.top},{b.right},{b.bottom})"
        )
    if len(keep) > limit:
        lines.append(
            f"... {len(keep) - limit} more nodes (raise max_depth filter or use perceive_screen)"
        )
    return "\n".join(lines)


def screen_header(screen: Screen) -> dict:
    return {
        "foreground_app": screen.phone.app or screen.phone.package,
        "package": screen.phone.package,
        "activity": screen.phone.activity.rsplit(".", 1)[-1],
        "keyboard_visible": screen.phone.keyboard_visible,
        "screen_size": [screen.width, screen.height],
    }


async def vision_marks(png: bytes, marks: list[Mark], lang: str) -> list[Mark]:
    """detail="full": detector boxes + OCR text the tree does not already cover (source=vision/ocr)."""
    from dataclasses import replace

    from ..detect import detect
    from ..models import Bounds

    boxes = await detect(png)
    lines = await ocr_mod.run_tesseract(png, lang) if ocr_mod.available() else []
    extra: list[Mark] = []
    for box in boxes:
        b = Bounds(box.left, box.top, box.right, box.bottom)
        cx, cy = b.center
        if any(
            m.bounds.contains_point(cx, cy) and m.bounds.area <= 4 * max(1, b.area) for m in marks
        ):
            continue  # the tree already has a box of about this size here
        text = " ".join(ln.text for ln in lines if b.contains(ln.bounds))[:80]
        extra.append(
            Mark(
                id=0,
                kind="icon",
                label=text,
                bounds=b,
                element_index=-1,
                source="vision",
                confidence=box.score,
            )
        )
    merged = ocr_mod.merge_ocr_marks(marks + extra, lines)
    return [replace(m, id=i) for i, m in enumerate(merged, start=1)]


async def perceive(
    session: DeviceSession,
    include_image: bool,
    ocr_mode: str,
    max_marks: int,
    lang: str,
    detail: str | None = None,
) -> tuple[dict, bytes | None]:
    screen, marks = await session.perceive(max_marks)
    full = detail == "full"
    interactive = sum(1 for m in marks if m.kind not in ("text", "scroll"))
    use_ocr = (
        not full
        and ocr_mod.available()
        and (ocr_mode == "always" or (ocr_mode == "auto" and interactive < SPARSE_INTERACTIVE))
    )
    png = await session.screenshot() if (include_image or use_ocr or full) else None
    if full and png is not None:
        marks = await vision_marks(png, marks, lang)
        session.marks = marks
    elif use_ocr and png is not None:
        lines = await ocr_mod.run_tesseract(png, lang)
        marks = ocr_mod.merge_ocr_marks(marks, lines)
        session.marks = marks
    result = {
        **screen_header(screen),
        "perception_tier": "full" if full else "tree_only",
        "e": element_entries(screen, marks),
        "mark_count": len(marks),
        "ocr_used": bool(use_ocr or full),
        "elements": format_marks(marks),
    }
    off = offscreen_text(screen)
    if off:
        result["offscreen"] = off
    if include_image and png is not None:
        return result, annotate(png, marks)
    return result, None


def register(mcp: FastMCP, rt: Runtime) -> None:
    @mcp.tool(tags={"read"})
    async def perceive_screen(
        description: str = "",
        detail: str | None = None,
        include_image: bool = True,
        ocr: str = "auto",
        max_marks: int = 150,
        lang: str = "eng",
        device: Device = None,
    ) -> list:
        """LOOK at the screen: an annotated screenshot plus every element and its tap point.

        `e` is an array whose INDEX is the som_id (first entry = som_id 1): [center_x, center_y,
        name, flags] (name/flags omitted when empty). `elements` is the same list as text.
        Box colours: BLUE tappable, GREEN text input (type_text), MAGENTA scrollable, AMBER
        toggle, GREY nothing declared, RED on-host vision (detector/OCR; a good guess, not a fact).
        Flags (only when true): e editable, c checked, o unchecked, d disabled, f focused,
        l long-pressable, ? low-confidence vision box, w scroll host (aim inside it).
        `offscreen`: text that exists but is not on screen (cannot be tapped).
        detail="full" adds the visual pass (OmniParser YOLOv8 icon detector + OCR) for icons the
        tree does not describe; perception_tier reports tree_only or full. description is
        logged only. ids go stale after any action."""
        if ocr not in ("auto", "always", "never"):
            fail("invalid_argument", "ocr must be auto, always or never")
        if detail not in (None, "", "full", "tree", "tree_only"):
            fail("invalid_argument", 'detail must be "full" or omitted')
        result, image_png = await perceive(
            get_session(rt, device), include_image, ocr, max_marks, lang, detail
        )
        if description:
            result["description"] = description
        parts: list = [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        if image_png is not None:
            parts.append(Image(data=image_png, format="png"))
        return parts

    @mcp.tool(tags={"read"})
    async def read_screen(device: Device = None) -> str:
        """Read the screen now (waits for it to stop moving first): the screen drawn as a
        character grid, each element a box with its som_id and label, then a table of what can
        be acted on: som (tap by this), in (som_id of the smallest box containing it), flg, label
        (only when it did not fit on the grid).
        Flags: * tappable, e text input (type_text, not tap), S scrollable, c toggle ON,
        o toggle OFF, l long-pressable, d disabled, - nothing declared (usually still tappable).
        N+k = som_id N plus k more elements with exactly those bounds; tap N.
        Header IDLE/BUSY: BUSY means it was still moving when the wait expired.
        Use perceive_screen instead for how something looks, when this ends with ESCALATE,
        or when what you need is missing."""
        session = get_session(rt, device)
        async with session.lock:
            _, _, _, settled = await settle(session.peek)
            screen, marks = await session.perceive()
        idle = settled and not has_loading_indicator(screen)
        return render_grid(screen, marks, idle, settled)

    @mcp.tool(tags={"read"})
    async def get_ui_tree(max_depth: int = 8, device: Device = None) -> dict:
        """Compact accessibility tree (class, id, label, flags C/L/E/S/K/P, bounds)."""
        screen = await get_session(rt, device).capture()
        return {**screen_header(screen), "tree": render_tree(screen, max_depth)}

    @mcp.tool(tags={"read"})
    async def get_screenshot(device: Device = None) -> Image:
        """Plain screenshot as an image."""
        return Image(data=await get_session(rt, device).screenshot(), format="png")

    @mcp.tool(tags={"read"})
    async def screenshot(hide_overlay: bool = False, device: Device = None) -> Image:
        """Plain screenshot. hide_overlay hides the Portal's element overlay first."""
        session = get_session(rt, device)
        if hide_overlay and session.has_adb:
            await session.ensure_connected()
            return Image(data=await session.portal.screenshot(hide_overlay=True), format="png")
        if hide_overlay:
            return Image(data=await session.core.screenshot_png(hide_overlay=True), format="png")
        return Image(data=await session.screenshot(), format="png")

    @mcp.tool(tags={"read"})
    async def screenshot_path(device: Device = None) -> dict:
        """Take a screenshot, save it as a PNG file and return the path."""
        png = await get_session(rt, device).screenshot()
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SHOT_DIR / f"screen-{int(time.time() * 1000)}.png"
        path.write_bytes(png)
        return {"path": str(path), "bytes": len(png)}
