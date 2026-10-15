import json
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

from atelier import Canvas, brush, studio


def overlaps(a, b):
    return abs(a[0] - b[0]) < a[2] and abs(a[1] - b[1]) < a[3]


@pytest.fixture
def detailed_png(tmp_path):
    """2048x1536 smooth gradient with one strongly textured patch and one weak one."""
    rng = np.random.default_rng(0)
    h, w = 1536, 2048
    img = np.zeros((h, w, 3), np.float32)
    img[:] = np.linspace(60, 190, w)[None, :, None]
    img[200:500, 1500:1800] += rng.normal(0, 60, (300, 300, 1))
    img[1000:1200, 300:500] += rng.normal(0, 15, (200, 200, 1))
    path = tmp_path / "painting.png"
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path)
    return path


def check_sheet(sheet, crops, original):
    assert sheet.size == (studio.SHEET_W, studio.SHEET_H)
    assert len(crops) == 4
    w, h = original.size
    for x, y, cw, ch in crops:
        assert (cw, ch) == (min(400, w), min(400, h))
        assert 0 <= x <= w - cw and 0 <= y <= h - ch
    src, out = np.asarray(original), np.asarray(sheet.convert("RGB"))
    for (x, y, cw, ch), (sx, sy) in zip(crops, studio.CROP_CELLS):
        np.testing.assert_array_equal(out[sy:sy + ch, sx:sx + cw], src[y:y + ch, x:x + cw])


