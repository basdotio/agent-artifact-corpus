#!/usr/bin/env python3
"""Render an explainer page and check it before it goes to the reader.

Opens the HTML file in headless Chromium at five widths (1440, 1280, 1024,
800 and 390 px), takes screenshots, prints the page to A4, and checks:

errors (the page fails)
  - network requests other than Google Fonts, and local files other than the
    page itself (the page must be self-contained)
  - horizontal page overflow, and content that spills out of or is clipped by
    its box (width or height)
  - annotation labels (.ann-label or [data-no-overlap]) that overlap each
    other, sit on top of the annotated text, or run outside their panel
  - SVG <text> labels that overlap each other or run outside their SVG
  - text-wrap: balance or pretty; max-width that narrows running text
  - one-sided accent marks: a coloured single edge on a box (border, pseudo-
    element bar, hard-stop gradient stripe, inset edge shadow)
  - em dashes, spaced en dashes or emoji in visible text (text inside
    data-ste="ignore", code and pre is exempt)
  - JavaScript errors on load
  - printed text smaller than 4.5 pt (A4) or 6.5 pt (A3)
warnings (look at them)
  - a spec sheet that needs more than one printed page; printed text under
    6.5 pt on A4 (ship the A3 PDF for a sheet that will be pinned up)
  - body paragraphs not justified at desktop width, or justified on a phone
  - <br> inside running text
  - a panel with a large empty area at the bottom
  - <title> that does not match the page's <h1>

Usage:
  check_page.py PAGE.html [--out DIR] [--json]
  check_page.py --self-test
Writes DIR/desktop.png (1440, full page), DIR/mobile.png (390, full page),
readable 2x tiles DIR/mobile-01.png ... and, for tall pages, DIR/desktop-01.png
..., DIR/print.pdf (the page's own print size, A4 by default), DIR/print-a3.pdf
(for a spec sheet: <html data-paper="a3">) and DIR/report.json. DIR defaults to a folder in the system
temp directory, so check output never lands in the user's project.
Exit code 0 pass, 1 fail, 2 the page could not be opened.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

PROBE_WIDTHS = [1440, 1280, 1024, 800, 390]
ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
TILE_H = {"desktop": 1100, "mobile": 800}

PAGE_PROBE = r"""
(viewportName) => {
  const errors = [];
  const warnings = [];
  const vw = window.innerWidth;
  const path = (el) => {
    const parts = [];
    while (el && el.nodeType === 1 && parts.length < 4) {
      let s = el.tagName.toLowerCase();
      if (el.id) { s += '#' + el.id; parts.unshift(s); break; }
      if (el.classList.length) s += '.' + [...el.classList].slice(0, 2).join('.');
      parts.unshift(s);
      el = el.parentElement;
    }
    return parts.join(' > ');
  };
  const hits = (a, b, pad = 1) => a.width && b.width && a.left < b.right - pad && b.left < a.right - pad && a.top < b.bottom - pad && b.top < a.bottom - pad;
  const rgb = (c) => { const m = (c || '').match(/[\d.]+/g); return m ? m.map(Number) : [0, 0, 0, 0]; };
  const coloured = (c) => { const [r, g, b, a = 1] = rgb(c); return a > 0.05 && (Math.max(r, g, b) - Math.min(r, g, b)) > 40; };
  const visible = (c) => { const v = rgb(c); return (v.length < 4 || v[3] > 0.05); };

  const docW = document.documentElement.scrollWidth;
  if (docW > vw + 1) errors.push({rule: 'page-overflow', detail: `page is ${docW}px wide in a ${vw}px viewport`});

  const all = [...document.body.querySelectorAll('*')];
  let spills = 0;
  for (const el of all) {
    const tag = el.tagName.toLowerCase();
    if (el.closest('svg') && tag !== 'svg') continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const scrollsX = ['auto', 'scroll'].includes(cs.overflowX);
    const scrollsY = ['auto', 'scroll'].includes(cs.overflowY);
    const clips = ['hidden', 'clip'].includes(cs.overflowX) || ['hidden', 'clip'].includes(cs.overflowY);
    const isInline = cs.display === 'inline';
    if (!isInline && !['html', 'body'].includes(tag) && el.clientWidth > 0) {
      let overX = !scrollsX && el.scrollWidth > el.clientWidth + 2;
      if (overX && el.querySelector('.ann-label')) {
        // Annotation labels hang outside their segment by design; measure without them.
        const ls = [...el.querySelectorAll('.ann-label')];
        const prev = ls.map(l => l.style.display);
        ls.forEach(l => { l.style.display = 'none'; });
        overX = el.scrollWidth > el.clientWidth + 2;
        ls.forEach((l, i) => { l.style.display = prev[i]; });
      }
      const overY = clips && !scrollsY && el.scrollHeight > el.clientHeight + 2;
      if (overX || overY) {
        if (spills < 15) errors.push({rule: clips ? 'content-clipped' : 'content-spills',
          detail: `${path(el)}: content ${el.scrollWidth}x${el.scrollHeight}px in a ${el.clientWidth}x${el.clientHeight}px box`});
        spills++;
      }
    }
    const tw = cs.textWrap || cs.textWrapStyle || '';
    const pcs = el.parentElement ? getComputedStyle(el.parentElement) : null;
    const ptw = pcs ? (pcs.textWrap || pcs.textWrapStyle || '') : '';
    if (/balance|pretty/.test(tw) && tw !== ptw) errors.push({rule: 'text-wrap', detail: `${path(el)} uses text-wrap: ${tw}`});
    if (['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'figcaption', 'dd', 'blockquote'].includes(tag) && cs.maxWidth !== 'none' && cs.maxWidth !== '100%') {
      const parentW = el.parentElement ? el.parentElement.clientWidth : vw;
      if (parseFloat(cs.maxWidth) < parentW - 2) errors.push({rule: 'text-max-width', detail: `${path(el)} has max-width ${cs.maxWidth}`});
    }
    // One-sided accent marks on the element itself.
    const side = (s) => ({w: parseFloat(cs['border' + s + 'Width']) * (cs['border' + s + 'Style'] === 'none' ? 0 : 1), c: cs['border' + s + 'Color']});
    const S = {Left: side('Left'), Right: side('Right'), Top: side('Top'), Bottom: side('Bottom')};
    const opp = {Left: 'Right', Right: 'Left', Top: 'Bottom', Bottom: 'Top'};
    const present = Object.keys(S).filter(k => S[k].w > 0 && visible(S[k].c));
    const minW = Math.min(S.Top.w, S.Bottom.w, S.Left.w, S.Right.w);
    for (const k of ['Left', 'Right', 'Top', 'Bottom']) {
      const a = S[k], b = S[opp[k]];
      if (!(a.w > 0 && visible(a.c))) continue;
      const thickAccent = a.w >= 2 && a.w - b.w >= 1 && a.w > minW + 0.5;
      const onlySide = present.length === 1 && (coloured(a.c) || a.w >= 2);
      const lrColour = (k === 'Left' || k === 'Right') && coloured(a.c) && (b.w === 0 || !visible(b.c) || b.c !== a.c);
      if (thickAccent || onlySide || lrColour) {
        errors.push({rule: 'one-sided-border', detail: `${path(el)} border ${k.toLowerCase()} ${a.w}px ${a.c} (L${S.Left.w} R${S.Right.w} T${S.Top.w} B${S.Bottom.w})`});
        break;
      }
    }
    if (cs.boxShadow && /inset/.test(cs.boxShadow)) {
      for (const m of cs.boxShadow.matchAll(/(-?\d+(?:\.\d+)?)px (-?\d+(?:\.\d+)?)px 0px(?: 0px)? inset|inset[^,]*?(-?\d+(?:\.\d+)?)px (-?\d+(?:\.\d+)?)px 0px/g)) {
        const x = parseFloat(m[1] ?? m[3]), y = parseFloat(m[2] ?? m[4]);
        if ((x !== 0) !== (y !== 0)) { errors.push({rule: 'inset-edge-shadow', detail: `${path(el)} box-shadow ${cs.boxShadow}`}); break; }
      }
    }
    if (/linear-gradient/.test(cs.backgroundImage) && /(\d+(?:\.\d+)?)px,\s*(?:transparent|rgba\([^)]*,\s*0\))\s+\1px/.test(cs.backgroundImage) && el.innerText && el.innerText.trim().length > 20) {
      errors.push({rule: 'gradient-stripe', detail: `${path(el)} background ${cs.backgroundImage.slice(0, 80)}`});
    }
    // Pseudo-element bars flush on one edge of a box that holds text.
    const r = el.getBoundingClientRect();
    if (r.height > 24 && el.innerText && el.innerText.trim().length > 20) {
      for (const pseudo of ['::before', '::after']) {
        const ps = getComputedStyle(el, pseudo);
        if (!ps || ps.content === 'none' || ps.content === 'normal' || ps.position !== 'absolute') continue;
        const pw = parseFloat(ps.width) || 0, ph = parseFloat(ps.height) || 0;
        const bg = coloured(ps.backgroundColor);
        const bl = parseFloat(ps.borderLeftWidth) > 0 && coloured(ps.borderLeftColor) && !(parseFloat(ps.borderRightWidth) > 0);
        if (((bg && pw > 0 && pw <= 6) || bl) && ph >= r.height * 0.6) {
          errors.push({rule: 'one-sided-border', detail: `${path(el)}${pseudo} is a ${pw}px coloured bar along one edge`});
        }
      }
    }
  }
  if (spills > 15) errors.push({rule: 'content-spills', detail: `${spills - 15} more elements spill`});

  // Annotation labels.
  const labels = [...document.querySelectorAll('.ann-label, [data-no-overlap]')].filter(el => getComputedStyle(el).display !== 'none')
    .map(el => ({el, r: el.getBoundingClientRect()}));
  for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++) {
    if (hits(labels[i].r, labels[j].r)) errors.push({rule: 'labels-overlap', detail: `"${labels[i].el.textContent.trim().slice(0, 40)}" overlaps "${labels[j].el.textContent.trim().slice(0, 40)}"`});
  }
  for (const {el, r} of labels) {
    const panel = el.closest('.panel') || document.body;
    const pr = panel.getBoundingClientRect();
    if (r.width && (r.left < pr.left - 1 || r.right > pr.right + 1 || r.bottom > pr.bottom + 1)) errors.push({rule: 'label-outside-panel', detail: `"${el.textContent.trim().slice(0, 40)}" runs outside its panel`});
    const line = el.closest('.ann-line');
    if (!line) continue;
    const walker = document.createTreeWalker(line, NodeFilter.SHOW_TEXT);
    let node, found = false;
    while (!found && (node = walker.nextNode())) {
      if (!node.textContent.trim() || node.parentElement.closest('.ann-label')) continue;
      const range = document.createRange(); range.selectNodeContents(node);
      for (const tr of range.getClientRects()) {
        if (hits(r, tr, 2)) { errors.push({rule: 'label-on-text', detail: `"${el.textContent.trim().slice(0, 40)}" sits on "${node.textContent.trim().slice(0, 30)}"`}); found = true; break; }
      }
    }
  }

  // SVG text.
  for (const svg of document.querySelectorAll('svg')) {
    const sr = svg.getBoundingClientRect();
    if (!sr.width) continue;
    // Compare the letters, not the font's line cell: on Linux a bold face can report a cell
    // 1.6 em tall, so stacked lines that do not touch would count as an overlap.
    const inkBox = el => {
      const r = el.getBoundingClientRect();
      try {
        const n = el.getNumberOfChars(), ctm = el.getScreenCTM();
        if (!n || !ctm || Math.abs(ctm.b) > 1e-6 || Math.abs(ctm.c) > 1e-6) return r;
        const fs = Math.max(...[el, ...el.querySelectorAll('tspan')].map(e => parseFloat(getComputedStyle(e).fontSize) || 0)) * Math.abs(ctm.d);
        const y = p => new DOMPoint(p.x, p.y).matrixTransform(ctm).y;
        const top = Math.max(r.top, y(el.getStartPositionOfChar(0)) - 0.8 * fs);
        const bottom = Math.min(r.bottom, y(el.getStartPositionOfChar(n - 1)) + 0.25 * fs);
        return bottom > top ? {left: r.left, right: r.right, top, bottom, width: r.width, height: bottom - top} : r;
      } catch (e) { return r; }
    };
    const texts = [...svg.querySelectorAll('text')].map(el => ({el, r: inkBox(el)})).filter(t => t.r.width > 0);
    let n = 0;
    for (let i = 0; i < texts.length && n < 10; i++) for (let j = i + 1; j < texts.length && n < 10; j++) {
      if (hits(texts[i].r, texts[j].r)) {
        errors.push({rule: 'svg-text-overlap', detail: `"${texts[i].el.textContent.trim().slice(0, 30)}" overlaps "${texts[j].el.textContent.trim().slice(0, 30)}"`});
        n++;
      }
    }
    if (vw === 1440 && sr.width > 300) {
      const ctm = svg.getScreenCTM ? svg.getScreenCTM() : null;
      const scale = ctm ? Math.hypot(ctm.a, ctm.b) : 1;
      const small = texts.filter(t => (t.el.textContent || '').trim().length > 1 && parseFloat(getComputedStyle(t.el).fontSize) * scale < 11.5);
      if (small.length) warnings.push({rule: 'svg-text-small', detail: `${small.length} SVG labels render under about 12 px at 1440 px, for example "${small[0].el.textContent.trim().slice(0, 30)}"`});
    }
    for (const t of texts) {
      if (t.r.left < sr.left - 2 || t.r.right > sr.right + 2 || t.r.top < sr.top - 2 || t.r.bottom > sr.bottom + 2)
        errors.push({rule: 'svg-text-clipped', detail: `"${t.el.textContent.trim().slice(0, 30)}" runs outside its SVG`});
    }
  }

  // Visible text, without quoted non-STE text and code.
  const parts = [];
  const tw2 = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let tn;
  while ((tn = tw2.nextNode())) {
    const p = tn.parentElement;
    if (!p || p.closest('[data-ste="ignore"], code, pre, kbd, samp, script, style')) continue;
    if (getComputedStyle(p).display === 'none') continue;
    parts.push(tn.textContent);
  }
  const text = parts.join(' ');
  const dashes = (text.match(/—| – /g) || []).length;
  if (dashes) errors.push({rule: 'dash', detail: `${dashes} em dash or spaced en dash in visible text`});
  const emoji = text.match(/[\p{Emoji_Presentation}\u{1F000}-\u{1FAFF}]/gu);
  if (emoji) errors.push({rule: 'emoji', detail: `emoji in visible text: ${[...new Set(emoji)].join(' ')}`});

  const paras = [...document.querySelectorAll('p')].filter(p => {
    const r = p.getBoundingClientRect();
    const lh = parseFloat(getComputedStyle(p).lineHeight) || 18;
    return r.height > lh * 2.5 && p.innerText.length > 120;
  });
  const justified = paras.filter(p => getComputedStyle(p).textAlign === 'justify').length;
  if (vw >= 1024 && paras.length && justified < paras.length) {
    warnings.push({rule: 'not-justified', detail: `${paras.length - justified} of ${paras.length} multi-line paragraphs are not justified`});
  }
  if (vw < 680 && justified) warnings.push({rule: 'justified-on-phone', detail: `${justified} paragraphs stay justified at ${vw}px`});
  const brs = [...document.querySelectorAll('p br, li br')].length;
  if (brs) warnings.push({rule: 'br-in-text', detail: `${brs} <br> inside p or li`});
  for (const panel of document.querySelectorAll('.panel')) {
    const pr = panel.getBoundingClientRect();
    // Content bottom: the lowest visible text, image or SVG in the panel, whatever its markup.
    let bottom = pr.top;
    const walker = document.createTreeWalker(panel, NodeFilter.SHOW_TEXT);
    let tnode;
    while ((tnode = walker.nextNode())) {
      if (!tnode.textContent.trim() || !tnode.parentElement || getComputedStyle(tnode.parentElement).display === 'none') continue;
      const range = document.createRange(); range.selectNodeContents(tnode);
      for (const rr of range.getClientRects()) bottom = Math.max(bottom, rr.bottom);
    }
    for (const media of panel.querySelectorAll('img, svg, canvas, video, .gauge-track, .timeline .node, table')) {
      const mr = media.getBoundingClientRect(); if (mr.height) bottom = Math.max(bottom, mr.bottom);
    }
    const gap = pr.bottom - bottom - 12;
    if (pr.height > 200 && gap > Math.max(70, pr.height * 0.15)) {
      const item = {rule: 'dead-space', detail: `${path(panel)}: ${Math.round(gap)}px empty at the bottom of a ${Math.round(pr.height)}px panel`};
      if (vw === 1440 && gap > Math.max(150, pr.height * 0.25)) errors.push(item); else warnings.push(item);
    }
  }
  const h1 = document.querySelector('h1');
  if (h1 && document.title.trim() !== h1.innerText.trim()) warnings.push({rule: 'title-mismatch', detail: `<title> "${document.title}" differs from <h1> "${h1.innerText.trim()}"`});

  return {errors, warnings, width: vw, height: document.documentElement.scrollHeight, isSheet: !!document.querySelector('.sheet'),
          words: (text.match(/[A-Za-z0-9'’]+/g) || []).length,
          fonts: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family).filter((v, i, a) => a.indexOf(v) === i)};
}
"""


PRINT_PROBE = r"""
() => {
  const sizes = [];
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = tw.nextNode())) {
    const t = n.textContent.trim();
    const el = n.parentElement;
    if (t.length < 2 || !el || el.closest('svg, script, style, [aria-hidden="true"]')) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const zoom = el.currentCSSZoom || 1;
    sizes.push({pt: parseFloat(cs.fontSize) * zoom * 0.75, text: t.slice(0, 30), tag: el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : '')});
  }
  sizes.sort((a, b) => a.pt - b.pt);
  const body = [...document.querySelectorAll('p, li, td')].map(el => parseFloat(getComputedStyle(el).fontSize) * (el.currentCSSZoom || 1) * 0.75).sort((a, b) => a - b);
  return {min: sizes.length ? sizes[0] : null, p10: sizes.length ? sizes[Math.floor(sizes.length * 0.1)].pt : null,
          bodyMedian: body.length ? body[Math.floor(body.length / 2)] : null};
}
"""


def _pdf_pages(data: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page(?!s)", data))


def check(page: Path, out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    page = page.resolve()
    if not page.is_file():
        raise FileNotFoundError(f"no such page: {page}")
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"page": str(page), "out": str(out), "passed": True, "errors": [], "warnings": [], "viewports": {}, "tiles": []}
    blocked: list[str] = []
    js_errors: list[str] = []
    page_uri = page.as_uri()

    def route(r):
        url = r.request.url
        u = urlparse(url)
        if u.scheme in {"data", "blob", "about"}:
            return r.continue_()
        if u.scheme == "file":
            if url.split("#")[0] == page_uri or Path(unquote(u.path)).resolve() == page:
                return r.continue_()
            blocked.append(url)
            return r.abort()
        if u.hostname in ALLOWED_HOSTS:
            return r.continue_()
        blocked.append(url)
        return r.abort()

    seen: set[tuple[str, str]] = set()

    def add(kind: str, item: dict, vp: str) -> None:
        key = (item["rule"], item["detail"])
        if key in seen:
            return
        seen.add(key)
        report[kind].append({**item, "viewport": vp})

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(channel="chrome")
        is_sheet = False
        for w in PROBE_WIDTHS:
            name = {1440: "desktop", 390: "mobile"}.get(w, f"{w}px")
            scale = 2 if name == "mobile" else 1
            ctx = browser.new_context(viewport={"width": w, "height": 900 if w > 600 else 844}, device_scale_factor=scale)
            tab = ctx.new_page()
            tab.on("pageerror", lambda e: js_errors.append(str(e)))
            tab.route("**/*", route)
            tab.goto(page_uri, wait_until="load")
            try:
                tab.evaluate("document.fonts.ready.then(() => true)")
            except Exception:
                pass
            tab.wait_for_timeout(400)
            result = tab.evaluate(PAGE_PROBE, name)
            is_sheet = is_sheet or result["isSheet"]
            for e in result["errors"]:
                add("errors", e, name)
            for wn in result["warnings"]:
                add("warnings", wn, name)
            info = {"width": result["width"], "height": result["height"], "fonts": result["fonts"], "words": result["words"]}
            if name in {"desktop", "mobile"}:
                shot = out / f"{name}.png"
                tab.screenshot(path=str(shot), full_page=True, scale="css")
                info["screenshot"] = str(shot)
                th = TILE_H[name]
                if name == "mobile" or result["height"] > 1500:
                    for i, y in enumerate(range(0, result["height"], th), start=1):
                        tile = out / f"{name}-{i:02d}.png"
                        tab.screenshot(path=str(tile), full_page=True,
                                       clip={"x": 0, "y": y, "width": w, "height": min(th, result["height"] - y)})
                        report["tiles"].append(str(tile))
            report["viewports"][name] = info
            if name == "desktop":
                tab.emulate_media(media="print")
                tab.evaluate("window.dispatchEvent(new Event('beforeprint'))")
                report["print"] = {}
                papers = [("default", "print.pdf")] + ([("a3", "print-a3.pdf")] if is_sheet else [])
                for paper, fname in papers:
                    if paper == "a3":
                        tab.evaluate("document.documentElement.dataset.paper = 'a3'; window.dispatchEvent(new Event('beforeprint'))")
                    sizes = tab.evaluate(PRINT_PROBE)
                    pdf = out / fname
                    data = tab.pdf(path=str(pdf), prefer_css_page_size=True, print_background=False)
                    pages = _pdf_pages(data)
                    box = re.search(rb"/MediaBox\s*\[\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)", data)
                    w_pt = float(box.group(1)) if box else 0
                    label = "A3" if max(w_pt, float(box.group(2)) if box else 0) > 1100 else "A4"
                    entry = {"pdf": str(pdf), "pages": pages, "paper": label,
                             "min_pt": round(sizes["min"]["pt"], 1) if sizes["min"] else None,
                             "p10_pt": round(sizes["p10"], 1) if sizes["p10"] else None,
                             "body_pt": round(sizes["bodyMedian"], 1) if sizes["bodyMedian"] else None}
                    report["print"][paper] = entry
                    floor = 6.5 if label == "A3" else 4.5
                    if sizes["min"] and sizes["min"]["pt"] < floor:
                        add("errors", {"rule": "print-type", "detail": f"{label}: text at {sizes['min']['pt']:.1f} pt ({sizes['min']['tag']} \"{sizes['min']['text']}\"), the floor is {floor} pt"}, "print")
                    elif label == "A4" and is_sheet and sizes["p10"] and sizes["p10"] < 6.5:
                        add("warnings", {"rule": "print-type", "detail": f"A4: a tenth of the text is under {sizes['p10']:.1f} pt; for a sheet that will be pinned up, ship the A3 PDF"}, "print")
                    if is_sheet and pages > 1:
                        add("warnings", {"rule": "print-pages", "detail": f"{label}: the sheet prints on {pages} pages; a drawing sheet reads best on 1"}, "print")
            ctx.close()
        browser.close()

    for url in sorted(set(blocked)):
        add("errors", {"rule": "not-self-contained", "detail": f"blocked request: {url}"}, "all")
    for msg in sorted(set(js_errors)):
        add("errors", {"rule": "js-error", "detail": msg}, "all")
    report["passed"] = not report["errors"]
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def print_report(report: dict) -> None:
    print(("PASS" if report["passed"] else "FAIL") + "  " + report["page"])
    for name, v in report["viewports"].items():
        shot = f"  screenshot {v['screenshot']}" if "screenshot" in v else ""
        print(f"  {name}: {v['width']}x{v['height']}{shot}  fonts {', '.join(v['fonts']) or 'none loaded'}")
    if "desktop" in report["viewports"]:
        print(f"  visible words: {report['viewports']['desktop']['words']} (a review of a document should stay under the document's own length)")
    for paper, p in report.get("print", {}).items():
        print(f"  print {p['paper']}: {p['pages']} page(s), body {p['body_pt']} pt, smallest {p['min_pt']} pt  {p['pdf']}")
    for e in report["errors"]:
        print(f"  [error] {e['rule']} ({e['viewport']}): {e['detail']}")
    for wn in report["warnings"]:
        print(f"  [warning] {wn['rule']} ({wn['viewport']}): {wn['detail']}")
    if report["tiles"]:
        print("  Read these tiles at full size, then the desktop screenshot:")
        for t in report["tiles"]:
            print(f"    {t}")
    else:
        print("  Look at both screenshots at full size before you hand over the page.")


GOOD = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Good page</title><style>body{margin:0;padding:16px;font:16px/1.5 system-ui} p{text-align:justify;hyphens:auto;max-width:100%}
@media (max-width:680px){p{text-align:left;hyphens:manual}} .box{border:1px solid #000;padding:8px}</style></head>
<body><div class="box"><h1>Good page</h1><p>The pump supplies fuel to the engine when the switch is on. The pump stops when the
switch is off. This paragraph is long enough to wrap onto more than two lines at the phone width and at the desktop width.</p>
<blockquote data-ste="ignore">Original: the plan — as written — is fine.</blockquote><p>Source: © IETF 2022, Plex™.</p>
<svg width="300" height="70" viewBox="0 0 300 70" style="font:13px monospace"><text x="8" y="20"><tspan font-weight="700">code_verifier</tspan> = random</text>
<text x="8" y="39"><tspan font-weight="700">code_challenge</tspan> =</text><text x="8" y="58">  BASE64URL(SHA256(v))</text></svg></div></body></html>"""

