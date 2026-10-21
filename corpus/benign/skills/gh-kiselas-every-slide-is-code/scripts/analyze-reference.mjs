#!/usr/bin/env node
// Reference analysis: break a deck someone else made (or your own earlier one) down into numbers you can
// write a style grammar from. Input: a PDF, a folder or list of images, or a deck.html.
// Output (in --out, default <name>-analysis/): report.md, analysis.json, contact-sheet.png.
//
//   node export/deck.mjs analyze reference.pdf [--out dir]          (this file is loaded by deck.mjs)
//   node scripts/analyze-reference.mjs shots/ [--out dir]           (or run it on its own)
//
// What it measures, per slide and for the deck: the palette (leader clustering in OKLab, so two colours that
// look alike are one), role guesses (background, ink, muted, rule, accent, second accent) by area share and
// contrast, the accent's share of every slide, words on the slide (text layer of a PDF, DOM of a deck; images have
// none), text sizes normalised to a 1080 px canvas, where the title sits and whether it stays put, ink coverage.
//
// Rasterising: a PDF is rendered by pdf.js (pdfjs-dist, a dependency of export/) inside the Chrome that the
// exporter already drives, onto a canvas, so nothing native is installed. Images are decoded by the same Chrome,
// which also reads WebP and AVIF. Colours are sampled from a 480 px wide nearest-neighbour copy (no blending of
// the anti-aliased edges into invented colours).

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { rgbToOklab, oklabToOklch, oklchToHex, deltaE, wcag } from './palette.mjs';

const AW = 480;                  // analysis width in pixels
const CLUSTER = .035;            // OKLab distance under which two colours are one colour on a slide
const DECK_CLUSTER = .05;        // ... and across the slides of a deck
const CHROMATIC = .06;           // OKLCH chroma from which a colour counts as a hue rather than a tone
const NORM = 1080;               // text sizes are reported in px of a 1080 px high canvas