def test_review_sheet_layout_and_crops(detailed_png):
    original = Image.open(detailed_png).convert("RGB")
    sheet, crops = studio.review_sheet(original)
    check_sheet(sheet, crops, original)
    details, center = crops[:3], crops[3]
    for i in range(3):
        for j in range(i + 1, 3):
            assert not overlaps(details[i], details[j])
    assert overlaps(details[0], (1500, 200, 300, 300))
    assert (center[0], center[1]) == ((2048 - 400) // 2, (1536 - 400) // 2)


def test_review_sheet_handles_small_images():
    img = Image.fromarray(np.random.default_rng(1).integers(0, 255, (300, 520, 3), dtype=np.uint8))
    sheet, crops = studio.review_sheet(img)
    check_sheet(sheet, crops, img)


def test_review_cli_writes_sheet_next_to_png(detailed_png):
    result = subprocess.run([sys.executable, "-m", "atelier.studio", "review", str(detailed_png)],
                            capture_output=True, text=True, check=True)
    review = detailed_png.with_name("painting_review.png")
    assert str(review) in result.stdout
    sheet = Image.open(review)
    original = Image.open(detailed_png).convert("RGB")
    _, crops = studio.review_sheet(original)
    check_sheet(sheet, crops, original)


def test_focus_crops_come_first_and_the_automatic_crops_avoid_them(detailed_png):
    original = Image.open(detailed_png).convert("RGB")
    sheet, crops = studio.review_sheet(original, focus=[(400, 1100), (10, 1530)])
    check_sheet(sheet, crops, original)
    assert crops[0] == (200, 900, 400, 400)                 # centered on the point
    assert crops[1] == (0, 1136, 400, 400)                  # clamped into the image at a corner
    assert overlaps(crops[2], (1500, 200, 300, 300))        # then the most detailed window
    assert not any(overlaps(c, crops[0]) or overlaps(c, crops[1]) for c in crops[2:])


def test_focus_must_be_inside_the_image_and_at_most_four_points(detailed_png):
    original = Image.open(detailed_png).convert("RGB")
    with pytest.raises(ValueError):
        studio.review_sheet(original, focus=[(2100, 100)])
    with pytest.raises(ValueError):
        studio.review_sheet(original, focus=[(100, 100)] * 5)


def test_review_cli_takes_focus_points(detailed_png):
    subprocess.run([sys.executable, "-m", "atelier.studio", "review", str(detailed_png), "--focus", "400,1100",
                    "--focus", "1000,700"], capture_output=True, text=True, check=True)
    sheet = Image.open(detailed_png.with_name("painting_review.png"))
    original = Image.open(detailed_png).convert("RGB")
    _, crops = studio.review_sheet(original, focus=[(400, 1100), (1000, 700)])
    assert crops[:2] == [(200, 900, 400, 400), (800, 500, 400, 400)]
    check_sheet(sheet, crops, original)


def test_compare_is_blind_and_its_order_follows_the_seed(detailed_png, tmp_path):
    a = Image.open(detailed_png).convert("RGB")
    b_path = tmp_path / "other.png"
    Image.fromarray(255 - np.asarray(a)).save(b_path)
    lefts = set()
    for seed in range(6):
        out, key = studio.compare(detailed_png, b_path, tmp_path / f"ab{seed}.png", seed=seed)
        assert key == tmp_path / f"ab{seed}_key.txt"
        lines = dict(line.split(": ", 1) for line in key.read_text().splitlines())
        left = lines["left (1)"]
        assert {left, lines["right (2)"]} == {str(detailed_png), str(b_path)}
        lefts.add(left)
        sheet = np.asarray(Image.open(out).convert("RGB"))
        fw, fh = studio.COMPARE_FULL
        y0 = studio.HEADER + studio.LABEL
        for x0, name in ((studio.GAP, left), (2 * studio.GAP + studio.COMPARE_COL, lines["right (2)"])):
            full = np.asarray(Image.open(name).convert("RGB").resize((fw, fh), Image.LANCZOS))
            np.testing.assert_array_equal(sheet[y0:y0 + fh, x0:x0 + fw], full)
    assert lefts == {str(detailed_png), str(b_path)}           # both orders happen
    again, _ = studio.compare(detailed_png, b_path, tmp_path / "again.png", seed=3)
    assert Image.open(again).tobytes() == Image.open(tmp_path / "ab3.png").tobytes()
    with pytest.raises(ValueError):
        studio.compare(detailed_png, a.resize((1024, 768)), tmp_path / "sizes.png", seed=1)


def test_compare_cli(detailed_png, tmp_path):
    b_path = tmp_path / "other.png"
    Image.fromarray(np.asarray(Image.open(detailed_png).convert("RGB"))[:, ::-1].copy()).save(b_path)
    result = subprocess.run([sys.executable, "-m", "atelier.studio", "compare", str(detailed_png), str(b_path),
                             "-o", str(tmp_path / "ab.png"), "--seed", "2", "--focus", "400,1100"],
                            capture_output=True, text=True, check=True)
    assert "ab.png" in result.stdout and "ab_key.txt" in result.stdout
    assert (tmp_path / "ab.png").exists() and (tmp_path / "ab_key.txt").exists()


def test_save_canvas_writes_final_and_review(tmp_path):
    cv = Canvas(640, 480, seed=5)
    cv.ground("raw_umber", texture="linen", tone=0.35)
    final, review = studio.save(cv, tmp_path / "sub" / "final.png")
    assert final == tmp_path / "sub" / "final.png"
    assert review == tmp_path / "sub" / "final_review.png"
    np.testing.assert_array_equal(np.asarray(Image.open(final)), cv.to_srgb_uint8())
    assert Image.open(review).size == (studio.SHEET_W, studio.SHEET_H)


def test_snapshots_and_contact_sheet(tmp_path):
    progress = tmp_path / "progress"
    progress.mkdir()
    Image.new("RGB", (10, 10)).save(progress / "07_stale.png")
    cv = Canvas(400, 300, seed=1)
    cv.ground("yellow_ochre", texture="cotton", tone=0.2)
    first = studio.snapshot(cv, "toned ground", dir=progress)
    cv.ground("burnt_umber", texture="cotton", tone=0.6)
    second = studio.snapshot(cv, "underpainting", dir=progress)
    assert first.name == "00_toned_ground.png" and second.name == "01_underpainting.png"
    assert Image.open(first).size == (800, 600)
    assert not (progress / "07_stale.png").exists()
    sheet_path = studio.contact_sheet(progress)
    sheet = Image.open(sheet_path)
    assert sheet_path.parent == progress
    assert sheet.width >= 2 * 400 and sheet.height > 300


def test_contact_cli(tmp_path):
    progress = tmp_path / "progress"
    cv = Canvas(200, 150, seed=1)
    cv.ground("raw_umber", texture="paper", tone=0.3)
    studio.snapshot(cv, "one", dir=progress)
    result = subprocess.run([sys.executable, "-m", "atelier.studio", "contact", str(progress)],
                            capture_output=True, text=True, check=True)
    assert "contact_sheet.png" in result.stdout
    assert (progress / "contact_sheet.png").exists()


def test_save_with_canvas_writes_stroke_and_time_stats(tmp_path):
    cv = Canvas(120, 80, seed=3)
    cv.ground("raw_umber")
    for y in (20, 40, 60):
        cv.stroke(brush("round_bristle"), [(10, y), (110, y)], "vermilion")
    studio.save(cv.finish(), tmp_path / "final.png", canvas=cv)
    stats = json.loads((tmp_path / "final_stats.json").read_text())
    assert stats["strokes"] == 3
    assert (stats["width"], stats["height"], stats["seed"]) == (120, 80, 3)
    assert stats["seconds"] >= 0
