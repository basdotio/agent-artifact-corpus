#!/usr/bin/env python3
"""Draft a company profile (the seller) from its website, plus any brand files you point at.

Usage:
    python3 setup_profile.py <your-company-url> [--out pitch-profile] [--assets <brand-folder>] [--force]

What it does
  - Crawls the homepage + up to 8 key pages (services, products, work, about, contact, pricing).
  - Detects: company name, tagline, contact (email, phone, address, booking link), social links,
    brand colours (from buttons/links/headings), heading + body fonts, logo (rendered from the page).
  - If --assets is given (or brand files are missing online), picks logos from that folder by file name
    (logo*, *white*, *light*, *dark*, *.svg/png) and local font files.
  - Writes company.yaml (filled), catalog.yaml / mapping.yaml / proof.yaml (skeletons with TODOs),
    brand/ (logos), _sources/*.txt (page text for Claude to draft the catalog), setup-report.md
    (what was found, what is missing, how to point at your own files).
Next: Claude fills catalog/mapping/proof from _sources (see SKILL.md "Setup"), you review, then run
profile_check.py.
"""
import argparse
import os
import re
import shutil
import sys
import urllib.parse
from collections import Counter

import numpy as np
import yaml
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import profile as P  # noqa: E402

PAGE_HINTS = r"(service|solution|product|platform|offer|what-we-do|capabilit|work|case|portfolio|client|about|company|contact|pricing|plans|industr)"
BOOKING = r"(calendly\.com/[^\s\"'<>]+|cal\.com/[^\s\"'<>]+|meetings\.hubspot\.com/[^\s\"'<>]+|zcal\.co/[^\s\"'<>]+|tidycal\.com/[^\s\"'<>]+|savvycal\.com/[^\s\"'<>]+)"
SOCIAL = {"linkedin": r"linkedin\.com/(company|in|school)/[A-Za-z0-9_\-%.]+", "instagram": r"instagram\.com/[A-Za-z0-9_.]+",
          "facebook": r"facebook\.com/[A-Za-z0-9_.\-]+", "x": r"(twitter|x)\.com/[A-Za-z0-9_]+", "youtube": r"youtube\.com/(@|channel/|c/)[A-Za-z0-9_\-]+"}

