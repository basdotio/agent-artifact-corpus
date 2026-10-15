import colorsys

import numpy as np
import pytest

from atelier import Palette
from atelier.color import hex_to_linear, linear_to_srgb, mix
from atelier.pigments import PIGMENTS, color_of


def hue_degrees(linear_rgb):
    h, _, _ = colorsys.rgb_to_hsv(*linear_to_srgb(linear_rgb))
    return h * 360


def test_pigment_table():
    assert 18 <= len(PIGMENTS) <= 26
    for name, p in PIGMENTS.items():
        assert p.name == name
        assert p.hex.startswith("#") and len(p.hex) == 7
        assert p.note and "\n" not in p.note
        np.testing.assert_allclose(p.linear, hex_to_linear(p.hex))
    for needed in ["lead_white", "yellow_ochre", "vermilion", "ultramarine", "burnt_umber",
                   "ivory_black", "raw_umber", "cadmium_yellow"]:
        assert needed in PIGMENTS


def test_palette_lookup_is_limited_to_its_pigments():
    pal = Palette(["lead_white", "ultramarine"])
    np.testing.assert_allclose(pal["ultramarine"], PIGMENTS["ultramarine"].linear)
    with pytest.raises(KeyError):
        pal["vermilion"]
    with pytest.raises(KeyError):
        Palette(["lead_white", "unobtainium"])


def test_palette_mix_uses_spectral_mixing():
    pal = Palette(["lead_white", "ultramarine", "yellow_ochre"])
    sky = pal.mix(("lead_white", 3), ("ultramarine", 1), ("yellow_ochre", 0.3))
    expected = mix((PIGMENTS["lead_white"].linear, 3), (PIGMENTS["ultramarine"].linear, 1),
                   (PIGMENTS["yellow_ochre"].linear, 0.3))
    np.testing.assert_allclose(sky, expected)
    lighter = pal.mix((sky, 1), ("lead_white", 1))
    assert lighter.sum() > sky.sum()


@pytest.mark.parametrize("blue,yellow", [(1, 1), (2, 1)])
def test_ultramarine_and_cadmium_yellow_make_green(blue, yellow):
    pal = Palette(["ultramarine", "cadmium_yellow"])
    green = pal.mix(("ultramarine", blue), ("cadmium_yellow", yellow))
    assert 70 <= hue_degrees(green) <= 170


def test_color_of_accepts_names_hex_and_triples():
    np.testing.assert_allclose(color_of("vermilion"), PIGMENTS["vermilion"].linear)
    np.testing.assert_allclose(color_of("#808080"), hex_to_linear("#808080"))
    np.testing.assert_allclose(color_of((0.1, 0.2, 0.3)), [0.1, 0.2, 0.3])
    with pytest.raises(KeyError):
        color_of("unobtainium")
