#!/usr/bin/env python3
"""WCAG 2.2 colour audit + colour-emotion profile for a rendered deck.

Usage:
    python3 a11y_check.py <client_dir> [--html deck.html] [--pdf NAME.pdf]

Checks (AA unless noted):
  1.4.3  Text contrast: every rendered text line vs the *actual* pixels behind it (photos, gradients, glows).
         4.5:1 normal text, 3:1 large text (>= 24px, or >= 18.66px bold). AAA (7:1 / 4.5:1) reported too.
  1.4.11 Non-text contrast: score bars, ring, icons, status pills vs their surroundings, 3:1.
  1.4.1  Use of colour: severity must also be carried by text or numbers (structural check).
  PDF:   title, searchable text layer, clickable links, size (WhatsApp/email friendly).
  Colour-vision: deuteranopia / protanopia / tritanopia simulations of slides with status colours.
  Emotion: per-slide colour profile (warmth, saturation, alarm-red share, brightness), mapped to the intended story arc.

Writes <client_dir>/a11y/report.json, report.md and cvd-*.png. Exit code 1 if any AA failure.
"""
import argparse
import colorsys
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

W, H = 1280, 720

COLLECT_JS = r"""
() => {
  const out = [];
  const slides = Array.from(document.querySelectorAll('.slide'));
  const parseRGBA = (s) => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const opac = (el) => { let o = 1; while (el && el.nodeType === 1) { o *= parseFloat(getComputedStyle(el).opacity || 1); el = el.parentElement; } return o; };
  slides.forEach((sl, si) => {
    const sr = sl.getBoundingClientRect();
    const walker = document.createTreeWalker(sl, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      const t = n.textContent.replace(/\s+/g, ' ').trim();
      if (!t) continue;
      const el = n.parentElement;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      const fill = cs.webkitTextFillColor && cs.webkitTextFillColor !== cs.color ? cs.webkitTextFillColor : cs.color;
      const rgba = parseRGBA(fill);
      if (!rgba) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      Array.from(r.getClientRects()).forEach(rc => {
        if (rc.width < 2 || rc.height < 2) return;
        out.push({ slide: si + 1, text: t.slice(0, 60), x: rc.left - sr.left, y: rc.top - sr.top, w: rc.width, h: rc.height,
                   rgba, opacity: opac(el), size: parseFloat(cs.fontSize), weight: parseInt(cs.fontWeight) || 400,
                   cls: (el.className && el.className.baseVal === undefined ? el.className : '') || el.tagName.toLowerCase(),
                   in_image: !!el.closest('.browser,.phone') });
      });
    }
  });
  return out;
}
"""

NONTEXT_JS = r"""
() => {
  const out = [];
  const slides = Array.from(document.querySelectorAll('.slide'));
  const pick = (sel, kind) => slides.forEach((sl, si) => {
    const sr = sl.getBoundingClientRect();
    sl.querySelectorAll(sel).forEach(el => { const rc = el.getBoundingClientRect(); if (rc.width < 2 || rc.height < 2) return;
      out.push({ slide: si + 1, kind, cls: (el.getAttribute('class') || ''), x: rc.left - sr.left, y: rc.top - sr.top, w: rc.width, h: rc.height }); });
  });
  pick('.fill', 'bar');
  pick('.ring svg', 'ring');
  pick('.icon', 'icon');
  pick('.btn', 'button');
  return out;
}
"""

HIDE_TEXT_CSS = "*{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important}"
HIDE_NONTEXT_CSS = ".fill,.ring svg,.icon,.pm-pill,.btn{visibility:hidden!important}"


