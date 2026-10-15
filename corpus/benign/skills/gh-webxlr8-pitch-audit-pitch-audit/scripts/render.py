#!/usr/bin/env python3
"""Render <client_dir>/deck-data.json into a 16:9 PDF using a deck style.

Usage:
    python3 render.py <client_dir> [--profile DIR] [--style style-1] [--theme PRODUCT_ID] [--preview] [--out NAME.pdf]

Brand, logo, contact and product logos come from the company profile (./pitch-profile, $PITCH_PROFILE or --profile).
One deck = one brand: the company's. Products appear by logo in the company colours. For a pure single-product
pitch, --theme <offer-id> (or deck-data "theme") uses pitch-profile/themes/<offer-id>.json, credited "A <Company> company".

Writes ONE file per client:
  <name>.pdf   one flattened image per page (1920 px, or 2560 px with --hq) + invisible text layer (searchable/copyable) + clickable links.
               Renders identically in WhatsApp, iOS/Android, Gmail, Outlook and Apple Mail.
  build/deck/ref-XX.png  browser ground truth used by compat_check.py.
--preview writes previews/*.png (identical to the PDF pages). --with-summary adds an optional 1-page summary PDF.
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import pathlib
from PIL import Image
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
STYLES = os.path.normpath(os.path.join(HERE, "..", "styles"))


def load_style(name):
    sdir = os.path.join(STYLES, name)
    lp = os.path.join(sdir, "layouts.py")
    if not os.path.exists(lp):
        sys.exit(f"style '{name}' not found in {STYLES}")
    spec = importlib.util.spec_from_file_location(f"style_{name.replace('-', '_')}", lp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, sdir


OVERFLOW_JS = """() => {
  const out = [];
  document.querySelectorAll('.slide').forEach((s, i) => {
    const sr = s.getBoundingClientRect();
    s.querySelectorAll('.content *').forEach(el => {
      if (el.closest('.browser,.phone,.arc')) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (r.bottom > sr.bottom - 20 || r.right > sr.right - 10 || r.left < sr.left + 10) {
        const t = (el.innerText || '').trim().slice(0, 50);
        if (t) out.push(`slide ${i + 1}: "${t}" overflows (${Math.round(r.right - sr.left)}x${Math.round(r.bottom - sr.top)})`);
      }
    });
  });
  return Array.from(new Set(out)).slice(0, 30);
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("client_dir")
    ap.add_argument("--style", default=None)
    ap.add_argument("--theme", default=None)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--with-summary", action="store_true", help="also write a separate 1-page summary PDF (off by default: one file per client)")
    ap.add_argument("--out")
    ap.add_argument("--hq", action="store_true", help="2560 px pages at JPEG 90 (for print); default 1920 px at 85")
    a = ap.parse_args()

    cdir = os.path.abspath(a.client_dir)
    with open(os.path.join(cdir, "deck-data.json")) as f:
        deck = json.load(f)
    style = a.style or deck.get("style") or "style-1"
    mod, sdir = load_style(style)
    sys.path.insert(0, HERE)
    import profile as P
    style_cfg = {}
    if os.path.exists(os.path.join(sdir, "style.json")):
        with open(os.path.join(sdir, "style.json")) as f:
            style_cfg = json.load(f)
    prof = P.load_profile(a.profile, client_dir=cdir, mode=style_cfg.get("mode", "dark"))
    if style_cfg.get("head_font"):  # a style may set its own heading personality (e.g. an editorial serif)
        hf = style_cfg["head_font"]
        prof["theme"].setdefault("fonts", []).insert(0, P.google_fonts_url([hf]).replace(":wght@400;500;600;700;800", ":wght@500;600;700"))
        prof["theme"]["vars"]["--head"] = f'"{hf}", Georgia, serif'
        prof["theme"]["vars"]["--head-weight"] = str(style_cfg.get("head_weight", 600))
        prof["theme"]["vars"]["--g-font"] = "inherit"
    theme, parent = prof["theme"], None
    theme_name = a.theme or deck.get("theme")
    if theme_name and theme_name not in ("default", prof["company"].get("id")):
        tp = os.path.join(prof["dir"], "themes", f"{theme_name}.json")
        if not os.path.exists(tp):
            sys.exit(f"product theme not found: {tp}")
        with open(tp) as f:
            pt = json.load(f)
        pt["logo"] = P.abspath(os.path.dirname(tp), pt.get("logo")) or theme.get("logo")
        pt.setdefault("contact", theme["contact"])
        parent, theme = {"label": theme.get("label"), "logo": theme.get("logo")}, pt
    theme_name = theme_name or theme.get("name", "company")
    company = prof["company"].get("name", "")

    ctx = {
        "style_dir": sdir, "client_dir": cdir,
        "asset": lambda p: pathlib.Path(os.path.join(sdir, p)).as_uri(),
        "theme": theme, "parent": parent, "products": prof["products"], "profile": prof,
        "theme_asset": lambda p: p if re.match(r"^(https?|file|data):", p) else pathlib.Path(p if os.path.isabs(p) else os.path.join(prof["dir"], p)).as_uri(),
        "client_file": lambda p: pathlib.Path(p if os.path.isabs(p) else os.path.join(cdir, p)).as_uri(),
    }
    client = deck.get("client", {}).get("name") or os.path.basename(cdir)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", client).strip("-")
    cslug = re.sub(r"[^A-Za-z0-9]+", "-", company).strip("-")
    name = a.out or deck.get("file_name") or f"{slug}-Website-Review{'-by-' + cslug if cslug else ''}.pdf"
    jobs = [("deck", deck, os.path.join(cdir, name), os.path.join(cdir, "previews") if a.preview else None)]
    if deck.get("summary") and a.with_summary:
        sdeck = dict(deck, slides=[dict(deck["summary"], layout="summary")])
        sname = deck.get("summary_file_name") or name.replace(".pdf", "-Summary.pdf")
        jobs.append(("summary", sdeck, os.path.join(cdir, sname), os.path.join(cdir, "previews", "summary") if a.preview else None))

    from playwright.sync_api import sync_playwright
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from browser import launch as launch_browser
    with sync_playwright() as p:
        b = launch_browser(p, args=["--allow-file-access-from-files"])
        for kind, dk, pdf_path, pdir in jobs:
            html_path = os.path.join(cdir, f"{kind}.html")
            with open(html_path, "w") as f:
                f.write(mod.render(dk, ctx))
            bdir = os.path.join(cdir, "build", kind)
            if os.path.isdir(bdir):
                shutil.rmtree(bdir)
            os.makedirs(bdir)
            # 1.5x = 1920 px pages: invisible loss on phones (PSNR ≈ 45 dB at phone size), half the file size of 2x.
            bctx = b.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=2 if a.hq else 1.5)
            pg = bctx.new_page()
            pg.emulate_media(media="print")  # lay out exactly as the PDF engine does
            pg.goto(pathlib.Path(html_path).as_uri(), wait_until="networkidle", timeout=60000)
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(400)
            issues = pg.evaluate(OVERFLOW_JS)
            slides = pg.query_selector_all(".slide")

            # 1. reference renders = ground truth of the design
            refs = []
            for n, el in enumerate(slides):
                rp = os.path.join(bdir, f"ref-{n + 1:02d}.png")
                el.screenshot(path=rp)
                refs.append(rp)
            text_runs = pg.evaluate(TEXT_RUNS_JS)

            # 2. THE PDF: one flattened image per page + invisible text layer + links.
            #    Nothing for a viewer to mis-draw: identical in WhatsApp, iOS/Android, Gmail, Outlook, Apple Mail.
            build_share_pdf(refs, text_runs, pdf_path, title=dk.get("title", ""), author=company, quality=90 if a.hq else 85)

            bctx.close()

            if pdir:
                os.makedirs(pdir, exist_ok=True)
                for f in os.listdir(pdir):
                    if f.endswith(".png"):
                        os.remove(os.path.join(pdir, f))
                for n, rp in enumerate(refs):  # previews = exactly what the client sees
                    Image.open(rp).resize((1280, 720), Image.LANCZOS).save(os.path.join(pdir, f"slide-{n + 1:02d}.png"))
            print(f"{kind.upper()}: {len(dk.get('slides', []))} page(s), style {style}, theme {theme_name}")
            print(f"  PDF: {pdf_path}  ({os.path.getsize(pdf_path) // 1024} KB)")
            if issues:
                print("  Layout warnings:")
                for x in issues:
                    print("    " + x)
            else:
                print("  No overflow detected.")
        b.close()


