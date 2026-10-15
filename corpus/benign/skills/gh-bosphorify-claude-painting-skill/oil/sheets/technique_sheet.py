"""Test page for WP3: each technique in its own panel, photographed with finish().

Run from painting-kit/oil:
    uv run python sheets/technique_sheet.py
Writes out/technique_sheet.png (finished, raking light) and out/technique_sheet_flat.png (the
canvas colors, unlit), each with its review sheet. The last panel is finished with varnish and
craquelure.
"""

import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from atelier import Canvas, brush, fields, studio

OUT = Path(__file__).resolve().parent.parent / "out"
PW, PH, COLS = 800, 700, 3
FOCUS = [(1100, 380), (400, 1000), (1200, 1240)]    # 1:1 crops first: scumble, knife slabs, knife scrapes
PANELS = [
    ("glaze", "madder lake + ultramarine films over a grisaille"),
    ("scumble", "lead white over dark umber: coverage 0.3 | 0.6"),
    ("impasto", "loaded flat and filbert, thickness 1-1.5"),
    ("knife", "slabs of paint, some over wet color"),
    ("knife: level + scrape", "knife through wet impasto | scraping wet red off dry yellow"),
    ("wet_in_wet", "wet bands as laid | worked together (angle 90)"),
    ("stipple", "optical mix of four colors | one color, density 0.15-0.6"),
    ("hatch", "single hatch on the half-tone, cross-hatch in the core shadow"),
    ("finish", "varnish 0.7 and craquelure 0.6"),
    ("spatter", "flicked specks, density 0.1 | driven streaks along a vortex, stretch 5"),
]


def rect(cv, x0, y0, x1, y1):
    m = np.zeros(cv.shape, np.float32)
    m[y0:y1, x0:x1] = 1
    return m


def ellipse(cv, cx, cy, rx, ry):
    yy, xx = np.mgrid[:cv.shape[0], :cv.shape[1]]
    return (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 < 1).astype(np.float32)


def bands(cv, x0, x1, y0, colors, h=34, b="flat_bristle"):
    """Lay horizontal bands of opaque paint, a few strokes each."""
    for i, c in enumerate(colors):
        for k in range(3):
            y = y0 + i * h + 6 + k * (h - 12) / 2
            cv.stroke(brush(b, load=1.6, size=1.5), [[x0, y], [(x0 + x1) / 2, y + 2], [x1, y - 1]], c)


def glaze_panel(cv, x, y):
    grays = ["lead_white", "#B8B2A6", "#7E786E", "#48443E", "ivory_black"]
    for i, c in enumerate(grays):
        for k in range(4):
            xx = x + 60 + i * 140 + k * 30
            cv.stroke(brush("flat_bristle", load=1.6, size=1.4), [[xx, y + 80], [xx + 3, y + 380], [xx - 2, y + 660]], c)
    cv.dry()
    cv.glaze(ellipse(cv, x + 300, y + 330, 230, 190), "madder_lake", strength=0.35)
    cv.dry()
    cv.glaze(rect(cv, x + 380, y + 150, x + 760, y + 560), "ultramarine", strength=0.3)
    cv.dry()


