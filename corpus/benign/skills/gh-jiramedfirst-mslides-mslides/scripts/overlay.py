"""QA preview: python overlay.py <workspace> <shot>... → <workspace>/preview/<shot>.png with numbered red boxes.
Check marks here before building — a wrong box is cheaper to see on one PNG than on a rendered 100-slide deck.
draw_marks() is shared with export_md.py so the Markdown edition shows the same boxes as the preview."""
import json, pathlib, sys
from PIL import Image, ImageDraw


def draw_marks(im, marks):
    dr = ImageDraw.Draw(im)
    for i, m in enumerate(marks, 1):
        dr.rectangle([m["x"], m["y"], m["x"] + m["w"], m["y"] + m["h"]], outline="red", width=3)
        # Badge OUTSIDE the box, to its left and vertically centred — on the corner it sat on the field's label
        # ("ame", "ategory"). No room on the left (mark at the image edge, e.g. a top bar): corner, kept whole.
        if m["x"] >= 34:
            cx, cy = m["x"] - 18, m["y"] + m["h"] / 2
        else:
            cx, cy = max(14, m["x"]), max(14, m["y"])
        dr.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill="red")
        dr.text((cx - 4, cy - 7), str(i), fill="white")
    return im


if __name__ == "__main__":
    ws = pathlib.Path(sys.argv[1]).expanduser()
    (ws / "preview").mkdir(exist_ok=True)
    for name in sys.argv[2:]:
        im = Image.open(ws / "shots" / f"{name}.png").convert("RGB")
        draw_marks(im, json.loads((ws / "shots" / f"{name}.json").read_text(encoding="utf-8"))["marks"])
        im.save(ws / "preview" / f"{name}.png")
        print(ws / "preview" / f"{name}.png")