TEXT_RUNS_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('.slide').forEach((sl, si) => {
    const sr = sl.getBoundingClientRect();
    const w = document.createTreeWalker(sl, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      const el = n.parentElement;
      if (!n.textContent.trim() || el.closest('.browser,.phone')) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      const r = document.createRange();
      // one run per rendered line: split the node by line boxes
      const rects = Array.from((r.selectNodeContents(n), r.getClientRects()));
      if (rects.length <= 1) {
        const rc = rects[0]; if (!rc) continue;
        out.push({ s: si, t: n.textContent.replace(/\s+/g, ' ').trim(), x: rc.left - sr.left, y: rc.top - sr.top, w: rc.width, h: rc.height, fs: parseFloat(cs.fontSize) });
      } else {
        const txt = n.textContent; let start = 0;
        for (let i = 1; i <= txt.length; i++) {
          r.setStart(n, start); r.setEnd(n, i);
          const rs = r.getClientRects();
          if (rs.length > 1 || i === txt.length) {
            const end = (rs.length > 1) ? i - 1 : i;
            r.setStart(n, start); r.setEnd(n, end);
            const rc = r.getBoundingClientRect(); const t = txt.slice(start, end).replace(/\s+/g, ' ').trim();
            if (t && rc.width > 1) out.push({ s: si, t, x: rc.left - sr.left, y: rc.top - sr.top, w: rc.width, h: rc.height, fs: parseFloat(cs.fontSize) });
            start = end;
          }
        }
      }
    }
  });
  // links: contact rows, CTA button
  const links = [];
  document.querySelectorAll('.slide').forEach((sl, si) => {
    const sr = sl.getBoundingClientRect();
    sl.querySelectorAll('.contact-row .t, .btn, .footer-note').forEach(el => {
      const t = el.innerText.trim(); let href = null;
      const m = t.match(/[\w.+-]+@[\w-]+\.[\w.]+/); const u = t.match(/\b((?:cal\.com|[\w-]+\.(?:com|in|us|io|org))(?:\/[\w\/-]*)?)/i);
      const tel = t.match(/^\+?[\d\s-]{9,}$/);
      if (m) href = 'mailto:' + m[0]; else if (tel) href = 'tel:' + t.replace(/[^\d+]/g, ''); else if (u) href = 'https://' + u[1];
      if (el.classList.contains('btn')) { const bk = Array.from(sl.querySelectorAll('.contact-row .t')).map(x => x.innerText).find(x => /cal\.com/.test(x)); if (bk) href = 'https://' + bk.trim(); }
      if (!href) return;
      const rc = el.getBoundingClientRect();
      links.push({ s: si, href, x: rc.left - sr.left, y: rc.top - sr.top, w: rc.width, h: rc.height });
    });
  });
  return { runs: out, links };
}
"""




def build_share_pdf(refs, text_runs, out_path, title="", author="", quality=85):
    """Image-per-page PDF with an invisible, selectable/searchable text layer and clickable links."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas

    PW, PH = 960.0, 540.0          # 1280x720 CSS px at 0.75 pt/px
    k = 0.75
    c = canvas.Canvas(out_path, pagesize=(PW, PH))
    c.setTitle(title)
    c.setAuthor(author)
    c.setCreator("pitch-audit")
    runs, links = text_runs["runs"], text_runs["links"]
    for n, rp in enumerate(refs):
        im = Image.open(rp).convert("RGB")
        jp = rp.replace(".png", ".jpg")
        # baseline JPEG, full colour resolution (4:4:4) so coloured small text stays crisp; baseline = widest viewer support
        im.save(jp, "JPEG", quality=quality, optimize=True, progressive=False, subsampling=0)
        c.drawImage(ImageReader(jp), 0, 0, width=PW, height=PH)
        for r in (x for x in runs if x["s"] == n):
            fs = max(4.0, r["fs"] * k)
            sw = stringWidth(r["t"], "Helvetica", fs) or 1
            t = c.beginText()
            t.setTextRenderMode(3)  # invisible: selectable + searchable, never drawn
            t.setFont("Helvetica", fs)
            t.setHorizScale(max(10, min(400, (r["w"] * k) / sw * 100)))
            t.setTextOrigin(r["x"] * k, PH - (r["y"] + r["h"] * 0.8) * k)
            t.textLine(r["t"])
            c.drawText(t)
        for l in (x for x in links if x["s"] == n):
            x0, y1 = l["x"] * k, PH - l["y"] * k
            c.linkURL(l["href"], (x0, y1 - l["h"] * k, x0 + l["w"] * k, y1), relative=0, thickness=0)
        c.showPage()
    c.save()


if __name__ == "__main__":
    main()
