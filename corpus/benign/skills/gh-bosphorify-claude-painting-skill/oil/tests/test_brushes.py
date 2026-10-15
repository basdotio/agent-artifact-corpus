import json

import pytest

from atelier import brush
from atelier.brushes import DEFAULTS, PRESET_DIR, SHAPES, Brush, preset_names, validate

STARTER = ["round_soft", "round_bristle", "flat_bristle", "filbert", "fan", "rigger",
           "dry_bristle", "palette_knife", "glaze_wide"]


def test_starter_presets_exist_and_validate():
    assert set(STARTER) <= set(preset_names())
    for name in STARTER:
        b = brush(name)
        assert isinstance(b, Brush)
        assert b.name == name and b.shape in SHAPES
        raw = json.loads((PRESET_DIR / f"{name}.json").read_text())
        assert set(raw) <= set(DEFAULTS)


def test_size_scales_width_and_overrides_apply():
    base = brush("round_bristle")
    big = brush("round_bristle", size=2.0, opacity=0.5)
    assert big.width_px == pytest.approx(2 * base.width_px)
    assert big.opacity == 0.5
    assert base.opacity != 0.5


def test_missing_fields_get_defaults():
    b = validate({"name": "tiny", "shape": "round", "width_px": 5})
    for field, value in DEFAULTS.items():
        if field not in ("name", "shape", "width_px"):
            assert getattr(b, field) == value


@pytest.mark.parametrize("bad", [
    {"shape": "sponge"},
    {"width_px": 0},
    {"opacity": 1.5},
    {"bristles": -1},
    {"bristles": 2.5},
    {"depletion": -0.1},
    {"colour": 1},
])
def test_validation_rejects_bad_fields(bad):
    with pytest.raises(ValueError):
        validate({"name": "x", "shape": "round", "width_px": 10, **bad})


def test_unknown_preset():
    with pytest.raises(KeyError):
        brush("toothbrush")