def scumble_panel(cv, x, y):
    for yy in range(y + 70, y + 680, 16):
        cv.stroke(brush("flat_bristle", load=1.6, size=1.3), [[x + 30, yy], [x + 400, yy + 6], [x + 770, yy - 4]],
                  "burnt_umber" if (yy // 16) % 3 else "ultramarine")
    for yy in range(y + 150, y + 650, 90):
        cv.impasto([[x + 60, yy], [x + 380, yy + 30], [x + 740, yy - 10]], "burnt_umber", thickness=0.8)
    cv.dry()
    cv.scumble(ellipse(cv, x + 210, y + 380, 170, 250), "lead_white", coverage=0.3)
    cv.scumble(ellipse(cv, x + 590, y + 380, 170, 250), "naples_yellow", coverage=0.6)


def impasto_panel(cv, x, y):
    cv.stroke(brush("flat_bristle", size=3), [[x + 20, y + 400], [x + 780, y + 400]], "#6B7A86")
    for yy in range(y + 80, y + 690, 40):
        cv.stroke(brush("flat_bristle", load=1.6, size=1.6), [[x + 20, yy], [x + 400, yy + 5], [x + 780, yy]], "#6E7C88")
    cv.dry()
    cv.impasto([[x + 60, y + 130], [x + 300, y + 110], [x + 560, y + 140]], "lead_white", thickness=1.2)
    cv.impasto([[x + 80, y + 240], [x + 360, y + 300], [x + 700, y + 230]], "naples_yellow", thickness=1.0,
               brush=brush("flat_bristle", size=1.6, load=2.0))
    cv.impasto([[x + 120, y + 420], [x + 300, y + 380], [x + 520, y + 470], [x + 740, y + 400]], "vermilion",
               thickness=1.5, brush=brush("filbert", size=1.4, load=2.0))
    for i in range(6):
        x0 = x + 90 + i * 110
        cv.impasto([[x0, y + 540], [x0 + 60, y + 640]], "lead_white", thickness=1.2,
                   brush=brush("round_bristle", size=1.2, load=2.0))


def knife_panel(cv, x, y):
    for yy in range(y + 380, y + 690, 22):
        cv.stroke(brush("flat_bristle", load=1.6, size=1.2), [[x + 20, yy], [x + 780, yy + 4]], "cerulean_blue")
    cv.knife([[x + 60, y + 110], [x + 420, y + 90], [x + 720, y + 120]], "lead_white", width=60)
    cv.knife([[x + 120, y + 200], [x + 560, y + 250]], "cadmium_yellow", width=45)
    cv.knife([[x + 480, y + 180], [x + 700, y + 330]], "vermilion", width=36)
    cv.knife([[x + 60, y + 440], [x + 400, y + 470], [x + 730, y + 430]], "lead_white", width=70)
    cv.knife([[x + 100, y + 590], [x + 700, y + 600]], "cadmium_yellow", width=50)


def level_scrape_panel(cv, x, y):
    for yy in range(y + 80, y + 330, 26):
        cv.impasto([[x + 40, yy], [x + 760, yy + 6]], "lead_white" if (yy // 26) % 2 else "naples_yellow",
                   thickness=1.0)
    cv.knife([[x + 380, y + 150], [x + 790, y + 160]], "lead_white", width=110, thickness=0.6)
    cv.knife([[x + 380, y + 270], [x + 790, y + 262]], "lead_white", width=90, thickness=0.6)
    for yy in range(y + 400, y + 690, 18):
        cv.stroke(brush("flat_bristle", load=1.6, size=1.2), [[x + 20, yy], [x + 780, yy + 3]], "cadmium_yellow")
    cv.dry()
    for yy in range(y + 400, y + 690, 18):
        cv.stroke(brush("flat_bristle", load=1.6, size=1.2), [[x + 20, yy], [x + 780, yy - 2]], "cadmium_red")
    for i, (a, b, w) in enumerate([((80, 430), (740, 470), 40), ((60, 540), (420, 520), 26),
                                   ((420, 560), (760, 640), 32), ((100, 650), (360, 610), 18)]):
        cv.knife([[x + a[0], y + a[1]], [x + b[0], y + b[1]]], None, width=w)


def wet_panel(cv, x, y):
    colors = ["ultramarine", "cerulean_blue", "cadmium_yellow", "vermilion", "madder_lake", "lead_white"]
    bands(cv, x + 20, x + 780, y + 90, colors, h=100)
    cv.wet_in_wet(rect(cv, x + 400, y + 60, x + 800, y + 700), strength=0.9, reach=22, angle=90)


def stipple_panel(cv, x, y):
    cv.stroke(brush("flat_bristle", size=4), [[x + 20, y + 380], [x + 780, y + 380]], "#3E4A3C")
    for yy in range(y + 70, y + 690, 70):
        cv.stroke(brush("flat_bristle", load=1.6, size=3), [[x + 20, yy], [x + 780, yy]], "#3E4A3C")
    cv.dry()
    cv.stipple(ellipse(cv, x + 210, y + 380, 180, 270), ["cadmium_yellow", "cerulean_blue", "lead_white", "vermilion"],
               density=0.55, size=9)
    ramp = np.zeros(cv.shape, np.float32)
    ramp[y + 90:y + 670, x + 440:x + 770] = np.linspace(0.25, 1, 580)[:, None]
    cv.stipple(ramp, "naples_yellow", density=0.6, size=7)


def hatch_panel(cv, x, y):
    yy, xx = np.mgrid[:cv.shape[0], :cv.shape[1]]
    cx, cy, r = x + 400, y + 390, 250
    d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / r ** 2
    ball = d2 < 1
    cv.stroke(brush("flat_bristle", size=4), [[x + 20, y + 380], [x + 780, y + 380]], "#D9CBB0")
    for yy0 in range(y + 70, y + 690, 60):
        cv.stroke(brush("flat_bristle", load=1.6, size=3), [[x + 20, yy0], [x + 780, yy0]], "#D9CBB0")
    cv.dry()
    shade = ball & ((xx - cx) * 0.6 + (yy - cy) * 0.8 > -0.15 * r)
    core = ball & ((xx - cx) * 0.6 + (yy - cy) * 0.8 > 0.35 * r)
    cv.hatch(shade, "burnt_umber", angle=60, spacing=11)
    cv.hatch(core, "ivory_black", angle=-30, spacing=12, cross=True)
    cast = ((xx - cx - 170) / 300) ** 2 + ((yy - cy - 240) / 60) ** 2 < 1
    cv.hatch(cast & ~ball, "burnt_umber", angle=0, spacing=9)


def study_panel(cv, x, y):
    colors = ["cerulean_blue", "lead_white", "naples_yellow", "yellow_ochre", "burnt_sienna", "burnt_umber"]
    bands(cv, x + 20, x + 780, y + 80, colors, h=102, b="filbert")
    cv.wet_in_wet(rect(cv, x, y + 60, x + 800, y + 700), strength=0.7, reach=18, angle=0)
    cv.dry()
    cv.glaze(ellipse(cv, x + 420, y + 560, 380, 180), "burnt_sienna", strength=0.3)
    cv.knife([[x + 480, y + 250], [x + 700, y + 240]], "lead_white", width=50)
    cv.impasto([[x + 150, y + 300], [x + 330, y + 280]], "naples_yellow", thickness=1.3)
    cv.impasto([[x + 170, y + 330], [x + 360, y + 320]], "lead_white", thickness=1.1,
               brush=brush("round_bristle", size=1.3, load=2.0))
    cv.hatch(ellipse(cv, x + 250, y + 560, 180, 80), "burnt_umber", angle=20, spacing=10)


def spatter_panel(cv, x, y):
    for yy in range(y + 70, y + 690, 34):
        cv.stroke(brush("flat_bristle", load=1.6, size=2), [[x + 20, yy], [x + 400, yy + 5], [x + 780, yy - 3]],
                  "#39414A" if (yy // 34) % 2 else "#4A4238")
    cv.dry()
    cv.spatter(rect(cv, x + 30, y + 80, x + 380, y + 680), ["lead_white", "#D9DDE0"], density=0.1, size=6)
    swirl = fields.vortex((x + 600, y + 380), twist=0.85)
    cv.spatter(ellipse(cv, x + 600, y + 380, 180, 280), "lead_white", density=0.08, size=4, stretch=5, field=swirl)


def paint_sheet():
    rows = -(-len(PANELS) // COLS)
    cv = Canvas(COLS * PW, rows * PH, seed=21)
    cv.ground("raw_umber", texture="linen", tone=0.3)
    for k, fn in enumerate([glaze_panel, scumble_panel, impasto_panel, knife_panel, level_scrape_panel,
                            wet_panel, stipple_panel, hatch_panel, study_panel, spatter_panel]):
        t0 = time.time()
        fn(cv, (k % COLS) * PW, (k // COLS) * PH)
        print(f"  {PANELS[k][0]:<22} {time.time() - t0:5.1f}s")
    return cv


def labeled(pixels):
    img = Image.fromarray(pixels)
    draw = ImageDraw.Draw(img)
    font, small = ImageFont.load_default(size=22), ImageFont.load_default(size=15)
    for k, (name, note) in enumerate(PANELS):
        x, y = (k % COLS) * PW, (k // COLS) * PH
        draw.rectangle((x, y, x + PW, y + 50), fill=(30, 28, 26))
        draw.text((x + 14, y + 6), name, font=font, fill=(245, 240, 230))
        draw.text((x + 14, y + 31), note, font=small, fill=(190, 185, 175))
    for c in range(1, COLS):
        draw.line([(c * PW, 0), (c * PW, img.height)], fill=(30, 28, 26), width=3)
    for r in range(1, -(-len(PANELS) // COLS)):
        draw.line([(0, r * PH), (img.width, r * PH)], fill=(30, 28, 26), width=3)
    return img


if __name__ == "__main__":
    t0 = time.time()
    cv = paint_sheet()
    print(f"painted in {time.time() - t0:.1f}s")
    t1 = time.time()
    lit = cv.finish(light=(-0.5, -0.6), varnish=0.15, weave=0.35)
    aged = cv.finish(light=(-0.5, -0.6), varnish=0.7, weave=0.35, crackle=0.6)
    print(f"finished twice in {time.time() - t1:.1f}s")
    x, y = (8 % COLS) * PW, (8 // COLS) * PH
    lit[y:y + PH, x:x + PW] = aged[y:y + PH, x:x + PW]
    studio.save(labeled(lit), OUT / "technique_sheet.png", focus=FOCUS)
    studio.save(labeled(cv.to_srgb_uint8()), OUT / "technique_sheet_flat.png", focus=FOCUS)
    print("wrote", OUT / "technique_sheet.png", OUT / "technique_sheet_review.png", OUT / "technique_sheet_flat.png")
