#!/usr/bin/env python3
"""
Check where each sound-effect cue's loudest point really sits in a finished mix.

  run.sh cuecheck.py OUT.mp4 [--report OUT.mp4.sfx.json] [--fps 60]

For every cue in the report mix.py wrote, the cue is rebuilt (same pitch, filter, trim), located in the
decoded output by cross-correlation (±25 ms search, so limiter or encoder delay shows up), and its
offset is reported as output peak time minus `at`. Also printed: the plain loudest 10 ms of the whole
output within ±45 ms of `at` (music and layered cues can win there, so it is a hint, not the verdict).
Exits 1 when any cue is off by more than one frame.
"""

import argparse
import json
import subprocess

import numpy as np

from common import probe
from mix import SR, cue_signal, rms_env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mix")
    ap.add_argument("--report", help="default: MIX.sfx.json")
    ap.add_argument("--fps", type=float, help="default: the video's frame rate, else 60")
    a = ap.parse_args()
    rep = json.load(open(a.report or f"{a.mix}.sfx.json"))
    fps = a.fps or probe(a.mix).get("fps") or 60
    tol = 1000 / fps
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.mix, "-map", "0:a:0", "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    out = np.frombuffer(raw, np.float32).astype(np.float64)
    env = rms_env(out)
    search, pre, post = int(0.025 * SR), int(0.03 * SR), int(0.1 * SR)

    print(f"{'cue':22s} {'at s':>8s} {'offset ms':>9s} {'frames':>6s} {'corr':>5s} {'env-peak ms':>11s}")
    worst = 0.0
    for c in rep["cues"]:
        y, pk = cue_signal(dict(c))
        t0 = max(0, pk - pre)
        tmpl = y[t0:pk + post]
        exp = int(round(c["start_s"] * SR)) + t0  # where the template should start in the output
        lo = max(0, exp - search)
        win = out[lo:exp + len(tmpl) + search]
        if exp + len(tmpl) > len(out) or len(win) < len(tmpl):
            print(f"{c.get('name', c['file']):22s} outside the output")
            worst = float("inf")
            continue
        xc = np.correlate(win, tmpl, "valid")
        norms = np.sqrt(np.convolve(win ** 2, np.ones(len(tmpl)), "valid")) * np.linalg.norm(tmpl) + 1e-12
        k = int(np.argmax(xc / norms))
        lag = lo + k - exp
        at = int(round(c["at"] * SR))
        off = (int(round(c["start_s"] * SR)) + pk + lag - at) / SR * 1000
        w0, w1 = max(0, at - int(0.045 * SR)), at + int(0.045 * SR)
        env_off = (w0 + int(np.argmax(env[w0:w1])) - at) / SR * 1000
        worst = max(worst, abs(off))
        print(f"{c.get('name', c['file']):22s} {c['at']:8.3f} {off:+9.2f} {off / tol:+6.2f} "
              f"{xc[k] / norms[k]:5.2f} {env_off:+11.1f}")
    ok = worst <= tol
    print(f"worst {worst:.2f} ms, tolerance ±{tol:.1f} ms (1 frame at {fps:g} fps): {'PASS' if ok else 'FAIL'}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
