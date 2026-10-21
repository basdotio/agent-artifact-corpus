"""Contact sheet from a folder of stills: python3 scripts/sheet.py review/stills review/sheet.jpg [cols] [width]"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
tw = int(sys.argv[4]) if len(sys.argv) > 4 else 640
files = sorted(f for f in os.listdir(src) if f.endswith(".png"))
ims = [Image.open(os.path.join(src, f)).convert("RGB") for f in files]
th = int(ims[0].height * tw / ims[0].width)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 30) + 8), (24, 24, 28))
d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
except Exception:
    font = None
for i, (f, im) in enumerate(zip(files, ims)):
    x = 8 + (i % cols) * (tw + 8)
    y = 8 + (i // cols) * (th + 30)
    sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
    d.text((x + 4, y + th + 4), f.replace(".png", ""), fill=(220, 220, 220), font=font)
sheet.save(out, quality=88)
print(out, sheet.size)
