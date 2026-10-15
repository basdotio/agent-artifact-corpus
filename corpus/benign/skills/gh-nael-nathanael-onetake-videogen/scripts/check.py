#!/usr/bin/env python3
"""
The gate before a generated video renders. Prints one line per problem and exits 1; prints nothing
when the video is clean.

  run.sh check.py explainer SCENES.json --words W --duration SEC [--beats B] [--theme T] [--no-captions]
                  [--format vertical] [--max-gap 1.2] [--stills DIR] [--texts]
  run.sh check.py illustrated --comp NAME --frames 120,480,... [--words W] [--max-gap 1.2]
                  [--stills DIR] [--texts]

Explainer, from the files alone: scenes run on from 0 without gaps, titles and points keep to their
word limits, every point pops inside its scene with time to be read, and no scene holds the same
picture for over 6 s. Then one settled frame per scene is rendered and its text is measured: nothing
cropped or inside the side margins, nothing in the caption band, every font loaded.

Illustrated: the same text measurement at the frames you name (the settled key frame of each beat).
Mark decoration that is meant to run off the frame with `data-bleed`.

--words adds the narration: it starts with the video, has no pause over --max-gap (raise it for a
scripted `[pause]`) and ends with it. --texts prints every on-screen string instead, to proofread.
--stills keeps the measured frames as DIR/fNNNN.jpg. Run it inside the same memory cap as a render.

The gate and what it looks for follow vincentfranstyo/video-gen-skill (kit/render.ts `check` and
`texts`, MIT; see LICENSES/video-gen-skill-MIT.txt).
"""

import argparse
import json
import tempfile
from pathlib import Path

from common import REMOTION_DIR, TARGET_FPS, load_json, run, save_json
from remotion import FORMATS, explainer_props

TITLE_WORDS, POINT_WORDS = 6, 5
# A scene is one idea of 3-6 s; past that the picture has to change (a new scene or a point).
MAX_HOLD = 6.0
# A point needs this long on screen before its scene leaves.
MIN_READ = 0.8
# Narration that starts later than this or stops earlier than this before the end is dead air.
MAX_LEAD, MAX_TAIL = 1.5, 2.0
# Frames before a scene's end where everything has arrived and the exit has not begun.
SETTLED = 20


def scene_problems(scenes):
    out = []
    if scenes[0]["start"] > 0.02:
        out.append(f"the first scene starts at {scenes[0]['start']:g} s: open on the hook at 0")
    for n, s in enumerate(scenes, 1):
        name = f'scene {n} "{s["title"]}"'
        if s["end"] <= s["start"]:
            out.append(f"{name} ends at {s['end']:g} s, before it starts")
            continue
        if n < len(scenes) and abs(scenes[n]["start"] - s["end"]) > 0.02:
            kind = "gap" if scenes[n]["start"] > s["end"] else "overlap"
            out.append(f"{abs(scenes[n]['start'] - s['end']):.2f} s {kind} between scene {n} and scene {n + 1}")
        if len(s["title"].split()) > TITLE_WORDS:
            out.append(f"{name}: the title has {len(s['title'].split())} words (max {TITLE_WORDS})")
        points = s.get("points") or []
        for p in points:
            if len(p["text"].split()) > POINT_WORDS:
                out.append(f'{name}: point "{p["text"]}" has {len(p["text"].split())} words (max {POINT_WORDS})')
            if not s["start"] <= p["at"] < s["end"]:
                out.append(f'{name}: point "{p["text"]}" pops at {p["at"]:g} s, outside the scene '
                           f"({s['start']:g}-{s['end']:g} s)")
            elif s["end"] - p["at"] < MIN_READ:
                out.append(f'{name}: point "{p["text"]}" pops {s["end"] - p["at"]:.1f} s before the scene ends, '
                           f"too short to read (min {MIN_READ} s)")
        events = [s["start"], *sorted(p["at"] for p in points if s["start"] < p["at"] < s["end"]), s["end"]]
        hold, at = max((b - a, a) for a, b in zip(events, events[1:]))
        if hold > MAX_HOLD:
            out.append(f"{name} holds the same picture for {hold:.1f} s from {at:g} s (max {MAX_HOLD:g}): "
                       "split it or add a point")
    return out


