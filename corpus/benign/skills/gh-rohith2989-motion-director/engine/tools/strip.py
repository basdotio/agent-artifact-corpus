"""Transition strips: frames every `step` seconds through each window of a video, tiled per window.
Every transition gets inspected this way before a final render (motion problems hide between seconds).

python tools/strip.py renders/preview.mkv out_prefix 4.2:5.8 12.9:13.7 [--step 0.2] [--fps 60] [--cols 5]
"""
import glob
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import ffmpeg  # noqa: E402
from sheet import grid  # noqa: E402


def main():
    a = sys.argv[1:]
    video, prefix = a[0], a[1]
    step = float(a[a.index("--step") + 1]) if "--step" in a else 0.2
    fps = float(a[a.index("--fps") + 1]) if "--fps" in a else 60.0
    cols = int(a[a.index("--cols") + 1]) if "--cols" in a else 5
    spans = [x for x in a[2:] if ":" in x and not x.startswith("--")]
    for sp in spans:
        t0, t1 = map(float, sp.split(":"))
        f0, f1, k = round(t0 * fps), round(t1 * fps), max(1, round(step * fps))
        tmp = tempfile.mkdtemp()
        sel = f"between(n\,{f0}\,{f1})*not(mod(n-{f0}\,{k}))"
        subprocess.run([ffmpeg(), "-v", "error", "-i", video, "-vf", f"select='{sel}',scale=480:-2", "-fps_mode", "passthrough", os.path.join(tmp, "s%03d.png")], check=True)
        fs = sorted(glob.glob(os.path.join(tmp, "s*.png")))
        labels = [f"{t0 + i * step:.2f}s" for i in range(len(fs))]
        grid(f"{prefix}_{t0:06.2f}.png", cols, 1.0, fs, labels)


if __name__ == "__main__":
    main()
