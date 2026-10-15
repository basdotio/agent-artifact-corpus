#!/usr/bin/env python3
"""
Cut each asset off a flat-background sprite sheet into a transparent PNG, then trace it to SVG with vtracer.

  split.py SHEET.png OUT_DIR [--bg auto|#14213d] [--threshold 40] [--downsample 4] [--min-area 200]
                             [--vtracer "--mode spline -f 8 -p 7 -g 12"]

Writes OUT_DIR/aNN.png, aNN.svg and assets.json ([{name, x, y, w, h}] in sheet pixels), in scan order
(top to bottom by each part's first row). Needs numpy, Pillow and the vtracer CLI (cargo install vtracer).
"""

import argparse
import json
import shlex
import subprocess
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("out")
    ap.add_argument("--bg", default="auto", help="background colour as #rrggbb, or auto = median of the top-left 20 px corner")
    ap.add_argument("--threshold", type=int, default=40, help="colour distance (sum of |RGB| differences) that counts as a part")
    ap.add_argument("--downsample", type=int, default=4, help="label connected parts on a mask this many times smaller")
    ap.add_argument("--min-area", type=int, default=200, help="drop parts smaller than this many downsampled pixels")
    ap.add_argument("--vtracer", default="--mode spline -f 8 -p 7 -g 12", help="options passed to vtracer")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    img = np.asarray(Image.open(a.sheet).convert("RGB")).astype(int)
    if a.bg == "auto":
        bg = np.median(img[:20, :20].reshape(-1, 3), axis=0)
    else:
        h = a.bg.lstrip("#")
        bg = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)])
    dist = np.abs(img - bg).sum(axis=2)
    alpha = np.clip((dist - 20) * 6, 0, 255).astype(np.uint8)  # soft edge keeps anti-aliasing

    S = a.downsample
    small = dist[::S, ::S] > a.threshold
    lab = np.zeros(small.shape, int)
    boxes = []
    for y, x in zip(*np.nonzero(small)):
        if lab[y, x]:
            continue
        n = len(boxes) + 1
        q, lab[y, x], ys, xs = deque([(y, x)]), n, [], []
        while q:
            cy, cx = q.popleft()
            ys.append(cy)
            xs.append(cx)
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < small.shape[0] and 0 <= nx < small.shape[1] and small[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n
                    q.append((ny, nx))
        boxes.append((min(ys), min(xs), max(ys), max(xs), len(ys)))

    rgba = np.dstack([img.astype(np.uint8), alpha])
    meta = []
    pad = 3
    for i, (y0, x0, y1, x1, _) in enumerate(b for b in boxes if b[4] > a.min_area):
        Y0, X0 = max(0, (y0 - pad) * S), max(0, (x0 - pad) * S)
        Y1, X1 = (y1 + pad + 1) * S, (x1 + pad + 1) * S
        name = f"a{i:02d}"
        Image.fromarray(rgba[Y0:Y1, X0:X1]).save(out / f"{name}.png")
        subprocess.run(["vtracer", "-i", out / f"{name}.png", "-o", out / f"{name}.svg", *shlex.split(a.vtracer)], check=True)
        meta.append({"name": name, "x": int(X0), "y": int(Y0), "w": int(X1 - X0), "h": int(Y1 - Y0)})
    (out / "assets.json").write_text(json.dumps(meta, indent=1))
    print(f"background {bg.astype(int).tolist()}, {len(meta)} parts -> {out}")


if __name__ == "__main__":
    main()
