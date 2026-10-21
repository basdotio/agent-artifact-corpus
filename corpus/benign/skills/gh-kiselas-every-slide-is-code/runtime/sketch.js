/*! deck-kit sketch plugin · optional · MIT · reference: 15-sketch-and-morph.md
 * Two independent features, both pure functions of (seed, variant) or of build progress, so rest frames, jumps, PDF and video stay exact:
 *  1. hand-drawn SVG: data-sketch redraws line, rect, circle, ellipse, polyline, polygon, path as double strokes with hachure fills
 *     and optional line boil. Inspired by Rough.js (github.com/rough-stuff/rough): the wobbling Bezier line with a bowing term,
 *     roughness gain by length, two passes with different offsets, scanline hachure. Own compact code, no dependency.
 *  2. path morph: data-morph-to / data-anim="morph-path" interpolate paths with different vertex counts, holes and subpaths, and
 *     the `morph` slide transition morphs data-morph elements that are SVG shapes. Inspired by Flubber (github.com/veltman/flubber):
 *     flatten to rings, bisect the longest edges until the counts match, match the winding and rotate to the start of least distance.
 * Load after runtime/deck.js and before the deck's own Deck.slide() calls. */
(function () {
'use strict';
const D = window.Deck;
if (!D) { console.error('deck-kit sketch plugin: runtime/deck.js must load first'); return; }
const { ease, clamp, lerp, seg } = D;
const NS = 'http://www.w3.org/2000/svg';
const $$ = (r, s) => [...r.querySelectorAll(s)];
const GEO = 'line,rect,circle,ellipse,polyline,polygon,path';
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const r1 = v => Math.round(v * 10) / 10, r2 = v => Math.round(v * 100) / 100;
const numOr = (v, d) => (v == null || v === '' || !isFinite(+v) ? d : +v);
let warned = false;
const warn = m => { if (!warned) { warned = true; console.warn(`deck-kit sketch: ${m}`); } };
const H3 = (a, b, c) => {
  let h = Math.imul(a | 0, 0x9E3779B1) ^ Math.imul((b | 0) + 0x7F4A7C15, 0x85EBCA6B) ^ Math.imul((c | 0) + 0x165667B1, 0xC2B2AE35);
  h = Math.imul(h ^ h >>> 16, 0x7feb352d); h = Math.imul(h ^ h >>> 15, 0x846ca68b);
  return (h ^ h >>> 16) >>> 0;
};
const seedOf = v => { if (v == null || v === '') return 1; if (isFinite(+v)) return Math.floor(+v); let h = 7; for (const c of String(v)) h = H3(h, c.charCodeAt(0), 3); return h; };

/* ───────────────────────── geometry: paths as subpaths of L and C segments ─────────────────────────
 * sub = { x, y, segs: [{t:'L', x, y} | {t:'C', x1, y1, x2, y2, x, y}], closed }. Arcs and quadratics become cubics, so everything downstream
 * has two segment kinds. Written by hand (no getPointAtLength): works in hidden slides, needs no layout, is deterministic. */
const NUM = /[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?/y;
function arcToC(out, x1, y1, rx, ry, phiDeg, fa, fs, x2, y2) {
  rx = Math.abs(rx); ry = Math.abs(ry);
  if (!rx || !ry || (x1 === x2 && y1 === y2)) { out.push({ t: 'L', x: x2, y: y2 }); return; }
  const phi = phiDeg * Math.PI / 180, cp = Math.cos(phi), sp = Math.sin(phi);
  const dx = (x1 - x2) / 2, dy = (y1 - y2) / 2, xp = cp * dx + sp * dy, yp = -sp * dx + cp * dy;
  const lam = xp * xp / (rx * rx) + yp * yp / (ry * ry);
  if (lam > 1) { const s = Math.sqrt(lam); rx *= s; ry *= s; }
  const den = rx * rx * yp * yp + ry * ry * xp * xp, co = (fa === fs ? -1 : 1) * Math.sqrt(Math.max(0, (rx * rx * ry * ry - den) / (den || 1)));
  const cxp = co * rx * yp / ry, cyp = -co * ry * xp / rx, cx = cp * cxp - sp * cyp + (x1 + x2) / 2, cy = sp * cxp + cp * cyp + (y1 + y2) / 2;
  const th1 = Math.atan2((yp - cyp) / ry, (xp - cxp) / rx);
  const ux = (xp - cxp) / rx, uy = (yp - cyp) / ry, vx = (-xp - cxp) / rx, vy = (-yp - cyp) / ry;
  let dth = Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
  if (!fs && dth > 0) dth -= 2 * Math.PI; else if (fs && dth < 0) dth += 2 * Math.PI;
  const n = Math.max(1, Math.ceil(Math.abs(dth) / (Math.PI / 2) - 1e-9)), st = dth / n, k = 4 / 3 * Math.tan(st / 4);
  const P = a => [cx + rx * Math.cos(a) * cp - ry * Math.sin(a) * sp, cy + rx * Math.cos(a) * sp + ry * Math.sin(a) * cp];
  const V = a => [-rx * Math.sin(a) * cp - ry * Math.cos(a) * sp, -rx * Math.sin(a) * sp + ry * Math.cos(a) * cp];
  for (let i = 0; i < n; i++) {
    const a0 = th1 + i * st, a1 = a0 + st, p0 = P(a0), p1 = P(a1), v0 = V(a0), v1 = V(a1);
    out.push({ t: 'C', x1: p0[0] + k * v0[0], y1: p0[1] + k * v0[1], x2: p1[0] - k * v1[0], y2: p1[1] - k * v1[1], x: i === n - 1 ? x2 : p1[0], y: i === n - 1 ? y2 : p1[1] });
  }
}
function parseD(d) {
  const subs = []; let cur = null, x = 0, y = 0, sx = 0, sy = 0, pc = null, pq = null, cmd = '', i = 0;
  const n = d.length;
  const skip = () => { while (i < n) { const c = d.charCodeAt(i); if (c === 32 || c === 44 || c === 9 || c === 10 || c === 13) i++; else break; } };
  const num = () => { skip(); NUM.lastIndex = i; const m = NUM.exec(d); if (!m) throw new Error('bad number at ' + i); i = NUM.lastIndex; return +m[0]; };
  const flag = () => { skip(); return d[i++] === '1' ? 1 : 0; };
  const need = () => { if (!cur) { cur = { x, y, segs: [], closed: false }; subs.push(cur); } return cur; };
  try {
    for (;;) {
      skip(); if (i >= n) break;
      const ch = d[i];
      if (/[A-Za-z]/.test(ch)) { cmd = ch; i++; } else if (!cmd) break;
      const rel = cmd !== cmd.toUpperCase(), C = cmd.toUpperCase(), ox = rel ? x : 0, oy = rel ? y : 0;
      let npc = null, npq = null;
      if (C === 'M') { x = num() + ox; y = num() + oy; sx = x; sy = y; cur = { x, y, segs: [], closed: false }; subs.push(cur); cmd = rel ? 'l' : 'L'; }
      else if (C === 'L') { const nx = num() + ox, ny = num() + oy; need().segs.push({ t: 'L', x: nx, y: ny }); x = nx; y = ny; }
      else if (C === 'H') { const nx = num() + ox; need().segs.push({ t: 'L', x: nx, y }); x = nx; }
      else if (C === 'V') { const ny = num() + oy; need().segs.push({ t: 'L', x, y: ny }); y = ny; }
      else if (C === 'C' || C === 'S') {
        let x1, y1;
        if (C === 'C') { x1 = num() + ox; y1 = num() + oy; } else { x1 = pc ? 2 * x - pc[0] : x; y1 = pc ? 2 * y - pc[1] : y; }
        const x2 = num() + ox, y2 = num() + oy, nx = num() + ox, ny = num() + oy;
        need().segs.push({ t: 'C', x1, y1, x2, y2, x: nx, y: ny }); npc = [x2, y2]; x = nx; y = ny;
      } else if (C === 'Q' || C === 'T') {
        let qx, qy;
        if (C === 'Q') { qx = num() + ox; qy = num() + oy; } else { qx = pq ? 2 * x - pq[0] : x; qy = pq ? 2 * y - pq[1] : y; }
        const nx = num() + ox, ny = num() + oy;
        need().segs.push({ t: 'C', x1: x + 2 / 3 * (qx - x), y1: y + 2 / 3 * (qy - y), x2: nx + 2 / 3 * (qx - nx), y2: ny + 2 / 3 * (qy - ny), x: nx, y: ny });
        npq = [qx, qy]; x = nx; y = ny;
      } else if (C === 'A') {
        const rx = num(), ry = num(), rot = num(), fa = flag(), fs = flag(), nx = num() + ox, ny = num() + oy;
        arcToC(need().segs, x, y, rx, ry, rot, fa, fs, nx, ny); x = nx; y = ny;
      } else if (C === 'Z') { if (cur) cur.closed = true; x = sx; y = sy; cur = null; cmd = ''; }
      else break;
      pc = npc; pq = npq;
    }
  } catch (e) { warn(`unreadable path data (${e.message}); drawn as far as it parses`); }
  return subs.filter(s => s.segs.length);
}
const K4 = 4 * (Math.SQRT2 - 1) / 3;
function rectSubs(a) {
  const x = a.x, y = a.y, w = a.w, h = a.h;
  let rx = Math.min(a.rx ?? a.ry ?? 0, w / 2), ry = Math.min(a.ry ?? a.rx ?? 0, h / 2);
  const L = (px, py) => ({ t: 'L', x: px, y: py });
  if (!(rx > 0 && ry > 0)) return [{ x, y, closed: true, segs: [L(x + w, y), L(x + w, y + h), L(x, y + h)] }];
  const C = (x1, y1, x2, y2, px, py) => ({ t: 'C', x1, y1, x2, y2, x: px, y: py }), kx = K4 * rx, ky = K4 * ry;
  return [{ x: x + rx, y, closed: true, segs: [L(x + w - rx, y), C(x + w - rx + kx, y, x + w, y + ry - ky, x + w, y + ry), L(x + w, y + h - ry),
    C(x + w, y + h - ry + ky, x + w - rx + kx, y + h, x + w - rx, y + h), L(x + rx, y + h), C(x + rx - kx, y + h, x, y + h - ry + ky, x, y + h - ry),
    L(x, y + ry), C(x, y + ry - ky, x + rx - kx, y, x + rx, y)] }];
}
function ellipseSubs(cx, cy, rx, ry) {
  const C = (x1, y1, x2, y2, x, y) => ({ t: 'C', x1, y1, x2, y2, x, y }), kx = K4 * rx, ky = K4 * ry;
  return [{ x: cx + rx, y: cy, closed: true, segs: [C(cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry), C(cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy),
    C(cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry), C(cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy)] }];
}
const at = (el, k, d = 0) => numOr(parseFloat(el.getAttribute(k)), d);
function pointsOf(el) { const v = (el.getAttribute('points') || '').trim().split(/[\s,]+/).map(Number).filter(isFinite); const out = []; for (let i = 0; i + 1 < v.length; i += 2) out.push([v[i], v[i + 1]]); return out; }
// one element -> subpaths (null when it has no geometry)
function subsOf(el) {
  const t = el.localName;
  if (t === 'path') return parseD(el.getAttribute('d') || '');
  if (t === 'line') return [{ x: at(el, 'x1'), y: at(el, 'y1'), closed: false, segs: [{ t: 'L', x: at(el, 'x2'), y: at(el, 'y2') }] }];
  if (t === 'polyline' || t === 'polygon') {
    const p = pointsOf(el); if (p.length < 2) return [];
    return [{ x: p[0][0], y: p[0][1], closed: t === 'polygon', segs: p.slice(1).map(q => ({ t: 'L', x: q[0], y: q[1] })) }];
  }
  if (t === 'rect') {
    const rx = el.hasAttribute('rx') ? at(el, 'rx') : null, ry = el.hasAttribute('ry') ? at(el, 'ry') : null;
    return rectSubs({ x: at(el, 'x'), y: at(el, 'y'), w: at(el, 'width'), h: at(el, 'height'), rx, ry });
  }
  if (t === 'circle') return ellipseSubs(at(el, 'cx'), at(el, 'cy'), at(el, 'r'), at(el, 'r'));
  if (t === 'ellipse') return ellipseSubs(at(el, 'cx'), at(el, 'cy'), at(el, 'rx'), at(el, 'ry'));
  return null;
}
function subsToD(subs) {
  let d = '';
  for (const s of subs) {
    d += `M${r2(s.x)} ${r2(s.y)}`;
    for (const g of s.segs) d += g.t === 'L' ? `L${r2(g.x)} ${r2(g.y)}` : `C${r2(g.x1)} ${r2(g.y1)} ${r2(g.x2)} ${r2(g.y2)} ${r2(g.x)} ${r2(g.y)}`;
    if (s.closed) d += 'Z';
  }
  return d;
}
const dOf = el => (el.localName === 'path' ? el.getAttribute('d') || '' : subsToD(subsOf(el) || []));
// flatten to points: a chord of about `step` px on curves
function flatten(sub, step = 5, tx) {
  const T = tx ? (x, y) => [tx[0] * x + tx[2] * y + tx[4], tx[1] * x + tx[3] * y + tx[5]] : (x, y) => [x, y];
  const pts = [T(sub.x, sub.y)]; let px = sub.x, py = sub.y;
  for (const s of sub.segs) {
    if (s.t === 'L') pts.push(T(s.x, s.y));
    else {
      const len = Math.hypot(s.x1 - px, s.y1 - py) + Math.hypot(s.x2 - s.x1, s.y2 - s.y1) + Math.hypot(s.x - s.x2, s.y - s.y2);
      const n = clamp(Math.ceil(len * (tx ? Math.hypot(tx[0], tx[1]) : 1) / step), 4, 40);
      for (let k = 1; k <= n; k++) {
        const t = k / n, u = 1 - t, a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, e = t * t * t;
        pts.push(T(a * px + b * s.x1 + c * s.x2 + e * s.x, a * py + b * s.y1 + c * s.y2 + e * s.y));
      }
    }
    px = s.x; py = s.y;
  }
  if (sub.closed && pts.length > 2) { const a = pts[0], b = pts[pts.length - 1]; if (Math.abs(a[0] - b[0]) < 1e-6 && Math.abs(a[1] - b[1]) < 1e-6) pts.pop(); }
  return pts;
}

/* ───────────────────────── styles ───────────────────────── */
const RGB = /^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+%?))?\s*\)$/;
function parseCol(s) {
  if (!s || s === 'none' || s === 'transparent') return null;
  const m = RGB.exec(String(s).trim());
  if (!m) return undefined;
  return [+m[1], +m[2], +m[3], m[4] == null ? 1 : m[4].endsWith('%') ? parseFloat(m[4]) / 100 : +m[4]];
}
const colStr = c => (c[3] >= .999 ? `rgb(${Math.round(c[0])},${Math.round(c[1])},${Math.round(c[2])})` : `rgba(${Math.round(c[0])},${Math.round(c[1])},${Math.round(c[2])},${+c[3].toFixed(3)})`);
// a colour written in any CSS syntax, as the browser resolves it (read once, in init: needs the document)
let probe = null;
function norm(s) {
  if (!s || s === 'none') return 'none';
  if (!probe) { probe = document.createElement('i'); probe.style.cssText = 'position:absolute;width:0;height:0;visibility:hidden'; document.body.append(probe); }
  probe.style.color = ''; probe.style.color = s;
  return probe.style.color ? getComputedStyle(probe).color : s;
}
function mixCol(sa, sb, t) {
  const A = parseCol(sa), B = parseCol(sb);
  if (A === undefined || B === undefined) return t < .5 ? sa : sb;
  if (!A && !B) return 'none';
  const a = A || [B[0], B[1], B[2], 0], b = B || [A[0], A[1], A[2], 0];
  return colStr(a.map((v, i) => lerp(v, b[i], t)));
}
// fill and stroke as the browser resolves them, with the separate fill/stroke-opacity folded into the alpha
function paintOf(el) {
  const cs = getComputedStyle(el), fold = (c, o) => { const p = parseCol(c); return p ? colStr([p[0], p[1], p[2], p[3] * (+o || 0)]) : c === 'none' ? 'none' : c; };
  return { fill: fold(cs.fill, cs.fillOpacity), stroke: fold(cs.stroke, cs.strokeOpacity), sw: parseFloat(cs.strokeWidth) || 0, rule: cs.fillRule, cap: cs.strokeLinecap, join: cs.strokeLinejoin };
}

