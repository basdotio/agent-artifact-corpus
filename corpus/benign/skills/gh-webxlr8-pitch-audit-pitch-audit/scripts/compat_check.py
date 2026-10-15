#!/usr/bin/env python3
"""Viewer-compatibility check: does every PDF look the same in real viewers as in the browser?

Usage:
    python3 compat_check.py <client_dir>

For each deliverable PDF (share + accessible, deck + summary) it renders every page with:
  - Apple PDFKit  (WhatsApp on iPhone/Mac, Apple Mail, Preview)   via pdfkit_render.swift (macOS only)
  - PDFium        (Chrome, Android PdfRenderer, Gmail/Drive previews)   via pypdfium2 (any OS)
  - poppler       (pdftoppm; Linux desktop viewers), optional: used when installed
and compares each page against the browser reference build/<kind>/ref-XX.png in 32x32 px tiles.
A page FAILS (after a 2.5 px blur that removes anti-aliasing noise) when any tile's mean difference > 30/255 (missing photo tile, dropped mask, lost shadow
block) or the whole page differs > 5/255 on average. Writes compat/report.md and diff sheets.
Exit code 1 if the SHARE pdf fails anywhere (that is the file we send).
"""
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1280, 720
TILE, TILE_FAIL, PAGE_FAIL = 32, 30.0, 5.0


def pdfkit_binary():
    """Compile pdfkit_render.swift once into a cache (keyed by source hash); later runs start instantly."""
    import hashlib
    src = os.path.join(HERE, "pdfkit_render.swift")
    h = hashlib.sha1(open(src, "rb").read()).hexdigest()[:12]
    cache = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "pitch-audit")
    exe = os.path.join(cache, f"pdfkit_render-{h}")
    if os.path.exists(exe):
        return [exe]
    if shutil.which("swiftc"):
        os.makedirs(cache, exist_ok=True)
        r = subprocess.run(["swiftc", "-O", src, "-o", exe], capture_output=True, text=True)
        if r.returncode == 0:
            return [exe]
    return ["swift", src]  # interpreted fallback (slower)


def render_pdfkit(pdf, out):
    if sys.platform != "darwin" or not (shutil.which("swiftc") or shutil.which("swift")):
        return None
    r = subprocess.run(pdfkit_binary() + [pdf, out, str(W)], capture_output=True, text=True)
    return sorted(os.path.join(out, f) for f in os.listdir(out)) if r.returncode == 0 else None


