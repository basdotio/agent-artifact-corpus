"""Draw numbered boxes over a screenshot so a vision model can refer to marks by id."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from .models import Mark

# AURA's colour legend: BLUE tappable, GREEN text input, MAGENTA scrollable, AMBER toggle,
# GREY nothing declared, RED on-host vision (detector/OCR, not the accessibility tree).
BLUE, GREEN, MAGENTA, AMBER, GREY, RED = (
    (40, 110, 240),
    (30, 170, 70),
    (210, 40, 200),
    (240, 170, 20),
    (128, 128, 128),
    (230, 40, 40),
)
COLORS = {"button": BLUE, "input": GREEN, "scroll": MAGENTA, "toggle": AMBER}


def color_for(mark: Mark) -> tuple[int, int, int]:
    if mark.source != "a11y":
        return RED
    return COLORS.get(mark.kind, GREY)


def annotate(png: bytes, marks: list[Mark]) -> bytes:
    image = Image.open(io.BytesIO(png)).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    for mark in marks:
        color = color_for(mark)
        b = mark.bounds
        draw.rectangle([b.left, b.top, b.right - 1, b.bottom - 1], outline=color, width=2)
        text = str(mark.id)
        box = draw.textbbox((0, 0), text, font=font)
        w, h = box[2] - box[0] + 6, box[3] - box[1] + 6
        x, y = max(0, b.left), max(0, b.top)
        draw.rectangle([x, y, x + w, y + h], fill=color)
        draw.text((x + 3, y + 1), text, fill=(255, 255, 255), font=font)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()
