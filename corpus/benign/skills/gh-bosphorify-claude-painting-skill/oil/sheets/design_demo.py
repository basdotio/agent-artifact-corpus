"""Demo for WP4: a procedural landscape design painted in three passes with paint_from_design.

Run from painting-kit/oil:
    uv run python sheets/design_demo.py
Writes out/design_flat.png (the design), out/design_demo.png (+ _review) and the pass-by-pass
frames in out/design_demo_progress/ (+ contact_sheet.png).
"""

import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

from atelier import Canvas, Palette, brush, studio
from atelier import fields
from atelier.color import linear_to_srgb
from atelier.design import paint_from_design

OUT = Path(__file__).resolve().parent.parent / "out"
W, H = 2048, 1536
SUN = (1480, 400)

pal = Palette(["lead_white", "naples_yellow", "yellow_ochre", "cadmium_yellow", "vermilion", "ultramarine",
               "cobalt_blue", "cerulean_blue", "viridian", "burnt_umber", "burnt_sienna", "terre_verte"])


def ramp(t, stops):
    """Colors along t (any shape) through (position, color) stops."""
    pos = [p for p, _ in stops]
    return np.stack([np.interp(t, pos, [c[i] for _, c in stops]) for i in range(3)], axis=-1)


def design_map():
    """Sky gradient with a sun glow, a mountain silhouette, and three bands of fields (linear RGB)."""
    y, x = np.mgrid[:H, :W].astype(np.float64)
    ridge = (760 - 170 * np.exp(-((x - 620) / 330) ** 2) - 120 * np.exp(-((x - 1180) / 260) ** 2)
             - 60 * np.sin(x / 97 + 1) * np.exp(-((x - 900) / 700) ** 2) + 18 * np.sin(x / 31))
    horizon = 1010 + 18 * np.sin(x / 260)
    band1 = 1150 + 40 * np.sin(x / 330 + 2)
    band2 = 1330 + 55 * np.sin(x / 410 - 1)

    sky = ramp(y / 1000, [
        (0.0, pal.mix(("ultramarine", 1), ("cobalt_blue", 0.6), ("lead_white", 1.1))),
        (0.45, pal.mix(("cerulean_blue", 1), ("lead_white", 2.4))),
        (0.85, pal.mix(("lead_white", 3), ("naples_yellow", 1.4), ("vermilion", 0.08))),
    ])
    glow = np.exp(-((x - SUN[0]) ** 2 + (y - SUN[1]) ** 2) / (2 * 260 ** 2))[..., None]
    img = sky * (1 - 0.8 * glow) + 0.8 * glow * pal.mix(("lead_white", 2), ("naples_yellow", 1.5))

    hill = y > ridge
    haze = np.clip((y - ridge) / np.maximum(horizon - ridge, 1), 0, 1)
    rock = ramp(haze, [
        (0.0, pal.mix(("ultramarine", 1), ("burnt_umber", 0.7), ("lead_white", 0.9))),
        (1.0, pal.mix(("ultramarine", 0.6), ("cerulean_blue", 0.4), ("lead_white", 2.2))),
    ])
    img[hill] = rock[hill]
    bands = [
        (horizon, pal.mix(("yellow_ochre", 1), ("viridian", 0.35), ("lead_white", 0.9))),
        (band1, pal.mix(("viridian", 1), ("cadmium_yellow", 1.1), ("burnt_umber", 0.25))),
        (band2, pal.mix(("yellow_ochre", 1.6), ("burnt_sienna", 0.35), ("naples_yellow", 0.6))),
    ]
    for top, color in bands:
        img[y > top] = color
    return img.astype(np.float32), gaussian_filter((~hill).astype(np.float32), 30)


def srgb8(lin):
    return np.round(linear_to_srgb(np.clip(lin, 0, 1)) * 255).astype(np.uint8)


if __name__ == "__main__":
    t0 = time.time()
    design, sky_mask = design_map()
    studio.save(srgb8(design), OUT / "design_flat.png")

    cv = Canvas(W, H, seed=21)
    cv.ground("burnt_sienna", texture="linen", tone=0.4)
    # A whirl around the sun that hands over to a wavering wind further out.
    near_sun = lambda p: np.exp(-((p[:, 0] - SUN[0]) ** 2 + (p[:, 1] - SUN[1]) ** 2) / (2 * 420 ** 2))
    wind = fields.noise(380, cv.rng, angle=-10, spread=35)
    sky = fields.combine((fields.vortex(SUN, twist=0.8), near_sun), (wind, 0.25))
    land = fields.combine((fields.contour(design, sigma=4), 1.0), (fields.noise(160, cv.rng), 0.4))
    flow = fields.combine((sky, sky_mask), (land, 1 - sky_mask))
    passes = [brush("filbert", size=3.6), brush("flat_bristle", size=1.1), brush("round_bristle", size=0.6)]
    progress = OUT / "design_demo_progress"
    studio.snapshot(cv, "ground", dir=progress)
    t1 = time.time()
    stats = paint_from_design(cv, design, passes, field=flow,
                              after_pass=lambda c, i: studio.snapshot(c, f"pass {i + 1}", dir=progress))
    t2 = time.time()
    for s in stats:
        print(f"{s['brush']:>14} {s['width']:5.1f}px  {s['strokes']:6d} strokes  error {s['error']:.4f}")
    print(f"setup {t1 - t0:.1f}s, 3 passes {t2 - t1:.1f}s")
    studio.save(cv, OUT / "design_demo.png")
    studio.contact_sheet(progress)
    print("wrote", OUT / "design_demo.png", OUT / "design_demo_review.png", OUT / "design_flat.png")
