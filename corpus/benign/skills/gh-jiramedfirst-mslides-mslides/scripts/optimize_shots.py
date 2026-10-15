"""Shrink screenshots before they are committed: python optimize_shots.py <shots-dir> [<shot> …]

When manual sources live in version control, every PNG is history forever. A 256-colour palette keeps UI text
crisp and cut an 84-shot set from 15.0 MB to 3.8 MB; the .json marks are untouched (same pixel size).
Idempotent: a PNG already in palette mode is skipped, so it is safe to run after every capture or --accept.
"""
import pathlib, sys
from PIL import Image

d = pathlib.Path(sys.argv[1]).expanduser()
only = set(sys.argv[2:])
before = after = n = 0
for p in sorted(d.glob("*.png")):
    if only and p.stem not in only:
        continue
    im = Image.open(p)
    if im.mode == "P":
        continue
    size = p.stat().st_size
    im.convert("RGB").quantize(256, method=Image.Quantize.FASTOCTREE).save(p, "PNG", optimize=True)
    before, after, n = before + size, after + p.stat().st_size, n + 1
print(f"optimized {n} shot(s): {before / 1e6:.1f} MB → {after / 1e6:.1f} MB")
