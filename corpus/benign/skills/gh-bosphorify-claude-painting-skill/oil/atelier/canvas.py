"""Canvas: the painting's state (color, paint height, wetness, surface tooth) and grounds."""

import time

import numpy as np
from scipy.ndimage import gaussian_filter, zoom

from atelier import design, surface, techniques
from atelier.color import lightness, linear_to_srgb, mix
from atelier.pigments import color_of
from atelier.stroke import paint_stroke

GESSO = "#F1EEE6"
TEXTURES = ("linen", "cotton", "paper", "panel")


class Canvas:
    """Painting state. color: linear RGB HxWx3; height: paint thickness; wet: 0..1; tooth: 0..1;
    underlayer: the color as of the last dry() (or the ground), which scraping wet paint reveals.
    texture: the ground's texture (None before ground()), which sets finish()'s craquelure pattern.
    strokes counts the brush strokes laid so far; started is when the canvas was made (perf_counter).

    All randomness goes through self.rng, so the same seed and calls give the same pixels.
    Techniques (atelier.techniques), design painting (atelier.design) and finish (atelier.surface)
    are methods: cv.glaze(...), cv.paint_from_design(...), cv.finish().
    """

    glaze = techniques.glaze
    scumble = techniques.scumble
    impasto = techniques.impasto
    knife = techniques.knife
    wet_in_wet = techniques.wet_in_wet
    stipple = techniques.stipple
    spatter = techniques.spatter
    hatch = techniques.hatch
    fill_strokes = design.fill_strokes
    paint_from_design = design.paint_from_design
    finish = surface.finish

    def __init__(self, width, height, seed=0):
        self.shape = (height, width)
        self.seed = seed
        self.strokes = 0
        self.started = time.perf_counter()
        self.rng = np.random.default_rng(seed)
        self.color = np.empty((height, width, 3), np.float32)
        self.color[:] = color_of(GESSO)
        self.underlayer = self.color.copy()
        self.height = np.zeros(self.shape, np.float32)
        self.wet = np.zeros(self.shape, np.float32)
        self.tooth = np.zeros(self.shape, np.float32)
        self.texture = None

    def ground(self, color, texture="linen", tone=0.35):
        """Prime the support and tone it (imprimatura).

        texture: linen (coarse, irregular weave), cotton (fine, even weave), paper, panel (smooth gesso).
        tone: 0 = white gesso, 1 = the pigment itself, linear in lightness (0.5 = halfway in value).
        The toning wash is brushed on unevenly and pools in the valleys of the weave. The ground is dry.
        """
        if texture not in TEXTURES:
            raise ValueError(f"unknown texture {texture!r}; choose from {TEXTURES}")
        relief, raw = {
            "linen": (1.0, lambda: _weave(self.rng, self.shape, period=7.0, wander=0.22, slub=0.2)),
            "cotton": (0.8, lambda: _weave(self.rng, self.shape, period=4.5, wander=0.06, slub=0.07)),
            "paper": (0.7, lambda: _paper(self.rng, self.shape)),
            "panel": (0.2, lambda: _panel(self.rng, self.shape)),
        }[texture]
        bumps = _normalize(raw())
        self.tooth = (0.5 + relief * (bumps - 0.5)).astype(np.float32)
        self.texture = texture

        streaks = _smooth_noise(self.rng, self.shape, (40, 220))
        valleys = np.median(self.tooth) - self.tooth
        local = np.clip(tone + tone * (1 - tone) * (0.15 * streaks + 1.2 * valleys), 0, 1)
        t = np.linspace(0, 1, 257)
        ramp = mix((color_of(GESSO), 1 - t), (color_of(color), t))
        light = lightness(ramp)
        axis = t if abs(light[0] - light[-1]) < 1e-3 else np.maximum.accumulate((light[0] - light) / (light[0] - light[-1]))
        toned = np.stack([np.interp(local, axis, ramp[:, c]) for c in range(3)], axis=-1)
        self.color = (toned * (1 - 0.1 * valleys)[..., None]).astype(np.float32)
        self.underlayer = self.color.copy()
        self.height = np.zeros(self.shape, np.float32)
        self.wet = np.zeros(self.shape, np.float32)

    def stroke(self, brush, path, color, pressure=None, load=None):
        """Drag `brush` along `path` ((N, 2) control points in px, x right, y down) laying down `color`.

        color: pigment name, '#rrggbb' or linear RGB. pressure: scalar, one value per control point,
        or a list of any length spread evenly along the stroke (0..1, default 1 = full width).
        load: paint on the brush (default brush.load).
        Returns the Mark: the pixels inside the stroke, their (s, u) stroke coordinates and coverage.
        """
        return paint_stroke(self, brush, path, color, pressure, load)

    def dry(self):
        """Let all wet paint dry: later strokes no longer pick it up or blend with it."""
        self.wet[:] = 0
        self.underlayer[:] = self.color

    def to_srgb_uint8(self):
        return np.round(linear_to_srgb(np.clip(self.color, 0, 1)) * 255).astype(np.uint8)


def _normalize(a):
    lo, hi = np.percentile(a, [1, 99])
    return np.clip((a - lo) / (hi - lo + 1e-8), 0, 1)


def _smooth_noise(rng, shape, scale):
    """Unit-variance noise with feature size scale=(sy, sx) pixels."""
    sy, sx = scale
    h, w = shape
    grid = gaussian_filter(rng.standard_normal((int(h / sy) + 4, int(w / sx) + 4)), 0.7)
    out = zoom(grid, (sy, sx), order=3)[:h, :w]
    return (out - out.mean()) / (out.std() + 1e-8)


def _fibers(rng, shape, sigma):
    return gaussian_filter(rng.standard_normal(shape, dtype=np.float32), sigma)


def _weave(rng, shape, period, wander, slub):
    """Plain weave height field: warp (vertical) and weft (horizontal) threads passing over and under."""
    y, x = np.indices(shape, dtype=np.float32)
    u = x / period + wander * _smooth_noise(rng, shape, (period * 9, period * 9))
    v = y / period + wander * _smooth_noise(rng, shape, (period * 9, period * 9))
    iu, iv = np.floor(u), np.floor(v)
    fu, fv = u - iu, v - iv
    over = 1 - 2 * ((iu + iv) % 2)
    warp_thick = np.clip(0.82 + slub * _smooth_noise(rng, shape, (period * 7, period)), 0.4, 1.0)
    weft_thick = np.clip(0.82 + slub * _smooth_noise(rng, shape, (period, period * 7)), 0.4, 1.0)
    warp = _thread(fu, warp_thick) * (0.35 + 0.65 * (0.5 + 0.5 * over * np.sin(np.pi * fv)))
    weft = _thread(fv, weft_thick) * (0.35 + 0.65 * (0.5 - 0.5 * over * np.sin(np.pi * fu)))
    return np.maximum(warp, weft) + 0.08 * _fibers(rng, shape, 0.6)


def _thread(f, thick):
    """Rounded cross-section of a thread centred in its cell, f in [0, 1)."""
    return np.sqrt(np.clip(1 - ((f - 0.5) / (0.5 * thick)) ** 2, 0, 1))


def _paper(rng, shape):
    return (0.5 * _fibers(rng, shape, 1.2) / 0.13 + 0.35 * _fibers(rng, shape, 3.0) / 0.05
            + 0.3 * _smooth_noise(rng, shape, (14, 14)))


def _panel(rng, shape):
    return 0.6 * _smooth_noise(rng, shape, (2, 60)) + 0.2 * _fibers(rng, shape, 0.8) / 0.2
