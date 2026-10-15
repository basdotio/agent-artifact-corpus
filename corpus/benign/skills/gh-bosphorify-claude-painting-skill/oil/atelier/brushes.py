"""Brush presets: a JSON schema with validation and defaults, and brush(name, size, **overrides).

Fields (units in brackets):
    name, shape      round | flat | filbert | fan | rigger | knife
    width_px         mark width at full pressure [px]
    bristles         bristle clumps across the width; 0 = solid (knife, sponge)
    bristle_jitter   irregularity of bristle spacing, thickness, load and length [0..1]
    load             paint on the brush at the start of a stroke [1 = well loaded]
    depletion        fraction of the load laid down per px of travel at full pressure
    dry_threshold    load below which a bristle starts to skip and catch only the tooth [0..1]
    opacity          hiding power of the deposit [0..1]
    impasto          paint thickness added to the height field [~0..1]
    pickup           how much wet paint the brush lifts and drags along [0..1]
    edge_softness    fraction of the half-width over which the edge fades [0..1]
    taper_start/end  length of the width taper at each end [brush widths]
    color_jitter     per-bristle color variation (unevenly mixed paint) [0..1]
    wobble           hand wobble of the path [fraction of width]
"""

import json
from dataclasses import dataclass, fields, replace
from pathlib import Path

PRESET_DIR = Path(__file__).resolve().parent / "presets"
SHAPES = ("round", "flat", "filbert", "fan", "rigger", "knife")
DEFAULTS = {
    "name": "custom", "shape": "round", "width_px": 16.0, "bristles": 24, "bristle_jitter": 0.35,
    "load": 1.0, "depletion": 0.004, "dry_threshold": 0.35, "opacity": 0.95, "impasto": 0.2,
    "pickup": 0.3, "edge_softness": 0.25, "taper_start": 0.8, "taper_end": 1.2, "color_jitter": 0.03,
    "wobble": 0.04,
}
UNIT_FIELDS = ("bristle_jitter", "dry_threshold", "opacity", "pickup", "edge_softness", "color_jitter", "wobble")


@dataclass(frozen=True)
class Brush:
    name: str
    shape: str
    width_px: float
    bristles: int
    bristle_jitter: float
    load: float
    depletion: float
    dry_threshold: float
    opacity: float
    impasto: float
    pickup: float
    edge_softness: float
    taper_start: float
    taper_end: float
    color_jitter: float
    wobble: float


def validate(raw):
    """Fill defaults and check a preset dict. Returns a Brush; raises ValueError on bad fields."""
    unknown = set(raw) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown brush fields {sorted(unknown)}; known: {', '.join(DEFAULTS)}")
    b = {**DEFAULTS, **raw}
    if b["shape"] not in SHAPES:
        raise ValueError(f"shape {b['shape']!r} not in {SHAPES}")
    if not isinstance(b["bristles"], int) or isinstance(b["bristles"], bool) or b["bristles"] < 0:
        raise ValueError(f"bristles must be a non-negative integer, got {b['bristles']!r}")
    for f in fields(Brush):
        if f.name in ("name", "shape", "bristles"):
            continue
        v = b[f.name]
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
            raise ValueError(f"{f.name} must be a non-negative number, got {v!r}")
        if f.name in UNIT_FIELDS and v > 1:
            raise ValueError(f"{f.name} must be in [0, 1], got {v!r}")
        b[f.name] = float(v)
    if b["width_px"] <= 0:
        raise ValueError("width_px must be positive")
    return Brush(**b)


def preset_names():
    return sorted(p.stem for p in PRESET_DIR.glob("*.json"))


def brush(name, size=1.0, **overrides):
    """Load preset `name` from presets/*.json, scale it by `size` and apply field overrides.

    A bigger brush holds more paint, so depletion per px falls as the size grows.
    """
    path = PRESET_DIR / f"{name}.json"
    if not path.exists():
        raise KeyError(f"unknown brush {name!r}; presets: {', '.join(preset_names())}")
    b = validate(json.loads(path.read_text()))
    b = replace(b, width_px=b.width_px * size, depletion=b.depletion / size)
    return validate({**b.__dict__, **overrides}) if overrides else b
