"""Check rendered deliverables by decoding them: duration, colours, audio, loop seam.

    uv run --with numpy python3 scripts/verify.py videos/<film>/out/<name>/v3 \
        --duration 25 --bg 11,18,38 [--loop] [--probe 13.2:540,900=255,138,61] [--lufs -14]

For every .mp4 / .webm / .mov in the folder:
- duration matches (to one frame), size and fps are read from the file
- frame 0 at a background point (--bg-at x,y, default the top-left safe corner)
  decodes to --bg within --tol (default 3; colours are 11x11 patch means, so grain averages out): catches colour-range and matrix mistakes
  (a limited-range master read as full range lifts #0a0a0a to #171717)
- colour tags: BT.709 primaries, transfer and matrix (untagged files shift on phones)
- with --loop: the last frame against frame 0 is only encoder noise
- each probe (seconds:x,y[=r,g,b]) prints its decoded colour, and checks it
  within 12 when a colour is given (an accent, the one highlight)
- audio: present or not, integrated loudness (EBU R128) and true peak;
  fails above -1 dBTP, warns if loudness is more than 3 LU from --lufs
Exits non-zero when a check fails. Uses ffmpeg/ffprobe from PATH
(or HYPERFRAMES_FFMPEG_PATH / HYPERFRAMES_FFPROBE_PATH).
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

import numpy as np

FF = os.environ.get("HYPERFRAMES_FFMPEG_PATH", "ffmpeg")
FP = os.environ.get("HYPERFRAMES_FFPROBE_PATH", "ffprobe")


def probe(path):
    out = subprocess.run([FP, "-v", "error", "-show_streams", "-show_format", "-of", "json", path], capture_output=True, text=True).stdout
    return json.loads(out)


def frame(path, seconds, w, h):
    raw = subprocess.run(
        [FF, "-v", "error", "-ss", f"{max(0, seconds):.4f}", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True).stdout
    if len(raw) < w * h * 3:
        return None
    return np.frombuffer(raw[: w * h * 3], np.uint8).reshape(h, w, 3).astype(int)


def patch(img, x, y, r=5):
    """Mean colour of an 11x11 patch: film grain averages out, a real shift does not."""
    h, w = img.shape[:2]
    return img[max(0, y - r): min(h, y + r + 1), max(0, x - r): min(w, x + r + 1)].reshape(-1, 3).mean(axis=0).round().astype(int)


def last_frame(path, w, h):
    raw = subprocess.run([FF, "-v", "error", "-sseof", "-0.5", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    if n == 0:
        return None
    return np.frombuffer(raw[(n - 1) * w * h * 3: n * w * h * 3], np.uint8).reshape(h, w, 3).astype(int)


def loudness(path):
    err = subprocess.run([FF, "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    p = re.findall(r"Peak:\s+(-?[\d.inf]+) dBFS", err)
    return (float(i[-1]) if i else None), (float(p[-1]) if p and p[-1] != "-inf" else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--bg", required=True, help="r,g,b of the background token")
    ap.add_argument("--bg-at", default=None, help="x,y of a point that is background in frame 0")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--probe", action="append", default=[])
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--tol", type=int, default=3, help="background tolerance; raise it (10 to 16) for films with a vignette or grain overlay, or probe a point the vignette does not reach")
    a = ap.parse_args()

    bg = np.array([int(v) for v in a.bg.split(",")])
    files = sorted(sum((glob.glob(os.path.join(a.folder, e)) for e in ("*.mp4", "*.webm", "*.mov")), []))
    files = [f for f in files if not os.path.basename(f).startswith("_")]
    failed = False
    if not files:
        print("no video files found")
        sys.exit(1)
    for path in files:
        info = probe(path)
        if "streams" not in info or not any(s["codec_type"] == "video" for s in info["streams"]):
            print(f"{os.path.basename(path)}: unreadable (still being written?)")
            failed = True
            continue
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        aud = [s for s in info["streams"] if s["codec_type"] == "audio"]
        w, h = int(v["width"]), int(v["height"])
        num, den = (int(x) for x in v.get("avg_frame_rate", v["r_frame_rate"]).split("/"))
        fps = num / den if den else 0
        dur = float(info["format"]["duration"])
        name = os.path.basename(path)
        problems = []

        ok_dur = abs(dur - a.duration) <= 1.5 / max(fps, 1) + 0.03
        if not ok_dur:
            problems.append(f"duration {dur:.3f}s != {a.duration}s")
        tags = (v.get("color_primaries"), v.get("color_transfer"), v.get("color_space"))
        if name.endswith(".mp4") and tags != ("bt709", "bt709", "bt709"):
            problems.append(f"colour tags {tags} (want bt709)")

        f0 = frame(path, 0, w, h)
        bx, by = (int(x) for x in a.bg_at.split(",")) if a.bg_at else (min(80, w // 10), min(80, h // 10))
        got = patch(f0, bx, by) if f0 is not None else None
        if got is None or np.any(np.abs(got - bg) > a.tol):
            problems.append(f"background at {bx},{by} is {None if got is None else got.tolist()}, want {bg.tolist()} (colour range/matrix?)")

        seam = ""
        if a.loop:
            fl = last_frame(path, w, h)
            if fl is not None and f0 is not None:
                diff = np.abs(f0 - fl).max(axis=2)
                noisy = int((diff > 6).sum())
                seam = f" | seam {noisy}px>6 max {int(diff.max())}"
                if noisy > 0.002 * w * h:
                    problems.append("loop seam jumps (last frame != frame 0)")

        audio = "no audio"
        if aud:
            lufs, peak = loudness(path)
            audio = f"audio {aud[0]['codec_name']} {aud[0].get('sample_rate')}Hz {lufs} LUFS, peak {peak} dBFS"
            if peak is not None and peak > -1.0:
                problems.append(f"true peak {peak} dBFS > -1")
            if lufs is not None and abs(lufs - a.lufs) > 3:
                audio += f" (target {a.lufs}: adjust the mix)"

        print(f"{name}: {w}x{h} {fps:.2f}fps {dur:.3f}s | bg {None if got is None else got.tolist()}{seam} | {audio}")
        for p in a.probe:
            when, rest = p.split(":")
            point, _, want = rest.partition("=")
            x, y = (int(t) for t in point.split(","))
            f = frame(path, float(when), w, h)
            c = patch(f, x, y).tolist() if f is not None else None
            verdict = ""
            if want and c is not None:
                target = np.array([int(t) for t in want.split(",")])
                good = bool(np.all(np.abs(np.array(c) - target) <= max(12, a.tol)))
                verdict = " ok" if good else f" OFF (want {target.tolist()})"
                if not good:
                    problems.append(f"probe {p} is {c}")
            print(f"    probe {when}s @ {x},{y}: {c}{verdict}")
        for pr in problems:
            print(f"    FAIL {pr}")
        failed |= bool(problems)
    print("all checks passed" if not failed else "some checks FAILED")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
