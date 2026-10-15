#!/usr/bin/env python3
"""
Render Remotion compositions from ~/OneTake/videogen/remotion (720p60).

  run.sh remotion.py explainer SCENES.json OUT.mp4 --words vo.words.json --duration SEC [--beats beats.json] [--theme theme.json] [--format vertical]
  run.sh remotion.py titlecard OUT.mov --title "..." [--subtitle "..."] [--seconds 4] [--center] [--format vertical]
  run.sh remotion.py illustrated OUT.mp4 [--comp Cell] [--concurrency 3] [--width 1920] [--procs 3 --frames N]

SCENES.json: [{"start", "end", "layout": "title|points|big|quote", "kicker", "title", "emoji",
               "points": [{"text", "at"}]}]   (seconds on the narration timeline)
--format vertical renders 720x1280 for TikTok, Reels and Shorts; the layout follows the frame.
Explainer renders silent video; add narration + music with mix.py.
Title cards render ProRes 4444 with alpha, to overlay on footage with mix.py --overlay.
Illustrated compositions are authored at 1920x1080 and rendered scaled to 720p60, muted; mix audio with mix.py.
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

from common import REMOTION_DIR, TARGET_W, load_json, run, save_json

ILLUSTRATED_W = 1920
FORMATS = ["landscape", "vertical"]


def snap_to_beats(scenes, beats, window=0.3):
    """Move scene boundaries onto the nearest beat (within `window` s) so cuts land on the music."""
    if not beats:
        return scenes
    import bisect
    def snap(t):
        i = bisect.bisect_left(beats, t)
        near = min((b for b in beats[max(0, i - 1):i + 1]), key=lambda b: abs(b - t), default=t)
        return near if abs(near - t) <= window else t
    out = [dict(s) for s in scenes]
    for a, b in zip(out, out[1:]):
        t = snap(b["start"])
        a["end"] = b["start"] = round(t, 3)
    return out


def explainer_props(scenes, words, duration, beats=None, theme=None, captions=True, fmt="landscape"):
    """Input props of the Explainer composition from the job's files (paths), as it will render."""
    beats = load_json(beats) if beats else {"bpm": 0, "beat_offset": 0, "beats": []}
    scenes = snap_to_beats(load_json(scenes), beats["beats"])
    scenes[-1]["end"] = duration
    return {"duration": duration, "scenes": scenes,
            "words": [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in load_json(words)["words"]],
            "bpm": beats["bpm"], "beatOffset": beats.get("beat_offset", 0), "captions": captions, "format": fmt,
            **(load_json(theme) if theme else {})}


def render(comp, out, props, extra):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        props_path = f.name
    save_json(props, props_path)
    run(["npx", "remotion", "render", "src/index.ts", comp, str(Path(out).resolve()),
         f"--props={props_path}", "--log=error", *extra], cwd=REMOTION_DIR)
    Path(props_path).unlink(missing_ok=True)
    print(f"-> {out}")


def render_split(comp, out, extra, frames, procs):
    """Render `frames` frames as `procs` parallel processes over one bundle, then join the parts.
    Separate processes scale where --concurrency does not: each has its own browser and encoder."""
    out = Path(out).resolve()
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        tmp = Path(tmp)
        run(["npx", "remotion", "bundle", "src/index.ts", f"--out-dir={tmp / 'bundle'}", "--log=error"],
            cwd=REMOTION_DIR)
        step = -(-frames // procs)
        parts, jobs = [], []
        for n, first in enumerate(range(0, frames, step)):
            part = tmp / f"part-{n:02d}.mp4"
            parts.append(part)
            jobs.append(subprocess.Popen(
                ["npx", "remotion", "render", str(tmp / "bundle"), comp, str(part),
                 f"--frames={first}-{min(first + step, frames) - 1}", "--log=error", *extra],
                cwd=REMOTION_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True))
        errors = [j.communicate()[1][-3000:] for j in jobs]
        failed = [e for j, e in zip(jobs, errors) if j.returncode != 0]
        if failed:
            raise RuntimeError(f"{len(failed)} of {len(jobs)} render processes failed:\n{failed[0]}")
        listing = tmp / "parts.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in parts))
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", out])
    print(f"-> {out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("explainer")
    e.add_argument("scenes")
    e.add_argument("out")
    e.add_argument("--words", required=True)
    e.add_argument("--duration", type=float, required=True)
    e.add_argument("--beats")
    e.add_argument("--no-captions", action="store_true")
    e.add_argument("--theme", help='JSON with any of {"palette": [...], "ink", "paper", "accent"}')
    t = sub.add_parser("titlecard")
    t.add_argument("out")
    t.add_argument("--title", required=True)
    t.add_argument("--subtitle")
    t.add_argument("--seconds", type=float, default=4)
    t.add_argument("--accent", default="#FF5A5F")
    t.add_argument("--center", action="store_true")
    for p in (e, t):
        p.add_argument("--format", default="landscape", choices=FORMATS, help="vertical renders 720x1280")
    i = sub.add_parser("illustrated")
    i.add_argument("out")
    i.add_argument("--comp", default="Cell")
    i.add_argument("--concurrency", type=int, default=3)
    i.add_argument("--width", type=int, default=TARGET_W, help="output width; 1920 renders 1080p unscaled")
    i.add_argument("--procs", type=int, default=1, help="render as this many parallel processes (needs --frames)")
    i.add_argument("--frames", type=int, help="the composition's length in frames, for --procs")
    a = ap.parse_args()

    if a.cmd == "explainer":
        props = explainer_props(a.scenes, a.words, a.duration, a.beats, a.theme, not a.no_captions, a.format)
        render("Explainer", a.out, props, ["--muted", "--codec=h264", "--crf=18"])
    elif a.cmd == "illustrated":
        extra = ["--muted", "--codec=h264", "--crf=18", f"--scale={a.width / ILLUSTRATED_W}",
                 f"--concurrency={a.concurrency}"]
        if a.procs > 1:
            if not a.frames:
                ap.error("--procs needs --frames")
            render_split(a.comp, a.out, extra, a.frames, a.procs)
        else:
            render(a.comp, a.out, {}, extra)
    else:
        props = {"title": a.title, "subtitle": a.subtitle, "seconds": a.seconds, "accent": a.accent,
                 "position": "center" if a.center else "lower-third", "format": a.format}
        render("TitleCard", a.out, props,
               ["--codec=prores", "--prores-profile=4444", "--pixel-format=yuva444p10le", "--image-format=png"])


if __name__ == "__main__":
    main()