BAD = """<!doctype html><html><head><meta charset="utf-8"><script src="https://cdn.example.com/x.js"></script>
<style>p{max-width:60ch;text-wrap:balance} .bar{border-left:4px solid red;padding:4px} .wide{width:2000px}
.top{border-top:4px solid blue;padding:8px} .thin{border-left:1px solid #1f5fbf;padding:8px}
.ps{position:relative;padding:8px 8px 8px 14px} .ps::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#1f5fbf}
.clip{width:80px;height:20px;overflow:hidden;display:inline-block}</style></head>
<body><p class="bar">Fast — most of the time \U0001F680</p>
<div class="top">A card with a coloured top edge only, long enough to count.</div>
<div class="thin">A card with a thin coloured left edge, long enough to count.</div>
<div class="ps">A card with a pseudo-element bar on the left edge, long enough.</div>
<span class="clip">Important instruction that is clipped</span>
<svg width="300" height="60" viewBox="0 0 300 60"><text x="10" y="30">First label here</text><text x="20" y="32">Second label</text><text x="10" y="100">Lost label</text></svg>
<svg width="300" height="60" viewBox="0 0 300 60" style="font:14px monospace"><text x="8" y="24">Upper line</text><text x="8" y="32">Lower line</text></svg>
<div class="wide">wide</div><img src="local.png"></body></html>"""


