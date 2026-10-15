import numpy as np
import pytest
from PIL import Image
from scipy.ndimage import gaussian_filter, label

from atelier import Canvas, brush, studio
from atelier.color import lightness, linear_to_srgb, srgb_to_linear


def bump_canvas(pigment="lead_white", seed=4):
    cv = Canvas(200, 200, seed=seed)
    cv.ground(pigment, texture="panel", tone=0.6)
    yy, xx = np.mgrid[:200, :200]
    cv.height[:] = 2.0 * np.exp(-((xx - 100) ** 2 + (yy - 100) ** 2) / (2 * 10.0 ** 2))
    return cv


def value(img):
    return lightness(srgb_to_linear(np.asarray(img, float) / 255))


def test_finish_is_deterministic_and_leaves_the_canvas_alone():
    def painted():
        cv = Canvas(260, 200, seed=9)
        cv.ground("raw_umber", texture="linen", tone=0.3)
        cv.stroke(brush("flat_bristle"), [[20, 60], [240, 80]], "lead_white")
        cv.impasto([[20, 130], [240, 140]], "vermilion")
        return cv

    cv = painted()
    state = [a.copy() for a in (cv.color, cv.height, cv.wet, cv.tooth)]
    rng_state = cv.rng.bit_generator.state
    a = cv.finish(crackle=0.5)
    b = cv.finish(crackle=0.5)
    assert a.shape == (200, 260, 3) and a.dtype == np.uint8
    assert a.tobytes() == b.tobytes()
    assert painted().finish(crackle=0.5).tobytes() == a.tobytes()
    for before, after in zip(state, (cv.color, cv.height, cv.wet, cv.tooth)):
        np.testing.assert_array_equal(before, after)
    assert cv.rng.bit_generator.state == rng_state


def test_raking_light_models_the_relief_and_leaves_flat_paint_alone():
    cv = bump_canvas()
    lit = value(cv.finish(light=(-0.5, -0.6), varnish=0, weave=0))
    upper_left, lower_right = lit[88:96, 88:96].mean(), lit[104:112, 104:112].mean()
    assert upper_left > lower_right + 0.15
    flip = value(cv.finish(light=(0.5, 0.6), varnish=0, weave=0))
    assert flip[88:96, 88:96].mean() < flip[104:112, 104:112].mean() - 0.15
    flat = np.abs(lit[:30, :30] - value(cv.to_srgb_uint8())[:30, :30])
    assert flat.max() < 0.02


def test_gloss_puts_highlights_on_the_relief():
    cv = bump_canvas("ultramarine")
    base = value(cv.to_srgb_uint8())[:30, :30].mean()
    glossy = value(cv.finish(varnish=0.8, weave=0))
    assert glossy[60:140, 60:140].max() > base + 0.15


def test_weave_shows_through_thin_paint_but_not_through_thick():
    cv = Canvas(240, 120, seed=2)
    cv.ground("yellow_ochre", texture="linen", tone=0.5)
    cv.height[:, 120:] = 1.5
    plain = value(cv.finish(weave=0.0, varnish=0))
    woven = value(cv.finish(weave=0.8, varnish=0))
    thin, thick = (woven - plain)[10:110, 10:110], (woven - plain)[10:110, 130:230]
    assert thin.std() > 0.02
    assert thick.std() < 0.5 * thin.std()


def test_varnish_warms_and_crackle_draws_a_connected_network():
    cv = Canvas(400, 300, seed=6)
    cv.ground("lead_white", texture="panel", tone=0.0)
    clean = cv.finish(varnish=0, weave=0).astype(float)
    aged = cv.finish(varnish=0.8, weave=0).astype(float)
    assert (aged[..., 0] - aged[..., 2]).mean() > (clean[..., 0] - clean[..., 2]).mean() + 10
    cracked = cv.finish(varnish=0, weave=0, crackle=0.7)
    dark = value(clean) - value(cracked) > 0.1
    assert 0.01 < dark.mean() < 0.2
    labels, n = label(dark, structure=np.ones((3, 3)))
    biggest = np.bincount(labels.ravel())[1:].argmax() + 1
    xs = np.nonzero(labels == biggest)[1]
    assert np.ptp(xs) > 0.5 * cv.shape[1]
    assert cv.finish(varnish=0, weave=0, crackle=0).tobytes() == clean.astype(np.uint8).tobytes()


def test_crackle_grows_steadily_with_its_amount():
    cv = Canvas(400, 300, seed=6)
    cv.ground("lead_white", texture="panel", tone=0.0)
    clean = value(cv.finish(varnish=0, weave=0))
    dark = [(clean - value(cv.finish(varnish=0, weave=0, crackle=a))).mean() for a in (0.05, 0.1, 0.2, 0.4, 0.7, 1.0)]
    assert dark[0] > 0
    assert all(later > earlier for earlier, later in zip(dark, dark[1:])), dark
    assert dark[1] < 0.25 * dark[4], dark          # 0.1 is a hint of age, not most of 0.7