def render_pdfium(pdf, out):
    """PDFium = the engine in Chrome, Android's PdfRenderer and Gmail/Drive previews. Pure pip install, any OS."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return None
    os.makedirs(out, exist_ok=True)
    doc = pdfium.PdfDocument(pdf)
    files = []
    for i in range(len(doc)):
        page = doc[i]
        img = page.render(scale=W / page.get_width()).to_pil()
        fp = os.path.join(out, f"page-{i + 1:02d}.png")
        img.save(fp)
        files.append(fp)
    return files


def render_poppler(pdf, out):
    if not shutil.which("pdftoppm"):
        return None
    os.makedirs(out, exist_ok=True)
    subprocess.run(["pdftoppm", "-png", "-scale-to-x", str(W), "-scale-to-y", str(H), pdf, os.path.join(out, "page")],
                   check=True, stderr=subprocess.DEVNULL)
    return sorted(os.path.join(out, f) for f in os.listdir(out) if f.endswith(".png"))


def structure_check(pdf):
    """Engine-independent guarantee: each page is ONE opaque image + invisible text + links.
    Soft masks, shadings and transparency groups are what WhatsApp/PDFKit mis-draw, so any of them = FAIL."""
    import pypdf
    problems = []
    r = pypdf.PdfReader(pdf)
    for n, page in enumerate(r.pages, 1):
        res = page.get("/Resources") or {}
        res = res.get_object() if hasattr(res, "get_object") else res
        xo = (res.get("/XObject") or {})
        xo = xo.get_object() if hasattr(xo, "get_object") else xo
        imgs = forms = 0
        for k in xo:
            o = xo[k].get_object()
            if o.get("/Subtype") == "/Image":
                imgs += 1
                if "/SMask" in o or "/Mask" in o:
                    problems.append(f"page {n}: image {k} has a soft mask")
            elif o.get("/Subtype") == "/Form":
                forms += 1
        if imgs != 1:
            problems.append(f"page {n}: {imgs} images (expected exactly 1 flattened page image)")
        if forms:
            problems.append(f"page {n}: {forms} form XObjects / transparency groups")
        if res.get("/Shading") or res.get("/Pattern"):
            problems.append(f"page {n}: shading/pattern resources")
        gs = res.get("/ExtGState") or {}
        gs = gs.get_object() if hasattr(gs, "get_object") else gs
        for k in gs:
            g = gs[k].get_object()
            if g.get("/SMask") not in (None, "/None") or float(g.get("/ca", 1)) < 1 or float(g.get("/CA", 1)) < 1:
                problems.append(f"page {n}: transparency in graphics state {k}")
        if "/Group" in page:
            problems.append(f"page {n}: page transparency group")
    return problems


def compare(ref_path, got_path):
    # blur first: ignore anti-aliasing / resampling noise, keep real breakage (missing tiles, dropped masks)
    prep = lambda p: np.asarray(Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.5)), dtype=float)
    a, b = prep(ref_path), prep(got_path)
    d = np.abs(a - b).mean(2)
    tiles = d[: H // TILE * TILE, : W // TILE * TILE].reshape(H // TILE, TILE, W // TILE, TILE).mean((1, 3))
    worst = float(tiles.max())
    bad = np.argwhere(tiles > TILE_FAIL)
    return float(d.mean()), worst, bad, d


def main():
    cdir = os.path.abspath(sys.argv[1])
    out = os.path.join(cdir, "compat")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    pdfs = sorted(f for f in os.listdir(cdir) if f.endswith(".pdf"))
    lines, share_fail, engines_run = ["# PDF viewer compatibility", ""], False, 0
    for f in pdfs:
        kind = "summary" if "Summary" in f else "deck"
        refdir = os.path.join(cdir, "build", kind)
        refs = sorted(os.path.join(refdir, x) for x in os.listdir(refdir) if re.match(r"ref-\d+\.png$", x))
        is_share = True
        lines += [f"## {f}", ""]
        sp = structure_check(os.path.join(cdir, f))
        st = "PASS" if not sp else "FAIL"
        if sp:
            share_fail = True
        lines.append(f"- Structure (flat pages, no masks/transparency): **{st}**" + (": " + "; ".join(sp[:6]) if sp else ""))
        print(f"{f[:60]:<60} {'Structure (any viewer)':<36} {st} {'; '.join(sp[:3])}")
        for eng, fn in (("PDFKit (Apple: WhatsApp/iOS/Mail)", render_pdfkit), ("PDFium (Chrome/Android/Gmail)", render_pdfium),
                        ("poppler (Linux/desktop)", render_poppler)):
            edir = os.path.join(out, re.sub(r"\W+", "_", f + "_" + eng.split()[0]))
            pages = fn(os.path.join(cdir, f), edir)
            if pages is None:
                lines.append(f"- {eng}: not available on this machine")
                print(f"{f[:60]:<60} {eng:<36} SKIPPED (not available here)")
                continue
            engines_run += 1
            fails = []
            for n, (rp, gp) in enumerate(zip(refs, pages)):
                mean, worst, bad, d = compare(rp, gp)
                if len(bad) or mean > PAGE_FAIL:
                    fails.append((n + 1, mean, worst, len(bad)))
                    heat = Image.fromarray(np.clip(d * 4, 0, 255).astype(np.uint8)).convert("RGB")
                    sheet = Image.new("RGB", (W * 3, H))
                    for k, im in enumerate([Image.open(rp).convert("RGB").resize((W, H)), Image.open(gp).convert("RGB").resize((W, H)), heat]):
                        sheet.paste(im, (k * W, 0))
                    sheet.resize((W * 3 // 2, H // 2)).save(os.path.join(out, f"FAIL_{kind}_{'share' if is_share else 'acc'}_{eng.split()[0]}_p{n + 1:02d}.png"))
            if len(pages) != len(refs):
                fails.append((0, 0, 0, -1))
            status = "PASS" if not fails else "FAIL"
            if fails and is_share:
                share_fail = True
            detail = "; ".join(f"page {p}: avg {m:.1f}, worst tile {w:.0f}, {c} bad tiles" if c >= 0 else "page count differs" for p, m, w, c in fails)
            lines.append(f"- {eng}: **{status}**" + (f": {detail}" if detail else ""))
            print(f"{f[:60]:<60} {eng:<36} {status} {detail}")
        lines.append("")
    open(os.path.join(out, "report.md"), "w").write("\n".join(lines) + "\n")
    if engines_run < 1:
        print("FAIL: no PDF engine available. pip install pypdfium2 (any OS); macOS also uses Apple PDFKit.")
        sys.exit(1)
    sys.exit(1 if share_fail else 0)


if __name__ == "__main__":
    main()