/* ───────────────────────── 1. hand-drawn strokes ─────────────────────────
 * o = { rough, bow, strokes, fill, gap, angle, fillWidth }. `r` is a seeded generator: same seed, same drawing. */
const jit = (o, r, gain, x) => o.rough * gain * (r() * 2 - 1) * x;
const gainOf = len => (len < 200 ? 1 : len > 500 ? .4 : -.0016668 * len + 1.233334);
// Rough.js _line: a Bezier that leaves the straight line by a bowing term, with jittered ends; `half` is the second, tighter pass
function lineD(x1, y1, x2, y2, o, r, half) {
  const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
  if (len < .5) return '';
  const g = gainOf(len); let off = 2; if (off * off * 100 > len * len) off = len / 10; if (half) off /= 2;
  const dv = .2 + r() * .2, mx = jit(o, r, g, o.bow * 2 * dy / 200), my = jit(o, r, g, o.bow * 2 * -dx / 200), j = () => jit(o, r, g, off);
  return `M${r1(x1 + j())} ${r1(y1 + j())}C${r1(mx + x1 + dx * dv + j())} ${r1(my + y1 + dy * dv + j())} ${r1(mx + x1 + 2 * dx * dv + j())} ${r1(my + y1 + 2 * dy * dv + j())} ${r1(x2 + j())} ${r1(y2 + j())}`;
}
function curveD(px, py, s, o, r, half) {
  const len = Math.hypot(s.x1 - px, s.y1 - py) + Math.hypot(s.x2 - s.x1, s.y2 - s.y1) + Math.hypot(s.x - s.x2, s.y - s.y2);
  if (len < .5) return '';
  const g = gainOf(len), off = Math.min(2, len / 10) * (half ? .5 : 1), j = () => jit(o, r, g, off);
  return `M${r1(px + j())} ${r1(py + j())}C${r1(s.x1 + j())} ${r1(s.y1 + j())} ${r1(s.x2 + j())} ${r1(s.y2 + j())} ${r1(s.x + j())} ${r1(s.y + j())}`;
}
function pathStroke(subs, o, r, half) {
  let d = '';
  for (const sub of subs) {
    let px = sub.x, py = sub.y;
    for (const s of sub.segs) { d += s.t === 'L' ? lineD(px, py, s.x, s.y, o, r, half) : curveD(px, py, s, o, r, half); px = s.x; py = s.y; }
    if (sub.closed && Math.hypot(px - sub.x, py - sub.y) > .5) d += lineD(px, py, sub.x, sub.y, o, r, half);
  }
  return d;
}
// an ellipse is drawn as one loop that overshoots its own start, through jittered points (Catmull-Rom as cubics)
function ellipseStroke(e, o, r, half) {
  const { cx, cy, rx, ry } = e;
  if (rx < .5 && ry < .5) return '';
  const per = 2 * Math.PI * Math.sqrt((rx * rx + ry * ry) / 2), n = Math.max(9, Math.ceil(per / 120)), inc = 2 * Math.PI / n;
  const a0 = (r() * 2 - 1) * .5 - Math.PI / 2, ovl = inc * (.25 + r() * .5), gain = gainOf(per / 3), amp = half ? .6 : 1, P = [];
  for (let k = -1; k <= n + 1; k++) {
    const a = a0 + (k === n ? 2 * Math.PI + ovl : k === n + 1 ? 2 * Math.PI + ovl + inc : k * inc), rj = 1 + jit(o, r, gain, .03 * amp);
    P.push([cx + rx * rj * Math.cos(a) + jit(o, r, gain, 1.4 * amp), cy + ry * rj * Math.sin(a) + jit(o, r, gain, 1.4 * amp)]);
  }
  let d = `M${r1(P[1][0])} ${r1(P[1][1])}`;
  for (let i = 1; i <= n; i++) {
    const p0 = P[i - 1], p1 = P[i], p2 = P[i + 1], p3 = P[i + 2];
    d += `C${r1(p1[0] + (p2[0] - p0[0]) / 6)} ${r1(p1[1] + (p2[1] - p0[1]) / 6)} ${r1(p2[0] - (p3[0] - p1[0]) / 6)} ${r1(p2[1] - (p3[1] - p1[1]) / 6)} ${r1(p2[0])} ${r1(p2[1])}`;
  }
  return d;
}
// scanline hachure over any number of polygons (even-odd, so holes stay empty); every other line is drawn backwards, as a pen would
function hachure(rings, gap, angle, o, r) {
  const a = angle * Math.PI / 180, c = Math.cos(-a), s = Math.sin(-a), ca = Math.cos(a), sa = Math.sin(a);
  const R = rings.map(g => g.map(p => [p[0] * c - p[1] * s, p[0] * s + p[1] * c]));
  let y0 = 1e9, y1 = -1e9;
  for (const g of R) for (const p of g) { y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
  let d = '', k = 0;
  for (let y = y0 + gap / 2; y < y1; y += gap) {
    const xs = [];
    for (const g of R) for (let i = 0; i < g.length; i++) {
      const p = g[i], q = g[(i + 1) % g.length];
      if ((p[1] <= y && q[1] > y) || (q[1] <= y && p[1] > y)) xs.push(p[0] + (y - p[1]) * (q[0] - p[0]) / (q[1] - p[1]));
    }
    xs.sort((u, v) => u - v);
    for (let i = 0; i + 1 < xs.length; i += 2) {
      if (xs[i + 1] - xs[i] < 1) continue;
      let A = [xs[i], y], B = [xs[i + 1], y];
      if (k++ % 2) [A, B] = [B, A];
      d += lineD(A[0] * ca - A[1] * sa, A[0] * sa + A[1] * ca, B[0] * ca - B[1] * sa, B[0] * sa + B[1] * ca, o, r, true);
    }
  }
  return d;
}
// solid fill: the outline pushed by a slow random drift (a fill that is slightly off register), not vertex noise
function solidD(rings, o, r) {
  let d = '';
  for (const g of rings) {
    const cum = [0]; for (let i = 1; i < g.length; i++) cum.push(cum[i - 1] + Math.hypot(g[i][0] - g[i - 1][0], g[i][1] - g[i - 1][1]));
    const total = cum[cum.length - 1] + Math.hypot(g[0][0] - g[g.length - 1][0], g[0][1] - g[g.length - 1][1]), m = Math.max(3, Math.round(total / 45));
    const ctl = Array.from({ length: m }, () => [jit(o, r, 1, 1.6), jit(o, r, 1, 1.6)]);
    ctl.push(ctl[0]);
    d += 'M' + g.map((p, i) => {
      const u = total ? cum[i] / total * m : 0, k = Math.min(m - 1, Math.floor(u)), f = u - k;
      return `${r1(p[0] + lerp(ctl[k][0], ctl[k + 1][0], f))} ${r1(p[1] + lerp(ctl[k][1], ctl[k + 1][1], f))}`;
    }).join('L') + 'Z';
  }
  return d;
}

/* ───────────────────────── sketch records: one per replaced element ───────────────────────── */
const OPT = { seed: 1, rough: 1, bow: 1, strokes: 2, fill: '', gap: 10, angle: -41, boil: 0, fillWidth: 0 };
const kebab = k => k.replace(/[A-Z]/g, c => '-' + c.toLowerCase());
function optsOf(node) {
  const o = {};
  for (const k of Object.keys(OPT)) {
    const host = node.closest(`[data-sketch-${kebab(k)}]`), v = host ? host.getAttribute(`data-sketch-${kebab(k)}`) : null;
    o[k] = k === 'seed' ? seedOf(v) : k === 'fill' ? (v || OPT.fill).trim().toLowerCase() : numOr(v, OPT[k]);
  }
  o.strokes = clamp(Math.round(o.strokes), 1, 3);
  return o;
}
const GEO_ATTR = /^(d|x|y|x1|y1|x2|y2|cx|cy|r|rx|ry|width|height|points|pathLength|fill|stroke|stroke-width|marker-start|marker-mid|marker-end)$/;
const svgEl = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
const scopeCount = new WeakMap();

function makeRec(orig, o, idx) {
  const t = orig.localName, cs = getComputedStyle(orig);
  const subs = subsOf(orig);
  if (!subs || !subs.length) return null;
  const stroke = cs.stroke !== 'none' && parseFloat(cs.strokeWidth) > 0, fillCol = cs.fill;
  const wantFill = fillCol !== 'none' && (parseCol(fillCol) === undefined || (parseCol(fillCol) || [0, 0, 0, 0])[3] > 0) && t !== 'line';
  const fillMode = wantFill ? (o.fill === 'none' ? 'none' : o.fill || 'hachure') : 'none';
  if (!stroke && fillMode === 'none') return null;
  const g = document.createElementNS(NS, 'g');
  for (const a of [...orig.attributes]) if (!GEO_ATTR.test(a.name)) g.setAttribute(a.name, a.value);
  g.classList.add('dk-sk');
  if (orig.hasAttribute('data-sketch-seed')) o = { ...o, seed: seedOf(orig.getAttribute('data-sketch-seed')) };
  const rec = { g, o, idx, subs, ell: null, stroke, fillMode, cache: new Map(), v: -1, paths: [], fps: o.boil > 0 ? Math.min(o.boil, 60) : 0, hasFill: false };
  if (t === 'circle' || t === 'ellipse') rec.ell = { cx: at(orig, 'cx'), cy: at(orig, 'cy'), rx: t === 'circle' ? at(orig, 'r') : at(orig, 'rx'), ry: t === 'circle' ? at(orig, 'r') : at(orig, 'ry') };
  rec.rings = fillMode === 'none' || fillMode === 'keep' ? null : (rec.ell
    ? [Array.from({ length: 48 }, (_, k) => [rec.ell.cx + rec.ell.rx * Math.cos(k / 48 * 2 * Math.PI), rec.ell.cy + rec.ell.ry * Math.sin(k / 48 * 2 * Math.PI)])]
    : subs.map(s => flatten(s, 6)).filter(p => p.length > 2));
  const sw = parseFloat(cs.strokeWidth) || 3, dash = cs.strokeDasharray;
  const fw = o.fillWidth || Math.max(1.5, (stroke ? sw : 3) * .7);
  const base = 'stroke-linecap:round;stroke-linejoin:round;';   // hatch lines get butt caps: hundreds of round-capped strokes make the GPU raster differ from run to run
  if (fillMode !== 'none') {
    // cross-hatch is two paths, one per direction: strokes that cross inside one path rasterise differently from run to run on some GPUs
    const solid = fillMode === 'solid' || fillMode === 'keep';
    for (let k = 0; k < (fillMode === 'cross' ? 2 : 1); k++) {
      const p = svgEl('path', { d: '', class: 'dk-sk-fill' + (solid ? ' dk-sk-solid' : ''), 'data-sk-ph': k ? '.3' : '.2' });
      p.style.cssText = solid ? `fill:${fillCol};fill-opacity:${cs.fillOpacity};stroke:none;fill-rule:evenodd`
        : `stroke-linecap:butt;stroke-linejoin:round;fill:none;stroke:${fillCol};stroke-opacity:${cs.fillOpacity};stroke-width:${fw}px`;
      g.append(p); rec.paths.push(p);
    }
    rec.hasFill = true;
  }
  if (stroke) {
    for (let k = 0; k < o.strokes; k++) {
      const p = svgEl('path', { d: '', class: 'dk-sk-line', 'data-sk-ph': k ? '.12' : '0' });
      p.style.cssText = `${base}fill:none;stroke:${cs.stroke};stroke-opacity:${cs.strokeOpacity};stroke-width:${sw}px`;
      if (dash && dash !== 'none') p.setAttribute('stroke-dasharray', dash);
      if (k === 0) for (const m of ['markerStart', 'markerMid', 'markerEnd']) if (cs[m] && cs[m] !== 'none') p.style[m] = cs[m];
      g.append(p); rec.paths.push(p);
    }
  }
  paint(rec, 0);
  orig.replaceWith(g);
  return rec;
}
function gen(rec, v) {
  const o = rec.o, r = D.rng(H3(o.seed, rec.idx, v)), out = [];
  if (rec.hasFill) {
    const m = rec.fillMode, gap = Math.max(3, o.gap);
    if (m === 'keep') out.push(subsToD(rec.subs));
    else if (m === 'solid') out.push(solidD(rec.rings, o, r));
    else { out.push(hachure(rec.rings, gap, o.angle, o, r)); if (m === 'cross') out.push(hachure(rec.rings, gap, o.angle + 90, o, r)); }
  }
  if (rec.stroke) for (let k = 0; k < o.strokes; k++) out.push(rec.ell ? ellipseStroke(rec.ell, o, r, k > 0) : pathStroke(rec.subs, o, r, k > 0));
  return out;
}
function paint(rec, v) {
  if (rec.v === v) return;
  let ds = rec.cache.get(v);
  if (!ds) { ds = gen(rec, v); rec.cache.set(v, ds); }
  rec.paths.forEach((p, i) => p.setAttribute('d', ds[i]));
  rec.v = v;
}

/* ───────────────────────── wiring: markup -> records ───────────────────────── */
const slideRecs = new WeakMap(), boilFps = new Map();
const SKIP = 'defs,clipPath,mask,pattern,marker,symbol,.dk-sk,[data-sketch="off"]';
function applySlide(sec) {
  const targets = new Set($$(sec, '[data-morph-to],[data-anim="morph-path"],[data-morph]'));   // morphing shapes stay clean
  for (const n of [...targets]) if (n.dataset.morphTo?.startsWith('#')) { const t = document.querySelector(n.dataset.morphTo); if (t) targets.add(t); }
  let recs = slideRecs.get(sec);
  for (const el of $$(sec, GEO)) {
    const root = el.closest('[data-sketch]');
    if (!root || root.getAttribute('data-sketch') === 'off' || el.closest(SKIP) || targets.has(el)) continue;
    const idx = scopeCount.get(root) || 0; scopeCount.set(root, idx + 1);
    const rec = makeRec(el, optsOf(el), idx);
    if (!rec) continue;
    if (!recs) slideRecs.set(sec, recs = []);
    recs.push(rec);
  }
  if (!recs) return 0;
  // draw-in keeps working: `draw` becomes `sketch-draw`, which also fades solid fills in after the outline
  for (const n of $$(sec, '[data-anim="draw"]')) if (n.matches('.dk-sk') || n.querySelector('.dk-sk')) n.dataset.anim = 'sketch-draw';
  const fps = Math.max(0, ...recs.map(r => r.fps));
  if (fps) {   // one invisible build per slide drives the boil of every shape in it
    let tk = sec.querySelector(':scope > .dk-sk-tick');
    if (!tk) { tk = document.createElement('i'); tk.className = 'dk-sk-tick'; tk.hidden = true; sec.append(tk); }
    tk.dataset.anim = 'sketch-boil'; boilFps.set(sec.id, fps);
  }
  return fps;
}
// Line boil: the drawing is one of a few variants, chosen by the tick of the global clock; frozen (variant 0) in exports, in the rest frame,
// and with reduced motion. Only slides that hold a boiling shape read the clock, and they declare ambient: fps, so others go idle as before.
const NV = 4, bv = t => H3(t, 11, 5) % NV;
const variant = t => { const v = bv(t); return t > 0 && bv(t - 1) === v ? (v + 1) % NV : v; };
D.anim('sketch-boil', { dur: 0,
  init: el => slideRecs.get(el.closest('section.slide')) || [],
  f(el, e, i) {
    const live = D.MODE === 'live' && !RM && !i.st.rest, T = live ? i.st.T : 0;
    for (const rec of i.b.data) paint(rec, rec.fps && live ? variant(Math.floor(T * rec.fps)) : 0);
    return {};
  } });
// Stroke-dash draw-in, but aware of the second stroke (starts a little later) and of solid fills (arrive last).
D.anim('sketch-draw', { dur: 1.2, curve: ease.inOutCubic,
  init(el) {
    const g = el instanceof SVGGeometryElement ? [el] : $$(el, 'path,line,polyline,polygon,circle,ellipse,rect');
    return g.map(x => {
      const solid = x.classList.contains('dk-sk-solid');
      if (!solid) { x.setAttribute('pathLength', '1'); x.style.strokeDasharray = '1 1'; }
      return { x, solid, ph: numOr(x.dataset.skPh, 0) };
    });
  },
  f(el, e, i) {
    const done = i.raw >= 1;
    for (const { x, solid, ph } of i.b.data) {
      if (solid) { x.style.opacity = done ? '' : String(+seg(e, .6, 1).toFixed(3)); continue; }
      const q = seg(e, ph, 1);
      x.style.strokeDasharray = done ? '' : '1 1'; x.style.strokeDashoffset = done ? '' : String(1 - q);
      x.style.opacity = done || q > 0 ? '' : '0';   // a zero-length round dash would show as a dot at the end of the stroke
    }
    return { opacity: i.raw > 0 ? 1 : 0 };
  } });

/* ───────────────────────── 2. path morph ─────────────────────────
 * rings: closed polygons (or open polylines) with a vertex per flattened point. Two sets of rings are paired, their vertex counts are
 * equalised by bisecting the longest edges, their winding is matched and the start vertex rotated to the least total distance. */
const area = p => { let s = 0; for (let i = 0; i < p.length; i++) { const a = p[i], b = p[(i + 1) % p.length]; s += a[0] * b[1] - b[0] * a[1]; } return s / 2; };
const centroid = p => { let x = 0, y = 0; for (const q of p) { x += q[0]; y += q[1]; } return [x / p.length, y / p.length]; };
function ringsOf(subs, tx) {
  return subs.map(s => ({ pts: flatten(s, 5, tx), closed: s.closed })).filter(g => g.pts.length > 1).map(g => ({ ...g, ar: Math.abs(area(g.pts)) }));
}
function grow(pts, n, closed) {
  pts = pts.slice();
  while (pts.length < n) {
    let bi = 0, bl = -1;
    for (let k = 0, m = closed ? pts.length : pts.length - 1; k < m; k++) {
      const a = pts[k], b = pts[(k + 1) % pts.length], l = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2;
      if (l > bl) { bl = l; bi = k; }
    }
    const a = pts[bi], b = pts[(bi + 1) % pts.length];
    pts.splice(bi + 1, 0, [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]);
  }
  return pts;
}
function matchRings(A, B) {
  // greedy pairing by distance between centroids plus difference in size: a ring left without a partner (a hole) is born from a point
  const ca = A.map(g => centroid(g.pts)), cb = B.map(g => centroid(g.pts)), cand = [];
  A.forEach((a, i) => B.forEach((b, j) => cand.push([Math.hypot(ca[i][0] - cb[j][0], ca[i][1] - cb[j][1]) + Math.abs(Math.sqrt(a.ar) - Math.sqrt(b.ar)), i, j])));
  cand.sort((p, q) => p[0] - q[0] || p[1] - q[1] || p[2] - q[2]);
  const ua = new Set(), ub = new Set(), pairs = [];
  for (const [, i, j] of cand) if (!ua.has(i) && !ub.has(j)) { ua.add(i); ub.add(j); pairs.push([i, j]); }
  const dot = (g, c) => ({ pts: g.pts.map(() => c), closed: g.closed, ar: 0 });
  // a ring without a partner is born from (or collapses into) the spot where its nearest neighbour's partner is, and travels with it
  const near = (cs, k, list) => list.reduce((best, [i, j]) => { const ci = cs[k], cc = cs === ca ? ca[i] : cb[j], d = Math.hypot(ci[0] - cc[0], ci[1] - cc[1]); return d < best[0] ? [d, i, j] : best; }, [Infinity, -1, -1]);
  const paired = pairs.slice(), extra = [];
  A.forEach((a, i) => { if (!ua.has(i)) { const [, , j] = near(ca, i, paired); extra.push([a, dot(a, cb[j])]); } });
  B.forEach((b, j) => { if (!ub.has(j)) { const [, i] = near(cb, j, paired); extra.push([dot(b, ca[i]), b]); } });
  return paired.map(([i, j]) => [A[i], B[j]]).concat(extra);
}
function morphRings(A, B) {
  if (!A.length) A = [{ pts: [[0, 0], [0, 0]], closed: false, ar: 0 }];
  if (!B.length) B = [{ pts: [[0, 0], [0, 0]], closed: false, ar: 0 }];
  const plan = [];
  for (const [a, b] of matchRings(A, B)) {
    const closed = a.closed || b.closed, n = Math.max(a.pts.length, b.pts.length, 32);
    let pa = a.ar ? grow(a.pts, n, closed) : Array.from({ length: n }, () => a.pts[0]), pb = b.ar ? grow(b.pts, n, closed) : Array.from({ length: n }, () => b.pts[0]);
    if (a.ar && b.ar) {
      if (closed) {
        if (area(pa) * area(pb) < 0) pb = pb.slice().reverse();
        let best = 0, bd = Infinity;
        for (let s = 0; s < n; s++) { let d = 0; for (let k = 0; k < n; k++) { const p = pa[k], q = pb[(k + s) % n]; d += (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2; } if (d < bd - 1e-9) { bd = d; best = s; } }
        pb = pb.slice(best).concat(pb.slice(0, best));
      } else {
        const d = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]);
        if (d(pa[0], pb[0]) + d(pa[n - 1], pb[n - 1]) > d(pa[0], pb[n - 1]) + d(pa[n - 1], pb[0])) pb = pb.slice().reverse();
      }
    }
    plan.push({ a: Float64Array.from(pa.flat()), b: Float64Array.from(pb.flat()), n, ca: a.closed, cb: b.closed });
  }
  return plan;
}
function planD(plan, e) {
  let d = '';
  for (const g of plan) {
    const { a, b, n } = g;
    for (let k = 0; k < n; k++) d += `${k ? 'L' : 'M'}${r2(a[2 * k] + (b[2 * k] - a[2 * k]) * e)} ${r2(a[2 * k + 1] + (b[2 * k + 1] - a[2 * k + 1]) * e)}`;
    if (e < .5 ? g.ca : g.cb) d += 'Z';
  }
  return d;
}
const planFor = (dA, dB) => morphRings(ringsOf(parseD(dA)), ringsOf(parseD(dB)));

