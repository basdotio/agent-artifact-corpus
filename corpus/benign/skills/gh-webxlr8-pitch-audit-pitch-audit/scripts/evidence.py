#!/usr/bin/env python3
"""Capture proof screenshots for finding slides (their own pages, cropped to the problem).

Usage (writes <client_dir>/screenshots/evidence-<name>.png at 1000x700 and prints a deck-data snippet):
    python3 evidence.py <client_dir> <url> --name cert --cert-warning          # browser security interstitial
    python3 evidence.py <client_dir> <url> --name band --text "Call Us for Order"  # section containing this text
    python3 evidence.py <client_dir> <url> --name form --selector "form#contact"  # element by CSS selector
    python3 evidence.py <client_dir> <url> --name hero --clip 0,0,1280,800        # page area
    python3 evidence.py <client_dir> <url> --name hero --mobile --clip 0,0,390,844 # phone view
    python3 evidence.py <client_dir> --name promise --stack band.png hours.png   # stack captures (top/bottom)
Options: --pad 8 (px around an element), --label "Top: homepage. Bottom: contact page." (caption hint).
"""
import argparse
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1000, 700


def trim(img, tol=14, pad=28):
    """Remove empty margins (the colour of the top-left corner), keep a little breathing room."""
    import numpy as np
    a = np.asarray(img.convert("RGB")).astype(int)
    edge = a[2, 2]
    diff = np.abs(a - edge).sum(2) > tol
    ys, xs = np.where(diff)
    if not len(xs):
        return img
    x0, x1, y0, y1 = max(0, xs.min() - pad), min(a.shape[1], xs.max() + pad), max(0, ys.min() - pad), min(a.shape[0], ys.max() + pad)
    return img.crop((x0, y0, x1, y1))


def fit(img, w=W, h=H):
    """Fit to width; crop extra height from the bottom, or letterbox with the image's own edge colour."""
    img = img.convert("RGB")
    s = w / img.width
    img = img.resize((w, max(1, round(img.height * s))), Image.LANCZOS)
    if img.height >= h:
        return img.crop((0, 0, w, h))
    bg = img.getpixel((2, img.height - 2))
    can = Image.new("RGB", (w, h), bg)
    can.paste(img, (0, (h - img.height) // 2))
    return can


def stack(paths, gap=18):
    """Stack captures top-to-bottom at full width; centred if they fit, proportionally cropped if not."""
    ims = [Image.open(p.replace(".png", ".src.png") if os.path.exists(p.replace(".png", ".src.png")) else p).convert("RGB") for p in paths]
    ims = [im.resize((W, round(im.height * W / im.width)), Image.LANCZOS) for im in ims]
    total = sum(i.height for i in ims) + gap * (len(ims) - 1)
    can = Image.new("RGB", (W, H), (24, 24, 24))
    if total <= H:
        y = (H - total) // 2
        for im in ims:
            can.paste(im, (0, y))
            y += im.height + gap
        return can
    share = [max(80, round((H - gap * (len(ims) - 1)) * i.height / total)) for i in ims]
    y = 0
    for im, hh in zip(ims, share):
        can.paste(im.crop((0, 0, W, min(hh, im.height))), (0, y))
        y += hh + gap
    return can


def capture(a, out):
    sys.path.insert(0, HERE)
    from browser import launch
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = launch(p)
        if a.mobile:
            ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                                ignore_https_errors=not a.cert_warning)
        else:
            ctx = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=2, ignore_https_errors=not a.cert_warning)
        pg = ctx.new_page()
        try:
            pg.goto(a.url, wait_until="load", timeout=45000)
        except Exception as e:  # noqa: BLE001
            if not a.cert_warning:
                sys.exit(f"could not load {a.url}: {str(e)[:120]}")
        pg.wait_for_timeout(1500)
        tmp = out + ".raw.png"
        if a.cert_warning:
            if not pg.url.startswith("chrome-error://"):
                sys.exit(f"no security warning: {a.url} loaded normally ({pg.url})")
            pg.screenshot(path=tmp)
            im = Image.open(tmp)
            sw = im.width / 1280
            im = im.crop((int(300 * sw), int(95 * sw), int(980 * sw), int(470 * sw)))  # the interstitial card
            im = im.resize((int(im.width * 0.62), int(im.height * 0.62)), Image.LANCZOS)
            can = Image.new("RGB", (W * 2 // 2, H), (255, 255, 255))
            im.thumbnail((W - 80, H - 80))
            can.paste(im, ((W - im.width) // 2, (H - im.height) // 2 - 10))
            os.remove(tmp)
            return can
        if a.text or a.selector:
            loc = pg.get_by_text(a.text, exact=False).first if a.text else pg.locator(a.selector).first
            loc.scroll_into_view_if_needed()
            pg.wait_for_timeout(400)
            if a.text:  # widen to the enclosing section so the claim reads in context
                handle = loc.element_handle()
                box = pg.evaluate("""(el) => { let e = el; for (let i = 0; i < 6 && e.parentElement; i++) {
                      const r = e.getBoundingClientRect(); if (r.width > window.innerWidth * 0.7 && r.height > 120) break; e = e.parentElement; }
                    const r = e.getBoundingClientRect(); return {x: r.left, y: r.top + window.scrollY, width: r.width, height: Math.min(r.height, 700)}; }""", handle)
            else:
                box = loc.bounding_box()
                box["y"] += pg.evaluate("window.scrollY")
            pad = a.pad
            clip = {"x": max(0, box["x"] - pad), "y": max(0, box["y"] - pad), "width": box["width"] + 2 * pad, "height": box["height"] + 2 * pad}
            pg.screenshot(path=tmp, full_page=True, clip=clip)
        elif a.clip:
            x, y, w, h = (float(v) for v in a.clip.split(","))
            pg.screenshot(path=tmp, full_page=True, clip={"x": x, "y": y, "width": w, "height": h})
        else:
            pg.screenshot(path=tmp)
        b.close()
    im = Image.open(tmp).convert("RGB")
    os.remove(tmp)
    if a.mobile:
        return im  # portrait, shown in the deck's phone frame
    im = trim(im) if (a.text or a.selector) else im
    im.save(out.replace(".png", ".src.png"))  # untouched crop, used by --stack
    return fit(im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("client_dir")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--name", required=True)
    ap.add_argument("--cert-warning", action="store_true")
    ap.add_argument("--text")
    ap.add_argument("--selector")
    ap.add_argument("--clip")
    ap.add_argument("--mobile", action="store_true")
    ap.add_argument("--stack", nargs="+")
    ap.add_argument("--pad", type=int, default=8)
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    sdir = os.path.join(a.client_dir, "screenshots")
    os.makedirs(sdir, exist_ok=True)
    out = os.path.join(sdir, f"evidence-{a.name}.png")
    if a.stack:
        img = stack([p if os.path.isabs(p) or os.path.exists(p) else os.path.join(sdir, p) for p in a.stack])
    else:
        if not a.url:
            sys.exit("url required (or use --stack)")
        img = capture(a, out)
    img.save(out)
    snippet = {"src": os.path.relpath(out, a.client_dir), "label": a.url or "", "inset": None if a.mobile else True,
               "size": None if a.mobile else "large", "frame": "phone" if a.mobile else None,
               "caption": a.label or None, "alt": "TODO: describe what the screenshot proves"}
    print(f"saved {out}")
    print("deck-data image:", json.dumps({k: v for k, v in snippet.items() if v is not None}, ensure_ascii=False))


if __name__ == "__main__":
    main()
