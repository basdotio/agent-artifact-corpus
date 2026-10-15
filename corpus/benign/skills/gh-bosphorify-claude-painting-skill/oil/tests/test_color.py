import numpy as np
import pytest

from atelier.color import hex_to_linear, linear_to_srgb, mix, srgb_to_linear

# Reference values computed with spectral.js 3.0.0 (npm), Color.toString({method: "clip"}).
# lrgb is Color.lRGB before clipping, given only for in-gamut results.
GOLDEN = [
    ("blue+yellow", [("#002185", 0.5), ("#FCD200", 0.5)], "#3D933E",
     [0.04622632175482532, 0.29326502288048867, 0.048295919859479536]),
    ("red+white", [("#FF0000", 1), ("#FFFFFF", 1)], "#FF424A", None),
    ("black+white", [("#000000", 1), ("#FFFFFF", 1)], "#A6A6A6",
     [0.3817807148376565, 0.3820593923390354, 0.38158652409142685]),
    ("same color", [("#3375DA", 1), ("#3375DA", 1)], "#3375DA",
     [0.0331047665708844, 0.1778884159836291, 0.7011018919329742]),
    ("t=0", [("#E53166", 1), ("#3375DA", 0)], "#E53166",
     [0.7835377915261926, 0.030713443732993822, 0.1328683215538181]),
    ("t=1", [("#E53166", 0), ("#3375DA", 1)], "#3375DA",
     [0.0331047665708844, 0.1778884159836291, 0.7011018919329742]),
    ("three colors", [("#FCF046", 1), ("#E53166", 1), ("#3375DA", 1)], "#8D7964",
     [0.2648821202128091, 0.18954443099527088, 0.12726297630077618]),
    ("weighted 3:1", [("#002185", 3), ("#FCD200", 1)], "#005348", None),
]


def hex_to_srgb255(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)


def test_srgb_linear_known_values():
    assert srgb_to_linear(0.5) == pytest.approx(0.21404114, abs=1e-7)
    assert linear_to_srgb(0.21404114) == pytest.approx(0.5, abs=1e-6)
    assert srgb_to_linear(0.02) == pytest.approx(0.02 / 12.92)


def test_srgb_linear_round_trip():
    x = np.linspace(0, 1, 257)
    np.testing.assert_allclose(linear_to_srgb(srgb_to_linear(x)), x, atol=1e-9)


@pytest.mark.parametrize("name,pairs,expected,lrgb", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_mix_matches_spectral_js(name, pairs, expected, lrgb):
    out = mix(*[(hex_to_linear(h), w) for h, w in pairs])
    srgb255 = linear_to_srgb(out) * 255
    np.testing.assert_allclose(srgb255, hex_to_srgb255(expected), atol=1.0)
    if lrgb is not None:
        np.testing.assert_allclose(out, lrgb, atol=1e-9)


def test_mix_tinting_strength():
    # spectral.js: red.tintingStrength = 0.35; mix([red, .5], [yellow, .5]) -> clip "#FF831E"
    out = mix((hex_to_linear("#FF0000"), 0.5, 0.35), (hex_to_linear("#FFFF00"), 0.5))
    np.testing.assert_allclose(linear_to_srgb(out) * 255, hex_to_srgb255("#FF831E"), atol=1.0)


def test_mix_is_vectorized_over_arrays():
    a = np.broadcast_to(hex_to_linear("#002185"), (4, 5, 3))
    b = np.broadcast_to(hex_to_linear("#FCD200"), (4, 5, 3))
    t = np.linspace(0, 1, 20).reshape(4, 5)
    out = mix((a, 1 - t), (b, t))
    assert out.shape == (4, 5, 3)
    np.testing.assert_allclose(out[1, 2], mix((a[0, 0], 1 - t[1, 2]), (b[0, 0], t[1, 2])), atol=1e-12)
    np.testing.assert_allclose(out[0, 0], hex_to_linear("#002185"), atol=2e-3)


def test_lightness():
    from atelier.color import lightness
    assert lightness([1, 1, 1]) == pytest.approx(1.0)
    assert lightness([0, 0, 0]) == pytest.approx(0.0)
    assert lightness(srgb_to_linear([0.4663] * 3)) == pytest.approx(0.5, abs=1e-3)