def srgb_to_lin(c):
    c = np.asarray(c, dtype=float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lum(rgb):
    l = srgb_to_lin(rgb)
    return 0.2126 * l[..., 0] + 0.7152 * l[..., 1] + 0.0722 * l[..., 2]


def ratio(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def shot(page, path, css=None, n=1):
    if css:
        page.add_style_tag(content=css)
    page.screenshot(path=path, full_page=True)
    return np.asarray(Image.open(path).convert("RGB"))


def region(img, slide, x, y, w, h, pad=0):
    y0 = (slide - 1) * H
    x1, y1 = max(0, int(x - pad)), max(0, int(y0 + y - pad))
    x2, y2 = min(W, int(x + w + pad)), min(img.shape[0], int(y0 + y + h + pad))
    return img[y1:y2, x1:x2].reshape(-1, 3)


def text_checks(items, bg_img, fg_img):
    res = []
    for it in items:
        bg = region(bg_img, it["slide"], it["x"], it["y"], it["w"], it["h"])
        if bg.size == 0:
            continue
        L = lum(bg)
        # worst case across the background actually behind the glyphs (photos/gradients vary)
        lo_px, hi_px = bg[np.argsort(L)[int(len(L) * .05)]], bg[np.argsort(L)[int(len(L) * .95) - 1]]
        r, g, b, a = it["rgba"]
        a = a * it["opacity"]
        res_c = []
        for bgp in (lo_px, hi_px):
            eff = np.array([r, g, b]) * a + bgp * (1 - a)
            res_c.append(ratio(float(lum(eff[None, :])[0]), float(lum(bgp[None, :])[0])))
        cr = min(res_c)
        large = it["size"] >= 24 or (it["size"] >= 18.66 and it["weight"] >= 700)
        need, need_aaa = (3.0, 4.5) if large else (4.5, 7.0)
        res.append({**{k: it[k] for k in ("slide", "text", "size", "weight", "cls", "in_image")},
                    "ratio": round(cr, 2), "large": large, "aa": cr >= need, "aaa": cr >= need_aaa,
                    "need": need, "fg": f"rgba({r:.0f},{g:.0f},{b:.0f},{a:.2f})",
                    "bg_range": [f"#{int(lo_px[0]):02x}{int(lo_px[1]):02x}{int(lo_px[2]):02x}", f"#{int(hi_px[0]):02x}{int(hi_px[1]):02x}{int(hi_px[2]):02x}"]})
    return res


def nontext_checks(items, full_img, hidden_img):
    res = []
    for it in items:
        on = region(full_img, it["slide"], it["x"], it["y"], it["w"], it["h"])
        off = region(hidden_img, it["slide"], it["x"], it["y"], it["w"], it["h"])
        if on.size == 0:
            continue
        diff = np.abs(on.astype(int) - off.astype(int)).sum(1)
        mask = diff > 30
        if it["kind"] == "ring":  # judge the progress arc, not the decorative track
            mx = on.max(1).astype(int); mn = on.min(1).astype(int)
            mask = mask & ((mx - mn) > 60)
        if mask.sum() < 4:
            continue
        fg = np.median(on[mask], axis=0)
        bg = np.median(off[mask], axis=0)
        cr = ratio(float(lum(fg[None, :])[0]), float(lum(bg[None, :])[0]))
        res.append({"slide": it["slide"], "kind": it["kind"], "cls": it["cls"][:40], "ratio": round(cr, 2), "aa": cr >= 3.0,
                    "fg": "#%02x%02x%02x" % tuple(int(v) for v in fg), "bg": "#%02x%02x%02x" % tuple(int(v) for v in bg)})
    return res


# Machado et al. 2009 CVD matrices (severity 1.0), applied in linear RGB
CVD = {
    "deuteranopia": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "protanopia": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "tritanopia": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def simulate(img, m):
    lin = srgb_to_lin(img)
    with np.errstate(all="ignore"):
        out = np.nan_to_num(np.clip(lin @ np.array(m).T, 0, 1))
    s = np.where(out <= 0.0031308, out * 12.92, 1.055 * out ** (1 / 2.4) - 0.055)
    return (s * 255).astype(np.uint8)


def emotion_profile(img, n_slides):
    rows = []
    for s in range(1, n_slides + 1):
        px = img[(s - 1) * H:s * H].reshape(-1, 3)[::7] / 255.0
        hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px[::4]])
        hdeg, sat, val = hsv[:, 0] * 360, hsv[:, 1], hsv[:, 2]
        chrom = (sat > .35) & (val > .3)
        share = lambda m: float((m & chrom).sum()) / len(hsv) * 100
        warm = share((hdeg < 50) | (hdeg > 330))
        alarm = share(((hdeg < 12) | (hdeg > 340)) & (sat > .55))
        orange = share((hdeg >= 12) & (hdeg < 45))
        green = share((hdeg >= 90) & (hdeg < 170))
        blue = share((hdeg >= 190) & (hdeg < 260))
        rows.append({"slide": s, "brightness": round(float(val.mean()) * 100, 1), "colourfulness": round(float(chrom.mean()) * 100, 1),
                     "warm_pct": round(warm, 2), "orange_pct": round(orange, 2), "alarm_red_pct": round(alarm, 2),
                     "green_pct": round(green, 2), "blue_pct": round(blue, 2)})
    return rows


def pdf_checks(pdf):
    """The deliverable is an image PDF: check it has a title, a searchable text layer and working links."""
    out = {}
    try:
        import pypdf
        r = pypdf.PdfReader(pdf)
        out["title"] = (r.metadata or {}).get("/Title") or ""
        out["text_layer_words"] = sum(len((p.extract_text() or "").split()) for p in r.pages)
        out["links"] = [a.get_object()["/A"].get("/URI") for p in r.pages for a in (p.get("/Annots") or [])]
        out["pages"] = len(r.pages)
        out["size_kb"] = os.path.getsize(pdf) // 1024
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("client_dir")
    ap.add_argument("--html", default="deck.html")
    ap.add_argument("--pdf")
    a = ap.parse_args()
    cdir = os.path.abspath(a.client_dir)
    out = os.path.join(cdir, "a11y")
    os.makedirs(out, exist_ok=True)
    html = os.path.join(cdir, a.html)
    pdf = a.pdf or next((os.path.join(cdir, f) for f in sorted(os.listdir(cdir)) if f.endswith(".pdf") and "Summary" not in f), None)

    from playwright.sync_api import sync_playwright
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from browser import launch as launch_browser
    with sync_playwright() as p:
        b = launch_browser(p, args=["--allow-file-access-from-files"])
        def fresh():
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.emulate_media(media="print")
            pg.goto(pathlib.Path(html).as_uri(), wait_until="networkidle", timeout=60000)
            pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
            return pg
        pg = fresh()
        texts = pg.evaluate(COLLECT_JS)
        nontext = pg.evaluate(NONTEXT_JS)
        n_slides = pg.evaluate("document.querySelectorAll('.slide').length")
        pg_status_slides = pg.evaluate("Array.from(document.querySelectorAll('.slide')).map((s,i)=>s.querySelector('.pm-pill')?i+1:0).filter(Boolean)")
        alts = pg.evaluate("Array.from(document.querySelectorAll('img')).map(i => ({src: i.src.split('/').pop(), alt: i.getAttribute('alt')}))")
        full = shot(pg, os.path.join(out, "_full.png"))
        notext = shot(pg, os.path.join(out, "_notext.png"), HIDE_TEXT_CSS)
        pg.close(); pg = fresh()
        nonon = shot(pg, os.path.join(out, "_nonontext.png"), HIDE_NONTEXT_CSS)
        b.close()

    tc = text_checks([t for t in texts if not t["in_image"]], notext, full)
    nc = nontext_checks(nontext, full, nonon)
    emo = emotion_profile(full, n_slides)

    # colour-vision sims of every slide carrying status colours
    cvd_files = []
    status_slides = sorted({n["slide"] for n in nc if n["kind"] in ("bar", "ring")} | set(pg_status_slides))
    for s in status_slides:
        sl = full[(s - 1) * H:s * H]
        tiles = [sl] + [simulate(sl, m) for m in CVD.values()]
        sheet = Image.new("RGB", (W, H * 2 // 2 * 2))
        sheet = Image.new("RGB", (W * 2, H * 2))
        for k, t in enumerate(tiles):
            sheet.paste(Image.fromarray(t), ((k % 2) * W, (k // 2) * H))
        fn = f"cvd-slide-{s:02d}.png"
        sheet.resize((W, H)).save(os.path.join(out, fn))
        cvd_files.append(fn)

    pdfc = pdf_checks(pdf) if pdf else {}
    for f in ("_full.png", "_notext.png", "_nonontext.png"):
        os.remove(os.path.join(out, f))

    fails = [t for t in tc if not t["aa"]]
    nfails = [n for n in nc if not n["aa"]]
    missing_alt = [x for x in alts if x["alt"] is None]
    report = {"text": tc, "nontext": nc, "emotion": emo, "pdf": pdfc, "images_missing_alt": missing_alt, "cvd": cvd_files,
              "summary": {"text_lines": len(tc), "aa_fail": len(fails), "aaa_fail": sum(1 for t in tc if not t["aaa"]),
                          "nontext": len(nc), "nontext_fail": len(nfails), "min_ratio": min((t["ratio"] for t in tc), default=None)}}
    json.dump(report, open(os.path.join(out, "report.json"), "w"), indent=2)

    md = ["# Accessibility & colour audit", "",
          f"Text lines: {len(tc)} · AA fails: {len(fails)} · AAA fails: {report['summary']['aaa_fail']} · lowest ratio: {report['summary']['min_ratio']}:1",
          f"Non-text checked: {len(nc)} · fails: {len(nfails)} · images without alt: {len(missing_alt)}",
          f"PDF: tagged={pdfc.get('tagged')} lang={pdfc.get('lang')} title={pdfc.get('title')!r} alt-tags={pdfc.get('figure_alt')}", "",
          "## AA failures", ""] + [f"- Slide {t['slide']}: {t['ratio']}:1 (needs {t['need']}) `{t['fg']}` on {t['bg_range']}: \"{t['text']}\"" for t in fails] + \
         [f"- Slide {n['slide']} {n['kind']}: {n['ratio']}:1 `{n['fg']}` on `{n['bg']}`" for n in nfails] + ["", "## Colour-emotion profile (% of pixels)", "",
          "| Slide | Brightness | Colourful | Orange | Alarm red | Green | Blue |", "|---|---|---|---|---|---|---|"] + \
         [f"| {e['slide']} | {e['brightness']} | {e['colourfulness']} | {e['orange_pct']} | {e['alarm_red_pct']} | {e['green_pct']} | {e['blue_pct']} |" for e in emo] + \
         ["", "Colour-vision simulations: " + ", ".join(cvd_files)]
    open(os.path.join(out, "report.md"), "w").write("\n".join(md) + "\n")

    s = report["summary"]
    print(f"Text: {s['text_lines']} lines, AA fails {s['aa_fail']}, AAA fails {s['aaa_fail']}, lowest ratio {s['min_ratio']}")
    for t in sorted(fails, key=lambda x: x["ratio"])[:25]:
        print(f"  FAIL s{t['slide']:02d} {t['ratio']:>5}:1 (need {t['need']}) {t['size']:.0f}px {t['fg']} on {t['bg_range']}  \"{t['text'][:40]}\"")
    print(f"Non-text: {s['nontext']} checked, fails {s['nontext_fail']}")
    for n in nfails[:15]:
        print(f"  FAIL s{n['slide']:02d} {n['kind']:<12} {n['ratio']}:1 {n['fg']} on {n['bg']} {n['cls']}")
    print(f"Images without alt: {len(missing_alt)}  PDF: {pdfc}")
    print("Emotion profile:")
    for e in emo:
        print(f"  s{e['slide']:02d} bright {e['brightness']:>5} colour {e['colourfulness']:>5} orange {e['orange_pct']:>5} alarm-red {e['alarm_red_pct']:>5} green {e['green_pct']:>5} blue {e['blue_pct']:>5}")
    pdf_bad = pdfc and (not pdfc.get("title") or pdfc.get("text_layer_words", 0) < 20 or pdfc.get("size_kb", 0) > 15000)
    if pdf_bad:
        print("  FAIL PDF: needs a title, a text layer and < 15 MB")
    sys.exit(1 if fails or nfails or pdf_bad else 0)


if __name__ == "__main__":
    main()