SCAN_JS = r"""
() => {
  const q = s => Array.from(document.querySelectorAll(s));
  const meta = n => (document.querySelector(`meta[name="${n}"],meta[property="${n}"]`) || {}).content || null;
  const vis = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const rgb = c => { const m = (c || '').match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    if (p.length > 3 && p[3] < 0.5) return null; return '#' + p.slice(0, 3).map(x => Math.round(x).toString(16).padStart(2, '0')).join(''); };
  const colours = [];
  q('a, button, [class*="btn"], [class*="button"], h1, h2, h3, [class*="accent"], [class*="primary"]').filter(vis).slice(0, 400).forEach(el => {
    const cs = getComputedStyle(el); const w = (el.matches('button,[class*="btn"],[class*="button"]') ? 3 : 1);
    [cs.backgroundColor, cs.color, cs.borderTopColor].forEach((c, i) => { const h = rgb(c); if (h) colours.push([h, w * (i === 0 ? 2 : 1)]); });
  });
  const cssVars = [];
  try { for (const sh of document.styleSheets) { let rules; try { rules = sh.cssRules; } catch (e) { continue; }
    for (const r of rules) { if (r.style) for (const k of r.style) if (k.startsWith('--')) { const v = r.style.getPropertyValue(k).trim(); if (/^#[0-9a-f]{3,8}$/i.test(v)) cssVars.push([k, v]); } } } } catch (e) {}
  const font = sel => { const el = document.querySelector(sel); return el ? getComputedStyle(el).fontFamily : null; };
  // logo candidates: header/nav images or svgs that mention logo or link home
  const cands = q('header img, header svg, nav img, nav svg, [class*="logo"] img, [class*="logo"] svg, img[alt*="logo" i], img[src*="logo" i], a[href="/"] img, a[href="/"] svg, [class*="logo"]')
    .filter(vis).map(el => { const r = el.getBoundingClientRect(); return { r, el }; })
    .filter(x => x.r.width >= 40 && x.r.height >= 12 && x.r.height <= 160 && x.r.top < 300)
    .sort((a, b) => a.r.top - b.r.top || a.r.left - b.r.left);
  // logo sources: the image URL, or inline SVG with computed colours baked in (so it renders alone)
  const inlineSvg = (svg) => { const c = svg.cloneNode(true); const src = [svg, ...svg.querySelectorAll('*')], dst = [c, ...c.querySelectorAll('*')];
    src.forEach((n, i) => { const cs = getComputedStyle(n); ['fill', 'stroke', 'color', 'opacity', 'stroke-width'].forEach(k => { const v = cs.getPropertyValue(k); if (v) dst[i].style.setProperty(k, v); }); });
    const r = svg.getBoundingClientRect(); c.setAttribute('width', r.width); c.setAttribute('height', r.height);
    if (!c.getAttribute('xmlns')) c.setAttribute('xmlns', 'http://www.w3.org/2000/svg'); return c.outerHTML; };
  const logoSrc = cands.slice(0, 4).map(x => { let el = x.el;
      if (!['IMG', 'svg'].includes(el.tagName)) el = el.querySelector('img, svg') || el;
      if (el.tagName === 'IMG') return { kind: 'img', src: el.currentSrc || el.src, w: x.r.width, h: x.r.height };
      if (el.tagName.toLowerCase() === 'svg') return { kind: 'svg', svg: inlineSvg(el), w: x.r.width, h: x.r.height };
      return null; }).filter(Boolean);
  const links = q('a[href]').map(a => ({ href: a.href, text: (a.innerText || '').trim().slice(0, 60) }));
  const ld = []; q('script[type="application/ld+json"]').forEach(s => { try { ld.push(JSON.parse(s.textContent)); } catch (e) {} });
  return {
    title: document.title, site_name: meta('og:site_name'), desc: meta('description') || meta('og:description'),
    og_image: meta('og:image'), touch_icon: (document.querySelector('link[rel="apple-touch-icon"]') || {}).href || null,
    body_bg: rgb(getComputedStyle(document.body).backgroundColor) || rgb(getComputedStyle(document.documentElement).backgroundColor) || '#ffffff',
    font_head: font('h1') || font('h2'), font_body: font('p') || font('body'),
    colours, cssVars, logos: logoSrc, links, ld,
    text: (document.body.innerText || '').replace(/\n{3,}/g, '\n\n').slice(0, 20000),
  };
}
"""


def hexn(h):
    h = h.lower()
    return "#" + "".join(c * 2 for c in h[1:4]) if len(h) == 4 else h[:7]


def saturation(h):
    r, g, b = (x / 255 for x in P.hex_to_rgb(h))
    mx, mn = max(r, g, b), min(r, g, b)
    return 0 if mx == 0 else (mx - mn) / mx, mx


def pick_accent(colours, css_vars):
    score = Counter()
    for h, w in colours:
        s, v = saturation(hexn(h))
        if s > 0.35 and 0.25 < v:
            score[hexn(h)] += w
    for k, v in css_vars:
        s, val = saturation(hexn(v))
        if s > 0.35 and val > 0.25:
            score[hexn(v)] += 6 if re.search(r"(primary|accent|brand|orange|blue|green|red|purple)", k) else 2
    return [c for c, _ in score.most_common(5)]


def first_family(ff):
    if not ff:
        return None
    f = ff.split(",")[0].strip().strip("\"'")
    return None if f.lower() in ("system-ui", "-apple-system", "sans-serif", "serif", "arial", "helvetica", "inherit", "ui-sans-serif") else f


