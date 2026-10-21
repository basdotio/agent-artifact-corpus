#!/usr/bin/env python3
"""Render every PDF page to PNG contact sheets for visual QA.
usage: python3 render_check.py out/notes.pdf   -> out/sheet-N.png (6 pages per sheet)"""
import sys, subprocess, pathlib, glob
pdf = pathlib.Path(sys.argv[1]).resolve(); d = pdf.parent
for f in d.glob("pg-*.png"): f.unlink()
subprocess.run(["pdftoppm", "-r", "55", "-png", str(pdf), str(d / "pg")], check=True, stderr=subprocess.DEVNULL)
from PIL import Image
files = sorted(d.glob("pg-*.png"))
for s in range(0, len(files), 6):
    imgs = [Image.open(f) for f in files[s:s+6]]; w, h = imgs[0].size
    sheet = Image.new("RGB", (w*3+40, h*2+30), "#888")
    for i, im in enumerate(imgs):
        sheet.paste(im, (10+(i%3)*(w+10), 10+(i//3)*(h+10)))
    sheet.save(d / f"sheet-{s//6}.png")
print(len(files), "pages ->", (len(files)+5)//6, "sheets in", d)