def self_test() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "dir with space"
        tmp_path.mkdir()
        good = tmp_path / "good.html"
        good.write_text(GOOD, encoding="utf-8")
        bad = tmp_path / "bad.html"
        bad.write_text(BAD, encoding="utf-8")
        r = check(good, tmp_path / "good-check")
        if not r["passed"]:
            failures += 1
            print("good page FAILED:", r["errors"])
        r = check(bad, tmp_path / "bad-check")
        rules = {e["rule"] for e in r["errors"]}
        details = " ".join(e["detail"] for e in r["errors"])
        want = {"not-self-contained", "text-wrap", "text-max-width", "one-sided-border", "dash", "emoji", "page-overflow",
                "svg-text-overlap", "svg-text-clipped", "content-clipped"}
        if r["passed"] or not want <= rules:
            failures += 1
            print("bad page FAILED: missing", sorted(want - rules), "got", sorted(rules))
        for needle in ["div.top", "div.thin", "div.ps::before", '"Upper line" overlaps "Lower line"']:
            if needle not in details:
                failures += 1
                print("bad page FAILED: no finding for", needle)
    print("self-test:", "OK" if not failures else f"{failures} failure(s)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", nargs="?")
    ap.add_argument("--out", help="folder for screenshots, print.pdf and report.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.page:
        ap.print_usage()
        return 2
    page = Path(args.page)
    out = Path(args.out) if args.out else Path(tempfile.gettempdir()) / "legible-check" / page.stem
    try:
        report = check(page, out)
    except Exception as e:  # the page could not be opened or rendered
        print(f"cannot check {page}: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
