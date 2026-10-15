"""Oil starter: the layered method end to end on a small canvas (an estuary at evening).

    uv run --project <skill>/oil python oil_starter.py <out_dir> [--width 900] [--seed 7]

Copy it to paintings/<slug>/paint.py and replace the palette, the design map, the fields and the
layers with the ones from your dossier. Sizes and distances are written for a 2048 px wide canvas
and scaled by S, so the same script renders a quick 900 px study or the 2048 px final.

Writes into <out_dir>: design.png (the flat plan; its review sheet is the value study),
final.png + final_review.png, and progress/NN_<layer>.png + progress/contact_sheet.png.
"""

import argparse
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, zoom

from atelier import Canvas, Palette, brush, fields, studio
from atelier.color import lightness, linear_to_srgb

pal = Palette(["lead_white", "naples_yellow", "yellow_ochre", "indian_yellow", "vermilion", "burnt_sienna",
               "burnt_umber", "ultramarine", "cerulean_blue", "viridian", "ivory_black"])


# ---- helpers for the design map: gradients, masks and noise (colors are linear RGB) ----

def ramp(t, stops):
    """Colors along t (any shape) through (position, color) stops."""
    pos = [p for p, _ in stops]
    return np.stack([np.interp(t, pos, [c[i] for _, c in stops]) for i in range(3)], axis=-1)


def polygon(shape, points):
    """HxW 0..1 mask of the polygon through (x, y) points."""
    img = Image.new("L", shape[::-1], 0)
    ImageDraw.Draw(img).polygon([tuple(map(float, p)) for p in points], fill=255)
    return np.asarray(img, np.float32) / 255


def soft(mask, sigma):
    return gaussian_filter(np.asarray(mask, np.float32), sigma)


