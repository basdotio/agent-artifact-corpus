"""Test page for WP1 materials: the four grounds, a full-size linen ground and the pigment table.

Run from painting-kit/oil:  uv run python sheets/ground_sheet.py
Writes out/ground_linen.png, out/grounds.png, out/palette.png and their review sheets.
"""

import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from atelier import PIGMENTS, Canvas, Palette, studio
from atelier.color import linear_to_srgb

OUT = Path(__file__).resolve().parent.parent / "out"

t0 = time.time()
cv = Canvas(2048, 1536, seed=7)
cv.ground("raw_umber", texture="linen", tone=0.35)
print("linen ground 2048x1536:", f"{time.time() - t0:.2f}s")
studio.save(cv, OUT / "ground_linen.png")

quads = [("linen", "raw_umber", 0.35), ("cotton", "burnt_sienna", 0.3),
         ("paper", "lead_white", 0.0), ("panel", "yellow_ochre", 0.25)]
grid = np.zeros((1536, 2048, 3), np.uint8)
for i, (texture, pigment, tone) in enumerate(quads):
    q = Canvas(1024, 768, seed=7)
    q.ground(pigment, texture=texture, tone=tone)
    y, x = divmod(i, 2)
    grid[y * 768:(y + 1) * 768, x * 1024:(x + 1) * 1024] = q.to_srgb_uint8()
studio.save(grid, OUT / "grounds.png")

font = ImageFont.load_default(size=16)
pal = Palette(list(PIGMENTS))
mixes = [
    ("ultramarine + cadmium_yellow", pal.mix(("ultramarine", 1), ("cadmium_yellow", 1))),
    ("prussian_blue + yellow_ochre", pal.mix(("prussian_blue", 1), ("yellow_ochre", 1))),
    ("vermilion + lead_white", pal.mix(("vermilion", 1), ("lead_white", 1))),
    ("ultramarine + burnt_umber", pal.mix(("ultramarine", 1), ("burnt_umber", 1))),
    ("madder_lake + ultramarine", pal.mix(("madder_lake", 1), ("ultramarine", 1))),
    ("lead_white 3 + ultramarine 1 + ochre 0.3", pal.mix(("lead_white", 3), ("ultramarine", 1), ("yellow_ochre", 0.3))),
]
swatches = [(name, PIGMENTS[name].linear) for name in PIGMENTS] + mixes
cols, cell = 4, (400, 110)
sheet = Image.new("RGB", (cols * cell[0], -(-len(swatches) // cols) * cell[1]), (38, 38, 38))
draw = ImageDraw.Draw(sheet)
for i, (name, color) in enumerate(swatches):
    x, y = (i % cols) * cell[0], (i // cols) * cell[1]
    rgb = tuple(int(round(v * 255)) for v in linear_to_srgb(color))
    draw.rectangle((x + 10, y + 10, x + 90, y + 100), fill=rgb)
    draw.text((x + 100, y + 30), name, font=font, fill=(215, 212, 205))
    draw.text((x + 100, y + 55), "#%02X%02X%02X" % rgb, font=font, fill=(150, 148, 142))
studio.save(sheet, OUT / "palette.png")
print("wrote", *sorted(p.name for p in OUT.glob("*.png")))