// the build: from the element's own d (progress 0) to data-to (progress 1); a target that is an #id is read once, in init
D.anim('morph-path', { dur: 1.1, curve: ease.inOutCubic,
  init(el) {
    const raw = (el.dataset.to || el.dataset.morphTo || '').trim();
    if (el.localName !== 'path') { warn('morph-path needs a <path> (other shapes are converted when they carry data-morph-to)'); return null; }
    let tgt = null, toD = raw;
    if (raw.startsWith('#')) { tgt = document.querySelector(raw); if (!tgt) { warn(`morph target ${raw} not found`); return null; } toD = dOf(tgt); }
    if (!toD) return null;
    const P0 = paintOf(el), P1 = tgt ? paintOf(tgt) : { ...P0 };
    if (el.dataset.toFill) P1.fill = norm(el.dataset.toFill);
    if (el.dataset.toStroke) P1.stroke = norm(el.dataset.toStroke);
    if (el.dataset.toStrokeWidth) P1.sw = +el.dataset.toStrokeWidth;
    const d0 = el.getAttribute('d') || '', plan = planFor(d0, toD);
    return { d0, d1: toD, plan, P0, P1, multi: plan.length > 1 || parseD(d0).length > 1 || parseD(toD).length > 1, last: '' };
  },
  f(el, e, i) {
    const m = i.b.data; if (!m) return {};
    const raw = i.raw;
    const key = raw <= 0 ? 'A' : raw >= 1 ? 'B' : e.toFixed(5);
    if (key !== m.last) {
      m.last = key;
      const st = el.style;
      if (raw <= 0) { el.setAttribute('d', m.d0); st.fill = st.stroke = st.strokeWidth = st.fillRule = st.fillOpacity = st.strokeOpacity = ''; }
      else {
        const end = raw >= 1;
        el.setAttribute('d', end ? m.d1 : planD(m.plan, e));
        st.fill = end ? m.P1.fill : mixCol(m.P0.fill, m.P1.fill, e); st.stroke = end ? m.P1.stroke : mixCol(m.P0.stroke, m.P1.stroke, e);
        st.strokeWidth = (end ? m.P1.sw : lerp(m.P0.sw, m.P1.sw, e)) + 'px'; st.fillOpacity = st.strokeOpacity = '1';
        st.fillRule = end ? m.P1.rule : m.multi ? 'evenodd' : '';
      }
    }
    return {};
  } });