def mottle(rng, shape, scale):
    """Smooth unit-variance noise with blobs about `scale` px across."""
    h, w = shape
    s = max(1, int(scale))
    z = zoom(rng.standard_normal((h // s + 4, w // s + 4)), s, order=3)[:h, :w]
    return (z - z.mean()) / z.std()


def srgb8(lin):
    return np.round(linear_to_srgb(np.clip(lin, 0, 1)) * 255).astype(np.uint8)


def dead_color(design, dark="burnt_umber", light="lead_white"):
    """The design's values in a two-pigment ramp: the monochrome underpainting."""
    t = np.linspace(0, 1, 256)
    ramp_rgb = pal.mix((dark, 1 - t), (light, t))
    idx = np.interp(lightness(design), np.maximum.accumulate(lightness(ramp_rgb)), np.arange(256))
    return ramp_rgb[np.rint(idx).astype(int)].astype(np.float32)


# ---- the plan: big shapes with their values and colors, no brushwork ----

def design_map(W, H, rng):
    """Linear RGB design plus the region masks the layers reuse (fields, glazes, scumbles)."""
    y, x = np.mgrid[:H, :W].astype(np.float32)
    u, v = x / W, y / H
    sun, horizon = (0.66 * W, 0.40 * H), 0.60 * H

    sky = ramp(v / 0.6, [(0.0, pal.mix(("ultramarine", 1), ("burnt_umber", 0.3), ("lead_white", 1.3))),
                         (0.55, pal.mix(("cerulean_blue", 0.4), ("yellow_ochre", 0.4), ("lead_white", 2.4))),
                         (1.0, pal.mix(("lead_white", 3), ("naples_yellow", 1.5), ("vermilion", 0.15)))])
    glow = np.exp(-((x - sun[0]) ** 2 + (y - sun[1]) ** 2) / (2 * (0.14 * W) ** 2))
    img = sky + (pal.mix(("lead_white", 3), ("naples_yellow", 1.2)) - sky) * glow[..., None]
    clouds = np.clip(mottle(rng, (H, W), 0.12 * W) - 0.3, 0, 1) * np.clip(1 - v / 0.42, 0, 1) * (1 - glow)
    img += (pal.mix(("burnt_umber", 0.7), ("ultramarine", 0.6), ("lead_white", 1.6)) - img) * clouds[..., None]

    ridge = H * (0.535 - 0.06 * np.exp(-((u - 0.22) / 0.13) ** 2) - 0.035 * np.exp(-((u - 0.43) / 0.08) ** 2)
                 + 0.004 * np.sin(u * 47))
    hills = (y > ridge) & (y < horizon)
    haze = ramp((y - ridge) / (horizon - ridge), [(0, pal.mix(("ultramarine", 1), ("burnt_sienna", 0.5), ("lead_white", 1.1))),
                                                  (1, pal.mix(("ultramarine", 0.6), ("lead_white", 2.0), ("naples_yellow", 0.4)))])
    img[hills] = haze[hills]

    # Water mirrors what is above the horizon, darker and cooler, with the sun's path across it.
    water = y >= horizon
    mirrored = img[np.clip(2 * horizon - y, 0, horizon - 1).astype(int), x.astype(int)]
    depth = np.clip((y - horizon) / (H - horizon), 0, 1)[..., None]
    img[water] = (mirrored * (0.5 - 0.2 * depth) * [0.82, 0.92, 1.0])[water]
    spread = 0.012 * W + 0.25 * np.maximum(y - horizon, 0)
    path = water * np.exp(-((x - sun[0]) / spread) ** 2) * (1 - 0.5 * depth[..., 0])
    img += (pal.mix(("lead_white", 3), ("naples_yellow", 1)) - img) * (0.9 * path)[..., None]

    # The boat's hull as a dark mass against the sun's path; the details layer sharpens it by hand.
    boat = (sun[0] - 0.02 * W, 0.68 * H)
    hull = polygon((H, W), [(boat[0] - 0.036 * W, boat[1] - 0.003 * H), (boat[0] + 0.038 * W, boat[1] - 0.005 * H),
                            (boat[0] + 0.03 * W, boat[1] + 0.008 * H), (boat[0] - 0.029 * W, boat[1] + 0.007 * H)])
    img += (pal.mix(("ivory_black", 1), ("burnt_umber", 0.6)) - img) * soft(hull, 1)[..., None]

    # The near bank, sloping out of the lower left corner.
    bank_top = H * (0.77 + 0.3 * u ** 1.6) + 0.012 * H * mottle(rng, (1, W), 0.05 * W)
    bank = y > bank_top
    earth = ramp((y - bank_top) / (0.2 * H), [(0, pal.mix(("yellow_ochre", 1), ("burnt_umber", 0.7), ("viridian", 0.25))),
                                               (1, pal.mix(("burnt_umber", 1), ("ultramarine", 0.35), ("ivory_black", 0.2)))])
    earth *= 1 + 0.12 * mottle(rng, (H, W), 0.04 * W)[..., None]
    img[bank] = earth[bank]

    masks = {"sun": sun, "horizon": horizon, "boat": boat, "bank_top": bank_top[0], "glow": glow,
             "sky": (~hills & ~water).astype(np.float32), "hills": hills.astype(np.float32),
             "water": (water & ~bank).astype(np.float32), "bank": bank.astype(np.float32)}
    return img.astype(np.float32), masks


def flow_field(W, m, rng):
    """Which way the brush travels: a swirl around the sun, level water and hills, the bank's own contour."""
    wind = fields.noise(0.25 * W, rng, angle=-6, spread=25)
    sky = fields.combine((fields.vortex(m["sun"], twist=0.9), m["glow"]), (wind, 0.5))
    level = fields.combine((fields.constant(0), 1.0), (fields.noise(0.1 * W, rng, spread=10), 0.3))
    land = fields.combine((fields.contour(m["bank"], sigma=0.01 * W), 1.0), (fields.noise(0.08 * W, rng), 0.5))
    s = 0.01 * W
    return fields.combine((sky, soft(m["sky"], s)), (level, soft(m["hills"] + m["water"], s)), (land, soft(m["bank"], s)))


# ---- the painting, layer by layer ----

def paint(out, W, seed):
    H = W * 3 // 4
    S = W / 2048
    progress = out / "progress"
    snap = lambda image, label: studio.snapshot(image, label, dir=progress)
    t0 = time.time()

    cv = Canvas(W, H, seed=seed)
    design, m = design_map(W, H, np.random.default_rng([seed, 1]))
    studio.save(srgb8(design), out / "design.png")
    snap(srgb8(design), "design")

    # 1. Ground: a warm mid-toned imprimatura on linen. Wherever strokes part, it glows through.
    cv.ground("burnt_sienna", texture="linen", tone=0.45)
    snap(cv, "ground")
    flow = flow_field(W, m, cv.rng)

    # 2. Underpainting (dead color): only the values, in umber and white, thin (impasto=0) and loose.
    cv.fill_strokes(None, flow, brush("filbert", size=4 * S, impasto=0.0), dead_color(design), density=1.2,
                    length=(80 * S, 240 * S))
    cv.dry()
    snap(cv, "underpainting")

    # 3. Block-in and refinement: big brush to small, lean to fat. The first pass covers everything; later
    #    passes repaint only where the canvas is still off the design, so broken color survives.
    passes = [brush("filbert", size=3.2 * S, impasto=0.04), brush("flat_bristle", size=1.2 * S, impasto=0.1),
              brush("round_bristle", size=0.6 * S)]
    stats = cv.paint_from_design(design, passes, field=flow, after_pass=lambda c, i: snap(c, f"pass {i + 1}"))
    # The last pass is still wet: melt it together in the air around the sun.
    cv.wet_in_wet(m["glow"], strength=0.5, reach=14 * S)
    cv.dry()

    # 4. Details and highlights, by hand: haze scumbled over the hills, the boat as the darkest accent
    #    against the sun's path, reeds with the rigger, and the lights (glints, the sun) in thick paint.
    rng, (sx, sy), light = cv.rng, m["sun"], pal.mix(("lead_white", 3), ("naples_yellow", 1))
    cv.scumble(soft(m["hills"], 4 * S), pal.mix(("lead_white", 3), ("cerulean_blue", 0.3)), coverage=0.15, size=0.8 * S)
    bx, by = m["boat"]
    dark = pal.mix(("ivory_black", 1), ("burnt_umber", 0.6))
    cv.stroke(brush("flat_bristle", size=0.9 * S), [[bx - 70 * S, by - 4 * S], [bx, by + 5 * S], [bx + 75 * S, by - 6 * S]],
              dark, pressure=[0.5, 1.0, 0.6])
    cv.stroke(brush("rigger", size=2.2 * S), [[bx + 4 * S, by - 4 * S], [bx + 9 * S, by - 150 * S]], dark)
    for k in range(3):
        cv.stroke(brush("filbert", size=0.9 * S), [[bx + 14 * S, by - (140 - 8 * k) * S], [bx + (40 + 12 * k) * S, by - 22 * S]],
                  pal.mix(("burnt_umber", 1), ("ultramarine", 0.3), ("lead_white", 0.6)), pressure=[0.3, 1.0])
    for _ in range(40):
        x0 = rng.uniform(0, 0.5 * W)
        y0 = np.interp(x0, np.arange(W), m["bank_top"]) + rng.uniform(5, 60) * S
        h, lean = rng.uniform(40, 150) * S, rng.normal(-0.2, 0.1)
        reed = pal.mix(("burnt_umber", 1), ("yellow_ochre", rng.uniform(0.2, 1.2)), ("viridian", 0.2))
        cv.stroke(brush("rigger", size=1.8 * S), [[x0, y0], [x0 + 0.3 * lean * h, y0 - 0.55 * h], [x0 + lean * h, y0 - h]],
                  reed, pressure=[1.0, 0.7, 0.3])
    for _ in range(14):
        gy = rng.uniform(by + 30 * S, 0.86 * H)
        gx = sx + rng.normal(0, 0.3) * (0.012 * W + 0.25 * (gy - m["horizon"]))
        half = rng.uniform(8, 30) * S
        cv.impasto([[gx - half, gy], [gx + half, gy + rng.normal(0, 2) * S]], light, thickness=rng.uniform(0.5, 1.0),
                   brush=brush("flat_bristle", size=rng.uniform(0.3, 0.6) * S, load=1.6))
    for a in np.pi * (np.arange(3) / 3 + rng.uniform(0, 0.3)):
        d = np.array([np.cos(a), np.sin(a)]) * 0.014 * W
        cv.impasto([[sx - d[0], sy - d[1]], [sx + d[0], sy + d[1]]], light, thickness=0.9,
                   brush=brush("filbert", size=1.3 * S, load=1.6))
    snap(cv, "details")
    cv.dry()

    # 5. Glazes: warm light around the sun, the foreground pushed back into cool shadow.
    cv.glaze(m["glow"], "indian_yellow", strength=0.2)
    cv.glaze(soft(m["bank"], 6 * S), "ultramarine", strength=0.25)
    cv.dry()
    snap(cv, "glazes")

    # 6. Finish: photograph it under a raking light. finish() returns a new image; the canvas is unchanged.
    #    scale=S lights the relief as on the 2048 px render, so a 900 px study looks about as embossed as the final;
    #    focus puts a 1:1 crop of the focal point (the boat) first on the review sheet.
    final = cv.finish(light=(-0.5, -0.6), varnish=0.15, weave=0.3, scale=S)
    studio.save(final, out / "final.png", focus=[m["boat"]], canvas=cv)  # + final_stats.json
    snap(final, "finish")
    studio.contact_sheet(progress)
    for s in stats:
        print(f"  {s['brush']:>14} {s['width']:5.1f}px {s['strokes']:6d} strokes  error {s['error']:.3f}")
    print(f"{W}x{H} in {time.time() - t0:.1f}s -> {out / 'final.png'}, {out / 'final_review.png'}, "
          f"{progress / 'contact_sheet.png'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path, help="output folder, e.g. paintings/<slug>")
    ap.add_argument("--width", type=int, default=900, help="900 for studies, 2048 for the final")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    paint(args.out, args.width, args.seed)