def test_scale_makes_a_study_as_embossed_as_the_final():
    def strokes(W):
        S, H = W / 2048, W * 3 // 4
        cv = Canvas(W, H, seed=4)
        cv.ground("raw_umber", texture="panel", tone=0.3)
        rng = np.random.default_rng(1)
        for _ in range(260):
            p0, a = rng.uniform((0, 0), (W, H)), rng.uniform(0, np.pi)
            d = np.array([np.cos(a), np.sin(a)]) * rng.uniform(60, 200) * S
            cv.stroke(brush("flat_bristle", size=rng.uniform(0.8, 2.0) * S, load=1.4), [p0, p0 + d / 2, p0 + d], "lead_white")
        return cv, S

    def relief(cv, size, **kw):
        """Mean lightness change from the relief, seen at `size` px wide like a viewer comparing the two."""
        seen = lambda a: np.asarray(Image.fromarray(a).resize(size, Image.LANCZOS))
        return np.abs(value(seen(cv.finish(varnish=0, weave=0, **kw))) - value(seen(cv.to_srgb_uint8()))).mean()

    study, s = strokes(512)
    final, f = strokes(1024)
    assert relief(study, (512, 384)) > 1.3 * relief(final, (512, 384))                   # relief in pixels
    assert 0.8 < relief(study, (512, 384), scale=s) / relief(final, (512, 384), scale=f) < 1.25


def finish_before_patina(cv, light=(-0.5, -0.6), varnish=0.2, weave=0.3, scale=1.0):
    """finish() as it was before crackle was redone and grime, edge and support came in (crackle 0)."""
    def unit(v):
        v = np.asarray(v, np.float64)
        if len(v) == 2:
            v = np.append(v, np.sqrt(max(1 - v @ v, 0.04)))
        return v / np.linalg.norm(v)

    h = cv.height.astype(np.float32)
    z = 3.0 * np.sqrt(scale) * gaussian_filter(h, 0.6) + weave * 2.5 * cv.tooth * np.exp(-h / 0.35)
    color = cv.color.astype(np.float32)
    lx, ly, lz = unit(light)
    gy, gx = np.gradient(z)
    lamp = np.clip((lz - gx * lx - gy * ly) / np.sqrt(gx * gx + gy * gy + 1), 0, None) / lz
    shade = 0.3 + 0.7 * lamp
    cavity = np.clip(1 + 0.12 * (z - gaussian_filter(z, 3.0)), 0.75, 1.05)
    hx, hy, hz = unit((lx, ly, lz + 1))
    zs = gaussian_filter(z, 0.4 + 1.5 * varnish)
    sy, sx = np.gradient(zs)
    ndoth = np.clip((hz - sx * hx - sy * hy) / np.sqrt(sx * sx + sy * sy + 1), 0, 1)
    gloss = 0.18 * np.clip(h / 0.2, 0, 1) + 0.35 * varnish
    spec = gloss * ndoth ** (30 + 90 * varnish)
    tint = np.array([1.0, 0.8, 0.5]) ** varnish
    color = color ** (1 + 0.2 * varnish) * tint
    out = color * (shade * cavity)[..., None] + spec[..., None] * (0.3 + 0.7 * tint)
    return np.round(linear_to_srgb(np.clip(out, 0, 1)) * 255).astype(np.uint8)


@pytest.mark.parametrize("texture, kw", [
    ("linen", {}),
    ("panel", dict(light=(0.3, -0.7), varnish=0.6, weave=0.1, scale=0.44)),
    ("cotton", dict(light=(-0.3, -0.2, 0.9), varnish=0.0, weave=0.8, scale=2.0)),
])
def test_finish_is_unchanged_at_the_defaults(texture, kw):
    cv = Canvas(240, 180, seed=5)
    cv.ground("raw_umber", texture=texture, tone=0.4)
    cv.stroke(brush("flat_bristle"), [[20, 50], [220, 70]], "lead_white")
    cv.impasto([[30, 120], [210, 130]], "vermilion")
    before = finish_before_patina(cv, **kw).tobytes()
    assert cv.finish(**kw).tobytes() == before
    assert cv.finish(crackle=0.0, grime=0.0, edge=0.0, support=None, **kw).tobytes() == before
    assert cv.finish(support="panel", **kw).tobytes() == before


def test_the_seed_fixes_the_grime_and_the_crack_network():
    def canvas(seed):
        cv = Canvas(300, 220, seed=seed)
        cv.ground("lead_white", texture="panel", tone=0.1)
        return cv

    aged = dict(varnish=0.3, weave=0, crackle=0.5, grime=0.4, edge=0.03)
    assert canvas(5).finish(**aged).tobytes() == canvas(5).finish(**aged).tobytes()
    nets = []
    for seed in (5, 6):
        cv = canvas(seed)
        nets.append(value(cv.finish(varnish=0, weave=0)) - value(cv.finish(varnish=0, weave=0, crackle=0.5)) > 0.05)
    assert nets[0].mean() > 0.01
    assert (nets[0] & nets[1]).sum() < 0.5 * nets[0].sum()


