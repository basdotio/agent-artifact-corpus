import numpy as np
import pytest

from atelier import Canvas, brush
from atelier.color import srgb_to_linear
from atelier.design import error_map, fill_strokes, paint_from_design
from atelier import fields
from atelier.pigments import color_of


def toned(w, h, seed):
    cv = Canvas(w, h, seed=seed)
    cv.ground("raw_umber", texture="linen", tone=0.35)
    return cv


def toy_design(w=300, h=220):
    """Linear RGB design: a sky gradient over a dark hill and two field bands."""
    y, x = np.mgrid[:h, :w].astype(float)
    t = (y / (0.6 * h))[..., None]
    img = (1 - t) * srgb_to_linear([0.35, 0.5, 0.8]) + t * srgb_to_linear([0.95, 0.85, 0.65])
    hill = y > 0.45 * h + 0.12 * h * np.cos(x / w * 5)
    img[hill] = srgb_to_linear([0.25, 0.3, 0.4])
    img[y > 0.7 * h] = srgb_to_linear([0.55, 0.62, 0.25])
    img[y > 0.85 * h + 6 * np.sin(x / 20)] = srgb_to_linear([0.72, 0.55, 0.28])
    return img.astype(np.float32)


PASSES = [("filbert", 1.4), ("flat_bristle", 0.6), ("round_bristle", 0.3)]


def paint(seed, **kw):
    cv = toned(300, 220, seed)
    stats = paint_from_design(cv, toy_design(), passes=[brush(n, s) for n, s in PASSES], **kw)
    return cv, stats


def test_mean_error_against_the_design_decreases_pass_by_pass():
    cv = toned(300, 220, 3)
    design = toy_design()
    errors = [error_map(cv, design).mean()]
    stats = paint_from_design(cv, design, passes=[brush(n, s) for n, s in PASSES])
    assert [s["brush"] for s in stats] == [n for n, _ in PASSES]
    errors += [s["error"] for s in stats]
    assert all(later < earlier for earlier, later in zip(errors, errors[1:])), errors
    assert errors[-1] < 0.4 * errors[0]
    assert errors[-1] == pytest.approx(error_map(cv, design).mean())


def test_passes_after_the_first_only_paint_where_the_error_is_high():
    _, stats = paint(3, threshold=1.0)
    assert stats[0]["strokes"] > 0
    assert stats[1]["strokes"] == 0 and stats[2]["strokes"] == 0


def test_paint_from_design_is_deterministic():
    a, sa = paint(5)
    b, sb = paint(5)
    c, _ = paint(6)
    assert sa == sb
    for f in ("color", "height", "wet"):
        assert getattr(a, f).tobytes() == getattr(b, f).tobytes()
    assert a.color.tobytes() != c.color.tobytes()


def test_uint8_designs_are_srgb():
    design = toy_design(120, 90)
    as_bytes = np.round(np.clip(design, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
    cv = toned(120, 90, 1)
    assert error_map(cv, as_bytes).mean() == pytest.approx(error_map(cv, design).mean(), abs=0.02)


def test_fill_strokes_stays_in_the_mask_and_follows_the_field():
    h, w = 200, 300
    y, x = np.mgrid[:h, :w]
    mask = np.hypot(x - 150, y - 100) < 70
    cv = toned(w, h, 2)
    before = cv.color.copy()
    b = brush("filbert", size=0.6)
    paths = fill_strokes(cv, mask, fields.constant(30), b, "vermilion", density=3, length=(20, 50))
    assert len(paths) > 20
    for p in paths:
        seg = np.diff(p, axis=0)
        if len(seg):
            d = seg / np.hypot(*seg.T)[:, None]
            assert np.abs(d @ [np.cos(np.radians(30)), np.sin(np.radians(30))]).min() > 0.99
    inside = np.hypot(x - 150, y - 100) < 55
    far = np.hypot(x - 150, y - 100) > 70 + b.width_px
    red = color_of("vermilion")
    moved = np.linalg.norm(cv.color - before, axis=-1)
    assert np.linalg.norm(cv.color[inside] - red, axis=-1).mean() < 0.12
    assert moved[far].max() < 1e-6


def test_fill_strokes_on_a_soft_mask_leaves_no_stray_dabs_in_its_margin():
    h, w = 300, 300
    y, x = np.mgrid[:h, :w]
    r = np.hypot(x - 150, y - 150)
    soft = np.exp(-r ** 2 / (2 * 60.0 ** 2))          # 0.5 at r = 71 px, a long faint tail beyond
    cv = toned(w, h, 2)
    before = cv.color.copy()
    b = brush("filbert", size=0.6)
    paths = fill_strokes(cv, soft, fields.constant(90), b, "vermilion", density=1.0, length=(20, 60))
    assert len(paths) > 20 and min(len(p) for p in paths) > 1
    moved = np.linalg.norm(cv.color - before, axis=-1) > 0.02
    assert moved[r < 50].mean() > 0.3
    assert not moved[r > 71 + b.width_px + 4].any()


def test_fill_strokes_skips_islands_too_small_for_one_step_of_the_brush():
    mask = np.zeros((260, 360), bool)
    mask[40:220, 20:160] = True                       # room for strokes
    for iy in range(40, 220, 12):                     # a field of 5x5 px islands, smaller than a 6 px step
        for ix in range(200, 340, 12):
            mask[iy:iy + 5, ix:ix + 5] = True
    cv = toned(360, 260, 4)
    before = cv.color.copy()
    paths = fill_strokes(cv, mask, fields.constant(90), brush("filbert", size=0.6), "vermilion", density=2.0,
                         length=(20, 60))
    assert len(paths) > 20 and min(len(p) for p in paths) > 1
    moved = np.linalg.norm(cv.color - before, axis=-1) > 0.02
    assert moved[60:200, 40:140].mean() > 0.5
    assert not moved[:, 185:].any()


def test_fill_strokes_without_a_mask_covers_the_whole_canvas():
    cv = toned(240, 160, 6)
    before = cv.color.copy()
    paths = fill_strokes(cv, None, fields.constant(0), brush("filbert", 0.5), "vermilion", density=2.0,
                         length=(15, 30))
    starts = np.array([p[len(p) // 2] for p in paths])
    assert len(paths) > 20
    assert starts[:, 0].min() < 40 and starts[:, 0].max() > 200
    assert starts[:, 1].min() < 30 and starts[:, 1].max() > 130
    moved = np.linalg.norm(cv.color - before, axis=-1) > 0.05
    assert moved.mean() > 0.5


def test_fill_strokes_samples_colors_from_a_design_image():
    h, w = 160, 240
    design = np.zeros((h, w, 3), np.float32)
    design[:, :120] = color_of("ultramarine")
    design[:, 120:] = color_of("cadmium_yellow")
    cv = toned(w, h, 4)
    fill_strokes(cv, np.ones((h, w), bool), fields.vortex((120, 80), twist=0.9), brush("filbert", 0.5),
                 design, density=2.0, length=(15, 30))
    left, right = cv.color[40:120, 20:90].mean(axis=(0, 1)), cv.color[40:120, 150:220].mean(axis=(0, 1))
    assert left[2] > left[0] and right[0] > right[2]