// data-morph-to on any shape: becomes a <path> and a build. Built once per slide, before the runtime collects the builds.
function pathify(sec) {
  for (const el of $$(sec, '[data-morph-to],[data-anim="morph-path"]')) {
    if (el.localName !== 'path') {
      const subs = subsOf(el); if (!subs) continue;
      const p = svgEl('path', { d: subsToD(subs) });
      for (const a of [...el.attributes]) if (!GEO_ATTR.test(a.name) || /^(fill|stroke|stroke-width)$/.test(a.name)) p.setAttribute(a.name, a.value);
      el.replaceWith(p); p.dataset.morphed = ''; el = p;
    }
    if (!el.dataset.anim) el.dataset.anim = 'morph-path';
    if (el.dataset.morphTo && !el.dataset.to) el.dataset.to = el.dataset.morphTo;
  }
}

/* ───────────────────────── the `morph` slide transition, with shapes ─────────────────────────
 * Same as the core transition for HTML items. For a data-morph item that is an SVG shape on both slides the shape itself morphs (rings in
 * canvas pixels, colours mixed), drawn by an overlay <svg> that lives in the morph layer and leaves with the clone. Ends are the authored
 * paths, so the first frame equals the outgoing slide and the last frame the incoming one.
 * This replaces the registered 'morph' spec (the core function is not reachable from outside); a core hook would make that unnecessary. */