const median = a => { if (!a.length) return 0; const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const pct = (x, d = 1) => `${(x * 100).toFixed(d)}%`;
const hexOf = lab => { const [L, C, h] = oklabToOklch(lab); return oklchToHex([L, C, h]); };

/* ───────── colour clustering ───────── */

// Leader clustering: the most frequent colours become centres, every other colour joins the nearest centre
// within `thr` (or founds one), then two refinement passes reassign against the final centres.
function leaders(items, thr) {
  items = [...items].sort((a, b) => b.c - a.c);
  let L = [];
  const near = lab => { let bi = -1, bd = 1e9; for (let k = 0; k < L.length; k++) { const d = deltaE(L[k].lab, lab); if (d < bd) { bd = d; bi = k; } } return [bi, bd]; };
  for (const it of items) {
    const [k, d] = near(it.lab);
    if (k >= 0 && d < thr) { const c = L[k].c + it.c; L[k].lab = L[k].lab.map((v, i) => (v * L[k].c + it.lab[i] * it.c) / c); L[k].c = c; }
    else L.push({ lab: [...it.lab], c: it.c });
  }
  for (let pass = 0; pass < 2; pass++) {
    const acc = L.map(() => ({ s: [0, 0, 0], c: 0, members: [] }));
    for (const it of items) { const [k] = near(it.lab); for (let i = 0; i < 3; i++) acc[k].s[i] += it.lab[i] * it.c; acc[k].c += it.c; acc[k].members.push(it); }
    L = acc.filter(a => a.c > 0).map(a => ({ lab: a.s.map(v => v / a.c), c: a.c, members: a.members }));
  }
  return L.sort((a, b) => b.c - a.c);
}

// colour histogram of one slide (5 bits per channel, computed in the page over the full-resolution canvas:
// [count, sumR, sumG, sumB] per bin, flat) -> [{ lab, hex, share, oklch }] most frequent first
function clusterSlide(flat) {
  const items = []; let n = 0;
  for (let i = 0; i < flat.length; i += 4) { const c = flat[i]; n += c; items.push({ lab: rgbToOklab([flat[i + 1] / c, flat[i + 2] / c, flat[i + 3] / c]), c }); }
  return leaders(items, CLUSTER).map(k => ({ lab: k.lab, hex: hexOf(k.lab), share: k.c / Math.max(1, n), oklch: oklabToOklch(k.lab) }));
}

const isChromatic = k => k.oklch[1] >= CHROMATIC;
const hueDiff = (a, b) => { const d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; };
const ratioOf = (a, b) => wcag(a.hex, b.hex);

// deck palette: the slides' clusters merged again, weighted by share (every slide counts the same)
function deckPalette(perSlide) {
  const items = [];
  perSlide.forEach((cl, s) => cl.forEach(k => { if (k.share >= .002) items.push({ lab: k.lab, c: k.share / perSlide.length, slide: s }); }));
  const merged = leaders(items, DECK_CLUSTER);
  return merged.map(m => {
    const big = new Set();
    perSlide.forEach((cl, s) => { if (cl.some(k => deltaE(k.lab, m.lab) < DECK_CLUSTER && k.share >= .005)) big.add(s); });
    return { lab: m.lab, hex: hexOf(m.lab), share: m.c, oklch: oklabToOklch(m.lab), slides: big.size };
  });
}

function guessRoles(deck, nSlides) {
  const roles = new Map(), take = (name, k) => { if (k && ![...roles.values()].includes(k)) roles.set(name, k); return !!k; };
  const bg = deck[0]; take('background', bg);
  const others = deck.filter(k => k !== bg && k.share >= .002);
  const far = k => deltaE(k.lab, bg.lab);
  // ink: what contrasts most with the background, neutral by preference, present on a good share of the slides
  const inkPool = others.filter(k => k.slides >= Math.max(1, Math.ceil(nSlides * .2)));
  const neutral = inkPool.filter(k => !isChromatic(k)).sort((a, b) => ratioOf(b, bg) - ratioOf(a, bg))[0];
  const ink = neutral && ratioOf(neutral, bg) >= 3 ? neutral : inkPool.sort((a, b) => ratioOf(b, bg) - ratioOf(a, bg))[0];
  take('ink', ink);
  const chromatic = others.filter(k => isChromatic(k) && far(k) >= .1 && k !== ink).sort((a, b) => b.share - a.share);
  const accent = chromatic[0]; take('accent', accent);
  const second = chromatic.find(k => k !== accent && (hueDiff(k.oklch[2], accent.oklch[2]) >= 30 || deltaE(k.lab, accent.lab) >= .12)); if (accent) take('second accent', second);
  // muted: a neutral between the background and the ink in lightness
  if (ink) {
    const lo = Math.min(bg.oklch[0], ink.oklch[0]), hi = Math.max(bg.oklch[0], ink.oklch[0]);
    const neutralMid = others.filter(k => !isChromatic(k) && k !== ink && k.oklch[0] > lo + .12 && k.oklch[0] < hi - .12 && ratioOf(k, bg) >= 2.2).sort((a, b) => b.share - a.share);
    take('muted', neutralMid[0]);
    const rules = others.filter(k => !isChromatic(k) && k !== ink && k !== roles.get('muted') && ratioOf(k, bg) >= 1.1 && ratioOf(k, bg) < 2.4).sort((a, b) => b.share - a.share);
    take('rule / panel', rules[0]);
  }
  return roles;
}

/* ───────── text runs -> per-slide text facts ───────── */

// letter-spaced text ("T A R E", a PDF stores every glyph of a tracked kicker apart) is one word
const countWords = s => { const t = s.split(/\s+/).filter(w => /[\p{L}\p{N}]/u.test(w)); return t.length >= 3 && t.every(w => w.length === 1) ? 1 : t.length; };

// runs: [{ txt, words, size (px at 1080), x, y, w, h (fractions of the canvas) }]
function textFacts(runs) {
  const words = runs.reduce((a, r) => a + r.words, 0);
  if (!runs.length) return { words: 0, maxSize: 0, title: null, left: null };
  const top = runs.filter(r => r.y < .45), pool = top.length ? top : runs;
  const maxTop = Math.max(...pool.map(r => r.size));
  const head = pool.filter(r => r.size >= maxTop * .96).sort((a, b) => a.y - b.y || a.x - b.x)[0];
  const lineH = head.size / NORM * 1.6;
  const lines = runs.filter(r => Math.abs(r.size - head.size) <= head.size * .04 && r.y >= head.y - .005 && r.y <= head.y + 3 * lineH);
  const x0 = Math.min(...lines.map(r => r.x)), y0 = Math.min(...lines.map(r => r.y)), x1 = Math.max(...lines.map(r => r.x + r.w)), y1 = Math.max(...lines.map(r => r.y + r.h));
  const title = { text: lines.map(r => r.txt).join(' ').replace(/\s+/g, ' ').trim(), x: x0, y: y0, w: x1 - x0, h: y1 - y0, size: head.size };
  return { words, maxSize: Math.max(...runs.map(r => r.size)), title, left: Math.min(...runs.map(r => r.x)) };
}

/* ───────── image-only fallback: where does the first band of ink sit ───────── */
function inkBand(rgba, W, H, bgLab) {
  const ink = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) ink[i] = deltaE(rgbToOklab([rgba[i * 4], rgba[i * 4 + 1], rgba[i * 4 + 2]]), bgLab) > .07 ? 1 : 0;
  const rows = new Uint32Array(H); let total = 0;
  for (let y = 0; y < H; y++) { let c = 0; for (let x = 0; x < W; x++) c += ink[y * W + x]; rows[y] = c; total += c; }
  const min = Math.max(2, W * .004);
  let y = Math.floor(H * .03);
  while (y < H) {
    while (y < H && rows[y] < min) y++;
    let y1 = y; while (y1 < H && rows[y1] >= min) y1++;
    if (y1 - y >= H * .02) {
      let x0 = W, x1 = 0;
      for (let yy = y; yy < y1; yy++) for (let x = 0; x < W; x++) if (ink[yy * W + x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; }
      if (x1 - x0 >= W * .06) return { x: x0 / W, y: y / H, w: (x1 - x0) / W, h: (y1 - y) / H, estimated: true, ink: total / (W * H) };
    }
    y = y1;
  }
  return { ink: total / (W * H) };
}

/* ───────── regularity ───────── */
function mode(values, tol) {
  let best = { v: null, n: 0 };
  for (const v of values) { const n = values.filter(u => Math.abs(u - v) <= tol).length; if (n > best.n) best = { v: median(values.filter(u => Math.abs(u - v) <= tol)), n }; }
  return best;
}

/* ───────── loaders ───────── */

const NATURAL = (a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
const IMG = /\.(png|jpe?g|webp|gif|avif|bmp)$/i;

function kindOf(inputs) {
  if (inputs.length === 1) {
    const p = inputs[0];
    if (!fs.existsSync(p)) throw new Error(`analyze: ${p} does not exist`);
    if (fs.statSync(p).isDirectory()) {
      const files = fs.readdirSync(p).filter(f => IMG.test(f)).sort(NATURAL).map(f => path.join(p, f));
      if (!files.length) throw new Error(`analyze: no images (png, jpg, webp) in ${p}`);
      return { kind: 'images', files };
    }
    if (/\.pdf$/i.test(p)) return { kind: 'pdf', file: p };
    if (/\.html?$/i.test(p)) return { kind: 'deck', file: p };
    if (IMG.test(p)) return { kind: 'images', files: [p] };
    throw new Error(`analyze: do not know what ${p} is (a PDF, a folder or list of images, or a deck.html)`);
  }
  for (const p of inputs) if (!IMG.test(p) || !fs.existsSync(p)) throw new Error(`analyze: a list of references must be existing image files (got ${p})`);
  return { kind: 'images', files: inputs };
}

// in-page: nearest-neighbour copy of a canvas/bitmap at AW pixels wide (RGBA, base64) and a JPEG thumbnail
const PAGE_HELPERS = `
  window.__small = (src, sw, sh) => {
    const w = ${AW}, h = Math.max(1, Math.round(w * sh / sw));
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    const x = c.getContext('2d', { willReadFrequently: true }); x.imageSmoothingEnabled = false; x.drawImage(src, 0, 0, sw, sh, 0, 0, w, h);
    const d = x.getImageData(0, 0, w, h).data; let s = ''; for (let i = 0; i < d.length; i += 0x8000) s += String.fromCharCode.apply(null, d.subarray(i, i + 0x8000));
    const t = document.createElement('canvas'); t.width = w; t.height = h; const y = t.getContext('2d'); y.imageSmoothingEnabled = true; y.imageSmoothingQuality = 'high'; y.drawImage(src, 0, 0, sw, sh, 0, 0, w, h);
    // the palette comes from the full-resolution pixels (at most 1920 wide), not from the small copy: thin text keeps its own colour
    const fw = Math.min(sw, 1920), fh = Math.round(fw * sh / sw), f = document.createElement('canvas'); f.width = fw; f.height = fh;
    const fx = f.getContext('2d', { willReadFrequently: true }); fx.imageSmoothingEnabled = fw === sw; fx.drawImage(src, 0, 0, sw, sh, 0, 0, fw, fh);
    const p = fx.getImageData(0, 0, fw, fh).data, bins = new Map();
    for (let i = 0; i < p.length; i += 4) { if (p[i + 3] < 128) continue; const k = ((p[i] >> 3) << 10) | ((p[i + 1] >> 3) << 5) | (p[i + 2] >> 3), e = bins.get(k); if (e) { e[0]++; e[1] += p[i]; e[2] += p[i + 1]; e[3] += p[i + 2]; } else bins.set(k, [1, p[i], p[i + 1], p[i + 2]]); }
    return { w, h, rgba: btoa(s), bins: [...bins.values()].flat(), thumb: t.toDataURL('image/jpeg', .82) };
  };`;
const unpack = r => ({ W: r.w, H: r.h, rgba: new Uint8Array(Buffer.from(r.rgba, 'base64')), bins: r.bins, thumb: r.thumb });

async function loadImages(ctx, files) {
  const page = await ctx.browser.newPage();
  await page.setContent('<body></body>'); await page.evaluate(PAGE_HELPERS);
  const slides = [];
  for (const f of files) {
    const b64 = fs.readFileSync(f).toString('base64');
    const mime = /\.png$/i.test(f) ? 'image/png' : /\.jpe?g$/i.test(f) ? 'image/jpeg' : /\.webp$/i.test(f) ? 'image/webp' : /\.avif$/i.test(f) ? 'image/avif' : /\.gif$/i.test(f) ? 'image/gif' : 'image/bmp';
    const r = await page.evaluate(async ({ b64, mime }) => {
      const bin = atob(b64), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const bmp = await createImageBitmap(new Blob([u8], { type: mime }));
      return { ...window.__small(bmp, bmp.width, bmp.height), nw: bmp.width, nh: bmp.height };
    }, { b64, mime });
    slides.push({ label: path.basename(f), ...unpack(r), native: [r.nw, r.nh], runs: null });
  }
  await page.close();
  return { slides, textKnown: false, note: `${files.length} image file(s); no text layer, so words per slide and text sizes are skipped` };
}

async function loadPdf(ctx, file) {
  const dir = path.join(ctx.exportDir, 'node_modules', 'pdfjs-dist');
  if (!fs.existsSync(path.join(dir, 'build', 'pdf.min.mjs'))) throw new Error('analyze: pdfjs-dist is not installed (cd export && npm install)');
  const page = await ctx.browser.newPage({ viewport: { width: 1280, height: 720 } });
  const O = 'https://analyze.local';
  const types = { '.mjs': 'text/javascript', '.js': 'text/javascript', '.pdf': 'application/pdf', '.html': 'text/html', '.bcmap': 'application/octet-stream', '.pfb': 'application/octet-stream', '.ttf': 'font/ttf' };
  await page.route(`${O}/**`, route => {
    const u = new URL(route.request().url()); let f;
    if (u.pathname === '/index.html') return route.fulfill({ contentType: 'text/html', body: '<!doctype html><body></body>' });
    if (u.pathname === '/file.pdf') f = file;
    else if (u.pathname === '/pdf.mjs') f = path.join(dir, 'build', 'pdf.min.mjs');
    else if (u.pathname === '/pdf.worker.mjs') f = path.join(dir, 'build', 'pdf.worker.min.mjs');
    else if (/^\/(cmaps|standard_fonts)\//.test(u.pathname)) f = path.join(dir, u.pathname);
    if (!f || !fs.existsSync(f)) return route.fulfill({ status: 404, body: '' });
    return route.fulfill({ contentType: types[path.extname(f)] || 'application/octet-stream', body: fs.readFileSync(f) });
  });
  await page.goto(`${O}/index.html`); await page.evaluate(PAGE_HELPERS);
  const n = await page.evaluate(async () => {
    const pdfjs = await import('https://analyze.local/pdf.mjs');
    pdfjs.GlobalWorkerOptions.workerSrc = 'https://analyze.local/pdf.worker.mjs';
    window.__pdfjs = pdfjs;
    window.__doc = await pdfjs.getDocument({ url: '/file.pdf', standardFontDataUrl: '/standard_fonts/', cMapUrl: '/cmaps/', cMapPacked: true }).promise;
    return window.__doc.numPages;
  });
  const slides = [];
  for (let p = 1; p <= n; p++) {
    const r = await page.evaluate(async p => {
      const pg = await window.__doc.getPage(p), v1 = pg.getViewport({ scale: 1 }), scale = 1920 / v1.width, vp = pg.getViewport({ scale });
      const c = document.createElement('canvas'); c.width = Math.round(vp.width); c.height = Math.round(vp.height);
      const x = c.getContext('2d', { willReadFrequently: true }); x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height);
      await pg.render({ canvasContext: x, viewport: vp }).promise;
      // text items -> runs: a PDF often has one item per glyph run (letter-spaced kickers, "$3,9" + "00"), so items on the
      // same baseline that nearly touch (gap under 0.3 em) are joined before words are counted
      const tc = await pg.getTextContent(), raw = [];
      for (const it of tc.items) {
        if (!it.str || !it.str.trim()) continue;
        const [bx, by] = window.__pdfjs.Util.applyTransform([it.transform[4], it.transform[5]], vp.transform);
        raw.push({ txt: it.str.replace(/\s+/g, ' ').trim(), size: Math.hypot(it.transform[0], it.transform[1]) * scale, x: bx, by, w: it.width * scale });
      }
      raw.sort((p, q) => (Math.abs(p.by - q.by) > .3 * Math.min(p.size, q.size) ? p.by - q.by : p.x - q.x));
      const merged = [];
      for (const r of raw) {
        const m = merged.at(-1);
        if (m && Math.abs(m.by - r.by) <= .3 * Math.min(m.size, r.size) && Math.abs(m.size - r.size) <= .1 * m.size && r.x - (m.x + m.w) < .3 * m.size && r.x - (m.x + m.w) > -.5 * m.size) { m.txt += r.txt; m.w = Math.max(m.w, r.x + r.w - m.x); }
        else merged.push({ ...r });
      }
      const runs = merged.map(m => ({ txt: m.txt, size: m.size / c.height * 1080, x: m.x / c.width, y: (m.by - m.size * .82) / c.height, w: m.w / c.width, h: m.size * 1.15 / c.height }));
      return { ...window.__small(c, c.width, c.height), runs, nw: c.width, nh: c.height };
    }, p);
    for (const q of r.runs) q.words = countWords(q.txt);
    slides.push({ label: `page ${p}`, ...unpack(r), native: [r.nw, r.nh], runs: r.runs });
  }
  await page.close();
  return { slides, textKnown: true, note: `PDF rendered by pdf.js (pdfjs-dist) in Chrome at 1920 px wide; text from the PDF text layer` };
}

async function loadDeck(ctx, file, nofonts) {
  const page = await ctx.browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  if (nofonts) await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto(pathToFileURL(path.resolve(file)).href + '?render');
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 }).catch(() => { throw new Error('analyze: the page did not set window.__ready (is it a deck-kit deck?)'); });
  const meta = await page.evaluate(() => ({ ...window.__meta, slides: window.__deck.slides, last: window.__deck.states('last') }));
  await page.setViewportSize({ width: meta.W, height: meta.H });
  const helper = await ctx.browser.newPage(); await helper.setContent('<body></body>'); await helper.evaluate(PAGE_HELPERS);
  const cdp = await page.context().newCDPSession(page);
  const slides = [];
  for (const st of meta.last) {
    await page.evaluate(({ i, step }) => window.__deck.show(i, step), st);
    await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', optimizeForSpeed: true, fromSurface: true, captureBeyondViewport: false, clip: { x: 0, y: 0, width: meta.W, height: meta.H, scale: 1 } });
    const probe = await page.evaluate(probeText);
    const r = await helper.evaluate(async b64 => {
      const bin = atob(b64), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const bmp = await createImageBitmap(new Blob([u8], { type: 'image/png' }));
      return window.__small(bmp, bmp.width, bmp.height);
    }, data);
    const k = NORM / meta.H;
    const runs = probe.map(q => ({ txt: q.txt, words: q.words, size: q.size * k, x: q.x / meta.W, y: q.y / meta.H, w: q.w / meta.W, h: q.h / meta.H }));
    const s = meta.slides[st.i];
    slides.push({ label: `${st.i + 1}${s.steps ? '.' + st.step : ''} ${s.id}`, id: s.id, ...unpack(r), native: [meta.W, meta.H], runs });
  }
  await page.close(); await helper.close();
  return { slides, textKnown: true, note: `deck.html: the last step of each slide as rendered by the exporter (${meta.W}x${meta.H}); words and sizes from the DOM (speaker notes excluded)` + (errors.length ? `; page errors: ${errors.length}` : '') };
}

