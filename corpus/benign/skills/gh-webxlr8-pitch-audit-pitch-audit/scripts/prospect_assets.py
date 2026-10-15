#!/usr/bin/env python3
"""Collect the prospect's own visuals for the deck: logo, their photos, and the page-load filmstrip.

Usage:
    python3 prospect_assets.py <client_dir> [url] [--max-photos 6]

Writes into <client_dir>/images/:
  prospect-logo.png, prospect-logo-on-dark.png   their logo rendered alone (+ a light version for dark slides)
  prospect-photo-N.jpg                           their own large photos (fleet, products, team, premises)
  prospect-photos.png                            numbered contact sheet, so you can look and pick
  filmstrip-NN.jpg + filmstrip.json              Lighthouse mobile frames with timings + first visible content time
  CREDITS.md                                     where every image came from
Use them in deck-data: client.logo, slide `photo`, finding `filmstrip`. Their own photos beat stock photos.
"""
import argparse
import base64
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from setup_profile import SCAN_JS, logo_kind, make_white, render_logos  # noqa: E402

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/129 Safari/537.36 pitch-audit"
PAGE_HINTS = r"(about|fleet|gallery|our-work|work|projects|services|products|team|company|portfolio|story)"

PHOTOS_JS = r"""
() => {
  const out = [];
  const seen = new Set();
  const add = (src, el, how) => {
    if (!src || seen.has(src) || /^data:/.test(src) || /\.svg(\?|$)/i.test(src)) return;
    const r = el.getBoundingClientRect();
    const hint = ((el.alt || '') + ' ' + (el.className && el.className.baseVal === undefined ? el.className : '') + ' ' + src).toLowerCase();
    if (/(logo|icon|sprite|avatar|badge|flag|payment|emoji)/.test(hint)) return;
    seen.add(src);
    out.push({ src, w: el.naturalWidth || r.width, h: el.naturalHeight || r.height, area: r.width * r.height, top: r.top + window.scrollY, how, alt: el.alt || '' });
  };
  document.querySelectorAll('img').forEach(i => add(i.currentSrc || i.src, i, 'img'));
  document.querySelectorAll('section, header, div, figure').forEach(el => {
    const bg = getComputedStyle(el).backgroundImage; const m = bg && bg.match(/url\(["']?([^"')]+)["']?\)/);
    const r = el.getBoundingClientRect();
    if (m && r.width > 500 && r.height > 250) add(new URL(m[1], location.href).href, el, 'bg');
  });
  return out;
}
"""


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=25).read()


def blank(im):
    a = np.asarray(im.convert("L"), dtype=float)
    return bool(a.std() < 6)  # an empty white/solid frame