const isGeo = n => n instanceof SVGGeometryElement && !!n.ownerSVGElement;
function toCanvas(node) {
  const M = node.getScreenCTM(), bb = document.querySelector('.deck').getBoundingClientRect(), k = bb.width / D.W;
  return [M.a / k, M.b / k, M.c / k, M.d / k, (M.e - bb.left) / k, (M.f - bb.top) / k];
}
const matrix = m => `matrix(${r2(m[0] * 1e4) / 1e4} ${r2(m[1] * 1e4) / 1e4} ${r2(m[2] * 1e4) / 1e4} ${r2(m[3] * 1e4) / 1e4} ${Math.round(m[4] * 1e3) / 1e3} ${Math.round(m[5] * 1e3) / 1e3})`;
function shapeOf(m) {
  if (m._sk !== undefined) return m._sk;
  const A = m.na, B = m.nb, host = m.ca && m.ca.parentNode;
  if (!isGeo(A) || !isGeo(B) || !host) return (m._sk = null);
  const ma = toCanvas(A), mb = toCanvas(B), sc = t => Math.sqrt(Math.abs(t[0] * t[3] - t[1] * t[2]));
  const sa = subsOf(A), sb = subsOf(B);
  const svg = svgEl('svg', { width: D.W, height: D.H, class: 'dk-sk-morph' }), path = svgEl('path', {});
  svg.style.cssText = 'position:absolute;left:0;top:0;overflow:visible';
  svg.append(path); host.append(svg);
  const rm = m.ca.remove.bind(m.ca); m.ca.remove = () => { rm(); svg.remove(); };
  return (m._sk = { path, ma, mb, sca: sc(ma), scb: sc(mb), dA: dOf(A), dB: dOf(B), PA: paintOf(A), PB: paintOf(B),
    plan: morphRings(ringsOf(sa, ma), ringsOf(sb, mb)), multi: sa.length > 1 || sb.length > 1 });
}
function paintShape(m, e) {
  const s = shapeOf(m); if (!s) return false;
  const st = s.path.style, ends = e <= .002 || e >= .998, P = e < .5 ? s.PA : s.PB;
  if (ends) {
    const b = e >= .5;
    s.path.setAttribute('d', b ? s.dB : s.dA); s.path.setAttribute('transform', matrix(b ? s.mb : s.ma));
    st.fill = P.fill; st.stroke = P.stroke; st.strokeWidth = P.sw + 'px'; st.fillRule = P.rule;
  } else {
    s.path.setAttribute('d', planD(s.plan, e)); s.path.removeAttribute('transform');
    st.fill = mixCol(s.PA.fill, s.PB.fill, e); st.stroke = mixCol(s.PA.stroke, s.PB.stroke, e);
    st.strokeWidth = lerp(s.PA.sw * s.sca, s.PB.sw * s.scb, e) + 'px'; st.fillRule = s.multi || s.plan.length > 1 ? 'evenodd' : P.rule;
  }
  st.strokeLinecap = P.cap; st.strokeLinejoin = P.join;
  return true;
}
D.transition('morph', { dur: 1, fn(A, B, p, o) {
  const e = ease.inOutCubic(p), tr = (x, y) => `translate(${x}px, ${y}px)`;
  A.style.opacity = 1 - ease.outCubic(seg(p, 0, .45));
  B.style.opacity = ease.inOutSine(seg(p, .35, 1));
  for (const m of o.morph || []) {
    if (paintShape(m, e)) continue;
    const { a, b, ca, cb } = m, x = lerp(a.x, b.x, e), y = lerp(a.y, b.y, e), w = lerp(a.w, b.w, e), h = lerp(a.h, b.h, e);
    ca.style.transform = `${tr(x, y)} scale(${w / a.w}, ${h / a.h})`;
    cb.style.transform = `${tr(x, y)} scale(${w / b.w}, ${h / b.h})`;
    const f = seg(e, .15, .85);
    ca.style.opacity = 1 - f; cb.style.opacity = f;
  }
} });

