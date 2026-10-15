"""Contact sheets: the fastest way to review a film is to look at many frames at once.

python tools/sheet.py out.png 6 0.25 a.png b.png ...       grid: 6 columns at 25% scale, filenames as labels
python tools/sheet.py --video renders/preview.mkv --every 1 out.png [--cols 6] [--width 384]
                                                            one frame per second of a video
"""
import glob
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import ffmpeg  # noqa: E402


def font(size):
    for f in ("arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def grid(out, cols, scale, paths, labels=None):
    ims = [Image.open(p).convert("RGB") for p in paths]
    w, h = int(ims[0].width * scale), int(ims[0].height * scale)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), (20, 20, 24))
    d = ImageDraw.Draw(sheet)
    f = font(max(12, h // 12))
    for i, im in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(im.resize((w, h), Image.LANCZOS), (x, y))
        lab = labels[i] if labels else os.path.splitext(os.path.basename(paths[i]))[0]
        tw = d.textlength(lab, font=f)
        d.rectangle([x, y, x + tw + 10, y + f.size + 8], fill=(0, 0, 0))
        d.text((x + 5, y + 3), lab, fill=(255, 230, 80), font=f)
    sheet.save(out)
    print(f"sheet -> {out}  ({len(ims)} frames, {cols} cols)")


def from_video(video, every, out, cols=6, width=384):
    tmp = tempfile.mkdtemp()
    subprocess.run([ffmpeg(), "-v", "error", "-i", video, "-vf", f"fps=1/{every},scale={width}:-2", os.path.join(tmp, "f%04d.png")], check=True)
    fs = sorted(glob.glob(os.path.join(tmp, "f*.png")))
    labels = [f"{i * every:.1f}s" for i in range(len(fs))]
    grid(out, cols, 1.0, fs, labels)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--video":
        video = a[1]
        every = float(a[a.index("--every") + 1]) if "--every" in a else 1.0
        cols = int(a[a.index("--cols") + 1]) if "--cols" in a else 6
        width = int(a[a.index("--width") + 1]) if "--width" in a else 384
        out = [x for x in a[2:] if x.endswith(".png")][0]
        from_video(video, every, out, cols, width)
    else:
        grid(a[0], int(a[1]), float(a[2]), a[3:])
