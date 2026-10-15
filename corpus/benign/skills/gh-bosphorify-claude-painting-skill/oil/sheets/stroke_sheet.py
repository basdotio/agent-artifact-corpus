"""Test page for WP2: every brush preset in four rows (straight, curved, varying pressure, over wet paint).

Run from painting-kit/oil:
    uv run python sheets/stroke_sheet.py          # out/stroke_sheet.png (+ _review) and out/stroke_sheet_lit.png
    uv run python sheets/stroke_sheet.py --bench  # 20k medium strokes on a 2048x1536 canvas
"""

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from atelier import Canvas, brush, studio

OUT = Path(__file__).resolve().parent.parent / "out"
PRESETS = [
    ("round_soft", "naples_yellow", "cobalt_blue"),
    ("round_bristle", "lead_white", "vermilion"),
    ("flat_bristle", "cerulean_blue", "cadmium_yellow"),
    ("filbert", "vermilion", "lead_white"),
    ("fan", "viridian", "naples_yellow"),
    ("rigger", "ivory_black", "lead_white"),
    ("dry_bristle", "burnt_umber", "lead_white"),
    ("palette_knife", "cadmium_yellow", "ultramarine"),
    ("glaze_wide", "madder_lake", "yellow_ochre"),
]
BLOCK_W, BLOCK_H, COLS = 800, 700, 3
ROWS = ("straight", "curved", "pressure", "over wet")
FOCUS = [(330, 1600), (1200, 1600), (2000, 1600)]    # 1:1 crops first: dry_bristle, palette_knife, glaze_wide


def block_paths(x, y):
    """Control points of the four rows of a block whose top-left corner is (x, y)."""
    h = BLOCK_H / 4
    xs = np.linspace(x + 70, x + BLOCK_W - 50, 7)
    yc = [y + h * (i + 0.5) + 12 for i in range(4)]
    straight = np.stack([xs, np.full(7, yc[0])], 1)
    curved = np.stack([xs, yc[1] + 42 * np.sin(np.linspace(0, 2 * np.pi, 7))], 1)
    press = np.stack([xs, yc[2] + 14 * np.sin(np.linspace(0, np.pi, 7))], 1)
    wet = np.stack([xs, yc[3] + 22 * np.sin(np.linspace(0.5, 3.5, 7))], 1)
    return straight, curved, press, wet, yc[3]


def paint_sheet():
    rows = -(-len(PRESETS) // COLS)
    cv = Canvas(COLS * BLOCK_W, rows * BLOCK_H, seed=11)
    cv.ground("raw_umber", texture="linen", tone=0.3)
    for k, (name, paint, under) in enumerate(PRESETS):
        x, y = (k % COLS) * BLOCK_W, (k // COLS) * BLOCK_H
        straight, curved, press, wet, wy = block_paths(x, y)
        b = brush(name)
        cv.stroke(b, straight, paint)
        cv.stroke(b, curved, paint)
        cv.stroke(b, press, paint, pressure=[0.15, 0.5, 1.0, 1.0, 0.8, 0.45, 0.2])
        for dy in (-28, -8, 12, 32):
            cv.stroke(brush("flat_bristle", load=1.4), [[x + 60, wy + dy], [x + BLOCK_W - 40, wy + dy + 3]], under)
        cv.stroke(b, wet, paint)
    return cv


def labeled(pixels):
    img = Image.fromarray(pixels)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=18)
    small = ImageFont.load_default(size=13)
    for k, (name, _, _) in enumerate(PRESETS):
        x, y = (k % COLS) * BLOCK_W, (k // COLS) * BLOCK_H
        draw.text((x + 12, y + 8), name, font=font, fill=(245, 240, 230))
        for i, row in enumerate(ROWS):
            draw.text((x + 8, y + BLOCK_H / 4 * (i + 0.5) + 4), row, font=small, fill=(230, 225, 215))
    return img


def bench(n=20000):
    rng = np.random.default_rng(0)
    cv = Canvas(2048, 1536, seed=1)
    cv.ground("raw_umber", texture="linen", tone=0.35)
    names = ["round_bristle", "flat_bristle", "filbert", "round_soft", "dry_bristle", "fan", "palette_knife"]
    brushes = {nm: [brush(nm, size=s) for s in np.linspace(0.4, 1.6, 7)] for nm in names}
    colors = ["lead_white", "yellow_ochre", "vermilion", "ultramarine", "burnt_umber", "viridian"]
    jobs = []
    for _ in range(n):
        nm = names[rng.integers(len(names))]
        b = min(brushes[nm], key=lambda b: abs(b.width_px - rng.uniform(8, 30)))
        length, ang = rng.uniform(60, 120), rng.uniform(0, np.pi)
        p0 = rng.uniform((0, 0), (2048, 1536))
        d = np.array([np.cos(ang), np.sin(ang)]) * length
        mid = p0 + 0.5 * d + rng.normal(0, 0.1 * length, 2)
        jobs.append((b, np.array([p0, mid, p0 + d]), colors[rng.integers(len(colors))], rng.uniform(0.5, 1.0)))
    t0 = time.perf_counter()
    for k, (b, path, color, p) in enumerate(jobs):
        cv.stroke(b, path, color, pressure=p)
        if k % 5000 == 4999:
            cv.dry()
    dt = time.perf_counter() - t0
    print(f"{n} strokes on 2048x1536: {dt:.1f}s ({dt / n * 1e3:.2f} ms/stroke)")
    studio.save(cv, OUT / "stroke_bench.png")


if __name__ == "__main__":
    if "--bench" in sys.argv:
        bench()
    else:
        t0 = time.time()
        cv = paint_sheet()
        print(f"painted in {time.time() - t0:.1f}s")
        studio.save(labeled(cv.to_srgb_uint8()), OUT / "stroke_sheet.png", focus=FOCUS)
        labeled(cv.finish()).save(OUT / "stroke_sheet_lit.png")
        print("wrote", OUT / "stroke_sheet.png", OUT / "stroke_sheet_review.png", OUT / "stroke_sheet_lit.png")
