#!/usr/bin/env python3
"""
Capture a cropped, highlighted screenshot of one finding on a live URL.

Use ONLY for Blocker and High findings. See SKILL.md step 4b.

The element is located in the SAME render that is captured, so no coordinates have to
survive between tools. Locate by visible text (preferred — it's what the reader sees)
or by CSS selector.

Examples
  # by visible text, climbing to the enclosing panel
  python3 crop.py --url https://archive.org/details/X \
      --text "DOWNLOAD OPTIONS" --expand-to "MPEG4" \
      --out finding-2.png --label "Finding 2 - Download options"

  # by selector
  python3 crop.py --url https://example.com --selector ".plan-card .primary" \
      --out finding-1.png --label "Finding 1 - CTA states no outcome"

  # explicit page region, when nothing selects cleanly
  python3 crop.py --url https://example.com --region 810,971,360,250 --out f3.png

Options
  --text S        deepest element whose text contains S
  --expand-to S   after --text, climb to the nearest ancestor also containing S
  --selector S    CSS selector (first visible match); pierces open shadow roots
  --region x,y,w,h  explicit page coordinates, CSS pixels
  --nth N         use the Nth match (0-based, default 0)
  --width / --height   viewport (default 1280x900)
  --pad N         context kept around the target (default 40)
  --label S       caption drawn under the crop
  --no-box        crop without the highlight rectangle
  --wait S        extra seconds after load (default 2.5)

Requires: pip install playwright && python3 -m playwright install chromium
ALWAYS open the result and confirm it frames the right thing before using it.
"""
import argparse, sys
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

HIGHLIGHT = (214, 69, 44)

FIND_BY_TEXT = """
([needle, expand, nth]) => {
  const hits = [...document.querySelectorAll('body *')].filter(
    e => (e.innerText || '').includes(needle));
  if (!hits.length) return null;
  const inner = hits.filter(e => !hits.some(o => o !== e && e.contains(o)));
  let el = (inner.length ? inner : hits)[Math.min(nth, (inner.length?inner:hits).length - 1)];
  if (expand) { let p = el; while (p && !(p.innerText||'').includes(expand)) p = p.parentElement; if (p) el = p; }
  const r = el.getBoundingClientRect();
  return {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
          tag: el.tagName, cls: (el.className||'').toString().slice(0,60)};
}
"""

FIND_BY_SELECTOR = """
([sel, nth]) => {
  const acc = [...document.querySelectorAll(sel)];
  const walk = r => r.querySelectorAll('*').forEach(e => {
    if (e.shadowRoot) { acc.push(...e.shadowRoot.querySelectorAll(sel)); walk(e.shadowRoot); } });
  walk(document);
  const vis = acc.filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  if (!vis.length) return null;
  const el = vis[Math.min(nth, vis.length - 1)];
  const r = el.getBoundingClientRect();
  return {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
          tag: el.tagName, cls: (el.className||'').toString().slice(0,60)};
}
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--out", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--selector")
    g.add_argument("--region")
    p.add_argument("--expand-to", default=None)
    p.add_argument("--nth", type=int, default=0)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=900)
    p.add_argument("--pad", type=int, default=40)
    p.add_argument("--label", default=None)
    p.add_argument("--wait", type=float, default=2.5)
    p.add_argument("--no-box", action="store_true")
    a = p.parse_args()

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": a.width, "height": a.height})
        page.goto(a.url, wait_until="load", timeout=60000)
        page.wait_for_timeout(int(a.wait * 1000))

        if a.region:
            try:
                x, y, w, h = [float(v) for v in a.region.split(",")]
            except ValueError:
                sys.exit("--region must be x,y,w,h")
            box = {"x": x, "y": y, "w": w, "h": h, "tag": "(region)", "cls": ""}
        elif a.text:
            box = page.evaluate(FIND_BY_TEXT, [a.text, a.expand_to, a.nth])
            if not box:
                browser.close(); sys.exit(f"No element containing text: {a.text!r}")
        else:
            box = page.evaluate(FIND_BY_SELECTOR, [a.selector, a.nth])
            if not box:
                browser.close(); sys.exit(f"No visible element matching: {a.selector!r}")

        shot = a.out + ".full.tmp.png"
        page.screenshot(path=shot, full_page=True)
        browser.close()

    img = Image.open(shot).convert("RGB")
    x, y, w, h = box["x"], box["y"], box["w"], box["h"]
    crop_box = (max(0, int(x - a.pad)), max(0, int(y - a.pad)),
                min(img.width, int(x + w + a.pad)), min(img.height, int(y + h + a.pad)))
    crop = img.crop(crop_box)

    if not a.no_box:
        d = ImageDraw.Draw(crop)
        rx, ry = x - crop_box[0], y - crop_box[1]
        for i in range(3):
            d.rectangle([rx - i, ry - i, rx + w + i, ry + h + i], outline=HIGHLIGHT)

    if a.label:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
        except OSError:
            font = ImageFont.load_default()
        d0 = ImageDraw.Draw(crop)
        def tw(t):
            return d0.textbbox((0, 0), t, font=font)[2]
        # canvas at least wide enough for a reasonable caption, then wrap into it
        canvas_w = max(crop.width, 360)
        lines, cur = [], ""
        for word in a.label.split():
            trial = (cur + " " + word).strip()
            if tw(trial) <= canvas_w - 16 or not cur:
                cur = trial
            else:
                lines.append(cur); cur = word
        if cur:
            lines.append(cur)
        line_h, top_pad, bot_pad = 19, 9, 10
        bar = top_pad + line_h * len(lines) + bot_pad
        out = Image.new("RGB", (canvas_w, crop.height + bar), (255, 255, 255))
        out.paste(crop, ((canvas_w - crop.width) // 2, 0))
        d = ImageDraw.Draw(out)
        for i, line in enumerate(lines):
            d.text((8, crop.height + top_pad + i * line_h), line,
                   fill=(40, 40, 40), font=font)
        crop = out

    crop.save(a.out)
    import os; os.remove(shot)
    print(f"{a.out}  {crop.width}x{crop.height}  "
          f"target={box['tag']}.{box['cls'][:30]} at {int(x)},{int(y)} {int(w)}x{int(h)}")


if __name__ == "__main__":
    main()