def _px(png):
    im = np.asarray(Image.open(png).convert("RGBA"), dtype=float)
    a = im[..., 3] > 60
    rgb = im[..., :3] / 255
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    lum = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    sat = (rgb.max(-1) - rgb.min(-1)) / np.maximum(rgb.max(-1), 1e-6)
    return im, a, lum, sat


def logo_kind(png):
    """'light' only if almost no visible pixel is dark (dark parts would vanish on a dark slide)."""
    im, a, lum, sat = _px(png)
    if a.sum() < 30:
        return None, 0
    dark_share = float(((lum < 0.18) & a).sum()) / a.sum()
    return ("light" if dark_share < 0.08 else "dark"), dark_share


def make_white(src, dst):
    """Version for dark slides: dark neutral pixels (text, outlines) turn white; brand-coloured parts keep their colour."""
    im, a, lum, sat = _px(src)
    out = im.copy()
    neutral_dark = (sat < 0.35) & (lum < 0.35)
    out[neutral_dark, 0:3] = 255
    Image.fromarray(out.astype(np.uint8), "RGBA").save(dst)


def render_logos(ctx, sources, out_dir):
    """Render each logo source alone on a transparent page; keep the original file too."""
    import base64
    import urllib.request
    pg = ctx.new_page()
    files = []
    for i, src in enumerate(sources[:3]):
        try:
            if src["kind"] == "img":
                req = urllib.request.Request(src["src"], headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=20).read()
                ext = ".svg" if (b"<svg" in data[:2000]) else os.path.splitext(urllib.parse.urlparse(src["src"]).path)[1] or ".png"
                orig = os.path.join(out_dir, f"_logo-original-{i}{ext}")
                open(orig, "wb").write(data)
                mime = "image/svg+xml" if ext == ".svg" else "image/" + ext.strip(".").replace("jpg", "jpeg")
                inner = f'<img src="data:{mime};base64,{base64.b64encode(data).decode()}" style="height:{max(40, src["h"])}px;width:auto;display:block">'
            else:
                orig = os.path.join(out_dir, f"_logo-original-{i}.svg")
                open(orig, "w").write(src["svg"])
                inner = f'<div style="height:{src["h"]}px;width:{src["w"]}px">{src["svg"]}</div>'
            pg.set_content(f'<html style="background:transparent"><body style="margin:0;background:transparent"><div id="l" style="display:inline-block">{inner}</div></body></html>')
            pg.wait_for_timeout(250)
            fp = os.path.join(out_dir, f"_logo-candidate-{i}.png")
            pg.locator("#l").screenshot(path=fp, omit_background=True)
            im = knock_out_background(Image.open(fp).convert("RGBA"))
            bbox = im.split()[3].point(lambda v: 255 if v > 20 else 0).getbbox()
            if bbox and (bbox[2] - bbox[0]) > 40:
                im.crop(bbox).save(fp)
                files.append((fp, orig))
        except Exception:  # noqa: BLE001
            continue
    pg.close()
    return files


