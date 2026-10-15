"""Studio: the painter's eyes. Saves renders with review sheets, progress snapshots and contact sheets.

CLI:
    python -m atelier.studio review file.png [--focus x,y ...]   # writes file_review.png next to it
    python -m atelier.studio contact <dir>                       # writes <dir>/contact_sheet.png
    python -m atelier.studio compare a.png b.png [-o ab.png] [--seed N] [--focus x,y ...]
                                                                 # blind A/B sheet + ab_key.txt
"""

import argparse
import json
import re
import secrets
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import uniform_filter

from atelier.color import lightness, srgb_to_linear

CROP = 400
GAP = 16
LABEL = 22
HEADER = 36
FULL_BOX = (1000, 750)
SHEET_W = GAP + 4 * CROP + 4 * GAP
SIDE_X = GAP + FULL_BOX[0] + GAP
SIDE_BOX = (SHEET_W - GAP - SIDE_X, (FULL_BOX[1] - LABEL - GAP) // 2)
CROPS_Y = HEADER + LABEL + FULL_BOX[1] + GAP
SHEET_H = CROPS_Y + LABEL + CROP + GAP
CROP_CELLS = [(GAP + i * (CROP + GAP), CROPS_Y + LABEL) for i in range(4)]
COMPARE_COL = (SHEET_W - 3 * GAP) // 2
COMPARE_FULL = (COMPARE_COL, COMPARE_COL * 3 // 4)
SNAPSHOT_W = 800
BACKGROUND = (38, 38, 38)
INK = (215, 212, 205)

_snapshot_counters = {}


def save(canvas_or_png, path, focus=None, canvas=None):
    """Write the final PNG and its review sheet (<name>_review.png) beside it. Returns both paths.

    focus: (x, y) points in px to crop at 1:1 first on the review sheet (see review_sheet).
    canvas: the Canvas a finished image came from (implied when saving a Canvas). Its stroke count,
    painting time, size and seed go to <name>_stats.json.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _as_image(canvas_or_png).save(path)
    canvas = canvas or (canvas_or_png if hasattr(canvas_or_png, "strokes") else None)
    if canvas is not None:
        h, w = canvas.shape
        stats = {"strokes": canvas.strokes, "seconds": round(time.perf_counter() - canvas.started, 1),
                 "width": w, "height": h, "seed": canvas.seed}
        path.with_name(f"{path.stem}_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    return path, write_review(path, focus)


def write_review(png_path, focus=None):
    png_path = Path(png_path)
    sheet, _ = review_sheet(Image.open(png_path), title=png_path.name, focus=focus)
    out = png_path.with_name(f"{png_path.stem}_review.png")
    sheet.save(out)
    return out


def review_sheet(image, title="", focus=None):
    """Full view, 5-level value map, squint view and four 1:1 crops.

    The crops are the `focus` points first (up to four (x, y) points in px, each the center of a crop:
    the focal point, which the automatic picks can miss), then the most detailed windows away from
    them, then the center. Returns (sheet, crops) where crops are (x, y, w, h) boxes in the original image.
    """
    img = _as_image(image)
    w, h = img.size
    pixels = np.asarray(img)
    sheet = Image.new("RGB", (SHEET_W, SHEET_H), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=15)
    draw.text((GAP, 10), f"{title}  {w}x{h}px".strip(), font=font, fill=INK)

    _panel(sheet, draw, font, img, (GAP, HEADER), FULL_BOX, "full view")
    side = _fit(img, SIDE_BOX)
    _panel(sheet, draw, font, _value_map(side), (SIDE_X, HEADER), SIDE_BOX, "values (5 levels)")
    squint = side.filter(ImageFilter.GaussianBlur(side.width / 60))
    _panel(sheet, draw, font, squint, (SIDE_X, HEADER + LABEL + SIDE_BOX[1] + GAP), SIDE_BOX, "squint")

    cw, ch = min(CROP, w), min(CROP, h)
    crops = _crops(_detail_score(pixels, cw, ch), w, h, cw, ch, focus, len(CROP_CELLS))
    for (x, y, _, _, name), (sx, sy) in zip(crops, CROP_CELLS):
        draw.text((sx, sy - LABEL + 3), f"1:1 {name}  x={x} y={y}", font=font, fill=INK)
        sheet.paste(img.crop((x, y, x + cw, y + ch)), (sx, sy))
    return sheet, [c[:4] for c in crops]


def compare(a, b, out, seed=None, focus=None):
    """A blind A/B sheet: two renders of one painting side by side, unlabeled, in an order set by `seed`.

    a, b: PNG paths or images of the same size. Each side shows the full view and the same two 1:1 crops
    (the `focus` points first, then the most detailed windows of the pair). Which side is which goes to
    <out>_key.txt beside the sheet, to open after the verdict; seed=None picks one at random and writes it
    there too. Returns (sheet path, key path).
    """
    ia, ib = _as_image(a), _as_image(b)
    if ia.size != ib.size:
        raise ValueError(f"compare needs two renders of the same size, got {ia.size} and {ib.size}")
    seed = secrets.randbelow(2 ** 31) if seed is None else seed
    swap = bool(np.random.default_rng(seed).integers(2))
    sides = [(ib, _name(b, "b")), (ia, _name(a, "a"))] if swap else [(ia, _name(a, "a")), (ib, _name(b, "b"))]
    w, h = ia.size
    cw, ch = min(CROP, w, (COMPARE_COL - GAP) // 2), min(CROP, h)
    score = _detail_score(np.asarray(ia), cw, ch) + _detail_score(np.asarray(ib), cw, ch)
    crops = _crops(score, w, h, cw, ch, focus, 2)
    crops_y = HEADER + LABEL + COMPARE_FULL[1] + GAP + LABEL
    sheet = Image.new("RGB", (SHEET_W, crops_y + ch + GAP), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=15)
    draw.text((GAP, 10), f"blind A/B: two versions of one painting, {w}x{h}px, the same crops on both sides",
              font=font, fill=INK)
    for k, (img, _) in enumerate(sides):
        x0 = GAP + k * (COMPARE_COL + GAP)
        _panel(sheet, draw, font, img, (x0, HEADER), COMPARE_FULL, f"{k + 1}")
        for j, (x, y, _, _, name) in enumerate(crops):
            sx = x0 + j * (cw + GAP)
            draw.text((sx, crops_y - LABEL + 3), f"{k + 1}  1:1 {name}  x={x} y={y}", font=font, fill=INK)
            sheet.paste(img.crop((x, y, x + cw, y + ch)), (sx, crops_y))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    key = out.with_name(f"{out.stem}_key.txt")
    key.write_text(f"left (1): {sides[0][1]}\nright (2): {sides[1][1]}\nseed: {seed}\n")
    return out, key


def snapshot(canvas, label, dir="progress"):
    """Save an 800 px wide progress frame as <dir>/NN_label.png.

    The first snapshot into a directory in this process removes that directory's old
    NN_*.png frames, so a re-run of a painting script does not mix in stale frames.
    """
    d = Path(dir).resolve()
    if d not in _snapshot_counters:
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("[0-9][0-9]_*.png"):
            old.unlink()
        _snapshot_counters[d] = 0
    n = _snapshot_counters[d]
    _snapshot_counters[d] += 1
    img = _as_image(canvas)
    frame = img.resize((SNAPSHOT_W, max(1, round(img.height * SNAPSHOT_W / img.width))), Image.LANCZOS)
    out = d / f"{n:02d}_{re.sub(r'[^A-Za-z0-9]+', '_', label).strip('_')}.png"
    frame.save(out)
    return out


def contact_sheet(dir, out=None, columns=4, cell_w=400):
    """Lay out the NN_label.png frames of `dir` in a labeled grid. Returns the written path."""
    d = Path(dir)
    frames = sorted(d.glob("[0-9][0-9]_*.png"))
    if not frames:
        raise FileNotFoundError(f"no NN_label.png frames in {d}")
    thumbs = [_fit(Image.open(f).convert("RGB"), (cell_w, 10 * cell_w)) for f in frames]
    cols = min(columns, len(thumbs))
    rows = -(-len(thumbs) // cols)
    cell_h = max(t.height for t in thumbs) + LABEL
    sheet = Image.new("RGB", (GAP + cols * (cell_w + GAP), GAP + rows * (cell_h + GAP)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=15)
    for i, (f, t) in enumerate(zip(frames, thumbs)):
        x = GAP + (i % cols) * (cell_w + GAP)
        y = GAP + (i // cols) * (cell_h + GAP)
        sheet.paste(t, (x, y))
        draw.text((x, y + t.height + 3), f.stem.replace("_", " ", 1), font=font, fill=INK)
    out = Path(out) if out else d / "contact_sheet.png"
    sheet.save(out)
    return out


def _as_image(obj):
    if hasattr(obj, "to_srgb_uint8"):
        return Image.fromarray(obj.to_srgb_uint8())
    if isinstance(obj, np.ndarray):
        return Image.fromarray(obj)
    if isinstance(obj, Image.Image):
        return obj.convert("RGB")
    return Image.open(obj).convert("RGB")


def _fit(img, box):
    scale = min(box[0] / img.width, box[1] / img.height)
    return img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)


def _panel(sheet, draw, font, img, pos, box, label):
    img = _fit(img, box)
    draw.text((pos[0], pos[1] + 3), label, font=font, fill=INK)
    sheet.paste(img, (pos[0] + (box[0] - img.width) // 2, pos[1] + LABEL + (box[1] - img.height) // 2))


def _value_map(img):
    """Lightness (CIE L*) posterized to 5 equal steps from black to white."""
    levels = np.clip(np.floor(lightness(srgb_to_linear(np.asarray(img) / 255)) * 5), 0, 4)
    return Image.fromarray((levels * 255 / 4).round().astype(np.uint8)).convert("RGB")


def _crops(score, w, h, cw, ch, focus, n):
    """n crop boxes (x, y, cw, ch, name): the focus points first, then the most detailed windows away from
    them, then the center (when there is no focus point)."""
    focus = [] if focus is None else [tuple(float(v) for v in p) for p in focus]
    if len(focus) > n:
        raise ValueError(f"at most {n} focus points, got {len(focus)}")
    boxes = []
    for i, (fx, fy) in enumerate(focus):
        if not (0 <= fx < w and 0 <= fy < h):
            raise ValueError(f"focus point ({fx:g}, {fy:g}) is outside the {w}x{h} image")
        x, y = int(np.clip(round(fx - cw / 2), 0, w - cw)), int(np.clip(round(fy - ch / 2), 0, h - ch))
        boxes.append((x, y, cw, ch, f"focus {i + 1}" if len(focus) > 1 else "focus"))
    picks = _pick_windows(score, cw, ch, n - max(len(boxes), 1), taken=[b[:2] for b in boxes])
    boxes += [(x, y, cw, ch, f"detail {i + 1}") for i, (x, y) in enumerate(picks)]
    while len(boxes) < n:
        boxes.append(((w - cw) // 2, (h - ch) // 2, cw, ch, "center"))
    return boxes


def _detail_score(pixels, cw, ch):
    """Local variance summed over each cw x ch window, at the window's top-left corner (-inf off the image)."""
    gray = pixels.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32) / 255
    h, w = gray.shape
    mean = uniform_filter(gray, 7)
    detail = uniform_filter(gray * gray, 7) - mean * mean
    centered = uniform_filter(detail, (ch, cw))
    score = np.full((h, w), -np.inf, np.float32)
    score[:h - ch + 1, :w - cw + 1] = centered[ch // 2:ch // 2 + h - ch + 1, cw // 2:cw // 2 + w - cw + 1]
    return score


def _pick_windows(score, cw, ch, n, taken=()):
    """Top-left corners of the n best-scoring windows, overlapping each other and `taken` as little as possible."""
    picks = []
    for k in (1, 2, 4, max(ch, cw)):
        s = score.copy()
        dy, dx = max(1, ch // k), max(1, cw // k)
        for x, y in [*taken, *picks]:
            s[max(y - dy + 1, 0):y + dy, max(x - dx + 1, 0):x + dx] = -np.inf
        while len(picks) < n and np.isfinite(s.max()):
            y, x = np.unravel_index(np.argmax(s), s.shape)
            picks.append((int(x), int(y)))
            s[max(y - dy + 1, 0):y + dy, max(x - dx + 1, 0):x + dx] = -np.inf
    return picks + picks[-1:] * (n - len(picks))


def _name(obj, fallback):
    return str(obj) if isinstance(obj, (str, Path)) else f"{fallback} (an image passed in memory)"


def _point(text):
    try:
        x, y = (float(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected x,y in px, got {text!r}") from None
    return x, y


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m atelier.studio")
    sub = parser.add_subparsers(dest="cmd", required=True)
    review = sub.add_parser("review", help="write <name>_review.png next to a PNG")
    review.add_argument("png")
    review.add_argument("--focus", type=_point, action="append", metavar="X,Y",
                        help="a point to crop at 1:1 first, e.g. the focal point (repeatable, up to 4)")
    contact = sub.add_parser("contact", help="write a contact sheet of NN_label.png frames")
    contact.add_argument("dir")
    contact.add_argument("-o", "--out")
    ab = sub.add_parser("compare", help="write a blind A/B sheet of two renders, and its key beside it")
    ab.add_argument("a")
    ab.add_argument("b")
    ab.add_argument("-o", "--out", help="the sheet (default: compare.png next to a)")
    ab.add_argument("--seed", type=int, help="sets the order (default: random, written to the key)")
    ab.add_argument("--focus", type=_point, action="append", metavar="X,Y",
                    help="a point to crop at 1:1 on both sides (repeatable, up to 2)")
    args = parser.parse_args(argv)
    if args.cmd == "review":
        print(write_review(args.png, args.focus))
    elif args.cmd == "contact":
        print(contact_sheet(args.dir, args.out))
    else:
        print(*compare(args.a, args.b, args.out or Path(args.a).with_name("compare.png"), args.seed, args.focus))


if __name__ == "__main__":
    main()