def filmstrip(cdir, out):
    lp = os.path.join(cdir, "lighthouse-mobile.json")
    if not os.path.exists(lp):
        return None
    lh = json.load(open(lp))
    items = (((lh.get("audits") or {}).get("screenshot-thumbnails") or {}).get("details") or {}).get("items") or []
    if not items:
        return None
    frames, first = [], None
    for i, it in enumerate(items, 1):
        im = Image.open(io.BytesIO(base64.b64decode(it["data"].split(",", 1)[1]))).convert("RGB")
        fp = os.path.join(out, f"filmstrip-{i:02d}.jpg")
        im.save(fp, quality=90)
        is_blank = blank(im)
        if first is None and not is_blank:
            first = round(it["timing"])
        frames.append({"src": os.path.relpath(fp, cdir), "t_ms": round(it["timing"]), "t_s": round(it["timing"] / 1000, 1), "blank": is_blank})
    data = {"source": "Lighthouse mobile (simulated slow 4G)", "frames": frames, "first_content_ms": first,
            "first_content_s": round(first / 1000, 1) if first else None,
            "lcp_s": round(lh["audits"]["largest-contentful-paint"]["numericValue"] / 1000, 1)}
    json.dump(data, open(os.path.join(out, "filmstrip.json"), "w"), indent=2)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("client_dir")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--max-photos", type=int, default=6)
    ap.add_argument("--no-filmstrip", action="store_true", help="skip filmstrip (prepare.py runs it after the audit)")
    ap.add_argument("--filmstrip-only", action="store_true", help="only extract the filmstrip from lighthouse-mobile.json")
    a = ap.parse_args()
    cdir = os.path.abspath(a.client_dir)
    if a.filmstrip_only:
        out = os.path.join(cdir, "images")
        os.makedirs(out, exist_ok=True)
        fs = None if a.no_filmstrip else filmstrip(cdir, out)
        print(f"filmstrip: {len(fs['frames']) if fs else 'none'}" + (f", first content at {fs['first_content_s']}s" if fs and fs.get('first_content_s') else ""))
        return
    url = a.url
    if not url and os.path.exists(os.path.join(cdir, "audit.json")):
        url = json.load(open(os.path.join(cdir, "audit.json"))).get("final_url")
    if not url:
        sys.exit("give the prospect URL (or run audit.py first)")
    out = os.path.join(cdir, "images")
    os.makedirs(out, exist_ok=True)
    credits = []

    from browser import launch
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = launch(p)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, ignore_https_errors=True)
        pg = ctx.new_page()
        pg.goto(url, wait_until="load", timeout=60000)
        try:
            pg.wait_for_load_state("networkidle", timeout=8000)
        except Exception:  # noqa: BLE001
            pass
        home = pg.evaluate(SCAN_JS)
        # lazy images: scroll the page before collecting
        pg.evaluate("async () => { for (let y = 0; y < Math.min(document.body.scrollHeight, 8000); y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } }")
        cands = pg.evaluate(PHOTOS_JS)
        host = urllib.parse.urlparse(pg.url).hostname or ""
        pages = []
        for l in home["links"]:
            pu = urllib.parse.urlparse(l["href"])
            if pu.hostname and pu.hostname.replace("www.", "") == host.replace("www.", "") and re.search(PAGE_HINTS, pu.path, re.I):
                u = l["href"].split("#")[0]
                if u not in pages:
                    pages.append(u)
        for u in pages[:3]:
            try:
                pg.goto(u, wait_until="load", timeout=30000)
                pg.evaluate("async () => { for (let y = 0; y < 6000; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 100)); } }")
                cands += pg.evaluate(PHOTOS_JS)
            except Exception:  # noqa: BLE001
                continue
        logos = render_logos(ctx, home["logos"], out)
        b.close()

    # ---- logo
    for f in os.listdir(out):
        if f.startswith("_logo-original"):
            os.remove(os.path.join(out, f))
    if logos:
        lp = os.path.join(out, "prospect-logo.png")
        os.replace(logos[0][0], lp)
        kind, _ = logo_kind(lp)
        dark_v = os.path.join(out, "prospect-logo-on-dark.png")
        if kind == "light":
            Image.open(lp).save(dark_v)
        else:
            make_white(lp, dark_v)
        credits.append(f"- `prospect-logo.png`: the prospect's own logo, rendered from {url}")
        for fp, orig in logos[1:]:
            for x in (fp, orig):
                if os.path.exists(x):
                    os.remove(x)

    # ---- their photos: big, landscape-ish, not logos/icons; largest + highest on page first
    seen, photos = set(), []
    for c in sorted(cands, key=lambda c: (c["top"], -(c["w"] * c["h"]))):  # page order: hero first
        if c["src"] in seen or (c["how"] == "img" and (c["w"] < 800 or c["h"] < 400)):
            continue
        seen.add(c["src"])
        try:
            im = Image.open(io.BytesIO(fetch(c["src"]))).convert("RGB")
        except Exception:  # noqa: BLE001
            continue
        if im.width < 800 or im.height < 400 or blank(im):
            continue
        r = im.width / im.height  # judge the real file, then keep a usable landscape crop
        if r > 2.4:
            nw = int(im.height * 2.4)
            im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
        elif r < 1.0:
            continue
        im.thumbnail((1920, 1920))
        n = len(photos) + 1
        fp = os.path.join(out, f"prospect-photo-{n}.jpg")
        im.save(fp, quality=88)
        photos.append((fp, c))
        credits.append(f"- `prospect-photo-{n}.jpg`: the prospect's own photo from their website ({c['src']})")
        if len(photos) >= a.max_photos:
            break
    if photos:
        tiles = []
        for i, (fp, c) in enumerate(photos, 1):
            im = Image.open(fp)
            im.thumbnail((400, 250))
            t = Image.new("RGB", (400, 280), (20, 20, 20))
            t.paste(im, ((400 - im.width) // 2, 0))
            ImageDraw.Draw(t).text((8, 260), f"#{i}  {im.width}x{im.height}  {c['alt'][:40]}", fill=(255, 255, 255))
            tiles.append(t)
        sheet = Image.new("RGB", (3 * 405, ((len(tiles) + 2) // 3) * 285), (0, 0, 0))
        for k, t in enumerate(tiles):
            sheet.paste(t, ((k % 3) * 405, (k // 3) * 285))
        sheet.save(os.path.join(out, "prospect-photos.png"))

    fs = filmstrip(cdir, out)
    if fs:
        credits.append(f"- `filmstrip-*.jpg`: {fs['source']} frames of {url}")
    if credits:
        with open(os.path.join(out, "CREDITS.md"), "a") as f:
            f.write("\n".join(credits) + "\n")
    print(f"logo: {'yes' if logos else 'not found'}  ·  their photos: {len(photos)}  ·  filmstrip: "
          f"{len(fs['frames']) if fs else ('later' if a.no_filmstrip else 'none (run audit.py with Lighthouse)')}"
          + (f", first content at {fs['first_content_s']}s" if fs and fs.get('first_content_s') else ""))
    if photos:
        print(f"look at: {os.path.join(out, 'prospect-photos.png')}")


if __name__ == "__main__":
    main()
