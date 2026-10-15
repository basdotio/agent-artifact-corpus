import numpy as np
import pytest

from atelier import Canvas
from atelier.canvas import TEXTURES
from atelier.pigments import PIGMENTS


def luminance(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def test_canvas_data_model():
    cv = Canvas(64, 48, seed=1)
    assert cv.shape == (48, 64)
    assert isinstance(cv.rng, np.random.Generator)
    assert cv.color.shape == (48, 64, 3) and cv.color.dtype == np.float32
    for field in (cv.height, cv.wet, cv.tooth):
        assert field.shape == (48, 64) and field.dtype == np.float32
    assert not cv.height.any() and not cv.wet.any()


def test_same_seed_ground_is_byte_identical():
    a, b = Canvas(320, 240, seed=7), Canvas(320, 240, seed=7)
    a.ground("raw_umber", texture="linen", tone=0.35)
    b.ground("raw_umber", texture="linen", tone=0.35)
    assert a.to_srgb_uint8().tobytes() == b.to_srgb_uint8().tobytes()
    assert a.color.tobytes() == b.color.tobytes()
    assert a.tooth.tobytes() == b.tooth.tobytes()
    c = Canvas(320, 240, seed=8)
    c.ground("raw_umber", texture="linen", tone=0.35)
    assert c.to_srgb_uint8().tobytes() != a.to_srgb_uint8().tobytes()


@pytest.mark.parametrize("texture", TEXTURES)
def test_textures_fill_tooth(texture):
    cv = Canvas(256, 192, seed=3)
    cv.ground("yellow_ochre", texture=texture, tone=0.3)
    assert cv.tooth.min() >= 0 and cv.tooth.max() <= 1
    assert cv.tooth.std() > 0.01
    assert not cv.wet.any() and not cv.height.any()


def test_textures_are_distinct_and_panel_is_smoothest():
    tooth = {}
    for texture in TEXTURES:
        cv = Canvas(256, 192, seed=3)
        cv.ground("lead_white", texture=texture, tone=0.0)
        tooth[texture] = cv.tooth
    names = list(tooth)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert not np.allclose(tooth[a], tooth[b])
    assert tooth["panel"].std() < 0.5 * min(tooth[t].std() for t in ("linen", "cotton", "paper"))


def test_tone_moves_ground_from_gesso_to_pigment():
    lum = {}
    for tone in (0.0, 0.35, 1.0):
        cv = Canvas(200, 150, seed=2)
        cv.ground("burnt_sienna", texture="cotton", tone=tone)
        lum[tone] = luminance(cv.color).mean()
        if tone == 1.0:
            np.testing.assert_allclose(np.median(cv.color.reshape(-1, 3), axis=0),
                                       PIGMENTS["burnt_sienna"].linear, atol=0.03)
    assert lum[0.0] > 0.7
    assert lum[0.0] > lum[0.35] > lum[1.0]


def test_toned_ground_shows_the_weave():
    cv = Canvas(256, 192, seed=4)
    cv.ground("raw_umber", texture="linen", tone=0.4)
    assert np.corrcoef(cv.tooth.ravel(), luminance(cv.color).ravel())[0, 1] > 0.2


def test_unknown_texture():
    with pytest.raises(ValueError):
        Canvas(32, 32).ground("raw_umber", texture="velvet")


def test_dry_clears_wetness():
    cv = Canvas(32, 32)
    cv.wet[:] = 0.8
    cv.dry()
    assert not cv.wet.any()


def test_to_srgb_uint8():
    cv = Canvas(8, 4)
    cv.color[:] = 0.21404114
    cv.color[0, 0] = (-0.5, 1.5, 0.0)
    out = cv.to_srgb_uint8()
    assert out.shape == (4, 8, 3) and out.dtype == np.uint8
    assert (out[1:] == 128).all()
    assert out[0, 0].tolist() == [0, 255, 0]


def test_tone_is_linear_in_lightness():
    from atelier.color import lightness
    ends = {}
    for tone in (0.0, 0.5, 1.0):
        cv = Canvas(200, 150, seed=2)
        cv.ground("burnt_umber", texture="panel", tone=tone)
        ends[tone] = np.median(lightness(cv.color))
    assert ends[0.5] == pytest.approx((ends[0.0] + ends[1.0]) / 2, abs=0.04)
