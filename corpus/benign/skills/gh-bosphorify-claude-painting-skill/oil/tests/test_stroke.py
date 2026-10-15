import colorsys

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

from atelier import Canvas, brush
from atelier.color import lightness, linear_to_srgb
from atelier.pigments import color_of
from atelier.stroke import catmull_rom


def hue_deg(lrgb):
    r, g, b = np.clip(linear_to_srgb(np.asarray(lrgb, float)), 0, 1)
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


def line(x0, x1, y, n=6):
    return np.stack([np.linspace(x0, x1, n), np.full(n, float(y))], axis=1)


def white_canvas(w=900, h=200, seed=1, texture="linen"):
    cv = Canvas(w, h, seed=seed)
    cv.ground("lead_white", texture=texture, tone=0.0)
    return cv


def test_catmull_rom_passes_through_points_at_unit_spacing():
    pts = np.array([[10, 10], [60, 40], [120, 20], [200, 80]], float)
    curve = catmull_rom(pts, spacing=1.0)
    for p in pts:
        assert np.min(np.hypot(*(curve - p).T)) < 0.75
    steps = np.hypot(*np.diff(curve, axis=0).T)
    assert steps.max() < 1.3 and steps.mean() == pytest.approx(1.0, abs=0.15)


def test_coverage_decays_along_a_long_stroke():
    cv = white_canvas(1000, 160)
    mark = cv.stroke(brush("round_bristle"), line(40, 960, 80), "ivory_black")
    s = mark.s / mark.s.max()
    core = np.abs(mark.u) < 0.8
    first = mark.coverage[core & (s < 0.2)].mean()
    last = mark.coverage[core & (s > 0.8)].mean()
    assert last < 0.85 * first


def test_dry_bristle_breaks_up_at_the_end():
    cv = white_canvas(900, 160)
    mark = cv.stroke(brush("dry_bristle"), line(40, 700, 80), "ivory_black")
    s = mark.s / mark.s.max()
    tail = (s > 0.85) & (np.abs(mark.u) < 0.8)
    gaps = (mark.coverage[tail] < 0.25).mean()
    assert gaps > 0.20


def test_dry_brush_on_linen_skips_along_the_stroke_not_in_a_grid_of_weave_dots():
    def orientation(ink):
        gy, gx = np.gradient(gaussian_filter(ink, 1.0))
        jxx, jyy, jxy = (gx * gx).mean(), (gy * gy).mean(), (gx * gy).mean()
        evals, evecs = np.linalg.eigh(np.array([[jxx, jxy], [jxy, jyy]]))
        vx, vy = evecs[:, 0]
        return np.degrees(np.arctan2(-vy, vx)) % 180, (evals[1] - evals[0]) / (evals[1] + evals[0])

    for angle in (30, -20):
        cv = white_canvas(700, 400, seed=2)
        before = lightness(cv.color)
        a = np.radians(angle)
        for k in range(4):
            p0 = np.array([60.0, 330 - 40 * k if angle > 0 else 70 + 40 * k])
            d = np.array([np.cos(a), -np.sin(a)]) * 560
            cv.stroke(brush("dry_bristle", load=0.3), [p0, p0 + d / 2, p0 + d], "ivory_black")
        along, coherence = orientation((before - lightness(cv.color))[40:360, 80:640])
        assert coherence > 0.5
        assert abs((along - angle + 90) % 180 - 90) < 15


def test_blue_over_wet_red_mixes_toward_purple_but_stays_blue_over_dry_red():
    blue = color_of("ultramarine")
    results = {}
    for state in ("wet", "dry"):
        cv = white_canvas(600, 200, seed=5)
        for y in range(60, 150, 12):
            cv.stroke(brush("flat_bristle", load=1.5), line(40, 560, y), "madder_lake")
        if state == "dry":
            cv.dry()
        mark = cv.stroke(brush("round_bristle"), line(60, 540, 105), blue)
        sel = (mark.coverage > 0.7) & (np.abs(mark.u) < 0.5)
        results[state] = cv.color[mark.ys[sel], mark.xs[sel]].mean(axis=0)
    wet, dry = results["wet"], results["dry"]
    assert 200 < hue_deg(blue) < 250
    assert 200 < hue_deg(dry) < 255
    assert 250 < hue_deg(wet) < 335
    assert hue_deg(wet) > hue_deg(dry) + 12
    assert wet[0] > dry[0] + 0.02


