#!/usr/bin/env python3
"""
Pull frames by index from a video and tile them into a labelled contact sheet.

  run.sh frames.py VIDEO OUT_DIR FRAME... [--cols 4] [--width 480]

FRAME is an index (240) or a range START:END[:STEP] (780:820:2 = every 2nd frame, END excluded).
Writes OUT_DIR/fNNNN.png at full size and OUT_DIR/sheet.png. Frames are picked with select=eq(n,N),
so indices are exact decoded frames, never a seek to the nearest keyframe.
"""

import argparse
import math
from pathlib import Path

from common import FONTS_DIR, run


def parse(specs):
    out = []
    for s in specs:
        if ":" in s:
            a, b, *step = (int(v) for v in s.split(":"))
            out += range(a, b, step[0] if step else 1)
        else:
            out.append(int(s))
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("frames", nargs="+")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--width", type=int, default=480, help="tile width in the sheet")
    a = ap.parse_args()

    frames = parse(a.frames)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pick = "select='" + "+".join(f"eq(n\\,{f})" for f in frames) + "'"
    tmp = out / "pick_%04d.png"
    run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf", pick, "-fps_mode", "passthrough", str(tmp)])
    for i, f in enumerate(frames):
        (out / f"pick_{i + 1:04d}.png").replace(out / f"f{f:04d}.png")

    font = str(FONTS_DIR / "PlusJakartaSans-700.ttf").replace(":", "\\:")
    cols = min(a.cols, len(frames))
    rows = math.ceil(len(frames) / cols)
    label = f"drawtext=fontfile='{font}':text='f%{{n}}':x=12:y=12:fontsize=h/20:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=6"
    run(["ffmpeg", "-v", "error", "-y", "-i", a.video,
         "-vf", f"{label},{pick},scale={a.width}:-2,tile={cols}x{rows}:padding=4:color=white",
         "-frames:v", "1", str(out / "sheet.png")])
    print(f"{len(frames)} frames -> {out / 'sheet.png'}")


if __name__ == "__main__":
    main()