def knock_out_background(im, tol=28):
    """Logos saved as JPG/PNG on a solid box (usually white): make that box transparent, keep soft edges."""
    a = np.asarray(im, dtype=float)
    if (a[..., 3] < 250).mean() > 0.05:  # already has real transparency
        return im
    h, w = a.shape[:2]
    corners = np.array([a[2, 2, :3], a[2, w - 3, :3], a[h - 3, 2, :3], a[h - 3, w - 3, :3]])
    if np.ptp(corners, axis=0).max() > 18:  # corners differ: not a solid box
        return im
    bgc = corners.mean(0)
    dist = np.abs(a[..., :3] - bgc).max(-1)
    alpha = np.clip((dist - 6) / tol, 0, 1) * 255
    a[..., 3] = np.minimum(a[..., 3], alpha)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def scan_assets(folder):
    found = {"logo_on_dark": None, "logo": None, "fonts": []}
    for root, _, files in os.walk(folder):
        for f in files:
            p, lf = os.path.join(root, f), f.lower()
            if lf.endswith((".ttf", ".otf", ".woff", ".woff2")):
                found["fonts"].append(p)
            elif lf.endswith((".png", ".svg", ".webp")) and "logo" in lf:
                if re.search(r"(white|light|reverse|negative|on[-_]?dark|inverse)", lf):
                    found["logo_on_dark"] = found["logo_on_dark"] or p
                elif re.search(r"(dark|black|primary|colou?r|main)", lf) or not found["logo"]:
                    found["logo"] = found["logo"] or p
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="pitch-profile")
    ap.add_argument("--assets")
    ap.add_argument("--max-pages", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    url = a.url if re.match(r"^https?://", a.url) else "https://" + a.url
    out = os.path.abspath(a.out)
    if os.path.exists(os.path.join(out, "company.yaml")) and not a.force:
        sys.exit(f"{out}/company.yaml exists. Use --force to redo setup (your edits would be overwritten).")
    os.makedirs(os.path.join(out, "brand"), exist_ok=True)
    for f in os.listdir(os.path.join(out, "brand")):  # only files this script generates; your own logos are kept
        if f.startswith(("logo-from-site", "logo-on-dark-auto", "_logo-")):
            os.remove(os.path.join(out, "brand", f))
    src_dir = os.path.join(out, "_sources")
    shutil.rmtree(src_dir, ignore_errors=True)
    os.makedirs(src_dir)
    report = {"found": [], "missing": [], "notes": []}

    from playwright.sync_api import sync_playwright
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from browser import launch as launch_browser
    with sync_playwright() as p:
        b = launch_browser(p)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=3)
        pg = ctx.new_page()
        pg.goto(url, wait_until="load", timeout=60000)
        try:
            pg.wait_for_load_state("networkidle", timeout=10000)
        except Exception:  # noqa: BLE001
            pass
        home = pg.evaluate(SCAN_JS)
        final = pg.url
        open(os.path.join(src_dir, "home.txt"), "w").write(f"URL: {final}\n\n{home['text']}")
        logos = render_logos(ctx, home["logos"], os.path.join(out, "brand"))
        host = urllib.parse.urlparse(final).hostname or ""
        pages, seen = [], {final.rstrip("/")}
        for l in home["links"]:
            u = l["href"].split("#")[0].rstrip("/")
            pu = urllib.parse.urlparse(u)
            if pu.hostname and pu.hostname.replace("www.", "") == host.replace("www.", "") and u not in seen and re.search(PAGE_HINTS, pu.path, re.I):
                seen.add(u)
                pages.append(u)
        texts = home["text"]
        all_links = list(home["links"])
        for u in pages[: a.max_pages]:
            try:
                pg.goto(u, wait_until="load", timeout=30000)
                d = pg.evaluate(SCAN_JS)
                name = re.sub(r"[^a-z0-9]+", "-", urllib.parse.urlparse(u).path.lower()).strip("-") or "page"
                open(os.path.join(src_dir, f"{name}.txt"), "w").write(f"URL: {u}\n\n{d['text']}")
                texts += "\n" + d["text"]
                all_links += d["links"]
            except Exception as e:  # noqa: BLE001
                report["notes"].append(f"could not read {u}: {str(e)[:80]}")
        b.close()

    hrefs = " ".join(l["href"] for l in all_links)
    emails = Counter(re.findall(r"mailto:([^?\"'\s]+)", hrefs) + re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", texts))
    phones = Counter((l["text"] if re.fullmatch(r"\+?[\d\s().-]{8,}", l["text"] or "") else re.sub(r"[^\d+]", "", l["href"][4:]))
                     for l in all_links if l["href"].startswith("tel:"))
    booking = re.search(BOOKING, hrefs + " " + texts)
    social = {k: (m.group(0) if (m := re.search(r"https?://(www\.)?" + v, hrefs)) else None) for k, v in SOCIAL.items()}
    address = address_short = None
    for blk in home["ld"]:
        for o in (blk if isinstance(blk, list) else blk.get("@graph", [blk]) if isinstance(blk, dict) else []):
            if isinstance(o, dict) and isinstance(o.get("address"), dict):
                ad = o["address"]
                address = ", ".join(str(ad.get(k)) for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry") if ad.get(k))
                address_short = ", ".join(str(ad.get(k)) for k in ("addressLocality", "addressCountry") if ad.get(k)) or None
                break
    name = (home.get("site_name") or re.split(r"\s[|\-–·:]\s", home.get("title") or "")[-1] or host.split(".")[0]).strip()
    accents = pick_accent(home["colours"], home["cssVars"])
    head_font, body_font = first_family(home["font_head"]), first_family(home["font_body"])

    # ---- logos: pointed-at assets win, then the rendered site logo
    brand = {"logo_on_dark": None, "logo": None, "logo_height": 30}
    assets = scan_assets(a.assets) if a.assets else {"logo_on_dark": None, "logo": None, "fonts": []}
    for key in ("logo_on_dark", "logo"):
        if assets[key]:
            ext = os.path.splitext(assets[key])[1]
            dst = os.path.join(out, "brand", ("logo-on-dark" if key == "logo_on_dark" else "logo") + ext)
            shutil.copy(assets[key], dst)
            brand[key] = os.path.relpath(dst, out)
            report["found"].append(f"{key}: from your assets folder ({assets[key]})")
    if logos:
        kind, lum = logo_kind(logos[0][0])
        site_logo = os.path.join(out, "brand", "logo-from-site.png")
        shutil.move(logos[0][0], site_logo)
        ext = os.path.splitext(logos[0][1])[1]
        shutil.move(logos[0][1], os.path.join(out, "brand", "logo-from-site-original" + ext))
        if not brand["logo"] and kind == "dark":
            brand["logo"] = os.path.relpath(site_logo, out)
        if not brand["logo_on_dark"]:
            if kind == "light":
                brand["logo_on_dark"] = os.path.relpath(site_logo, out)
                report["found"].append("logo_on_dark: rendered from your website header (light logo)")
            else:
                auto = os.path.join(out, "brand", "logo-on-dark-auto.png")
                make_white(site_logo, auto)
                brand["logo_on_dark"] = os.path.relpath(auto, out)
                report["notes"].append("logo_on_dark: your site logo is dark, so a white version was auto-generated "
                                       "(brand/logo-on-dark-auto.png). Replace it with your official light/white logo if you have one.")
    for f in os.listdir(os.path.join(out, "brand")):
        if f.startswith(("_logo-candidate", "_logo-original")):
            os.remove(os.path.join(out, "brand", f))
    if not brand["logo_on_dark"]:
        report["missing"].append("Logo: none found. Put a white/light logo (PNG/SVG, ≥ 600 px wide) in pitch-profile/brand/ "
                                 "and set brand.logo_on_dark in company.yaml, or re-run with --assets <your-brand-folder>.")
    fonts_css = None
    if assets["fonts"]:
        fonts_dir = os.path.join(out, "brand", "fonts")
        os.makedirs(fonts_dir, exist_ok=True)
        faces = []
        for fp in assets["fonts"]:
            shutil.copy(fp, fonts_dir)
            fam = re.split(r"[-_ ]", os.path.splitext(os.path.basename(fp))[0])[0]
            w = 800 if re.search(r"(black|extrabold|heavy)", fp, re.I) else 700 if re.search("bold", fp, re.I) else 500 if re.search("medium", fp, re.I) else 400
            faces.append(f'@font-face{{font-family:"{fam}";src:url("fonts/{os.path.basename(fp)}");font-weight:{w};}}')
        fonts_css = os.path.join(out, "brand", "fonts.css")
        open(fonts_css, "w").write("\n".join(faces) + "\n")
        report["found"].append(f"fonts: {len(assets['fonts'])} local font files → brand/fonts.css")

    company = {
        "id": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
        "name": name, "website": final.rstrip("/"),
        "tagline": None, "one_liner": (home.get("desc") or "")[:180] or None,
        "region": None, "currency": "USD", "language": "en",
        "contact": {"email": emails.most_common(1)[0][0] if emails else None,
                    "phone": phones.most_common(1)[0][0] if phones else None,
                    "address": address, "address_short": address_short,
                    "booking_url": ("https://" + booking.group(1)) if booking else None},
        "social": {k: v for k, v in social.items() if v},
        "brand": {**brand, "accent": accents[0] if accents else None, "accent_candidates": accents,
                  "site_background": home["body_bg"], "background": "#0B0B0B",
                  "heading_font": head_font, "body_font": body_font, "fonts_css": "brand/fonts.css" if fonts_css else None},
    }
    for k, v in (("email", company["contact"]["email"]), ("phone", company["contact"]["phone"]),
                 ("booking link", company["contact"]["booking_url"]), ("accent colour", company["brand"]["accent"])):
        (report["found"] if v else report["missing"]).append(f"{k}: {v}" if v else f"{k}: not found. Fill it in company.yaml")
    with open(os.path.join(out, "company.yaml"), "w") as f:
        f.write("# Drafted by setup_profile.py from " + final + ". Review every field.\n")
        yaml.safe_dump(company, f, sort_keys=False, allow_unicode=True)
    skel = {
        "catalog.yaml": {"offers": [{"id": "TODO-offer-id", "name": "TODO offer name", "type": "service",
                                     "capabilities": ["web"], "promise": "TODO one line", "includes": ["TODO"],
                                     "first_step": "TODO smallest first step", "price": None}]},
        "mapping.yaml": {"capabilities": {c: "TODO-offer-id" for c in P.CAPABILITIES},
                         "fit_rules": [{"offer": "TODO-offer-id", "score": 80, "keywords": ["TODO industry keyword"]}],
                         "default_fit": {"offer": "TODO-offer-id", "score": 50},
                         "guidance": "TODO: when to lead with which offer"},
        "proof.yaml": {"stats": [], "clients": [], "case_studies": [], "how_we_work": []},
    }
    for fn, data in skel.items():
        fp = os.path.join(out, fn)
        if not os.path.exists(fp) or a.force:
            with open(fp, "w") as f:
                f.write("# Skeleton: Claude drafts this from _sources/*.txt, you approve it. Only real, public claims.\n")
                yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    rep = [f"# Profile setup report: {name}", "", f"Source: {final}  ·  pages read: {1 + min(len(pages), a.max_pages)}", "", "## Found", ""]
    rep += [f"- {x}" for x in report["found"]] + ["", "## Missing: please provide", ""] + [f"- {x}" for x in report["missing"] or ["nothing"]]
    rep += ["", "## Notes", ""] + [f"- {x}" for x in report["notes"] or ["none"]]
    rep += ["", "## How to point at your own files",
            "- Logos: copy into `pitch-profile/brand/` and set `brand.logo_on_dark` (white/light, for dark slides) and `brand.logo` in company.yaml.",
            "- Or re-run: `setup_profile.py <url> --assets <folder> --force` (picks files named *logo*white*, *logo*dark*, fonts).",
            "- Colours: set `brand.accent` (and optionally `accent_2`, `background`). Candidates found: " + ", ".join(accents or ["none"]),
            "- Fonts: Google Fonts names in `heading_font` / `body_font`, or local files via --assets.",
            "", "Next: Claude drafts catalog.yaml, mapping.yaml, proof.yaml from `_sources/`. Then run `profile_check.py`."]
    open(os.path.join(out, "setup-report.md"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