/* ───────────────────────── scan and hook into Deck.slide ───────────────────────── */
const origSlide = D.slide;
function prepare(sec) { pathify(sec); return applySlide(sec); }
D.slide = function (id, spec) {
  const user = spec || {};
  spec = { ...user, setup(el, api) { user.setup?.(el, api); const f = prepare(el); if (f && spec.ambient == null) spec.ambient = f; } };
  if (boilFps.has(id) && spec.ambient == null) spec.ambient = boilFps.get(id);
  return origSlide.call(D, id, spec);
};
function scan() {
  const deck = document.querySelector('.deck');
  if (!deck) { console.error('deck-kit sketch: no .deck element yet; load the plugin after the deck markup'); return; }
  for (const me of document.scripts) {
    if (me.id === 'deck-kit-sketch-js') break;
    if (!me.src && !/^deck-kit/.test(me.id) && /Deck\.slide\(/.test(me.text)) { console.error('deck-kit sketch: load the plugin before the deck script that calls Deck.slide(); its hooks would be replaced'); break; }
  }
  $$(deck, ':scope > section.slide').forEach((sec, i) => {
    if (!sec.querySelector('[data-sketch],[data-morph-to],[data-anim="morph-path"]')) return;
    if (!sec.id) sec.id = `sketch-slide-${i + 1}`;
    const f = prepare(sec);
    if (f) origSlide.call(D, sec.id, { ambient: f });
  });
}
scan();

D.sketch = {
  // sketch every [data-sketch] shape under root (a slide's setup() that builds SVG calls this; the plugin already calls it after every setup)
  apply: root => prepare(root),
  // Flubber-style: morph('M..', 'M..') -> t => path data; t = 0 and 1 return the inputs untouched
  morph(dA, dB) { const plan = planFor(dA, dB); return t => (t <= 1e-4 ? dA : t >= 1 - 1e-4 ? dB : planD(plan, t)); },
  // the strokes of a path as sketchy path data: strokes('M..', { seed, rough, bow, strokes }) -> [d, d]
  strokes(d, opt = {}) {
    const o = { ...OPT, ...opt, seed: seedOf(opt.seed) }, r = D.rng(H3(o.seed, 0, 0)), subs = parseD(d);
    return Array.from({ length: clamp(Math.round(o.strokes), 1, 3) }, (_, k) => pathStroke(subs, o, r, k > 0));
  },
};
})();