def test_craquelure_grows_smoothly_and_keeps_its_network():
    cv = Canvas(400, 300, seed=8)
    cv.ground("lead_white", texture="panel", tone=0.0)
    clean = value(cv.finish(varnish=0, weave=0))
    amounts = np.arange(1, 21) / 20
    cracked = [np.abs(value(cv.finish(varnish=0, weave=0, crackle=a)) - clean) > 0.03 for a in amounts]
    share = np.array([c.mean() for c in cracked])
    steps = np.diff(share)
    assert 0 < share[0] < 0.01                                     # at 0.05 a few hairlines
    assert (steps > 0).all(), share                                # grows at every step
    assert steps.max() < 2.5 * (share[-1] - share[0]) / len(steps), share   # with no jump
    kept = (cracked[5] & cracked[11]).sum() / cracked[5].sum()     # 0.3's cracks are still there at 0.6
    assert kept > 0.9


def test_a_paint_dab_only_moves_the_cracks_near_it():
    def render(dab):
        cv = Canvas(900, 600, seed=3)
        cv.ground("lead_white", texture="panel", tone=0.0)
        if dab:
            cv.height[80:120, 80:120] = 2.0                  # a 40 px dab of thick paint: islands under it stop splitting
        kw = dict(varnish=0, weave=0)
        cracked = cv.finish(crackle=0.5, **kw)
        return cracked, np.abs(value(cracked) - value(cv.finish(**kw))) > 0.05

    (plain_img, plain), (dabbed_img, dabbed) = render(False), render(True)
    dist = np.hypot(*(np.mgrid[:600, :900] - 100)) - 20      # px from the dab's edge
    far = dist > 300
    assert plain[far].sum() > 10_000
    assert (plain & dabbed)[far].sum() > 0.95 * (plain | dabbed)[far].sum()          # the same cracks out there
    assert np.abs(plain_img.astype(int) - dabbed_img)[far].max() <= 1                # down to the pixel
    assert (plain != dabbed)[dist < 60].sum() > 100                                  # and the dab did change its own


def test_panel_cracks_run_along_the_grain_and_canvas_cracks_have_no_direction():
    def grain(texture=None, support=None, size=(512, 512)):
        """Energy of the cracks' vertical gradients over the horizontal: > 1 for cracks running across x."""
        cv = Canvas(*size, seed=8)
        if texture:
            cv.ground("lead_white", texture=texture, tone=0.0)
        kw = dict(light=(-0.5, -0.5), varnish=0, weave=0)
        gy, gx = np.gradient(value(cv.finish(crackle=0.7, support=support, **kw)) - value(cv.finish(**kw)))
        return (gy ** 2).sum() / (gx ** 2).sum()

    assert grain("panel") > 1.8
    assert grain("panel", size=(384, 512)) < 1 / 1.8                # an upright panel's grain runs up it
    assert grain("panel", size=(512, 384)) > 1.8
    assert 0.8 < grain("linen") < 1.25
    assert 0.8 < grain() < 1.25                                    # no ground: canvas
    assert 0.8 < grain("panel", support="canvas") < 1.25
    assert grain("linen", support="panel") > 1.8


def test_thick_paint_cracks_wider_and_more_sparsely():
    cv = Canvas(600, 300, seed=3)
    cv.ground("lead_white", texture="linen", tone=0.0)
    cv.height[:, 300:] = 1.2
    crack = value(cv.finish(varnish=0, weave=0)) - value(cv.finish(varnish=0, weave=0, crackle=0.9)) > 0.08

    def spacing_and_width(m):
        crossings = (m[:, 1:] & ~m[:, :-1]).sum() + (m[1:] & ~m[:-1]).sum()
        return crossings / m.size, m.sum() / crossings

    (thin_n, thin_w), (thick_n, thick_w) = spacing_and_width(crack[:, 20:280]), spacing_and_width(crack[:, 320:580])
    assert thick_n < 0.75 * thin_n
    assert thick_w > 1.2 * thin_w


def test_grime_darkens_toward_the_edges_and_the_rebate_band_stays_cleaner():
    cv = Canvas(400, 300, seed=2)
    cv.ground("lead_white", texture="panel", tone=0.3)
    plain = value(cv.finish(varnish=0.5, weave=0))
    loss = plain - value(cv.finish(varnish=0.5, weave=0, grime=0.8))
    assert loss[:, :8].mean() > 2 * loss[140:160, 190:210].mean() > 0
    dirty = value(cv.finish(varnish=0.6, weave=0, grime=0.5))
    band = value(cv.finish(varnish=0.6, weave=0, grime=0.5, edge=0.05)) - dirty      # 15 px under the rebate
    assert band[:, 3:11].mean() > 0.02 and band[3:11, :].mean() > 0.02
    assert np.abs(band[40:260, 40:360]).max() == 0


def test_finish_names_its_supports():
    with pytest.raises(ValueError, match="support"):
        bump_canvas().finish(crackle=0.3, support="oak")


def test_studio_saves_a_finished_painting(tmp_path):
    cv = bump_canvas()
    img = cv.finish()
    final, review = studio.save(img, tmp_path / "final.png")
    np.testing.assert_array_equal(np.asarray(Image.open(final)), img)
    assert Image.open(review).size == (studio.SHEET_W, studio.SHEET_H)