def test_impasto_raises_height_and_strokes_deposit_wetness():
    cv = white_canvas(600, 200)
    mark = cv.stroke(brush("palette_knife"), line(60, 400, 100), "lead_white")
    covered = mark.coverage > 0.5
    assert cv.height[mark.ys[covered], mark.xs[covered]].mean() > 0.2
    assert cv.wet[mark.ys[covered], mark.xs[covered]].mean() > 0.5
    thin = white_canvas(600, 200)
    m2 = thin.stroke(brush("glaze_wide"), line(60, 400, 100), "lead_white")
    assert thin.height[m2.ys, m2.xs].mean() < cv.height[mark.ys, mark.xs].mean()


def test_same_seed_same_pixels():
    def paint(seed):
        cv = white_canvas(400, 300, seed=seed)
        rng = np.random.default_rng(0)
        for name in ("round_bristle", "flat_bristle", "palette_knife", "fan", "dry_bristle", "rigger"):
            pts = rng.uniform(30, 270, (4, 2)) * [1.3, 1]
            cv.stroke(brush(name), pts, "burnt_sienna", pressure=np.linspace(1, 0.4, 4))
        return cv
    a, b, c = paint(3), paint(3), paint(4)
    for field in ("color", "height", "wet"):
        assert getattr(a, field).tobytes() == getattr(b, field).tobytes()
    assert a.color.tobytes() != c.color.tobytes()


def test_pressure_widens_the_mark():
    widths = []
    for p in (0.3, 1.0):
        cv = white_canvas(500, 160)
        mark = cv.stroke(brush("round_bristle"), line(40, 460, 80), "ivory_black", pressure=p)
        widths.append((mark.coverage > 0.3).sum())
    assert widths[1] > 1.5 * widths[0]


def test_a_pressure_list_of_another_length_spreads_along_the_stroke():
    def painted(pressure):
        cv = white_canvas(700, 160)
        mark = cv.stroke(brush("round_bristle"), line(40, 660, 80, n=6), "ivory_black", pressure=pressure)
        s, inked = mark.s / mark.s.max(), mark.coverage > 0.3
        return cv, [(inked & (s > a) & (s < a + 0.15)).sum() for a in (0.15, 0.42, 0.7)]

    # two values on six evenly spaced points: the same stroke as one value per point, ramping evenly
    short, _ = painted([0.2, 1.0])
    per_point, _ = painted(np.linspace(0.2, 1.0, 6))
    assert short.color.tobytes() == per_point.color.tobytes()
    _, (left, middle, right) = painted([0.2, 1.0, 0.2])
    assert middle > 1.25 * left and middle > 1.25 * right
    _, (start, _, end) = painted(np.linspace(1.0, 0.2, 9))
    assert start > 1.5 * end


def test_load_argument_and_stroke_stays_on_canvas():
    cv = white_canvas(300, 120)
    before = cv.color.copy()
    mark = cv.stroke(brush("flat_bristle"), [[-50, 60], [150, 60], [400, 60]], "#203050", load=0.0)
    assert mark.coverage.max() < 0.05
    np.testing.assert_allclose(cv.color, before, atol=0.05)
    mark = cv.stroke(brush("flat_bristle"), [[-50, 60], [150, 60], [400, 60]], "#203050")
    assert mark.xs.min() >= 0 and mark.xs.max() < 300
    assert mark.coverage.max() > 0.9


def test_single_point_is_a_dab():
    cv = white_canvas(200, 200)
    mark = cv.stroke(brush("round_bristle"), [[100, 100]], "ivory_black")
    assert (mark.coverage > 0.5).sum() > 50
    assert np.ptp(mark.xs) < brush("round_bristle").width_px * 1.2
