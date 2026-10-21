"""Shared timing for the audio scripts: the same timeline.json that src/stage.js reads.

A time can be seconds (2.5), a grid position ({"beat": 8}, {"bar": 2, "plus": -0.1}), a timeline key ("tap"),
or a key with an offset ("tap+0.12", "end-0.3").
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
TL = json.load(open(os.path.join(ROOT, "timeline.json")))
BEAT = 60 / TL["bpm"]


def resolve(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        base = TL["firstBeat"] + (v["beat"] * BEAT if "beat" in v else v["bar"] * 4 * BEAT)
        return base + v.get("plus", 0)
    m = re.fullmatch(r"([A-Za-z_][\w]*)\s*([+-]\s*[\d.]+)?", str(v).strip())
    if not m:
        raise ValueError(f"bad time {v!r}")
    base = resolve(TL["T"][m.group(1)])
    return base + (float(m.group(2).replace(" ", "")) if m.group(2) else 0.0)


DUR = resolve(TL["T"].get("dur", TL["dur"]))
MUSIC_START = float(TL.get("musicStart", 0))