// runs in the deck page: every visible text node with its size and box
function probeText() {
  const layer = document.querySelector('.deck:not(.dk-print) .dk-layer.is-on');
  const alpha = el => { let a = 1; for (let e = el; e && e !== layer; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none') return 0; a *= +cs.opacity; } return a; };
  const out = [], tw = document.createTreeWalker(layer, NodeFilter.SHOW_TEXT);
  for (let n; (n = tw.nextNode());) {
    const txt = n.textContent.replace(/\s+/g, ' ').trim(), el = n.parentElement;
    if (!txt || el.closest('.notes') || alpha(el) < .05) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    const r = rg.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    const k = el instanceof SVGElement && el.getScreenCTM ? Math.hypot(el.getScreenCTM().a, el.getScreenCTM().b) : 1;
    const t = txt.split(' ').filter(w => /[\p{L}\p{N}]/u.test(w)), words = t.length >= 3 && t.every(w => w.length === 1) ? 1 : t.length;
    out.push({ txt, words, size: parseFloat(getComputedStyle(el).fontSize) * k, x: r.left, y: r.top, w: r.width, h: r.height });
  }
  return out;
}

/* ───────── analysis ───────── */

function analyseAll(ref, loaded) {
  const { slides } = loaded, N = slides.length;
  const perSlide = slides.map(s => clusterSlide(s.bins));
  const deck = deckPalette(perSlide), roles = guessRoles(deck, N);
  const role = new Map([...roles].map(([r, k]) => [k, r]));
  const roleOf = lab => { let best = null, bd = 1e9; for (const k of deck) { const d = deltaE(k.lab, lab); if (d < bd) { bd = d; best = k; } } return bd < DECK_CLUSTER * 1.3 ? best : null; };
  const accent = roles.get('accent'), second = roles.get('second accent'), bg = roles.get('background');
  const rows = slides.map((s, n) => {
    const cl = perSlide[n], sbg = cl[0];
    const share = target => target ? cl.filter(k => roleOf(k.lab) === target).reduce((a, k) => a + k.share, 0) : 0;
    const facts = loaded.textKnown ? textFacts(s.runs) : null;
    const band = inkBand(s.rgba, s.W, s.H, sbg.lab);
    const palette = cl.filter(k => k.share >= .005).slice(0, 6).map(k => { const d = roleOf(k.lab); return { hex: k.hex, share: +k.share.toFixed(4), role: d ? role.get(d) || null : null }; });
    return { n: n + 1, label: s.label, id: s.id || null, bg: sbg.hex, bgShare: +sbg.share.toFixed(3), ink: +(1 - sbg.share).toFixed(3), accentShare: +share(accent).toFixed(4), secondShare: +share(second).toFixed(4),
      words: facts ? facts.words : null, maxSize: facts ? Math.round(facts.maxSize) : null, title: facts && facts.title ? { ...facts.title, x: +facts.title.x.toFixed(4), y: +facts.title.y.toFixed(4), w: +facts.title.w.toFixed(4), h: +facts.title.h.toFixed(4), size: Math.round(facts.title.size) } : null,
      left: facts && facts.left != null ? +facts.left.toFixed(4) : null, band: facts ? null : band.x != null ? { x: +band.x.toFixed(4), y: +band.y.toFixed(4), w: +band.w.toFixed(4), h: +band.h.toFixed(4) } : null, palette };
  });
  // text sizes: shares of words by size class, and the sizes that carry the most words
  let sizeDist = null;
  if (loaded.textKnown) {
    const cls = [['under 24 px (captions, axis labels)', 0, 24], ['24-39 px (body)', 24, 40], ['40-71 px (subtitles, numbers)', 40, 72], ['72-119 px (titles)', 72, 120], ['120 px and up (display)', 120, 1e9]];
    const all = slides.flatMap(s => s.runs), W = all.reduce((a, r) => a + r.words, 0) || 1, by = new Map();
    for (const r of all) by.set(Math.round(r.size / 2) * 2, (by.get(Math.round(r.size / 2) * 2) || 0) + r.words);
    sizeDist = { classes: cls.map(([name, a, b]) => ({ name, words: all.filter(r => r.size >= a && r.size < b).reduce((s, r) => s + r.words, 0) })).map(c => ({ ...c, share: +(c.words / W).toFixed(3) })),
      topSizes: [...by].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([size, words]) => ({ size, words })), smallest: all.length ? Math.round(Math.min(...all.map(r => r.size))) : null };
  }
  // regularity of the title's place
  let regularity = null;
  if (loaded.textKnown || rows.some(r => r.band)) {
    const pts = rows.map(r => r.title ? { n: r.n, x: r.title.x, y: r.title.y, size: r.title.size } : r.band ? { n: r.n, x: r.band.x, y: r.band.y, size: null } : null).filter(Boolean);
    const mx = mode(pts.map(p => p.x), .012), my = mode(pts.map(p => p.y), .015), msz = pts.some(p => p.size) ? mode(pts.filter(p => p.size).map(p => p.size), 3) : null;
    const on = pts.filter(p => Math.abs(p.x - mx.v) <= .012 && Math.abs(p.y - my.v) <= .015);
    regularity = { basis: loaded.textKnown ? 'title text box' : 'first band of ink (pixel estimate, no text layer)', slides: pts.length,
      x: { mode: mx.v, count: mx.n }, y: { mode: my.v, count: my.n }, size: msz ? { mode: msz.v, count: msz.n } : null,
      onGrid: on.length, offGrid: pts.filter(p => !on.includes(p)).map(p => p.n),
      leftEdge: loaded.textKnown ? (m => ({ mode: m.v, count: m.n }))(mode(rows.filter(r => r.left != null).map(r => r.left), .012)) : null };
  }
  const words = rows.map(r => r.words).filter(w => w != null);
  const summary = {
    slides: N, canvas: `${slides[0].native[0]}x${slides[0].native[1]}`, words: loaded.textKnown ? { median: median(words), max: Math.max(...words), over40: words.filter(w => w > 40).length, over60: words.filter(w => w > 60).length, total: words.reduce((a, b) => a + b, 0) } : null,
    ink: { median: +median(rows.map(r => r.ink)).toFixed(3), max: Math.max(...rows.map(r => r.ink)) },
    accent: accent ? { median: +median(rows.map(r => r.accentShare)).toFixed(4), max: Math.max(...rows.map(r => r.accentShare)), overTenPercent: rows.filter(r => r.accentShare > .1).map(r => r.n), withAccent: rows.filter(r => r.accentShare >= .005).length } : null,
    density: densityClass(loaded.textKnown ? median(words) : null, median(rows.map(r => r.ink))),
  };
  const deckOut = deck.filter(k => k.share >= .004).slice(0, 12).map(k => ({ hex: k.hex, share: +k.share.toFixed(4), slides: k.slides, oklch: k.oklch.map((v, i) => +v.toFixed(i === 2 ? 0 : 3)), role: role.get(k) || null, contrastOnBg: bg ? +ratioOf(k, bg).toFixed(2) : null }));
  return { rows, deck: deckOut, roles: Object.fromEntries([...roles].map(([r, k]) => [r, k.hex])), summary, sizeDist, regularity };
}

function densityClass(medWords, medInk) {
  const w = medWords == null ? null : medWords < 15 ? 'sparse (under 15 words a slide)' : medWords < 40 ? 'moderate (15-40 words)' : medWords < 70 ? 'dense (40-70 words)' : 'document-like (70+ words)';
  const i = medInk < .08 ? 'airy' : medInk < .2 ? 'balanced' : medInk < .4 ? 'full' : 'covered edge to edge';
  return w ? `${w}; ${i} (${pct(medInk, 0)} of the canvas is not background)` : `${i} by ink coverage (${pct(medInk, 0)} of the canvas is not background); words unknown`;
}

/* ───────── output ───────── */

function writeReport(dir, ref, loaded, A) {
  const { rows, deck, summary: S, sizeDist, regularity: R } = A, name = path.basename(ref.file || ref.files[0]), L = [];
  L.push(`# Reference analysis: ${name}${ref.kind === 'images' && ref.files.length > 1 ? ` (+${ref.files.length - 1} more)` : ''}`, '');
  L.push('| | |', '|---|---|', `| Kind | ${ref.kind === 'pdf' ? 'PDF' : ref.kind === 'deck' ? 'deck-kit HTML deck' : 'images'} |`, `| Slides | ${S.slides} |`, `| Canvas | ${S.canvas} |`);
  L.push(`| Density | ${S.density} |`);
  if (S.words) L.push(`| Words per slide | median ${S.words.median}, max ${S.words.max}, total ${S.words.total}; ${S.words.over40} slides over 40 words, ${S.words.over60} over 60 |`);
  else L.push('| Words per slide | not measured: images have no text layer (give the PDF or the HTML for words and text sizes) |');
  L.push(`| Source | ${loaded.note} |`, '');
  L.push('## Palette', '', 'Colours are clustered in OKLab (two colours closer than one just-noticeable step are one); the share is the mean share of the slide area. Roles are guesses from area, contrast and chroma: check them against the sheet.', '');
  L.push('| Role | Hex | OKLCH | Area | On slides | Contrast on background |', '|---|---|---|---|---|---|');
  for (const k of deck) L.push(`| ${k.role || ''} | \`${k.hex}\` | L${k.oklch[0]} C${k.oklch[1]} h${k.oklch[2]} | ${pct(k.share)} | ${k.slides}/${S.slides} | ${k.contrastOnBg == null ? '' : k.role === 'background' ? '' : k.contrastOnBg + ':1'} |`);
  L.push('');
  if (S.accent) {
    L.push(`**Accent** (\`${A.roles.accent}\`): median ${pct(S.accent.median)} of a slide, at most ${pct(S.accent.max)}, present on ${S.accent.withAccent} of ${S.slides} slides` + (S.accent.overTenPercent.length ? `; over 10% on slide${S.accent.overTenPercent.length > 1 ? 's' : ''} ${S.accent.overTenPercent.join(', ')}` : '; never over 10%') + '. The kit keeps it under 10% and gives it one meaning.', '');
  } else L.push('No chromatic accent found: the deck is tonal (background, ink, greys).', '');
  L.push('## Slides', '', '| # | ' + (loaded.textKnown ? 'Title (guess) | Words | Largest text | ' : '') + 'Background | Not background | Accent | Second |', '|---|' + (loaded.textKnown ? '---|---|---|' : '') + '---|---|---|---|');
  for (const r of rows) L.push(`| ${r.n} | ${loaded.textKnown ? `${r.title ? r.title.text.replace(/\|/g, '/').slice(0, 48) + (r.title.text.length > 48 ? '…' : '') : ''} | ${r.words} | ${r.maxSize ? r.maxSize + ' px' : ''} | ` : ''}\`${r.bg}\` | ${pct(r.ink, 0)} | ${pct(r.accentShare)} | ${pct(r.secondShare)} |`);
  L.push('');
  if (sizeDist) {
    L.push('## Text sizes (px on a 1080 px canvas, by share of words)', '', '| Size class | Words | Share |', '|---|---|---|');
    for (const c of sizeDist.classes) L.push(`| ${c.name} | ${c.words} | ${pct(c.share, 0)} |`);
    L.push('', `Sizes that carry the most words: ${sizeDist.topSizes.map(s => `${s.size} px (${s.words})`).join(', ')}. Smallest text: ${sizeDist.smallest} px${sizeDist.smallest < 20 ? ' (under the kit\'s 20 px floor)' : ''}.`, '');
  }
  if (R) {
    L.push('## Layout regularity', '', `Basis: ${R.basis}, ${R.slides} slides.`, '');
    const f = v => `${(v * 100).toFixed(1)}%`;
    L.push(`- Title left edge: most common at ${f(R.x.mode)} of the width (${R.x.count} of ${R.slides} slides within 1.2%).`);
    L.push(`- Title top: most common at ${f(R.y.mode)} of the height (${R.y.count} of ${R.slides} within 1.5%).`);
    if (R.size) L.push(`- Title size: most common ${R.size.mode} px (${R.size.count} slides within 3 px).`);
    if (R.leftEdge) L.push(`- Left edge of all text: most common at ${f(R.leftEdge.mode)} (${R.leftEdge.count} slides).`);
    L.push(`- ${R.onGrid} of ${R.slides} slides keep the title at the same place${R.offGrid.length ? `; the others (${R.offGrid.join(', ')}) are the exceptions: title cards, statements, full-bleed images: look at what they have in common` : ''}.`, '');
  }
  L.push('## Images', '', '- `contact-sheet.png`: every slide, numbered, with its words, accent share and palette strip.', '');
  L.push('## Style grammar to write down', '',
    'Read the contact sheet, then write these down before designing anything. Borrow the structure (how the argument is paced, where things sit, what the accent means), not the look (the exact colours, the typeface, the illustration style).', '',
    '- **Palette and roles**: background, ink, muted, rule, accent, second accent, and what the accent means every time it appears.',
    '- **Type**: how many sizes, which one carries a slide, how the title relates to the number or claim.',
    '- **Grid**: where the title, the kicker and the footer sit; what is allowed to break the grid and on which slides.',
    '- **Density**: words per slide by slide type; which slides are statements and which are evidence.',
    '- **Rhythm**: the order of slide types over the whole deck (opening, claim, proof, turn, ask) and where it slows down.',
    '- **Devices that repeat**: one thing the deck does on several slides (a number treatment, a chart style, a frame) and why it works.',
    '- **What not to copy**: anything that is decoration in the reference and would be noise in yours.', '');
  fs.writeFileSync(path.join(dir, 'report.md'), L.join('\n'));
}

async function contactSheet(ctx, dir, loaded, A, cols = 5) {
  const { slides } = loaded, tw = 384, th = Math.round(tw * slides[0].H / slides[0].W);
  const page = await ctx.browser.newPage({ viewport: { width: cols * (tw + 14) + 14, height: 400 } });
  const chips = r => r.palette.slice(0, 5).map(p => `<i style="background:${p.hex};flex:${Math.max(p.share, .03)}" title="${p.hex} ${(p.share * 100).toFixed(1)}%"></i>`).join('');
  const deck = A.deck.filter(k => k.role).map(k => `<span class="d"><i style="background:${k.hex}"></i>${k.role} ${k.hex} ${(k.share * 100).toFixed(0)}%</span>`).join('');
  await page.setContent(`<style>body{margin:0;background:#161616;font:600 14px/1.3 ui-monospace,Consolas,monospace;color:#ddd}
    .top{padding:14px 14px 0;display:flex;flex-wrap:wrap;gap:6px 22px}.d{display:flex;align-items:center;gap:8px}.d i{width:22px;height:22px;border-radius:4px;outline:1px solid #444}
    .g{display:grid;grid-template-columns:repeat(${cols},${tw}px);gap:14px;padding:14px}
    figure{margin:0}img{display:block;width:${tw}px;height:${th}px;outline:1px solid #333}.bar{display:flex;height:9px;margin-top:4px}.bar i{display:block}
    figcaption{padding:5px 2px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}</style>
    <div class="top">${deck}</div>
    <div class="g">${slides.map((s, k) => { const r = A.rows[k]; return `<figure><img src="${s.thumb}"><div class="bar">${chips(r)}</div><figcaption>${r.n}${r.words != null ? ` · ${r.words}w` : ''} · accent ${(r.accentShare * 100).toFixed(0)}%${r.title ? ` · ${r.title.size}px` : ''}</figcaption></figure>`; }).join('')}</div>`);
  await page.screenshot({ path: path.join(dir, 'contact-sheet.png'), fullPage: true });
  await page.close();
}

/* ───────── entry ───────── */

export async function analyze({ inputs, out, chromium, launchOpts, chromeArgs = [], exportDir, nofonts = false }) {
  const ref = kindOf(inputs);
  const first = ref.file || ref.files[0];
  const dir = path.resolve(out || `${path.basename(ref.kind === 'images' && inputs.length === 1 && fs.statSync(inputs[0]).isDirectory() ? inputs[0] : first).replace(/\.[^.]+$/, '')}-analysis`);
  fs.mkdirSync(dir, { recursive: true });
  const browser = await chromium.launch({ ...launchOpts, args: chromeArgs });
  const ctx = { browser, exportDir };
  try {
    const t0 = Date.now();
    const loaded = ref.kind === 'pdf' ? await loadPdf(ctx, ref.file) : ref.kind === 'deck' ? await loadDeck(ctx, ref.file, nofonts) : await loadImages(ctx, ref.files);
    console.log(`analyze: ${loaded.slides.length} slide(s) loaded (${loaded.note.split(';')[0]}) in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
    const A = analyseAll(ref, loaded);
    writeReport(dir, ref, loaded, A);
    fs.writeFileSync(path.join(dir, 'analysis.json'), JSON.stringify({ input: inputs, kind: ref.kind, source: loaded.note, summary: A.summary, roles: A.roles, palette: A.deck, textSizes: A.sizeDist, titleRegularity: A.regularity, slides: A.rows }, null, 1));
    await contactSheet(ctx, dir, loaded, A);
    const S = A.summary;
    console.log(`  palette: ${Object.entries(A.roles).map(([r, h]) => `${r} ${h}`).join(', ')}`);
    if (S.accent) console.log(`  accent share per slide: median ${pct(S.accent.median)}, max ${pct(S.accent.max)}${S.accent.overTenPercent.length ? `, over 10% on ${S.accent.overTenPercent.join(', ')}` : ''}`);
    if (S.words) console.log(`  words per slide: median ${S.words.median}, max ${S.words.max}`);
    if (A.regularity) console.log(`  title in the same place on ${A.regularity.onGrid} of ${A.regularity.slides} slides (${A.regularity.basis})`);
    console.log(`analyze: ${dir}${path.sep}{report.md,analysis.json,contact-sheet.png}`);
  } finally { await browser.close(); }
}

// run on its own: node scripts/analyze-reference.mjs REF... [--out dir] [--no-webfonts]
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const a = process.argv.slice(2), i = a.indexOf('--out'), out = i >= 0 ? a.splice(i, 2)[1] : null, nf = a.indexOf('--no-webfonts'); if (nf >= 0) a.splice(nf, 1);
  if (!a.length || a[0] === '-h' || a[0] === '--help') { console.log('usage: node scripts/analyze-reference.mjs <reference.pdf | images-folder | a.png b.png ... | deck.html> [--out dir] [--no-webfonts]'); process.exit(a.length ? 0 : 1); }
  const exportDir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'export');
  const { chromium } = createRequire(path.join(exportDir, 'package.json'))('playwright-core');
  const launchOpts = process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: 'chrome' };
  analyze({ inputs: a, out, chromium, launchOpts, chromeArgs: ['--force-color-profile=srgb', '--hide-scrollbars'], exportDir, nofonts: nf >= 0 }).catch(e => { console.error(e.message || e); process.exit(1); });
}