def narration_problems(words, duration, max_gap):
    if not words:
        return ["the words file has no words"]
    out = []
    if words[0]["start"] > MAX_LEAD:
        out.append(f"narration starts at {words[0]['start']:.1f} s (max {MAX_LEAD}): open on the hook")
    for a, b in zip(words, words[1:]):
        if b["start"] - a["end"] > max_gap:
            out.append(f'{b["start"] - a["end"]:.1f} s of dead air after "{a["text"]}" at {a["end"]:.1f} s '
                       f"(max {max_gap:g})")
    if duration - words[-1]["end"] > MAX_TAIL:
        out.append(f"{duration - words[-1]['end']:.1f} s of silence after the last word (max {MAX_TAIL:g}): "
                   "end on the payoff")
    return out


def layout_problems(reports, where=lambda frame: f"frame {frame}"):
    out, fonts = [], {}
    for r in reports:
        out += [f'{where(r["frame"])}: "{t}" is cropped or inside the side margins' for t in r["cropped"]]
        out += [f'{where(r["frame"])}: "{t}" runs into the caption band' for t in r["overCaptions"]]
        for family, sample in r["fallbackFonts"]:
            fonts.setdefault(family, sample)
    return out + [f'font "{family}" did not load, so a fallback is drawn (e.g. "{sample}")'
                  for family, sample in fonts.items()]


def measure(comp, frames, props=None, stills=None):
    """Render `frames` of `comp` with the layout report on; -> one report per frame."""
    with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
        save_json(props or {}, f.name)
        cmd = ["node", "layoutcheck.mjs", comp, ",".join(map(str, frames)), f"--props={f.name}"]
        if stills:
            cmd.append(f"--stills={Path(stills).resolve()}")
        lines = run(cmd, cwd=REMOTION_DIR).stdout.splitlines()
    return json.loads(next(x for x in reversed(lines) if x.startswith("LAYOUTCHECK "))[len("LAYOUTCHECK "):])


def settled_frames(scenes, fps=TARGET_FPS):
    return [max(round(s["start"] * fps) + 1, round(s["end"] * fps) - SETTLED) for s in scenes]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("explainer")
    e.add_argument("scenes")
    e.add_argument("--words", required=True)
    e.add_argument("--duration", type=float, required=True)
    e.add_argument("--beats")
    e.add_argument("--theme")
    e.add_argument("--no-captions", action="store_true")
    e.add_argument("--format", default="landscape", choices=FORMATS)
    i = sub.add_parser("illustrated")
    i.add_argument("--comp", required=True)
    i.add_argument("--frames", required=True, help="comma-separated frame numbers: each beat's settled key frame")
    i.add_argument("--words")
    for p in (e, i):
        p.add_argument("--max-gap", type=float, default=1.2, help="longest pause allowed inside the narration")
        p.add_argument("--stills", help="keep the measured frames here")
        p.add_argument("--texts", action="store_true", help="print every on-screen string and stop")
    a = ap.parse_args()

    found = []
    if a.cmd == "explainer":
        props = explainer_props(a.scenes, a.words, a.duration, a.beats, a.theme, not a.no_captions, a.format)
        scenes, words, duration = props["scenes"], props["words"], a.duration
        frames = settled_frames(scenes)
        found += scene_problems(scenes)
        label = {f: f'scene {n} "{s["title"]}"' for n, (f, s) in enumerate(zip(frames, scenes), 1)}
        reports = measure("Explainer", frames, props, a.stills)
        layout = layout_problems(reports, lambda frame: label[frame])
    else:
        words = load_json(a.words)["words"] if a.words else None
        reports = measure(a.comp, [int(f) for f in a.frames.split(",")], stills=a.stills)
        duration = None
        layout = layout_problems(reports)

    if a.texts:
        print("\n".join(dict.fromkeys(t for r in reports for t in r["texts"])))
        return
    if words is not None:
        # An illustrated scene has no duration argument: its narration is checked up to its last word.
        found += narration_problems(words, duration if duration is not None else words[-1]["end"], a.max_gap)
    found += layout
    if found:
        raise SystemExit("\n".join(found))


if __name__ == "__main__":
    main()
