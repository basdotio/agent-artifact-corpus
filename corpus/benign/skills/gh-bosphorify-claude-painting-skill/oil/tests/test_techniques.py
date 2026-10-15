import numpy as np
import pytest
from scipy.ndimage import binary_dilation, binary_erosion, gaussian_filter, label

from atelier import Canvas, brush
from atelier.color import lightness, linear_to_srgb
from atelier.pigments import color_of


def line(x0, x1, y, n=6):
    return np.stack([np.linspace(x0, x1, n), np.full(n, float(y))], axis=1)


def white_canvas(w=400, h=300, seed=1, texture="linen"):
    cv = Canvas(w, h, seed=seed)
    cv.ground("lead_white", texture=texture, tone=0.0)
    return cv


def disk(shape, cx, cy, r):
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    return (xx - cx) ** 2 + (yy - cy) ** 2 < r * r


def hue_deg(lrgb):
    import colorsys
    r, g, b = np.clip(linear_to_srgb(np.asarray(lrgb, float)), 0, 1)
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


def test_glaze_tints_lights_keeps_darks_and_the_modelling_underneath():
    cv = white_canvas(260, 180, texture="panel")
    stripes = (np.arange(260) // 20) % 2 == 1
    cv.color[:, stripes] = color_of("ivory_black")
    cv.dry()
    before = cv.color.copy()
    mask = np.zeros(cv.shape, bool)
    mask[30:150, 40:220] = True
    cv.glaze(mask, "ultramarine", strength=0.3)

    inner = binary_erosion(mask, iterations=12)
    white, black = inner & ~stripes[None, :], inner & stripes[None, :]
    w0, w1 = before[white].mean(0), cv.color[white].mean(0)
    k0, k1 = lightness(before[black]).mean(), lightness(cv.color[black]).mean()
    assert w1[2] / w1[0] > 1.6 * w0[2] / w0[0]
    assert 200 < hue_deg(w1) < 250
    assert lightness(w1) < lightness(w0)
    assert k1 < k0 + 0.03
    contrast = (lightness(cv.color[white]).mean() - k1) / (lightness(before[white]).mean() - k0)
    assert contrast > 0.5
    np.testing.assert_array_equal(cv.color[~binary_dilation(mask, iterations=2)],
                                  before[~binary_dilation(mask, iterations=2)])


def test_glaze_pools_at_the_edge_of_its_mask():
    cv = white_canvas(240, 240, texture="panel")
    mask = disk(cv.shape, 120, 120, 80)
    cv.glaze(mask, "madder_lake", strength=0.25)
    rim = mask & ~binary_erosion(mask, iterations=3)
    core = binary_erosion(mask, iterations=20)
    assert lightness(cv.color[rim]).mean() < lightness(cv.color[core]).mean() - 0.03


def test_glaze_follows_a_soft_mask_smoothly_without_speckle_or_pinholes():
    cv = white_canvas(320, 320, texture="panel")
    before = lightness(cv.color)
    y, x = np.mgrid[:320, :320]
    r = np.hypot(x - 160, y - 160)
    ramp = np.clip((110 - r) / 50, 0, 1)            # full inside r = 60, fading to nothing at r = 110
    cv.glaze(ramp, "ultramarine", strength=0.5, pooling=0.0)
    dark = before - lightness(cv.color)
    band = (ramp > 0.1) & (ramp < 0.9)
    speckle = dark - gaussian_filter(dark, 3)
    assert speckle[band].std() < 0.1 * dark[band].mean()
    assert dark[r < 55].min() > 0.5 * dark[r < 55].mean()
    rings = [dark[(r >= a) & (r < a + 5)].mean() for a in range(60, 110, 5)]
    assert all(b < a for a, b in zip(rings, rings[1:]))


def test_scumble_is_broken_semi_opaque_and_catches_the_tooth():
    cv = Canvas(320, 260, seed=3)
    cv.ground("burnt_umber", texture="linen", tone=0.9)
    before = cv.color.copy()
    mask = np.zeros(cv.shape, np.float32)
    mask[40:220, 40:280] = 1
    cv.scumble(mask, "lead_white", coverage=0.4)
    lift = lightness(cv.color) - lightness(before)
    inside = binary_erosion(mask > 0, iterations=15)
    touched = lift[inside] > 0.05
    assert 0.2 < touched.mean() < 0.8
    assert np.median(lightness(cv.color[inside][touched])) < lightness(color_of("lead_white")) - 0.1
    assert np.corrcoef(lift[inside], cv.tooth[inside])[0, 1] > 0.1
    np.testing.assert_array_equal(cv.color[mask == 0], before[mask == 0])

    more = Canvas(320, 260, seed=3)
    more.ground("burnt_umber", texture="linen", tone=0.9)
    more.scumble(mask, "lead_white", coverage=0.8)
    assert ((lightness(more.color) - lightness(before))[inside] > 0.05).mean() > touched.mean() + 0.1


def test_impasto_stands_up_with_furrows_edge_ridges_and_an_end_crest():
    cv = white_canvas(640, 200)
    mark = cv.impasto(line(60, 560, 100), "lead_white", thickness=1.0)
    h = cv.height[mark.ys, mark.xs]
    plain = white_canvas(640, 200)
    m2 = plain.stroke(brush("flat_bristle"), line(60, 560, 100), "lead_white")
    assert h.mean() > 2.5 * plain.height[m2.ys, m2.xs].mean()

    L, au = mark.s.max(), np.abs(mark.u)
    mid = (mark.s > 0.3 * L) & (mark.s < 0.6 * L) & (mark.coverage > 0.5)
    edge, center = mid & (au > 0.72) & (au < 0.92), mid & (au < 0.4)
    assert h[edge].mean() > 1.15 * h[center].mean()
    crest = (mark.s > L - 9) & (mark.s < L - 1) & (au < 0.6)
    assert h[crest].mean() > 1.25 * h[center].mean()
    # bristle furrows: the height ripples across the stroke
    rows = cv.height[88:112, 250:400]
    assert np.abs(np.diff(rows, axis=0)).mean() > 0.08 * rows.mean()


def test_knife_lays_a_flat_slab_with_sharp_edges():
    cv = white_canvas(520, 200)
    mark = cv.knife(line(40, 480, 100), "cadmium_yellow", width=40)
    L = mark.s.max()
    core = (np.abs(mark.u) < 0.6) & (mark.s > 0.2 * L) & (mark.s < 0.7 * L)
    h = cv.height[mark.ys[core], mark.xs[core]]
    assert h.mean() > 0.6 and h.std() < 0.2 * h.mean()
    top = np.median(h)
    for x in (150, 260, 370):
        col = cv.height[:, x]
        ramp = ((col > 0.1 * top) & (col < 0.8 * top)).sum()
        assert ramp <= 6


def test_short_narrow_knife_strokes_and_tiny_glazes_stay_sane():
    cv = white_canvas(320, 120)
    for i, (length, width) in enumerate([(6, 5), (14, 6), (30, 8), (50, 12)]):
        x0 = 20 + 75 * i
        cv.knife(line(x0, x0 + length, 60, n=2), "lead_white", width=width, thickness=0.6)
    assert np.isfinite(cv.height).all()
    assert cv.height.min() >= 0 and cv.height.max() < 3
    before = lightness(cv.color[95:105, 150:170]).mean()
    cv.glaze(disk(cv.shape, 160, 100, 6), "ultramarine", strength=0.3)
    after = lightness(cv.color[95:105, 150:170])
    assert np.isfinite(after).all() and 0.5 * before < after.mean() < before


def test_knife_flattens_wet_impasto():
    cv = white_canvas(560, 300)
    for y in range(95, 215, 16):
        cv.impasto(line(40, 520, y), "lead_white", thickness=1.0)
    region = (slice(125, 175), slice(180, 380))
    var0 = cv.height[region].var()
    cv.knife(line(20, 540, 150), "lead_white", width=90)
    assert cv.height[region].var() < 0.35 * var0


def test_knife_without_paint_scrapes_wet_paint_back_to_the_layer_below():
    def painted(dry_before_scrape):
        cv = white_canvas(420, 220)
        for y in range(50, 170, 12):
            cv.stroke(brush("flat_bristle", load=1.5), line(20, 400, y), "cadmium_yellow")
        cv.dry()
        for y in range(50, 170, 12):
            cv.stroke(brush("flat_bristle", load=1.5), line(20, 400, y), "ultramarine")
        if dry_before_scrape:
            cv.dry()
        return cv

    cv = painted(False)
    before, h0 = cv.color.copy(), cv.height.copy()
    mark = cv.knife(line(30, 390, 110), None, width=50)
    sel = (mark.coverage > 0.5) & (np.abs(mark.u) < 0.7)
    ys, xs = mark.ys[sel], mark.xs[sel]
    under = cv.underlayer[ys, xs]
    d0 = np.abs(before[ys, xs] - under).mean()
    d1 = np.abs(cv.color[ys, xs] - under).mean()
    assert d1 < 0.6 * d0
    assert cv.height[ys, xs].mean() < h0[ys, xs].mean()
    # paint stays behind in the valleys of the weave, so the scraped passage follows the tooth
    left = np.abs(cv.color[ys, xs] - under).mean(axis=1)
    assert np.corrcoef(left, cv.tooth[ys, xs])[0, 1] < -0.1

    dry = painted(True)
    before = dry.color.copy()
    dry.knife(line(30, 390, 110), None, width=50)
    np.testing.assert_allclose(dry.color, before, atol=1e-6)


def test_wet_in_wet_melts_adjacent_wet_colors_into_a_km_mix():
    def two_bands(wet):
        cv = white_canvas(300, 220, texture="panel")
        cv.color[:110] = color_of("ultramarine")
        cv.color[110:] = color_of("cadmium_yellow")
        cv.wet[:] = wet
        return cv

    cv = two_bands(1.0)
    cv.wet_in_wet(None, strength=0.8, angle=90)
    band = cv.color[95:125, 20:280].reshape(-1, 3)
    hues = np.array([hue_deg(c) for c in band[::7]])
    assert ((hues > 70) & (hues < 170)).mean() > 0.3
    # the boundary softens: the value changes gradually over more rows
    rows = lightness(cv.color[:, 20:280]).mean(axis=1)
    lo, hi = lightness(color_of("ultramarine")), lightness(color_of("cadmium_yellow"))
    transition = ((rows > lo + 0.1 * (hi - lo)) & (rows < hi - 0.1 * (hi - lo))).sum()
    assert transition > 8

    dry = two_bands(0.0)
    before = dry.color.copy()
    dry.wet_in_wet(None, strength=0.8, angle=90)
    np.testing.assert_array_equal(dry.color, before)


def test_stipple_lays_separate_dabs_inside_the_mask():
    cv = white_canvas(320, 320, texture="panel")
    before = lightness(cv.color)
    mask = disk(cv.shape, 160, 160, 110)
    cv.stipple(mask, ["vermilion", "ultramarine"], density=0.35, size=8)
    painted = before - lightness(cv.color) > 0.1
    _, n = label(painted)
    assert n > 80
    assert not painted[~binary_dilation(mask, iterations=8)].any()
    assert 0.15 < painted[mask].mean() < 0.65
    reds = painted & (cv.color[..., 0] > 2 * cv.color[..., 2])
    blues = painted & (cv.color[..., 2] > 2 * cv.color[..., 0])
    assert reds.sum() > 0.15 * painted.sum() and blues.sum() > 0.15 * painted.sum()


def stroke_orientation(ink):
    """Direction (degrees, counterclockwise on screen, 0..180) along which ink varies least, and coherence."""
    gy, gx = np.gradient(gaussian_filter(ink, 1.5))
    jxx, jyy, jxy = (gx * gx).mean(), (gy * gy).mean(), (gx * gy).mean()
    evals, evecs = np.linalg.eigh(np.array([[jxx, jxy], [jxy, jyy]]))
    vx, vy = evecs[:, 0]
    return np.degrees(np.arctan2(-vy, vx)) % 180, (evals[1] - evals[0]) / (evals[1] + evals[0])


def test_hatch_follows_its_angle_and_stays_in_the_mask():
    cv = white_canvas(320, 320, texture="panel")
    before = lightness(cv.color)
    mask = np.zeros(cv.shape, bool)
    mask[:, :200] = True
    cv.hatch(mask, "ivory_black", angle=30, spacing=10)
    ink = before - lightness(cv.color)
    angle, coherence = stroke_orientation(ink[20:300, 20:180])
    assert abs(angle - 30) < 8
    assert (ink[20:300, 20:180] > 0.1).mean() > 0.2
    assert (ink[:, 212:] > 0.1).mean() < 0.01

    crossed = white_canvas(320, 320, texture="panel")
    crossed.hatch(mask, "ivory_black", angle=30, spacing=10, cross=True)
    _, coherence2 = stroke_orientation((before - lightness(crossed.color))[20:300, 20:180])
    assert coherence2 < 0.6 * coherence


def test_techniques_are_deterministic():
    def paint(seed):
        cv = white_canvas(300, 240, seed=seed)
        m = disk(cv.shape, 150, 120, 90)
        cv.impasto(line(40, 260, 60), "vermilion")
        cv.knife(line(40, 260, 120), "lead_white", width=30)
        cv.knife(line(60, 240, 60), None, width=20)
        cv.wet_in_wet(m, strength=0.3, angle=20)
        cv.dry()
        cv.glaze(m, "madder_lake", strength=0.2)
        cv.scumble(m, "naples_yellow", coverage=0.3)
        cv.stipple(m, "cobalt_blue", density=0.2, size=6)
        cv.hatch(m, "burnt_umber", angle=60, spacing=12)
        return cv
    a, b, c = paint(5), paint(5), paint(6)
    for field in ("color", "height", "wet"):
        assert getattr(a, field).tobytes() == getattr(b, field).tobytes()
    assert a.color.tobytes() != c.color.tobytes()


def test_masks_must_match_the_canvas():
    cv = white_canvas(100, 80)
    with pytest.raises(ValueError):
        cv.glaze(np.ones((10, 10)), "ultramarine")


def test_spatter_scatters_specks_of_many_sizes_at_random_inside_the_mask():
    cv = white_canvas(400, 320, texture="panel")
    before = lightness(cv.color)
    mask = disk(cv.shape, 200, 160, 120)
    n = cv.spatter(mask, "ivory_black", density=0.12, size=6)
    ink = before - lightness(cv.color) > 0.15
    labels, k = label(ink)
    assert n > 60 and k > 0.5 * n
    assert not ink[~binary_dilation(mask, iterations=10)].any()
    assert 0.07 < ink[mask].mean() < 0.2
    areas = np.bincount(labels.ravel())[1:]
    assert np.percentile(areas, 90) > 3 * np.percentile(areas, 25)     # many small specks and a few large

    denser = white_canvas(400, 320, texture="panel")
    denser.spatter(mask, "ivory_black", density=0.24, size=6)
    assert (before - lightness(denser.color) > 0.15)[mask].mean() > 1.5 * ink[mask].mean()


def test_spatter_streaks_lie_along_the_field_and_are_deterministic():
    from atelier import fields

    def flick(seed, stretch, field):
        cv = white_canvas(360, 360, seed=seed, texture="panel")
        before = lightness(cv.color)
        cv.spatter(None, "ivory_black", density=0.1, size=4, stretch=stretch, field=field)
        return cv, before - lightness(cv.color)

    cv, ink = flick(2, 5, fields.constant(30))
    angle, coherence = stroke_orientation(ink[20:340, 20:340])
    assert abs(angle - 150) < 10          # fields count y-down: 30 falls to the right, i.e. 150 counterclockwise
    assert coherence > 0.3
    _, round_ink = flick(2, 1, None)
    assert stroke_orientation(round_ink[20:340, 20:340])[1] < 0.5 * coherence
    assert cv.height.max() > 0.1

    again, _ = flick(2, 5, fields.constant(30))
    other, _ = flick(3, 5, fields.constant(30))
    assert again.color.tobytes() == cv.color.tobytes() and again.height.tobytes() == cv.height.tobytes()
    assert other.color.tobytes() != cv.color.tobytes()


def test_broken_spatter_lands_dry_and_catches_the_tooth():
    def flecks(broken):
        cv = white_canvas(360, 300, seed=4, texture="linen")
        before = lightness(cv.color)
        cv.spatter(disk(cv.shape, 180, 150, 120), "ivory_black", density=0.15, size=7, broken=broken)
        return cv, before - lightness(cv.color)

    _, wet = flecks(0.0)
    cv, dry = flecks(1.0)
    assert (dry > 0.15).mean() < 0.7 * (wet > 0.15).mean()
    touched = dry > 0.02
    assert np.corrcoef(dry[touched], cv.tooth[touched])[0, 1] > 0.1
