/*!
 * video-gaga runtime — deterministic Canvas motion graphics for video.
 * MIT License. Zero dependencies. Works in any modern browser and in the
 * video-gaga renderer (headless Chromium → ffmpeg).
 *
 * The one rule: every pixel of frame N must be a pure function of time
 * t = N / fps. No Date.now(), no Math.random(), no setTimeout, no state
 * carried between frames. Use CV.rand(seed) and the helpers below.
 */
(function (root) {
  'use strict';

  // ===========================================================================
  // Math & easing
  // ===========================================================================
  const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
  const lerp = (a, b, p) => a + (b - a) * p;
  const invLerp = (a, b, v) => (b === a ? 0 : (v - a) / (b - a));
  const remap = (v, a, b, c, d, ease) => {
    const p = clamp(invLerp(a, b, v));
    return lerp(c, d, ease ? ease(p) : p);
  };

  // Cubic-bezier easing identical to CSS cubic-bezier(x1, y1, x2, y2).
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = (t) => ((ax * t + bx) * t + cx) * t;
    const sy = (t) => ((ay * t + by) * t + cy) * t;
    const dsx = (t) => (3 * ax * t + 2 * bx) * t + cx;
    return function (x) {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      let t = x;
      for (let i = 0; i < 8; i++) {
        const e = sx(t) - x;
        if (Math.abs(e) < 1e-6) return sy(t);
        const d = dsx(t);
        if (Math.abs(d) < 1e-6) break;
        t -= e / d;
      }
      let lo = 0, hi = 1;
      t = x;
      for (let i = 0; i < 30; i++) {
        const v = sx(t);
        if (Math.abs(v - x) < 1e-6) break;
        if (v < x) lo = t; else hi = t;
        t = (lo + hi) / 2;
      }
      return sy(t);
    };
  }

  const ease = {
    linear: (p) => p,
    inQuad: (p) => p * p,
    outQuad: (p) => 1 - (1 - p) * (1 - p),
    inOutQuad: (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2),
    inCubic: (p) => p * p * p,
    outCubic: (p) => 1 - Math.pow(1 - p, 3),
    inOutCubic: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    outQuart: (p) => 1 - Math.pow(1 - p, 4),
    inOutQuart: (p) => (p < 0.5 ? 8 * p ** 4 : 1 - Math.pow(-2 * p + 2, 4) / 2),
    outQuint: (p) => 1 - Math.pow(1 - p, 5),
    inOutQuint: (p) => (p < 0.5 ? 16 * p ** 5 : 1 - Math.pow(-2 * p + 2, 5) / 2),
    inExpo: (p) => (p === 0 ? 0 : Math.pow(2, 10 * p - 10)),
    outExpo: (p) => (p === 1 ? 1 : 1 - Math.pow(2, -10 * p)),
    inOutExpo: (p) =>
      p === 0 ? 0 : p === 1 ? 1 : p < 0.5 ? Math.pow(2, 20 * p - 10) / 2 : (2 - Math.pow(2, -20 * p + 10)) / 2,
    outCirc: (p) => Math.sqrt(1 - Math.pow(p - 1, 2)),
    inOutSine: (p) => -(Math.cos(Math.PI * p) - 1) / 2,
    outBack: (p, s = 1.4) => 1 + (s + 1) * Math.pow(p - 1, 3) + s * Math.pow(p - 1, 2),
    // Motion-design vocabulary (named for intent, not math):
    standard: bezier(0.2, 0, 0, 1), // default UI/graphic move: quick start, long settle
    enter: bezier(0.05, 0.7, 0.1, 1), // decelerate into place (things arriving)
    exit: bezier(0.3, 0, 0.8, 0.15), // accelerate away (things leaving)
    swift: bezier(0.55, 0, 0.1, 1), // punchy scene moves, camera pushes
    gentle: bezier(0.45, 0, 0.55, 1), // slow ambient drifts
    bezier,
  };

  // Closed-form damped spring step response from 0 → 1.
  // Pure function of time: spring(t) never depends on previous frames.
  // Physical knobs {stiffness, damping, mass}, or the one number every library
  // translates to: {ratio, hz} (damping ratio 1 = no bounce, 0.8 premium,
  // 0.5 playful; hz = natural frequency, default 2).
  function spring(opts = {}) {
    let k = opts.stiffness ?? 170, c = opts.damping ?? 26, m = opts.mass ?? 1;
    if (opts.ratio != null) {
      const w = 2 * Math.PI * (opts.hz ?? 2);
      k = w * w * m;
      c = 2 * opts.ratio * Math.sqrt(k * m);
    }
    const v0 = -(opts.velocity ?? 0);
    const w0 = Math.sqrt(k / m), zeta = c / (2 * Math.sqrt(k * m));
    return function (t) {
      if (t <= 0) return 0;
      let x;
      if (zeta < 1) {
        const wd = w0 * Math.sqrt(1 - zeta * zeta);
        x = Math.exp(-zeta * w0 * t) * (Math.cos(wd * t) + ((zeta * w0 - v0) / wd) * Math.sin(wd * t));
      } else if (zeta === 1) {
        x = Math.exp(-w0 * t) * (1 + (w0 - v0) * t);
      } else {
        const r = Math.sqrt(zeta * zeta - 1);
        const a = -w0 * (zeta - r), b = -w0 * (zeta + r);
        const A = (v0 - b) / (a - b);
        x = A * Math.exp(a * t) + (1 - A) * Math.exp(b * t);
        return 1 - x;
      }
      return 1 - x;
    };
  }
  spring.presets = {
    smooth: { stiffness: 120, damping: 22 }, // ratio 1.0: no overshoot, natural settle
    snappy: { stiffness: 300, damping: 30 }, // ratio 0.87: fast, barely overshoots
    bouncy: { stiffness: 220, damping: 14 }, // ratio 0.47: visible overshoot — use sparingly
    heavy: { stiffness: 80, damping: 20, mass: 1.6 }, // ratio 0.88, slow
  };

  // Eased 0→1 progress of a window [start, start+dur] at time t.
  function progress(t, start, dur, e = ease.standard) {
    if (dur <= 0) return t >= start ? 1 : 0;
    return e(clamp((t - start) / dur));
  }

  // Keyframes: tween(t, [[0, 0], [1, 100, ease.outCubic], [2, 50]])
  // Each key is [time, value, easeIntoThisKey]. Values may be numbers or arrays.
  function tween(t, keys) {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const [t1, v1, e] = keys[i];
      if (t <= t1) {
        const [t0, v0] = keys[i - 1];
        const p = (e || ease.standard)(clamp(invLerp(t0, t1, t)));
        if (Array.isArray(v0)) return v0.map((a, j) => lerp(a, v1[j], p));
        return lerp(v0, v1, p);
      }
    }
    return keys[keys.length - 1][1];
  }

  // A value that is re-targeted over time, animated by springs: the sum of one
  // spring per change keeps it a pure function of t.
  // springTrack(t, [[0, 0], [1.2, 300], [2.0, 120]], spring.presets.snappy)
  function springTrack(t, changes, opts) {
    const s = spring(opts);
    let v = changes[0][1];
    for (let i = 1; i < changes.length; i++) {
      const [tc, target] = changes[i];
      const prev = changes[i - 1][1];
      v += (target - prev) * s(t - tc);
    }
    return v;
  }

  const stagger = (i, each, start = 0) => start + i * each;

  // Deterministic PRNG (mulberry32). CV.rand(seed)() → [0,1)
  function rand(seed = 1) {
    let a = (typeof seed === 'string' ? hashString(seed) : seed) >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hashString(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
    return h >>> 0;
  }
  // Smooth 1D value noise in [-1, 1], deterministic by seed.
  function noise(x, seed = 0) {
    const h = (n) => {
      const r = Math.sin(n * 127.1 + seed * 311.7) * 43758.5453;
      return (r - Math.floor(r)) * 2 - 1;
    };
    const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
    return lerp(h(i), h(i + 1), u);
  }

  // ===========================================================================
  // Color
  // ===========================================================================
  function parseColor(c) {
    if (Array.isArray(c)) return c.length === 3 ? [...c, 1] : c;
    c = String(c).trim();
    if (c[0] === '#') {
      let h = c.slice(1);
      if (h.length === 3 || h.length === 4) h = h.split('').map((x) => x + x).join('');
      const n = parseInt(h.slice(0, 6), 16);
      const a = h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1;
      return [(n >> 16) & 255, (n >> 8) & 255, n & 255, a];
    }
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (m) {
      const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
      return [p[0], p[1], p[2], p[3] ?? 1];
    }
    return [0, 0, 0, 1];
  }
  const color = {
    parse: parseColor,
    rgba: (c, a) => {
      const [r, g, b, a0] = parseColor(c);
      return `rgba(${r | 0},${g | 0},${b | 0},${a ?? a0})`;
    },
    // Mixed in OKLab, so the midpoint keeps its lightness and saturation
    // (an sRGB lerp goes grey and muddy between two saturated colours).
    mix: (a, b, p) => {
      const A = parseColor(a), B = parseColor(b);
      const LA = toOklab(A), LB = toOklab(B);
      const [r, g, bl] = fromOklab([lerp(LA[0], LB[0], p), lerp(LA[1], LB[1], p), lerp(LA[2], LB[2], p)]);
      return `rgba(${r},${g},${bl},${lerp(A[3], B[3], p)})`;
    },
  };
  function toOklab([r, g, b]) {
    const lin = (c) => ((c /= 255) <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    r = lin(r); g = lin(g); b = lin(b);
    const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
  }
  function fromOklab([L, a, b]) {
    const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
    const srgb = (x) => Math.round(255 * clamp(x <= 0.0031308 ? 12.92 * x : 1.055 * x ** (1 / 2.4) - 0.055, 0, 1));
    return [srgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s), srgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s), srgb(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s)];
  }

  // ===========================================================================
  // Text: CJK-aware line breaking + per-glyph animation helpers
  // ===========================================================================
  const CJK = /[\u2E80-\u2FFF\u3000-\u303F\u3040-\u30FF\u3100-\u312F\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AF\uF900-\uFAFF\uFF00-\uFFEF]/;
  // Characters that must not start a line (kinsoku shori) / must not end one.
  const NO_START = '，。、；：？！）》」』】〉〕”’…—～·,.!?;:)]}%‰℃°';
  const NO_END = '（《「『【〈〔“‘([{$¥￥#';
  const isCJK = (ch) => CJK.test(ch);

  // Split text into breakable units: each CJK char is a unit; Latin words,
  // numbers (incl. 3.5%, 2026) and spaces are units. Punctuation attaches to
  // the preceding unit (no-start) or the following unit (no-end).
  function tokenize(text) {
    const units = [];
    let buf = '';
    const flush = () => { if (buf) { units.push(buf); buf = ''; } };
    for (const ch of Array.from(text)) {
      if (ch === '\n') { flush(); units.push('\n'); continue; }
      if (/\s/.test(ch)) { flush(); units.push(' '); continue; }
      if (NO_START.includes(ch)) {
        if (buf) buf += ch;
        else if (units.length && units[units.length - 1] !== ' ' && units[units.length - 1] !== '\n') units[units.length - 1] += ch;
        else buf = ch;
        continue;
      }
      if (isCJK(ch)) {
        const openPending = buf && Array.from(buf).every((c) => NO_END.includes(c));
        if (!openPending) flush();
        buf += ch;
        flush();
        continue;
      }
      if (NO_END.includes(ch)) { flush(); buf = ch; continue; }
      // Latin / digits: extend current run unless it ended in a CJK char
      if (buf && isCJK(Array.from(buf).pop())) flush();
      buf += ch;
    }
    flush();
    return units;
  }

  // Break text into lines that fit maxWidth using ctx's current font.
  function wrap(ctx, text, maxWidth) {
    const units = tokenize(String(text));
    const lines = [];
    let line = '';
    const push = () => { lines.push(line.replace(/\s+$/, '')); line = ''; };
    for (const u of units) {
      if (u === '\n') { push(); continue; }
      if (u === ' ' && !line) continue;
      const test = line + u;
      if (line && ctx.measureText(test).width > maxWidth) {
        // hanging punctuation: allow a lone no-start char to overflow
        if (Array.from(u).every((c) => NO_START.includes(c))) { line = test; continue; }
        push();
        line = u === ' ' ? '' : u;
      } else line = test;
    }
    if (line || !lines.length) push();
    return lines;
  }

  // Largest font size (px) at which `text` fits in maxWidth (single line).
  function fitSize(ctx, text, fontTpl, maxWidth, maxSize = 400, minSize = 8) {
    let lo = minSize, hi = maxSize;
    for (let i = 0; i < 18; i++) {
      const mid = (lo + hi) / 2;
      ctx.font = fontTpl.replace('{size}', mid.toFixed(2));
      if (ctx.measureText(text).width > maxWidth) hi = mid; else lo = mid;
    }
    ctx.font = fontTpl.replace('{size}', lo.toFixed(2));
    return lo;
  }

  // Per-glyph layout for kinetic typography. Returns [{ch, x, y, w, i, line}]
  // positioned for textAlign='left', textBaseline='alphabetic'.
  function glyphs(ctx, text, x, y, opts = {}) {
    const lines = opts.maxWidth ? wrap(ctx, text, opts.maxWidth) : String(text).split('\n');
    const lh = opts.lineHeight ?? parseFloat(ctx.font.match(/(\d+(?:\.\d+)?)px/)?.[1] || 40) * 1.2;
    const align = opts.align || 'left';
    const out = [];
    let gi = 0;
    lines.forEach((ln, li) => {
      const lw = ctx.measureText(ln).width;
      let cx = align === 'center' ? x - lw / 2 : align === 'right' ? x - lw : x;
      const chars = Array.from(ln);
      let acc = '';
      for (const ch of chars) {
        const before = ctx.measureText(acc).width;
        acc += ch;
        const after = ctx.measureText(acc).width;
        out.push({ ch, x: cx + before, y: y + li * lh, w: after - before, i: gi++, line: li });
      }
    });
    out.lines = lines;
    out.lineHeight = lh;
    return out;
  }

  // Words (space-separated) or CJK chars as reveal units with their positions.
  function words(ctx, text, x, y, opts = {}) {
    const g = glyphs(ctx, text, x, y, opts);
    const out = [];
    let cur = null;
    for (const c of g) {
      const breakHere = c.ch === ' ' || isCJK(c.ch) || !cur || cur.line !== c.line || isCJK(cur.text.slice(-1));
      if (c.ch === ' ') { cur = null; continue; }
      if (breakHere && !(cur && NO_START.includes(c.ch))) {
        cur = { text: c.ch, x: c.x, y: c.y, w: c.w, line: c.line, i: out.length };
        out.push(cur);
      } else {
        cur.text += c.ch;
        cur.w = c.x + c.w - cur.x;
      }
    }
    out.lines = g.lines;
    out.lineHeight = g.lineHeight;
    return out;
  }

  const text = { tokenize, wrap, fitSize, glyphs, words, isCJK };

  // ===========================================================================
  // Drawing helpers
  // ===========================================================================
  function roundRect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  // Stroke a polyline progressively (p in 0..1) — "draw-on" lines.
  function drawOn(ctx, pts, p) {
    if (p <= 0 || pts.length < 2) return;
    let total = 0;
    const seg = [];
    for (let i = 1; i < pts.length; i++) {
      const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      seg.push(d);
      total += d;
    }
    let left = total * clamp(p);
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length && left > 0; i++) {
      const d = seg[i - 1];
      const k = Math.min(1, left / d);
      ctx.lineTo(lerp(pts[i - 1][0], pts[i][0], k), lerp(pts[i - 1][1], pts[i][1], k));
      left -= d;
    }
    ctx.stroke();
  }

  // Hand-drawn wobbly line points between two points (deterministic by seed).
  function sketchLine(x1, y1, x2, y2, opts = {}) {
    const r = rand(opts.seed ?? 7);
    const n = opts.steps ?? Math.max(4, Math.round(Math.hypot(x2 - x1, y2 - y1) / 24));
    const amp = opts.roughness ?? 2.2;
    const nx = -(y2 - y1), ny = x2 - x1, nl = Math.hypot(nx, ny) || 1;
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const k = i / n;
      const off = (r() - 0.5) * 2 * amp * Math.sin(Math.PI * k + 0.2);
      pts.push([lerp(x1, x2, k) + (nx / nl) * off, lerp(y1, y2, k) + (ny / nl) * off]);
    }
    return pts;
  }

  function sketchCircle(cx, cy, rad, opts = {}) {
    const r = rand(opts.seed ?? 11);
    const n = opts.steps ?? 48, amp = opts.roughness ?? 2.5;
    const start = r() * Math.PI * 2, over = opts.overshoot ?? 0.12;
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const a = start + (i / n) * Math.PI * 2 * (1 + over);
      const rr = rad + (r() - 0.5) * amp * 2 + Math.sin(a * 3) * amp * 0.5;
      pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
    }
    return pts;
  }

  // Film grain: pre-rendered seeded noise tiles, cycled per frame.
  const grainTiles = [];
  function grain(ctx, frame, amount = 0.06, opts = {}) {
    if (amount <= 0) return;
    const size = 256;
    if (!grainTiles.length) {
      for (let k = 0; k < 8; k++) {
        const c = makeCanvas(size, size);
        const g = c.getContext('2d', { willReadFrequently: RENDER });
        const img = g.createImageData(size, size);
        const r = rand(1000 + k);
        for (let i = 0; i < img.data.length; i += 4) {
          const v = (r() * 255) | 0;
          img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
          img.data[i + 3] = 255;
        }
        g.putImageData(img, 0, 0);
        grainTiles.push(c);
      }
    }
    const tile = grainTiles[(frame | 0) % grainTiles.length];
    const W = ctx.canvas.__cvW || ctx.canvas.width, H = ctx.canvas.__cvH || ctx.canvas.height;
    ctx.save();
    ctx.globalAlpha = amount;
    ctx.globalCompositeOperation = opts.blend || 'overlay';
    const pat = ctx.createPattern(tile, 'repeat');
    const r = rand(frame + 99);
    ctx.translate(-r() * size, -r() * size);
    ctx.fillStyle = pat;
    ctx.fillRect(0, 0, W + size, H + size);
    ctx.restore();
  }

  function vignette(ctx, W, H, amount = 0.45, col = '#000') {
    const g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.25, W / 2, H / 2, Math.hypot(W, H) * 0.6);
    g.addColorStop(0, color.rgba(col, 0));
    g.addColorStop(1, color.rgba(col, amount));
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
  }

  // Camera: scale/rotate/translate around the frame centre (or a focus point).
  // cam.depth places a layer relative to the subject plane (1): a far layer
  // (0.3) sees the same camera with less zoom and travel, a near one (1.6)
  // more, so planes separate when the camera moves.
  function camera(ctx, W, H, cam, fn) {
    const d = cam.depth ?? 1;
    const zoom = (cam.zoom ?? 1) ** d, x = (cam.x ?? 0) * d, y = (cam.y ?? 0) * d, rot = (cam.rotate ?? 0) * d;
    const fx = cam.focusX ?? W / 2, fy = cam.focusY ?? H / 2;
    ctx.save();
    ctx.translate(W / 2, H / 2);
    ctx.rotate(rot);
    ctx.scale(zoom, zoom);
    ctx.translate(-fx - x, -fy - y);
    fn();
    ctx.restore();
  }

  // A keyed camera: cameraAt(t, [[0, { zoom: 1 }], [1.5, { zoom: 3, x: 120 }, ease.swift]])
  // → { zoom, x, y, rotate, focusX, focusY } for camera(). Each key is
  // [time, fields, easeIntoThisKey]; fields a key leaves out hold. Zoom is
  // interpolated in log space, so a push from 1 to 4 moves evenly instead of
  // speeding up as it gets closer.
  function cameraAt(t, keys) {
    let cur = { zoom: 1, x: 0, y: 0, rotate: 0 };
    const k = keys.map(([kt, v, e]) => {
      cur = { ...cur, ...v };
      return [kt, [Math.log2(cur.zoom), cur.x, cur.y, cur.rotate, cur.focusX ?? NaN, cur.focusY ?? NaN], e];
    });
    const [lz, x, y, rotate, fx, fy] = tween(t, k);
    const out = { zoom: 2 ** lz, x, y, rotate };
    if (!Number.isNaN(fx)) out.focusX = fx;
    if (!Number.isNaN(fy)) out.focusY = fy;
    return out;
  }

  function makeCanvas(w, h) {
    if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
    const c = document.createElement('canvas');
    c.width = w;
    c.height = h;
    return c;
  }

  // Arrow that draws on from (x1,y1) to (x2,y2); the head appears at the end.
  // opts: { head=18, bend (perpendicular offset of the midpoint, px), width }
  function arrow(ctx, x1, y1, x2, y2, p, opts = {}) {
    if (p <= 0) return;
    const bend = opts.bend ?? 0, n = bend ? 24 : 1;
    const mx = (x1 + x2) / 2 - (y2 - y1) * 0, my = (y1 + y2) / 2;
    const len = Math.hypot(x2 - x1, y2 - y1) || 1;
    const cx = mx + (-(y2 - y1) / len) * bend, cy = my + ((x2 - x1) / len) * bend;
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const k = i / n;
      pts.push(bend ? [(1 - k) ** 2 * x1 + 2 * (1 - k) * k * cx + k * k * x2, (1 - k) ** 2 * y1 + 2 * (1 - k) * k * cy + k * k * y2] : [lerp(x1, x2, k), lerp(y1, y2, k)]);
    }
    if (opts.width) ctx.lineWidth = opts.width;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    drawOn(ctx, pts, p);
    const hp = clamp((p - 0.8) / 0.2);
    if (hp <= 0) return;
    const tip = along(pts, p), h = (opts.head ?? 18) * ease.outCubic(hp);
    ctx.beginPath();
    ctx.moveTo(tip.x - Math.cos(tip.angle - 0.5) * h, tip.y - Math.sin(tip.angle - 0.5) * h);
    ctx.lineTo(tip.x, tip.y);
    ctx.lineTo(tip.x - Math.cos(tip.angle + 0.5) * h, tip.y - Math.sin(tip.angle + 0.5) * h);
    ctx.stroke();
  }

  // Arc stroked from a0 toward a1 (radians, 0 = 3 o'clock) by progress p.
  function arcOn(ctx, cx, cy, r, a0, a1, p) {
    if (p <= 0) return;
    ctx.beginPath();
    ctx.arc(cx, cy, r, a0, lerp(a0, a1, clamp(p)), a1 < a0);
    ctx.stroke();
  }

  const draw = { roundRect, drawOn, sketchLine, sketchCircle, grain, vignette, camera, cameraAt, arrow, arc: arcOn };

  // ===========================================================================
  // Motion primitives (fx) — the reusable "moves" of motion design
  // ===========================================================================
  // Masked line reveal: each line rises out of its own clip box, staggered.
  // opts: { lineHeight, stagger=0.08, dur=0.7, ease, align, rise=1 (in line heights), exit: 0..1 }
  function lineReveal(ctx, lines, x, y, t, opts = {}) {
    const size = parseFloat(ctx.font.match(/(\d+(?:\.\d+)?)px/)?.[1] || 40);
    const lh = opts.lineHeight ?? size * 1.1;
    const e = opts.ease || ease.enter, dur = opts.dur ?? 0.7, st = opts.stagger ?? 0.08;
    const exit = opts.exit ?? 0;
    ctx.save();
    ctx.textAlign = opts.align || ctx.textAlign;
    lines.forEach((ln, i) => {
      const p = e(clamp((t - i * st) / dur));
      const q = ease.exit(clamp(exit * (1 + st * lines.length) - i * st));
      if (p <= 0) return;
      const w = ctx.measureText(ln).width;
      const align = ctx.textAlign;
      const lx = align === 'center' ? x - w / 2 : align === 'right' || align === 'end' ? x - w : x;
      const ly = y + i * lh;
      ctx.save();
      ctx.beginPath();
      ctx.rect(lx - size, ly - size * 1.05, w + size * 2, size * 1.35);
      ctx.clip();
      ctx.fillText(ln, x, ly + (1 - p) * lh * (opts.rise ?? 1) - q * lh);
      ctx.restore();
    });
    ctx.restore();
  }

  // Per-character reveal (fade + rise + optional blur), staggered.
  // `exit` (0..1) sends the characters out again with the same stagger.
  function charReveal(ctx, str, x, y, t, opts = {}) {
    const g = glyphs(ctx, str, x, y, opts);
    const e = opts.ease || ease.enter, dur = opts.dur ?? 0.5, st = opts.stagger ?? 0.035;
    const rise = opts.rise ?? 0.35, exit = opts.exit ?? 0;
    const size = parseFloat(ctx.font.match(/(\d+(?:\.\d+)?)px/)?.[1] || 40);
    ctx.save();
    const align = ctx.textAlign;
    ctx.textAlign = 'left';
    for (const c of g) {
      const p = e(clamp((t - c.i * st) / dur));
      const q = ease.exit(clamp(exit * 1.4 - (c.i / Math.max(1, g.length - 1)) * 0.4));
      if (p <= 0 || q >= 1) continue;
      ctx.globalAlpha = p * (1 - q) * (opts.alpha ?? 1);
      if (opts.blur) ctx.filter = `blur(${((1 - p + q) * opts.blur).toFixed(2)}px)`;
      ctx.fillText(c.ch, c.x, c.y + (1 - p) * size * rise - q * size * rise);
    }
    ctx.filter = 'none';
    ctx.textAlign = align;
    ctx.restore();
    return g;
  }

  // Formatted number count-up. countUp(p, 0, 12500, { decimals: 0, sep: ',' })
  function countUp(p, from, to, opts = {}) {
    const v = lerp(from, to, clamp(p));
    const d = opts.decimals ?? 0;
    let s = v.toFixed(d);
    if (opts.sep !== false) {
      const [i, f] = s.split('.');
      s = i.replace(/\B(?=(\d{3})+(?!\d))/g, opts.sep ?? ',') + (f ? '.' + f : '');
    }
    return (opts.prefix ?? '') + s + (opts.suffix ?? '');
  }

  // Typewriter: substring by grapheme, with optional blinking caret.
  function typewriter(str, p, opts = {}) {
    const chars = Array.from(str);
    const n = Math.floor(clamp(p) * chars.length + 1e-6);
    let s = chars.slice(0, n).join('');
    if (opts.caret && (p < 1 || Math.floor((opts.t ?? 0) * 2) % 2 === 0)) s += opts.caret;
    return s;
  }

  // Clip drawing to a rect (mask).
  function mask(ctx, x, y, w, h, fn) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    ctx.clip();
    fn();
    ctx.restore();
  }

  // "On twos/threes": quantize time to animate at a lower rate (hand-made feel).
  const onTwos = (t, fps = 30, n = 2) => Math.floor((t * fps) / n) * (n / fps);

  const fontPx = (ctx) => parseFloat(ctx.font.match(/(\d+(?:\.\d+)?)px/)?.[1] || 40);

  // Word-by-word reveal (rise + fade + optional unblur). CJK reveals per
  // character. Timing: `times` (local seconds per unit), or `sync: s` to land
  // every word exactly when the voice says it, else a plain `stagger`.
  // `exit` (0..1) sends the words out again, staggered, in reading order.
  // opts: { stagger=0.06, dur=0.45, rise=0.3, blur, ghost (alpha before reveal), align, maxWidth, lineHeight, colorFor(unit, i) }
  function wordReveal(ctx, str, x, y, t, opts = {}) {
    const ws = words(ctx, str, x, y, opts);
    const e = opts.ease || ease.enter, dur = opts.dur ?? 0.45, st = opts.stagger ?? 0.06;
    const size = fontPx(ctx), rise = opts.rise ?? 0.3, ghost = opts.ghost ?? 0;
    const times = opts.times || (opts.sync ? opts.sync.syncTimes(ws.map((w) => w.text), opts.stagger ?? 0.12) : null);
    const exit = opts.exit ?? 0, n = ws.length;
    ctx.save();
    const base = ctx.fillStyle;
    ctx.textAlign = 'left';
    ws.forEach((w, i) => {
      const t0 = times ? times[Math.min(i, times.length - 1)] ?? 0 : i * st;
      const p = e(clamp((t - t0) / dur));
      const q = ease.exit(clamp(exit * (1 + 0.4) - (i / Math.max(1, n - 1)) * 0.4));
      const a = (ghost + (1 - ghost) * p) * (1 - q);
      if (a <= 0.001) return;
      ctx.globalAlpha = a * (opts.alpha ?? 1);
      if (opts.blur && p < 1) ctx.filter = `blur(${((1 - p) * opts.blur).toFixed(2)}px)`;
      ctx.fillStyle = opts.colorFor ? opts.colorFor(w, i, p) || base : base;
      ctx.fillText(w.text, w.x, w.y + (1 - p) * size * rise - q * size * rise);
      ctx.filter = 'none';
    });
    ctx.restore();
    return ws;
  }

  // Decode / scramble text: resolved characters left→right, the rest cycle
  // through `chars` (deterministic for a given p and seed).
  function scramble(str, p, opts = {}) {
    const chars = Array.from(str);
    const pool = Array.from(opts.chars || '01<>/#%&*+=?ABCDEFGHJKLMNPQRSTUVWXYZ');
    const n = Math.floor(clamp(p) * chars.length + 1e-6);
    const r = rand((opts.seed ?? 1) * 7919 + Math.floor(clamp(p) * (opts.rate ?? 40)));
    // spaces and punctuation (":", ".", "-") stay put: only letters and digits scramble
    return chars.map((c, i) => (i < n || /[\s\p{P}\p{S}]/u.test(c) ? c : pool[Math.floor(r() * pool.length)])).join('');
  }

  // Odometer: each digit rolls up into place inside its own mask, rightmost
  // digits spin further (like a real counter). Non-digits fade in.
  // opts: { stagger=0.06, dur (fraction of p each digit uses)=0.75, spins=1, align, ease }
  function roll(ctx, str, x, y, p, opts = {}) {
    const chars = Array.from(String(str));
    const size = fontPx(ctx), lh = opts.lineHeight ?? size * 1.05;
    const e = opts.ease || ease.outQuart;
    const widths = chars.map((c) => ctx.measureText(c).width);
    const total = widths.reduce((a, b) => a + b, 0);
    const align = opts.align || ctx.textAlign;
    let cx = align === 'center' ? x - total / 2 : align === 'right' || align === 'end' ? x - total : x;
    const digits = chars.filter((c) => /\d/.test(c)).length;
    const span = opts.dur ?? 0.75, st = digits > 1 ? (1 - span) / (digits - 1) : 0;
    let k = 0;
    ctx.save();
    ctx.textAlign = 'left';
    chars.forEach((c, i) => {
      if (/\d/.test(c)) {
        const d = Number(c), spins = (opts.spins ?? 1) + Math.floor((digits - 1 - k) / 2);
        const q = e(clamp((clamp(p) - k * st) / span));
        const pos = (d + 10 * spins) * q; // distance rolled, in digits
        const lo = Math.floor(pos), frac = pos - lo;
        ctx.save();
        ctx.beginPath();
        ctx.rect(cx - 2, y - size * 0.92, widths[i] + 4, size * 1.12);
        ctx.clip();
        ctx.fillText(String(lo % 10), cx, y - frac * lh);
        if (frac > 0.001) ctx.fillText(String((lo + 1) % 10), cx, y + (1 - frac) * lh);
        ctx.restore();
        k++;
      } else {
        const a0 = ctx.globalAlpha;
        ctx.globalAlpha = a0 * clamp(p * 3);
        ctx.fillText(c, cx, y);
        ctx.globalAlpha = a0;
      }
      cx += widths[i];
    });
    ctx.restore();
    return total;
  }

  // Marker swipe behind a term: a rounded bar grows left→right (draw before the text).
  function highlight(ctx, x, y, w, h, p, opts = {}) {
    if (p <= 0) return;
    ctx.save();
    ctx.fillStyle = opts.color || 'rgba(255,216,77,.75)';
    if (opts.blend) ctx.globalCompositeOperation = opts.blend;
    const skew = opts.skew ?? 0;
    ctx.transform(1, 0, skew, 1, -skew * y, 0);
    roundRect(ctx, x, y, w * clamp(p), h, opts.radius ?? h * 0.18);
    ctx.fill();
    ctx.restore();
  }

  // Point + tangent angle at progress p along a polyline (motion paths).
  function along(pts, p) {
    let total = 0;
    const seg = [];
    for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); total += d; }
    let left = total * clamp(p);
    for (let i = 1; i < pts.length; i++) {
      const d = seg[i - 1];
      if (left <= d || i === pts.length - 1) {
        const k = d ? Math.min(1, left / d) : 0;
        const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
        return { x: lerp(x0, x1, k), y: lerp(y0, y1, k), angle: Math.atan2(y1 - y0, x1 - x0) };
      }
      left -= d;
    }
    return { x: pts[0][0], y: pts[0][1], angle: 0 };
  }

  // Eased progress of item i in a staggered group: stagger(t, i, {each, dur, start, ease}).
  function staggerP(t, i, opts = {}) {
    return (opts.ease || ease.enter)(clamp((t - (opts.start ?? 0) - i * (opts.each ?? 0.08)) / (opts.dur ?? 0.5)));
  }

  // Impact jitter that decays after `start` (only for literal impacts).
  function shake(t, start, amount = 10, opts = {}) {
    const dt = t - start;
    if (dt < 0) return { x: 0, y: 0, r: 0 };
    const k = Math.exp(-dt / (opts.decay ?? 0.18)) * amount;
    const f = opts.freq ?? 24, sd = opts.seed ?? 5;
    return { x: noise(dt * f, sd) * k, y: noise(dt * f, sd + 9) * k, r: noise(dt * f, sd + 17) * k * 0.002 };
  }

  const fx = { lineReveal, charReveal, wordReveal, countUp, roll, typewriter, scramble, highlight, along, stagger: staggerP, shake, mask, onTwos };

  // ===========================================================================
  // Images (preloaded; the renderer waits for them)
  // ===========================================================================
  const imagePromises = [];
  // assets that failed to load (3D maps, environments, models): a missing map
  // would render a flat surface silently, so the renderer refuses to start
  const assetErrors = [];
  // wait for every pending asset, including ones queued while waiting
  async function settleAssets() {
    let n;
    do { n = imagePromises.length; await Promise.all(imagePromises.slice()); } while (imagePromises.length !== n);
  }
  function image(src) {
    const img = new Image();
    img.decoding = 'sync';
    const p = new Promise((res) => {
      img.onload = () => res(img);
      img.onerror = () => { console.warn('[video-gaga] image failed', src); res(img); };
    });
    img.src = src;
    imagePromises.push(p);
    return img;
  }
  // Cover-fit an image into a rect.
  function drawCover(ctx, img, x, y, w, h, focusX = 0.5, focusY = 0.5) {
    if (!img.naturalWidth) return;
    const s = Math.max(w / img.naturalWidth, h / img.naturalHeight);
    const sw = w / s, sh = h / s;
    ctx.drawImage(img, (img.naturalWidth - sw) * focusX, (img.naturalHeight - sh) * focusY, sw, sh, x, y, w, h);
  }

  // ===========================================================================
  // Transitions — composite outgoing buffer A and incoming buffer B.
  // p is eased 0→1. Buffers are canvases at output resolution.
  // ===========================================================================
  const transitions = {
    cut(ctx, A, B, p) { ctx.drawImage(p < 0.5 ? A : B, 0, 0); },
    fade(ctx, A, B, p) {
      ctx.drawImage(A, 0, 0);
      ctx.globalAlpha = p;
      ctx.drawImage(B, 0, 0);
      ctx.globalAlpha = 1;
    },
    dip(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      ctx.drawImage(p < 0.5 ? A : B, 0, 0);
      ctx.fillStyle = color.rgba(o.color || '#000', 1 - Math.abs(p * 2 - 1));
      ctx.fillRect(0, 0, W, H);
    },
    push(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const [dx, dy] = dirVec(o.direction || 'left');
      ctx.drawImage(A, -dx * W * p, -dy * H * p);
      ctx.drawImage(B, dx * W * (1 - p), dy * H * (1 - p));
    },
    slide(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const [dx, dy] = dirVec(o.direction || 'left');
      ctx.drawImage(A, -dx * W * p * 0.25, -dy * H * p * 0.25);
      ctx.fillStyle = color.rgba('#000', 0.35 * p);
      ctx.fillRect(0, 0, W, H);
      ctx.drawImage(B, dx * W * (1 - p), dy * H * (1 - p));
    },
    wipe(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const ang = ((o.angle ?? 20) * Math.PI) / 180;
      const soft = (o.softness ?? 0) * W;
      ctx.drawImage(A, 0, 0);
      ctx.save();
      ctx.translate(W / 2, H / 2);
      ctx.rotate(ang);
      const span = Math.hypot(W, H);
      const edge = lerp(-span / 2 - soft, span / 2 + soft, p);
      ctx.beginPath();
      ctx.rect(-span / 2 - soft, -span, edge + span / 2 + soft, span * 2);
      ctx.rotate(-ang);
      ctx.translate(-W / 2, -H / 2);
      ctx.clip();
      ctx.drawImage(B, 0, 0);
      ctx.restore();
      if (o.lineColor) {
        ctx.save();
        ctx.translate(W / 2, H / 2);
        ctx.rotate(ang);
        ctx.fillStyle = o.lineColor;
        ctx.fillRect(edge - (o.lineWidth ?? 6) / 2, -span, o.lineWidth ?? 6, span * 2);
        ctx.restore();
      }
    },
    iris(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const cx = (o.x ?? 0.5) * W, cy = (o.y ?? 0.5) * H;
      const R = Math.hypot(Math.max(cx, W - cx), Math.max(cy, H - cy)) * p;
      ctx.drawImage(A, 0, 0);
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, Math.max(0.01, R), 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(B, 0, 0);
      ctx.restore();
    },
    zoom(ctx, A, B, p) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const sa = 1 + p * 0.25, sb = 0.92 + 0.08 * p;
      ctx.save();
      ctx.globalAlpha = 1 - p;
      ctx.translate(W / 2, H / 2); ctx.scale(sa, sa); ctx.translate(-W / 2, -H / 2);
      ctx.drawImage(A, 0, 0);
      ctx.restore();
      ctx.save();
      ctx.globalAlpha = p;
      ctx.translate(W / 2, H / 2); ctx.scale(sb, sb); ctx.translate(-W / 2, -H / 2);
      ctx.drawImage(B, 0, 0);
      ctx.restore();
    },
    blur(ctx, A, B, p) {
      const b = Math.sin(p * Math.PI) * 18;
      ctx.filter = `blur(${b.toFixed(2)}px)`;
      ctx.drawImage(A, 0, 0);
      ctx.globalAlpha = p;
      ctx.drawImage(B, 0, 0);
      ctx.globalAlpha = 1;
      ctx.filter = 'none';
    },
    // Horizontal slice displacement — digital/cyber aesthetics only.
    glitch(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const src = p < 0.5 ? A : B;
      const k = Math.sin(p * Math.PI);
      const r = rand(o.seed ?? 3 + Math.floor(p * 12));
      ctx.drawImage(src, 0, 0);
      const n = 14;
      for (let i = 0; i < n; i++) {
        const y = r() * H, h = (0.01 + r() * 0.06) * H;
        const dx = (r() - 0.5) * W * 0.18 * k;
        ctx.drawImage(src, 0, y, W, h, dx, y, W, h);
      }
      if (o.tint) {
        ctx.fillStyle = color.rgba(o.tint, 0.18 * k);
        ctx.fillRect(0, 0, W, H);
      }
    },
    // Whip pan: a push with motion blur that peaks mid-move (energy, "next").
    whip(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const [dx, dy] = dirVec(o.direction || 'left');
      const n = o.samples ?? 9, spread = (o.blur ?? 0.16) * Math.sin(Math.PI * p);
      for (let i = 0; i < n; i++) {
        const q = clamp(p + (n > 1 ? i / (n - 1) - 0.5 : 0) * spread);
        ctx.globalAlpha = 1 / (i + 1); // running average → equal weights
        ctx.drawImage(A, -dx * W * q, -dy * H * q);
        ctx.drawImage(B, dx * W * (1 - q), dy * H * (1 - q));
      }
      ctx.globalAlpha = 1;
    },
    // Split: the old frame opens like doors onto the new one.
    split(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const vert = (o.direction || 'horizontal') === 'vertical';
      const s = lerp(o.zoom ?? 1.06, 1, p);
      ctx.save();
      ctx.translate(W / 2, H / 2); ctx.scale(s, s); ctx.translate(-W / 2, -H / 2);
      ctx.drawImage(B, 0, 0);
      ctx.restore();
      ctx.fillStyle = color.rgba('#000', 0.3 * (1 - p));
      ctx.fillRect(0, 0, W, H);
      if (vert) {
        const off = (H / 2) * p;
        ctx.drawImage(A, 0, 0, W, H / 2, 0, -off, W, H / 2);
        ctx.drawImage(A, 0, H / 2, W, H / 2, 0, H / 2 + off, W, H / 2);
      } else {
        const off = (W / 2) * p;
        ctx.drawImage(A, 0, 0, W / 2, H, -off, 0, W / 2, H);
        ctx.drawImage(A, W / 2, 0, W / 2, H, W / 2 + off, 0, W / 2, H);
      }
    },
    // Blinds: the new frame opens strip by strip (staggered).
    blinds(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const n = o.count ?? 8, st = o.stagger ?? 0.5, vert = (o.direction || 'vertical') === 'vertical';
      ctx.drawImage(A, 0, 0);
      const size = (vert ? W : H) / n;
      for (let i = 0; i < n; i++) {
        const q = ease.standard(clamp(p * (1 + st) - (i / Math.max(1, n - 1)) * st));
        if (q <= 0) continue;
        const a = i * size, w = size * q, c = a + (size - w) / 2;
        ctx.save();
        ctx.beginPath();
        if (vert) ctx.rect(Math.floor(c), 0, Math.ceil(w) + 1, H); else ctx.rect(0, Math.floor(c), W, Math.ceil(w) + 1);
        ctx.clip();
        ctx.drawImage(B, 0, 0);
        ctx.restore();
      }
    },
    // Stripes: brand-coloured bands sweep across, covering the old frame and
    // uncovering the new one behind them. opts: { colors:[…], count=4, direction, stagger }
    stripes(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const cols = o.colors || ['#111'], n = o.count ?? cols.length ?? 4, st = o.stagger ?? 0.25;
      const d = o.direction || 'right'; // the way the bands travel
      const horiz = d === 'left' || d === 'right';
      const L = horiz ? W : H, band = (horiz ? H : W) / n;
      for (let i = 0; i < n; i++) {
        const q = clamp(p * (1 + st) - (i / Math.max(1, n - 1)) * st);
        let a = L * Math.max(0, q * 2 - 1), b = L * Math.min(1, q * 2); // [a,b] covered by the band
        if (d === 'left' || d === 'up') [a, b] = [L - b, L - a];
        const lo = Math.floor(i * band), hi = Math.ceil((i + 1) * band);
        const rect = (s0, s1) => (horiz ? [s0, lo, s1 - s0, hi - lo] : [lo, s0, hi - lo, s1 - s0]);
        const paint = (src, s0, s1) => {
          if (s1 - s0 <= 0) return;
          const [x, y, w, h] = rect(s0, s1);
          ctx.drawImage(src, x, y, w, h, x, y, w, h);
        };
        const fwd = d === 'right' || d === 'down';
        paint(fwd ? B : A, 0, a);
        paint(fwd ? A : B, b, L);
        if (b > a) {
          const [x, y, w, h] = rect(Math.floor(a), Math.ceil(b));
          ctx.fillStyle = cols[i % cols.length];
          ctx.fillRect(x, y, w, h);
        }
      }
    },
    // Clock wipe: the new frame sweeps in around the centre.
    clock(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const cx = (o.x ?? 0.5) * W, cy = (o.y ?? 0.5) * H, R = Math.hypot(W, H);
      const a0 = -Math.PI / 2;
      ctx.drawImage(A, 0, 0);
      if (p <= 0) return;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, R, a0, a0 + Math.PI * 2 * p, !!o.reverse);
      ctx.closePath();
      ctx.clip();
      ctx.drawImage(B, 0, 0);
      ctx.restore();
    },
    // Light leak: a warm bloom passes across while the frames cross.
    flash(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      ctx.drawImage(A, 0, 0);
      ctx.globalAlpha = ease.inOutSine(clamp((p - 0.25) / 0.5));
      ctx.drawImage(B, 0, 0);
      ctx.globalAlpha = 1;
      const k = Math.sin(Math.PI * p) * (o.strength ?? 0.85);
      const x = lerp(-0.2, 1.2, p) * W;
      const g = ctx.createRadialGradient(x, H * 0.45, 0, x, H * 0.45, W * 0.75);
      g.addColorStop(0, color.rgba(o.color || '#fff4e0', k));
      g.addColorStop(0.45, color.rgba(o.color || '#ffb36b', k * 0.45));
      g.addColorStop(1, color.rgba(o.color || '#ffb36b', 0));
      ctx.globalCompositeOperation = 'screen';
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'source-over';
    },
    // Mosaic: blocks grow to a peak, the frames swap, blocks resolve.
    pixelate(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const k = Math.sin(Math.PI * p), block = Math.max(1, Math.round(1 + k * (o.size ?? 64) * (W / 1920)));
      const src = p < 0.5 ? A : B;
      if (block <= 1) { ctx.drawImage(src, 0, 0); return; }
      const w = Math.max(1, Math.round(W / block)), h = Math.max(1, Math.round(H / block));
      const tmp = scratch('px', w, h);
      const g = tmp.getContext('2d', CPU2D);
      g.imageSmoothingEnabled = true;
      g.clearRect(0, 0, w, h);
      g.drawImage(src, 0, 0, w, h);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(tmp, 0, 0, w, h, 0, 0, W, H);
      ctx.imageSmoothingEnabled = true;
    },
    // Noise dissolve: organic grain-level reveal (film, memory, soft change).
    dissolve(ctx, A, B, p, o) {
      // fine, film-like grain: two octaves of noise (aspect-corrected) plus per-pixel jitter
      const sd = o.seed ?? 3, f = o.scale ?? 1;
      maskReveal(ctx, A, B, p, o, `dissolve${f}`, (x, y, r, aspect) => clamp(0.5 + 0.3 * noise2(x * aspect * 16 * f, y * 16 * f, sd) + 0.17 * noise2(x * aspect * 47 * f, y * 47 * f, sd + 1) + (r() - 0.5) * 0.12));
    },
    // Ink bloom: the new frame spreads from a point with an organic edge.
    ink(ctx, A, B, p, o) {
      const ox = o.x ?? 0.5, oy = o.y ?? 0.5, sd = o.seed ?? 7;
      maskReveal(ctx, A, B, p, o, `ink${ox},${oy}`, (x, y, r, aspect) => {
        const d = Math.hypot((x - ox) * aspect, y - oy) / Math.hypot(Math.max(ox, 1 - ox) * aspect, Math.max(oy, 1 - oy));
        return clamp(d * 0.82 + 0.18 * (noise2(x * 5, y * 5, sd) * 0.7 + noise2(x * 17, y * 17, sd + 1) * 0.3) + 0.09);
      });
    },
    // Zoom through with radial streaks: going "into" the idea.
    zoomBlur(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      const n = o.samples ?? 7, k = Math.sin(Math.PI * p);
      const scaled = (src, s, a) => {
        ctx.save();
        ctx.globalAlpha = a;
        ctx.translate(W / 2, H / 2); ctx.scale(s, s); ctx.translate(-W / 2, -H / 2);
        ctx.drawImage(src, 0, 0);
        ctx.restore();
      };
      const q = ease.inOutSine(clamp((p - 0.3) / 0.4));
      // outgoing rushes toward the viewer, smeared into radial streaks
      if (q < 1) for (let i = 0; i < n; i++) scaled(A, (1 + p * 0.6) * (1 + (i / n) * 0.12 * k * (o.strength ?? 1)), 1 / (i + 1));
      // incoming arrives from slightly large and settles at 1
      if (q > 0) scaled(B, lerp(1.25, 1, ease.outCubic(p)), q);
      ctx.globalAlpha = 1;
    },
    // Cube: rotate to the next face (sequential topics, "turn the page" in 3D).
    cube(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      ctx.fillStyle = o.color || '#000';
      ctx.fillRect(0, 0, W, H);
      const dir = (o.direction || 'left') === 'right' ? -1 : 1;
      const a = p * (Math.PI / 2) * dir, h = W / 2;
      // face A: front face; face B: the adjacent side face
      const faceA = (u) => [u * Math.cos(a) - h * Math.sin(a), -u * Math.sin(a) - h * Math.cos(a)];
      const faceB = (w) => [dir * h * Math.cos(a) + w * Math.sin(a) * dir, -dir * h * Math.sin(a) + w * Math.cos(a)];
      const shade = (k) => color.rgba('#000', clamp(k) * 0.6);
      facet(ctx, A, (s) => faceA(lerp(-h, h, s)), h, W, H, shade(p));
      facet(ctx, B, (s) => faceB(lerp(-h, h, s)), h, W, H, shade(1 - p));
    },
    // Card flip around the vertical axis.
    flip(ctx, A, B, p, o) {
      const W = ctx.canvas.width, H = ctx.canvas.height;
      ctx.fillStyle = o.color || '#000';
      ctx.fillRect(0, 0, W, H);
      const a = p * Math.PI, h = W / 2;
      const src = p < 0.5 ? A : B, ang = p < 0.5 ? a : a - Math.PI;
      facet(ctx, src, (s) => { const u = lerp(-h, h, s); return [u * Math.cos(ang), -u * Math.sin(ang)]; }, 0, W, H, color.rgba('#000', Math.sin(a) * 0.35));
    },
  };
  function dirVec(d) {
    return { left: [1, 0], right: [-1, 0], up: [0, 1], down: [0, -1] }[d] || [1, 0];
  }

  // Reusable scratch canvases for transitions (pure: contents are fully
  // rewritten on every use).
  const scratchMap = new Map();
  // keep helper canvases on the CPU rasteriser, like the frame buffers: a canvas
  // Chromium migrates GPU→CPU mid-render rasterises differently afterwards
  const CPU2D = { willReadFrequently: true };
  function scratch(key, w, h) {
    const k = `${key}:${w}x${h}`;
    let c = scratchMap.get(k);
    if (!c) { c = makeCanvas(w, h); scratchMap.set(k, c); }
    return c;
  }

  // 2D value noise in [-1, 1].
  function noise2(x, y, seed = 0) {
    const h = (i, j) => { const r = Math.sin(i * 127.1 + j * 311.7 + seed * 74.7) * 43758.5453; return (r - Math.floor(r)) * 2 - 1; };
    const i = Math.floor(x), j = Math.floor(y), fx_ = x - i, fy = y - j;
    const u = fx_ * fx_ * (3 - 2 * fx_), v = fy * fy * (3 - 2 * fy);
    return lerp(lerp(h(i, j), h(i + 1, j), u), lerp(h(i, j + 1), h(i + 1, j + 1), u), v);
  }

  // Threshold reveal through a cached scalar field (0..1 per pixel, low-res).
  const fieldCache = new Map();
  function maskReveal(ctx, A, B, p, o, key, field) {
    const W = ctx.canvas.width, H = ctx.canvas.height;
    const fw = 480, fh = Math.max(1, Math.round((480 * H) / W));
    const ck = `${key}:${fw}x${fh}:${o.seed ?? ''}`;
    let f = fieldCache.get(ck);
    if (!f) {
      f = new Float32Array(fw * fh);
      const r = rand(o.seed ?? 3);
      for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) f[y * fw + x] = field(x / fw, y / fh, r, W / H);
      fieldCache.set(ck, f);
    }
    const soft = o.softness ?? 0.06;
    const m = scratch('mask', fw, fh), mg = m.getContext('2d', CPU2D);
    const img = mg.createImageData(fw, fh);
    const th = lerp(-soft, 1 + soft, p);
    for (let i = 0; i < f.length; i++) img.data[i * 4 + 3] = 255 * clamp((th - f[i]) / soft + 0.5);
    mg.putImageData(img, 0, 0);
    const layer = scratch('layer', W, H), lg = layer.getContext('2d', CPU2D);
    lg.globalCompositeOperation = 'source-over';
    lg.clearRect(0, 0, W, H);
    lg.drawImage(B, 0, 0);
    lg.globalCompositeOperation = 'destination-in';
    lg.imageSmoothingEnabled = true;
    lg.drawImage(m, 0, 0, W, H);
    lg.globalCompositeOperation = 'source-over';
    ctx.drawImage(A, 0, 0);
    if (o.edgeColor) {
      // a thin coloured rim just ahead of the reveal (ink edge)
      for (let i = 0; i < f.length; i++) img.data[i * 4 + 3] = 255 * clamp(1 - Math.abs(th + soft * 1.5 - f[i]) / (soft * 0.9));
      mg.putImageData(img, 0, 0);
      const e = scratch('edge', W, H), eg = e.getContext('2d', CPU2D);
      eg.globalCompositeOperation = 'source-over';
      eg.clearRect(0, 0, W, H);
      eg.fillStyle = o.edgeColor;
      eg.fillRect(0, 0, W, H);
      eg.globalCompositeOperation = 'destination-in';
      eg.drawImage(m, 0, 0, W, H);
      eg.globalCompositeOperation = 'source-over';
      ctx.drawImage(e, 0, 0);
    }
    ctx.drawImage(layer, 0, 0);
  }

  // Draw a source image as a plane rotated about the vertical axis, in
  // vertical strips with perspective. pos(s) → [x, z] (relative to the cube
  // centre, z toward the viewer is negative) for s in 0..1 across the image.
  function facet(ctx, src, pos, depth, W, H, shadeCol) {
    const n = 72, f = W * 1.6; // strips, focal length
    const cols = [];
    for (let i = 0; i <= n; i++) {
      const [x, z] = pos(i / n);
      const k = f / (f + z + depth); // the front plane (z = -depth) has scale 1
      cols.push([W / 2 + x * k, k]);
    }
    for (let i = 0; i < n; i++) {
      const [x0, k0] = cols[i], [x1, k1] = cols[i + 1];
      if (x1 - x0 <= 0.05) continue; // back-facing or edge-on
      const h = H * (k0 + k1) / 2;
      const sx = (i / n) * src.width, sw = src.width / n;
      const dx = Math.floor(x0), dw = Math.ceil(x1 - x0) + 1;
      ctx.drawImage(src, sx, 0, sw, src.height, dx, H / 2 - h / 2, dw, h);
      if (shadeCol) { ctx.fillStyle = shadeCol; ctx.fillRect(dx, H / 2 - h / 2, dw, h); }
    }
  }

  // ===========================================================================
  // Narration & subtitles
  // ===========================================================================
  const SENT_END = /[。！？!?…]$|[.](?=["'”’)]?$)/;
  const CLAUSE_END = /[，、；：,;:—]$/;
  const STRIP_PUNCT = /[，。、；：？！,.;:?!…"“”'‘’]/g;

  // Rough speech-length estimate used before TTS exists (preview/storyboard).
  function estimateSpeech(textStr, lang) {
    const s = String(textStr);
    const zh = lang ? lang.startsWith('zh') || lang.startsWith('ja') : CJK.test(s);
    const units = tokenize(s).filter((u) => u.trim());
    const pauses = (s.match(/[，。、；：？！,.;:?!]/g) || []).length;
    const rate = zh ? 4.3 : 2.5; // CJK chars/s, words/s (Edge neural voices at +0%)
    const count = zh ? Array.from(s.replace(STRIP_PUNCT, '').replace(/\s/g, '')).length : units.length;
    const duration = 0.1 + count / rate + pauses * 0.22;
    // Fake word timings, proportional to unit length
    const totalLen = units.reduce((a, u) => a + u.length, 0) || 1;
    let acc = 0.1;
    const wordsOut = units.map((u) => {
      const d = (u.length / totalLen) * (duration - 0.1);
      const w = { text: u.replace(STRIP_PUNCT, ''), start: acc, end: acc + d };
      acc += d;
      return w;
    }).filter((w) => w.text);
    return { duration, words: wordsOut, estimated: true };
  }

  // Map TTS word boundaries back onto the original text so cues keep
  // punctuation and spacing. Returns words with {i0, i1} char indices.
  function alignWords(textStr, wordList) {
    let cursor = 0;
    return wordList.map((w) => {
      const idx = textStr.indexOf(w.text, cursor);
      if (idx >= 0 && idx - cursor < 40) {
        cursor = idx + w.text.length;
        return { ...w, i0: idx, i1: cursor };
      }
      return { ...w, i0: cursor, i1: cursor };
    });
  }

  // How long a line is actually spoken (s): TTS clips carry 0.4–1.1 s of
  // silence after the last word, so speech ends at the last word's end plus the
  // decay of its final syllable (0.25 s), never later than the clip itself.
  // Estimated timings (no TTS yet) keep their length.
  function speechEnd(seg) {
    const w = seg?.words;
    if (!w || !w.length || seg.estimated) return seg?.duration ?? 0;
    return Math.min(seg.duration ?? Infinity, w[w.length - 1].end + 0.25);
  }

  // Start time (s, relative to the clip) of a spoken phrase, or null.
  // Exact word / run of words first, so a short phrase ("S", "in") can't match
  // inside an earlier word; then a substring match as a fallback.
  function findPhrase(words, phrase) {
    if (!words || !words.length) return null;
    const n = (x) => String(x).replace(/[\s\p{P}]/gu, '').toLowerCase();
    const want = n(phrase);
    if (!want) return null;
    const scan = (loose) => {
      for (let i = 0; i < words.length; i++) {
        const wi = n(words[i].text);
        if (!wi) continue;
        if (loose ? wi.includes(want) : wi === want) return words[i].start;
        // phrase spans several words starting at word i
        let acc = '';
        for (let j = i; j < words.length; j++) {
          acc += n(words[j].text);
          if (loose ? acc.startsWith(want) : acc === want) return words[i].start;
          if (!want.startsWith(acc)) break;
        }
      }
      return null;
    };
    return scan(false) ?? scan(true);
  }

  // Build subtitle cues for one narration segment.
  // opts: { maxChars, minChars, lang, punctuation: 'strip'|'keep', offset }
  function buildCues(textStr, wordList, opts = {}) {
    if (!wordList || !wordList.length) return [];
    const zh = opts.lang ? /^(zh|ja|ko)/.test(opts.lang) : CJK.test(textStr);
    const maxChars = opts.maxChars ?? (zh ? 18 : 42);
    const minChars = opts.minChars ?? (zh ? 6 : 16);
    const strip = (opts.punctuation ?? (zh ? 'strip' : 'keep')) === 'strip';
    const off = opts.offset ?? 0;
    const aligned = alignWords(textStr, wordList);
    const len = (s) => (zh ? Array.from(s.replace(/\s/g, '')).length : s.length);
    const cues = [];
    aligned.forEach((w, k) => {
      // punctuation/space between this word and the next word (or end of text)
      const end = k + 1 < aligned.length ? aligned[k + 1].i0 : textStr.length;
      w.trail = textStr.slice(w.i1, end);
    });
    const spanText = (g) => textStr.slice(g[0].i0, g[g.length - 1].i1 + g[g.length - 1].trail.replace(/\s+$/, '').length);
    const emit = (group) => {
      if (!group.length) return;
      const first = group[0], last = group[group.length - 1];
      const raw = spanText(group).replace(/\s+/g, ' ').trim();
      let display = raw;
      if (strip) {
        display = raw.replace(/[，、；：,;:]/g, ' ').replace(/[。！？!?….;“”"'‘’]/g, (m) => (/[？?！!]/.test(m) ? m : ' '))
          .replace(/\s+/g, ' ').trim();
      }
      cues.push({ start: first.start + off, end: last.end + off, text: display, words: group.map((w) => ({ text: w.text, start: w.start + off, end: w.end + off })) });
    };
    // 1) phrases: break at sentence ends, at clause marks once long enough, and at pauses
    const phrases = [];
    let group = [];
    aligned.forEach((w, k) => {
      const prev = group[group.length - 1];
      if (prev && w.start - prev.end > 0.55) { phrases.push(group); group = []; }
      group.push(w);
      const t = w.trail.trim();
      if (t && SENT_END.test(t)) { phrases.push(group); group = []; }
      // minChars counts spoken characters: "中文、日文、" is 4, not 6
      else if (t && CLAUSE_END.test(t) && len(spanText(group).replace(STRIP_PUNCT, '')) >= minChars) { phrases.push(group); group = []; }
    });
    if (group.length) phrases.push(group);
    // 2) long phrases: split into k balanced chunks at word boundaries (no orphans)
    for (const ph of phrases) {
      const total = len(spanText(ph));
      const k = Math.ceil(total / maxChars);
      if (k <= 1) { emit(ph); continue; }
      // a clause mark inside the phrase is the natural place to split, when
      // both halves fit ("2023 年，| 全球最繁忙的机场是哪一座？")
      if (k === 2) {
        let best = -1, bestDiff = Infinity;
        for (let i = 0; i < ph.length - 1; i++) {
          if (!CLAUSE_END.test(ph[i].trail.trim())) continue;
          const a = len(spanText(ph.slice(0, i + 1))), b = len(spanText(ph.slice(i + 1)));
          if (a <= maxChars && b <= maxChars && Math.abs(a - b) < bestDiff) { best = i; bestDiff = Math.abs(a - b); }
        }
        if (best >= 0) { emit(ph.slice(0, best + 1)); emit(ph.slice(best + 1)); continue; }
      }
      const target = total / k;
      let cur = [];
      for (let i = 0; i < ph.length; i++) {
        cur.push(ph[i]);
        const here = len(spanText(cur));
        const nextLen = i + 1 < ph.length ? len(spanText([...cur, ph[i + 1]])) : Infinity;
        // cut when adding the next word would move us further from the target
        if (i + 1 < ph.length && Math.abs(here - target) <= Math.abs(nextLen - target) && here >= target * 0.6) {
          emit(cur);
          cur = [];
        }
      }
      emit(cur);
    }
    // timing polish: small lead-out, min duration, no overlaps
    for (let i = 0; i < cues.length; i++) {
      const c = cues[i], next = cues[i + 1];
      c.end = Math.max(c.end + 0.12, c.start + 0.8);
      if (next && c.end > next.start - 0.02) c.end = next.start - 0.02;
    }
    return cues;
  }

  function subtitleStyleDefaults(W, H) {
    const u = Math.min(W, H) / 1080;
    return {
      font: `600 ${Math.round(46 * u)}px "Noto Sans SC", "PingFang SC", "Helvetica Neue", sans-serif`,
      color: '#ffffff',
      highlight: null, // karaoke colour for spoken words
      box: 'rgba(0,0,0,0.55)',
      stroke: null, strokeWidth: 0,
      y: H > W ? 0.78 : 0.9, // baseline position (fraction of height)
      maxWidth: W * (H > W ? 0.84 : 0.8),
      padX: 22 * u, padY: 12 * u, radius: 10 * u,
      lineHeight: 1.35,
      fadeIn: 0.12,
    };
  }

  function drawSubtitles(ctx, cues, t, style) {
    const cue = cues.find((c) => t >= c.start && t < c.end);
    if (!cue) return;
    const W = ctx.canvas.__cvW, H = ctx.canvas.__cvH;
    const s = Object.assign(subtitleStyleDefaults(W, H), style || {});
    ctx.save();
    ctx.font = s.font;
    ctx.textBaseline = 'alphabetic';
    const lines = wrap(ctx, cue.text, s.maxWidth);
    const size = parseFloat(s.font.match(/(\d+(?:\.\d+)?)px/)[1]);
    const lh = size * s.lineHeight;
    const a = clamp((t - cue.start) / s.fadeIn) * clamp((cue.end - t) / 0.08);
    ctx.globalAlpha = a;
    const baseY = s.y * H - (lines.length - 1) * lh;
    lines.forEach((ln, li) => {
      const w = ctx.measureText(ln).width;
      const x = W / 2 - w / 2, y = baseY + li * lh;
      if (s.box) {
        ctx.fillStyle = s.box;
        roundRect(ctx, x - s.padX, y - size * 0.95 - s.padY / 2, w + s.padX * 2, size * 1.25 + s.padY, s.radius);
        ctx.fill();
      }
      if (s.stroke && s.strokeWidth) {
        ctx.lineJoin = 'round';
        ctx.strokeStyle = s.stroke;
        ctx.lineWidth = s.strokeWidth;
        ctx.strokeText(ln, x, y);
      }
      ctx.fillStyle = s.color;
      ctx.fillText(ln, x, y);
    });
    // karaoke highlight: overpaint spoken portion of single-line cues
    if (s.highlight && lines.length === 1 && cue.words) {
      const bare = (x) => x.replace(/[\s\p{P}]/gu, '');
      // count spoken characters, including partial progress through the current word
      let need = 0;
      for (const w of cue.words) {
        if (t >= w.end) need += bare(w.text).length;
        else if (t >= w.start) need += Math.round(bare(w.text).length * clamp((t - w.start) / Math.max(0.05, w.end - w.start)));
      }
      let prefix = '', got = 0;
      for (const ch of Array.from(lines[0])) {
        if (got >= need) break;
        prefix += ch;
        if (bare(ch)) got++;
      }
      const w = ctx.measureText(lines[0]).width;
      ctx.save();
      ctx.beginPath();
      ctx.rect(W / 2 - w / 2, baseY - size * 1.2, ctx.measureText(prefix).width, size * 1.6);
      ctx.clip();
      ctx.fillStyle = s.highlight;
      ctx.fillText(lines[0], W / 2 - w / 2, baseY);
      ctx.restore();
    }
    ctx.restore();
  }

  // ===========================================================================
  // Video composition
  // ===========================================================================
  const fail = (msg) => { throw new Error(`[video-gaga] ${msg}`); };

  // The sound a transition naturally makes (only when music/sfx are enabled).
  const TRANSITION_SFX = {
    push: 'whoosh', slide: 'whoosh', whip: 'whoosh', wipe: 'swish', stripes: 'swish', split: 'whoosh', blinds: 'swish',
    clock: 'swish', zoom: 'whoosh', zoomBlur: 'whoosh', cube: 'whoosh', flip: 'swish', iris: 'swish',
    glitch: 'glitch', flash: 'shimmer', pixelate: 'glitch', ink: 'swell', dissolve: 'swell',
  };

  // Local time (s) at which a phrase is spoken in a voice segment (exact words
  // first, then a substring: see findPhrase).
  function phraseTime(voice, voiceDelay, phrase, fallback = 0) {
    const at = findPhrase(voice?.words, phrase);
    return at == null ? fallback : voiceDelay + at;
  }

  const params = typeof location !== 'undefined' ? new URLSearchParams(location.search) : new URLSearchParams();
  const RENDER = params.get('render') === '1' || !!root.__CV_RENDER__;
  let fontEpoch = 0; // bumped once webfonts are ready (invalidates text caches)

  function create(config) {
    const W = config.width ?? 1920, H = config.height ?? 1080, fps = config.fps ?? 30;
    const scale = Number(params.get('scale') || config.pixelRatio || 1);
    const narr = config.narration ?? root.CV_NARRATION ?? null;
    const lang = config.lang ?? narr?.lang ?? 'en';
    const burnSubs = params.has('subs') ? params.get('subs') === '1' : config.subtitles?.burn ?? false;
    const bg = config.background ?? '#000';

    // ---- music & beat grid ----------------------------------------------------
    // music: 'bed.mp3' | { bpm, beatsPerBar, offset, snap, voiceOnBeat, volume, sfx, file,
    //   and the score designed for this video: key, mode, progression, layers, lead, seed … }
    // (scripts/music.mjs validates and renders the score; there are no preset styles)
    const mus = typeof config.music === 'string' ? { file: config.music } : config.music ? { ...config.music } : null;
    if (mus && 'style' in mus) fail(`music.style ('${mus.style}') is not supported: there are no preset music styles. Write the score for this video (bpm, key, mode, script: 'score.mjs'), see docs/music-and-sound.md`);
    if (mus && !mus.file && (mus.layers || mus.lead || mus.script) && !mus.bpm) fail('music.bpm is required for a generated score');
    const bpm = mus?.bpm ?? null;
    const beatsPerBar = mus?.beatsPerBar ?? 4;
    const beatLen = bpm ? 60 / bpm : 0, barLen = beatLen * beatsPerBar;
    const gridOffset = mus?.offset ?? 0;
    const unitOf = (u) => ({ beat: beatLen, half: beatLen / 2, bar: barLen }[u] ?? 0);
    const snapUnit = bpm ? unitOf(mus.snap ?? 'beat') : 0;
    // smallest grid time ≥ x (x itself when it is already on the grid)
    const snapUp = (x, unit) => (unit ? gridOffset + Math.ceil((x - gridOffset) / unit - 1e-6) * unit : x);

    // ---- timeline resolution (voice drives duration) -------------------------
    if (!config.scenes?.length) fail('no scenes yet: add one scene per storyboard row to CV.create({ scenes: [ … ] })');
    const scenes = config.scenes.map((s, i) => ({ ...s, index: i }));
    // One take (narration.track, written by `gaga voicetrack`): the whole voice
    // was recorded or synthesized in one pass and cut into one slice per scene.
    // track.segments[id] = [start, end] in the take. A run of scenes cut from it
    // follows the take: each cut sits in the pause between two slices and no
    // cut or voice is moved onto the beat, so the pauses stay as recorded.
    const track = narr?.track?.segments ? narr.track : null;
    const spanOf = (s) => { const id = s.narration === false ? null : s.narration ?? s.id; return id && track?.segments[id] && narr?.segments?.[id] ? track.segments[id] : null; };
    let cursor = 0, part = null;
    for (const s of scenes) {
      // music parts (chapters of a long score): a scene's `part` holds until the
      // next scene that names one, and a new part starts on a bar line
      const newPart = s.part != null && s.part !== part;
      if (s.part != null && !mus?.parts?.[s.part]) fail(`scene "${s.id}": part '${s.part}' is not defined in music.parts`);
      if (s.part != null) part = s.part;
      s._part = part;
      const tr = s.index > 0 ? normTransition(s.transition ?? config.transition) : null;
      const overlap = tr && tr.type !== 'cut' ? tr.duration : 0;
      s._tr = tr;
      s.start = Math.max(0, cursor - overlap);
      // cut on the beat: the middle of the transition lands on the grid; the
      // previous scene holds a little longer to get there
      const span = spanOf(s);
      if (s.index > 0 && snapUnit && s.snap !== false && !span) {
        const prev = scenes[s.index - 1];
        const unit = s.snap ? unitOf(s.snap) || snapUnit : newPart && mus.parts ? barLen : snapUnit;
        s.start = snapUp(s.start + overlap / 2, unit) - overlap / 2;
        prev.end = s.start + overlap;
        prev.dur = prev.end - prev.start;
      }
      const segId = s.narration === false ? null : s.narration ?? s.id;
      let seg = null;
      if (segId && narr?.segments?.[segId]) seg = narr.segments[segId];
      else if (s.say) seg = { text: s.say, ...estimateSpeech(s.say, lang) };
      else if (segId && config.script?.[segId]) seg = { text: config.script[segId], ...estimateSpeech(config.script[segId], lang) };
      s.voice = seg;
      s.voiceDelay = span ? overlap * 0.5 : s.voiceDelay ?? config.voiceDelay ?? overlap * 0.5 + 0.25;
      // the first spoken syllable starts on an eighth note of the music grid
      if (seg && bpm && !span && (s.voiceOnBeat ?? mus.voiceOnBeat ?? true)) {
        const lead = seg.words?.[0]?.start ?? 0;
        s.voiceDelay = snapUp(s.start + s.voiceDelay + lead, beatLen / 2) - s.start - lead;
      }
      // Size from the last spoken word, not the clip: Edge TTS clips end with
      // 0.4–1.1 s of silence, which would otherwise pad every voiced scene.
      s.speech = seg ? speechEnd(seg) : 0;
      const tail = s.tail ?? config.tail ?? 0.55;
      const need = seg ? s.voiceDelay + s.speech + tail : 0;
      const fixed = s.duration ?? (s.bars != null || s.beats != null
        // counted from the cut into the scene (the middle of its transition)
        ? (bpm ? (s.bars ?? 0) * barLen + (s.beats ?? 0) * beatLen + overlap / 2 : fail(`scene "${s.id}" uses beats/bars but no music bpm is set`))
        : null);
      s.dur = fixed ?? Math.max(s.minDuration ?? (seg ? 0 : 3), need);
      // one take: when the next scene is the next slice of the take, end where
      // its cut sits (the middle of its transition lands on the slice boundary)
      const next = config.scenes[s.index + 1];
      if (span && next && !fixed && spanOf(next)) {
        const ntr = normTransition(next.transition ?? config.transition);
        s.dur = (span[1] - span[0]) + overlap * 0.5 + (ntr && ntr.type !== 'cut' ? ntr.duration : 0) * 0.5;
      }
      if (s.maxDuration) s.dur = Math.min(s.dur, s.maxDuration);
      s.end = s.start + s.dur;
      cursor = s.end;
    }
    let duration = config.duration ?? cursor + (config.outro ?? 0);
    // end on a beat too, so the music's last note and the last frame agree
    if (config.duration == null && snapUnit) {
      const last = scenes[scenes.length - 1];
      duration = snapUp(duration, beatLen);
      last.end = duration;
      last.dur = last.end - last.start;
    }
    const totalFrames = Math.round(duration * fps);

    // ---- sound effects (absolute time) -----------------------------------------
    // scene.sfx: [{ at: seconds | 'spoken phrase', type, gain, dur }]; transitions
    // add their natural sound unless `sfx: false`.
    const sfx = [];
    const sfxOn = mus ? mus.sfx ?? true : false;
    for (const s of scenes) {
      for (const e of s.sfx || []) {
        const local = typeof e.at === 'string' ? phraseTime(s.voice, s.voiceDelay, e.at, null)
          : typeof e.at === 'function' ? e.at(sceneInfo(s, s.start, 0)) : e.at ?? 0;
        if (local == null) { console.warn(`[video-gaga] sfx phrase not found in "${s.id}": ${e.at}`); continue; }
        sfx.push({ ...e, t: s.start + local + (e.offset ?? 0), scene: s.id });
      }
      const tr = s._tr;
      if (sfxOn && tr && tr.sfx !== false) {
        const type = tr.sfx ?? (typeof tr.type === 'string' ? TRANSITION_SFX[tr.type] : null);
        if (type) sfx.push({ type, t: s.start + (tr.type === 'cut' ? 0 : tr.duration / 2), dur: tr.duration, gain: tr.sfxGain ?? 1, scene: s.id, transition: true });
      }
    }
    sfx.sort((x, y) => x.t - y.t);

    // ---- subtitle cues (absolute time) ---------------------------------------
    let cues = [];
    const subOpts = Object.assign({ lang }, config.subtitles || {});
    if (H > W && subOpts.maxChars == null) subOpts.maxChars = /^(zh|ja|ko)/.test(lang) ? 12 : 28;
    // scene.captions: true (default) | 'file' (in .srt/.vtt, not burned) | false (no cue)
    for (const s of scenes) {
      if (!s.voice || !s.voice.words || s.captions === false) continue;
      const sc = buildCues(s.voice.text, s.voice.words, { ...subOpts, offset: s.start + s.voiceDelay });
      if (s.captions === 'file') sc.forEach((c) => { c.burn = false; });
      cues = cues.concat(sc);
    }
    const burnCues = cues.filter((c) => c.burn !== false);

    // ---- canvas ---------------------------------------------------------------
    const canvas = config.canvas || document.createElement('canvas');
    canvas.width = Math.round(W * scale);
    canvas.height = Math.round(H * scale);
    canvas.__cvW = W;
    canvas.__cvH = H;
    // willReadFrequently keeps every canvas on the CPU rasterizer from frame 0.
    // Without it Chromium migrates a canvas GPU→CPU after repeated readbacks,
    // which subtly changes anti-aliasing mid-render (non-deterministic pixels).
    const ctxOpts = { alpha: false, willReadFrequently: RENDER };
    const ctx = canvas.getContext('2d', ctxOpts);
    const bufs = [makeCanvas(canvas.width, canvas.height), makeCanvas(canvas.width, canvas.height)];
    bufs.forEach((b) => { b.__cvW = W; b.__cvH = H; });
    const bctx = bufs.map((b) => b.getContext('2d', ctxOpts));

    function sceneInfo(s, T, frame) {
      const t = T - s.start;
      const tr = s._tr;
      const enterDur = tr && tr.type !== 'cut' ? tr.duration : 0;
      const next = scenes[s.index + 1];
      const exitDur = next && next._tr && next._tr.type !== 'cut' ? next._tr.duration : 0;
      const info = {
        id: s.id, index: s.index, t, T, dur: s.dur, p: clamp(t / s.dur), frame, fps, W, H,
        u: Math.min(W, H) / 1080, // 1u = 1px at 1080p short side
        enter: enterDur ? clamp(t / enterDur) : 1,
        exit: exitDur ? clamp((t - (s.dur - exitDur)) / exitDur) : 0,
        isRender: RENDER, lang,
        voice: s.voice,
        voiceStart: s.voice ? s.voiceDelay : 0,
        voiceEnd: s.voice ? s.voiceDelay + s.speech : 0, // the last spoken word, not the clip's trailing silence
        scene: s,
      };
      // eased local progress helper: s.at(start, dur, ease)
      info.at = (start, dur, e) => progress(t, start, dur, e);
      // local time when a phrase is spoken (falls back if not found)
      info.when = (phrase, fallback = 0) => phraseTime(s.voice, s.voiceDelay, phrase, fallback);
      // the last moments of the scene: 0→1 over [dur - lead - d, dur - lead].
      // Use it for exit choreography so the cut happens on action.
      info.out = (d = 0.5, e = ease.exit, lead = 0) => progress(t, s.dur - lead - d, d, e);
      // local start time for each on-screen unit, matched against the spoken
      // text in order (units that are never spoken follow the previous one)
      info.syncTimes = (units, step = 0.12) => {
        if (!s._sync) s._sync = new Map();
        const key = units.join('\u0001');
        if (s._sync.has(key)) return s._sync.get(key);
        const out = [];
        if (s.voice && s.voice.words) {
          const aligned = alignWords(s.voice.text, s.voice.words);
          const norm = (x) => x.replace(/[\s\p{P}]/gu, '').toLowerCase();
          // map normalised voice-text characters to word start times
          const map = [];
          let flat = '';
          aligned.forEach((w) => {
            const seg = norm(s.voice.text.slice(w.i0, w.i1) || w.text);
            for (const ch of Array.from(seg)) { flat += ch; map.push(w.start); }
          });
          let cur = 0;
          for (const u of units) {
            const nu = norm(u);
            const idx = nu ? flat.indexOf(nu, cur) : -1;
            if (idx >= 0 && idx - cur < 24) { out.push(s.voiceDelay + map[Array.from(flat.slice(0, idx)).length] - 0.06); cur = idx + nu.length; }
            else out.push(null);
          }
          // units that are shown but said differently ("30" / "三十") appear
          // with the next spoken unit, else just after the previous one
          for (let i = out.length - 1, next = null; i >= 0; i--) {
            if (out[i] != null) next = out[i];
            else if (next != null) out[i] = next;
          }
          for (let i = 0; i < out.length; i++) if (out[i] == null) out[i] = (i ? out[i - 1] : s.voiceDelay) + step;
        } else units.forEach((_, i) => out.push(0.3 + i * step));
        s._sync.set(key, out);
        return out;
      };
      // beat grid (NaN without music bpm)
      info.beatLen = beatLen;
      info.beat = bpm ? (T - gridOffset) / beatLen : NaN;
      info.bar = bpm ? (T - gridOffset) / barLen : NaN;
      // local time of the i-th grid point at or after the scene start
      info.onBeat = (i = 0, unit = 'beat') => (bpm ? snapUp(s.start, unitOf(unit)) + i * unitOf(unit) - s.start : i * 0.5);
      // local time of the next grid point at or after local time lt
      info.nextBeat = (lt = t, unit = 'beat') => (bpm ? snapUp(s.start + lt, unitOf(unit)) - s.start : lt);
      // 1 on each beat, decaying exponentially (subtle beat-synced accents)
      info.pulse = (decay = 0.16, unit = 'beat') => {
        if (!bpm) return 0;
        const u = unitOf(unit), since = (T - gridOffset) - Math.floor((T - gridOffset) / u + 1e-6) * u;
        return Math.exp(-since / decay);
      };
      return info;
    }

    function paintScene(c, s, T, frame) {
      c.save();
      c.setTransform(scale, 0, 0, scale, 0, 0);
      c.fillStyle = s.background ?? bg;
      c.fillRect(0, 0, W, H);
      s.draw(c, sceneInfo(s, T, frame));
      c.restore();
    }

    // text probe (`gaga still`): boxes of the text drawn straight onto the frame,
    // in design px. Captions are left out; text drawn into an offscreen layer
    // first (sprites, transition buffers, 3D textures) isn't seen.
    let textProbe = false, textLog = null;
    function logText(c, txt, x, y, maxW, stroke) {
      if (c !== ctx || !textLog || c.globalAlpha < 0.15 || !String(txt).trim()) return;
      const m = c.measureText(txt), M = c.getTransform();
      let x0 = x - m.actualBoundingBoxLeft, x1 = x + m.actualBoundingBoxRight;
      if (maxW != null && x1 - x0 > maxW) x1 = x0 + maxW;
      const y0 = y - m.actualBoundingBoxAscent, y1 = y + m.actualBoundingBoxDescent;
      const xs = [], ys = [];
      for (const [px, py] of [[x0, y0], [x1, y0], [x0, y1], [x1, y1]]) {
        xs.push((M.a * px + M.c * py + M.e) / scale);
        ys.push((M.b * px + M.d * py + M.f) / scale);
      }
      // the solid colour it is drawn in (null for a gradient or pattern), for the contrast check
      const style = stroke ? c.strokeStyle : c.fillStyle;
      textLog.push({ text: String(txt).slice(0, 40), x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys), color: typeof style === 'string' ? style : null, stroke: !!stroke });
    }
    // where burned captions can sit: the tallest cue at the style's position
    function captionBand() {
      if (!cues.length) return null;
      const s = Object.assign(subtitleStyleDefaults(W, H), config.subtitles?.style || {});
      ctx.save();
      ctx.font = s.font;
      const lines = Math.max(...cues.map((c) => wrap(ctx, c.text, s.maxWidth).length));
      ctx.restore();
      const size = parseFloat(s.font.match(/(\d+(?:\.\d+)?)px/)[1]), lh = size * s.lineHeight;
      return { x0: W / 2 - s.maxWidth / 2 - s.padX, x1: W / 2 + s.maxWidth / 2 + s.padX, y0: s.y * H - (lines - 1) * lh - size * 0.95 - s.padY / 2, y1: s.y * H + size * 0.3 + s.padY / 2 };
    }

    function drawAt(T, frame) {
      frame = frame ?? Math.floor(T * fps + 1e-6);
      if (textProbe) textLog = [];
      const active = scenes.filter((s) => T >= s.start && T < s.end);
      if (!active.length) active.push(T < 0 ? scenes[0] : scenes[scenes.length - 1]);
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      if (active.length === 1) {
        const s = active[0];
        ctx.setTransform(scale, 0, 0, scale, 0, 0);
        ctx.fillStyle = s.background ?? bg;
        ctx.fillRect(0, 0, W, H);
        s.draw(ctx, sceneInfo(s, Math.min(T, s.end - 1e-6), frame));
      } else {
        const [a, b] = active.slice(-2);
        const tr = b._tr;
        paintScene(bctx[0], a, T, frame);
        paintScene(bctx[1], b, T, frame);
        const p = (tr.ease || ease.inOutCubic)(clamp((T - b.start) / tr.duration));
        const fn = typeof tr.type === 'function' ? tr.type : transitions[tr.type] || transitions.fade;
        // start from a known state: transitions that composite with alpha must
        // never blend over whatever the previous drawFrame() left behind
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        fn(ctx, bufs[0], bufs[1], p, tr);
      }
      ctx.restore();
      ctx.save();
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      if (config.overlay) {
        const beat = bpm ? (T - gridOffset) / beatLen : NaN;
        const pulse = (decay = 0.16) => (bpm ? Math.exp(-((beat - Math.floor(beat + 1e-6)) * beatLen) / decay) : 0);
        config.overlay(ctx, { T, frame, fps, W, H, u: Math.min(W, H) / 1080, duration, p: T / duration, scenes, isRender: RENDER, beat, beatLen: beatLen || NaN, bar: beat / beatsPerBar, pulse });
      }
      if (burnSubs && burnCues.length) {
        // a scene may restyle captions over its own field (e.g. a highlight that contrasts with it)
        const cur = scenes.filter((x) => T >= x.start && T < x.end).pop();
        const style = cur && cur.captionStyle ? Object.assign({}, config.subtitles?.style, cur.captionStyle) : config.subtitles?.style;
        const log = textLog;
        textLog = null;
        drawSubtitles(ctx, burnCues, T, style);
        textLog = log;
      }
      ctx.restore();
    }

    // Time of a motion-blur subframe. The shutter never reaches across a hard
    // cut (it would blend the last frame of one scene into the first of the
    // next) or outside the video.
    function subTime(f, sub) {
      const T0 = f / fps;
      let T = (f + sub) / fps;
      if (!sub) return T;
      for (const s of scenes) {
        if (!s._tr || s._tr.type !== 'cut') continue;
        if (T0 < s.start && T >= s.start) T = s.start - 1e-6;
        else if (T0 >= s.start && T < s.start) T = s.start;
      }
      return clamp(T, 0, duration - 1e-6);
    }

    // ---- font / asset readiness ----------------------------------------------
    async function ready() {
      if (typeof document === 'undefined' || !document.fonts) return;
      const seen = new Map();
      const proto = CanvasRenderingContext2D.prototype;
      const origFill = proto.fillText, origStroke = proto.strokeText, origMeasure = proto.measureText;
      const rec = function (txt) {
        const k = this.font;
        seen.set(k, (seen.get(k) || '') + String(txt));
      };
      proto.fillText = function (txt, ...r) { rec.call(this, txt); return origFill.call(this, txt, ...r); };
      proto.strokeText = function (txt, ...r) { rec.call(this, txt); return origStroke.call(this, txt, ...r); };
      proto.measureText = function (txt) { rec.call(this, txt); return origMeasure.call(this, txt); };
      const OProto = typeof OffscreenCanvasRenderingContext2D !== 'undefined' ? OffscreenCanvasRenderingContext2D.prototype : null;
      const oFill = OProto && OProto.fillText, oMeasure = OProto && OProto.measureText;
      if (OProto) {
        OProto.fillText = function (txt, ...r) { rec.call(this, txt); return oFill.call(this, txt, ...r); };
        OProto.measureText = function (txt) { rec.call(this, txt); return oMeasure.call(this, txt); };
      }
      for (const f of config.fonts || []) seen.set(f, (seen.get(f) || '') + 'AaBb0123');
      await settleAssets();
      // Declared fonts first, so setup() can already rasterise text (3D textures).
      await Promise.all((config.fonts || []).map((f) => document.fonts.load(f).catch(() => [])));
      if (config.setup) await config.setup(api);
      await settleAssets();
      api.missingAssets = assetErrors.slice();
      // Warm-up pass: sample the timeline so every font+glyph combo gets requested.
      try {
        const step = Math.max(1, Math.round(fps / 6));
        for (let f = 0; f < totalFrames; f += step) drawAt(f / fps, f);
      } catch (e) { console.error(e); }
      proto.fillText = origFill; proto.strokeText = origStroke; proto.measureText = origMeasure;
      if (OProto) { OProto.fillText = oFill; OProto.measureText = oMeasure; }
      const loads = [];
      for (const [font, txt] of seen) {
        const uniq = Array.from(new Set(Array.from(txt))).join('').slice(0, 4000);
        loads.push(document.fonts.load(font, uniq || 'A').catch(() => []));
      }
      await Promise.all(loads);
      await document.fonts.ready;
      const missing = [];
      for (const [font, txt] of seen) {
        const fam = font.match(/"([^"]+)"/)?.[1];
        if (!fam) continue;
        const faces = Array.from(document.fonts).filter((f) => f.family.replace(/"/g, '') === fam);
        const uniq = Array.from(new Set(Array.from(txt))).join('').slice(0, 4000);
        // every glyph drawn must be covered by a loaded face: a unicode-range
        // subset that failed to download would otherwise fall back silently
        if (faces.length && !faces.some((f) => f.status === 'loaded')) missing.push(fam);
        else if (uniq && !document.fonts.check(font, uniq)) missing.push(fam);
      }
      api.missingFonts = Array.from(new Set(missing));
      // Anything rasterised from text before the fonts arrived is stale now.
      fontEpoch++;
      scenes.forEach((s) => { s._sync = null; });
    }

    const api = {
      W, H, fps, duration, totalFrames, canvas, ctx, scenes, cues, scale, bpm, sfx, missingFonts: [], missingAssets: [],
      drawFrame: (f, sub = 0) => drawAt(subTime(f, sub), f),
      // What the renderer calls: if drawing the frame started a webfont download
      // (a glyph subset the warm-up never saw), wait for it and draw again, so the
      // captured pixels never depend on download timing or render order.
      renderFrame: async (f, sub = 0) => {
        drawAt(subTime(f, sub), f);
        for (let k = 0; k < 4 && typeof document !== 'undefined' && document.fonts && document.fonts.status === 'loading'; k++) {
          await document.fonts.ready;
          fontEpoch++;
          drawAt(subTime(f, sub), f);
        }
      },
      // renders frame f and returns the boxes of the text on it (see logText)
      textBoxes: async (f) => {
        const P = CanvasRenderingContext2D.prototype, fill = P.fillText, stroke = P.strokeText;
        P.fillText = function (...a) { logText(this, a[0], a[1], a[2], a[3], false); return fill.apply(this, a); };
        P.strokeText = function (...a) { logText(this, a[0], a[1], a[2], a[3], true); return stroke.apply(this, a); };
        textProbe = true;
        try { await api.renderFrame(f); } finally { P.fillText = fill; P.strokeText = stroke; textProbe = false; }
        const seen = new Set();
        return (textLog || []).filter((b) => {
          const k = [b.text, Math.round(b.x0), Math.round(b.y0), Math.round(b.x1), Math.round(b.y1)].join('|');
          return !seen.has(k) && seen.add(k);
        });
      },
      drawAt,
      ready,
      info: () => ({
        width: W, height: H, fps, duration, totalFrames, scale, lang,
        pixelWidth: canvas.width, pixelHeight: canvas.height,
        captionBand: captionBand(),
        scenes: scenes.map((s) => ({ id: s.id, start: s.start, dur: s.dur, voiceStart: s.voice ? s.start + s.voiceDelay : null, voiceDuration: s.voice?.duration ?? null, estimated: !!s.voice?.estimated })),
        voice: scenes.filter((s) => s.voice && s.voice.file && !s.voice.estimated).map((s) => ({ id: s.id, file: s.voice.file, start: s.start + s.voiceDelay, duration: s.voice.duration, speech: speechEnd(s.voice) })),
        cues: cues.map((c) => ({ start: c.start, end: c.end, text: c.text })),
        missingFonts: api.missingFonts,
        missingAssets: api.missingAssets,
        music: mus?.file || null,
        // beat grid + arrangement plan for the generated score (scripts/music.mjs)
        bpm, beatsPerBar, gridOffset,
        score: mus && (mus.layers || mus.lead || mus.script) && !mus.file ? {
          bpm, beatsPerBar, offset: gridOffset, seed: mus.seed ?? 1,
          key: mus.key ?? null, mode: mus.mode ?? null, progression: mus.progression ?? null, sevenths: mus.sevenths ?? false,
          chordBars: mus.chordBars ?? 1, layers: mus.layers ?? [], lead: mus.lead ?? null, fills: mus.fills ?? true, ...(mus.parts ? { parts: mus.parts } : {}),
          volume: mus.volume ?? 1, duck: mus.duck ?? null, gap: mus.gap ?? null, duration, fps,
          intro: mus.intro ?? null, ending: mus.ending ?? 'resolve', script: mus.script ?? null,
          sections: scenes.map((s) => ({ id: s.id, start: s.start, end: s.end, energy: s.energy ?? null, voiced: !!s.voice, ...(s._part != null ? { part: s._part } : {}),
            ...(mus.script && s.voice?.words ? { words: s.voice.words.map((w) => ({ text: w.text, t: s.start + s.voiceDelay + w.start, end: s.start + s.voiceDelay + (w.end ?? w.start) })) } : {}) })),
          voice: scenes.filter((s) => s.voice).map((s) => ({ start: s.start + s.voiceDelay, end: s.start + s.voiceDelay + speechEnd(s.voice) })),
          sfx: sfx.map((e) => ({ ...e })),
        } : null,
        sfx: sfx.map((e) => ({ ...e })),
      }),
      capture: (type = 'image/png', q) => canvas.toDataURL(type, q),
    };
    root.__CV = api;

    if (!RENDER && typeof document !== 'undefined') mountPlayer(api, config);
    return api;
  }

  function normTransition(tr) {
    if (!tr) return { type: 'cut', duration: 0 };
    if (typeof tr === 'string') return { type: tr, duration: tr === 'cut' ? 0 : 0.6 };
    return { duration: 0.6, ...tr };
  }

  // ===========================================================================
  // Preview player (only when opened in a normal browser)
  // ===========================================================================
  function mountPlayer(api, config) {
    const start = () => {
      const { canvas, fps, duration, scenes } = api;
      document.body.style.cssText = 'margin:0;background:#111;color:#ddd;font:13px/1.4 ui-monospace,Menlo,monospace;display:flex;flex-direction:column;height:100vh;overflow:hidden';
      const stage = document.createElement('div');
      stage.style.cssText = 'flex:1;display:flex;align-items:center;justify-content:center;min-height:0;padding:12px';
      canvas.style.cssText = 'max-width:100%;max-height:100%;box-shadow:0 10px 40px rgba(0,0,0,.6);background:#000';
      stage.appendChild(canvas);
      const bar = document.createElement('div');
      bar.style.cssText = 'padding:10px 16px 14px;display:flex;gap:12px;align-items:center;background:#1a1a1a';
      bar.innerHTML = `<button id="cvp" style="width:64px">Play</button><div id="cvtrack" style="flex:1;position:relative;height:22px;cursor:pointer"><div style="position:absolute;top:10px;left:0;right:0;height:2px;background:#444"></div><div id="cvhead" style="position:absolute;top:3px;width:2px;height:16px;background:#fff"></div></div><span id="cvtime"></span>`;
      document.body.appendChild(stage);
      document.body.appendChild(bar);
      const track = bar.querySelector('#cvtrack');
      for (const s of scenes) {
        const m = document.createElement('div');
        m.title = s.id;
        m.style.cssText = `position:absolute;top:6px;left:${(s.start / duration) * 100}%;width:1px;height:10px;background:#888`;
        track.appendChild(m);
      }
      const inf = api.info();
      const tracks = inf.voice.slice();
      // background music: a licensed file, or the score rendered by `gaga music`
      const bed = inf.music || (inf.score ? 'build/music.wav' : null);
      if (bed) tracks.push({ id: 'music', file: bed, start: 0, duration });
      const audios = tracks.map((v) => { const a = new Audio(v.file); a.preload = 'auto'; a.onerror = () => { v.dead = true; }; return Object.assign(v, { a }); });
      let t = 0, playing = false, last = 0;
      const head = bar.querySelector('#cvhead'), time = bar.querySelector('#cvtime'), btn = bar.querySelector('#cvp');
      const paint = () => {
        api.drawAt(t);
        head.style.left = `${(t / duration) * 100}%`;
        const s = scenes.find((x) => t >= x.start && t < x.end) || scenes[scenes.length - 1];
        time.textContent = `${t.toFixed(2)}s / ${duration.toFixed(2)}s  f${Math.floor(t * fps)}  [${s.id}]`;
      };
      const syncAudio = () => {
        for (const v of audios) {
          if (v.dead) continue;
          const local = t - v.start;
          if (playing && local >= 0 && local < v.duration) {
            if (v.a.paused) { v.a.currentTime = local; v.a.play().catch(() => {}); }
            else if (Math.abs(v.a.currentTime - local) > 0.15) v.a.currentTime = local;
          } else if (!v.a.paused) v.a.pause();
        }
      };
      const loop = (now) => {
        if (playing) {
          t += (now - last) / 1000;
          if (t >= duration) { t = 0; }
          last = now;
          syncAudio();
          paint();
          requestAnimationFrame(loop);
        }
      };
      const toggle = () => {
        playing = !playing;
        btn.textContent = playing ? 'Pause' : 'Play';
        if (playing) { last = performance.now(); requestAnimationFrame(loop); } else syncAudio();
      };
      btn.onclick = toggle;
      const seekTo = (e) => {
        const r = track.getBoundingClientRect();
        t = clamp((e.clientX - r.left) / r.width) * duration;
        audios.forEach((v) => v.a.pause());
        paint();
        syncAudio();
      };
      track.onmousedown = (e) => { seekTo(e); window.onmousemove = seekTo; window.onmouseup = () => (window.onmousemove = null); };
      window.addEventListener('keydown', (e) => {
        if (e.code === 'Space') { e.preventDefault(); toggle(); }
        if (e.code === 'ArrowRight') { t = Math.min(duration, t + (e.shiftKey ? 1 : 1 / fps)); paint(); }
        if (e.code === 'ArrowLeft') { t = Math.max(0, t - (e.shiftKey ? 1 : 1 / fps)); paint(); }
      });
      const hash = parseFloat(location.hash.slice(1));
      if (!isNaN(hash)) t = hash;
      api.ready().then(paint);
      paint();
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
  }

  // ===========================================================================
  // three.js bridge (optional). The composition imports three itself:
  //   <script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.min.js"}}</script>
  //   <script type="module">import * as THREE from 'three'; const gl = CV.three(THREE, { width, height }); … CV.create({…})</script>
  // One WebGLRenderer is shared by every scene: scenes render one after the
  // other (also inside transitions), so the WebGL context limit is never hit.
  // ===========================================================================
  function three(THREE, opts = {}) {
    const W = opts.width ?? 1920, H = opts.height ?? 1080;
    const scale = Number(params.get('scale') || opts.pixelRatio || 1);
    const canvas = document.createElement('canvas');
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: opts.antialias ?? true, alpha: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1);
    renderer.setSize(Math.round(W * scale), Math.round(H * scale), false);
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    // 'aces' (default: filmic, darkens and shifts saturated colours), 'neutral'
    // (keeps brand and product colours true), 'agx', or false
    if (opts.toneMapping !== false) {
      const tm = { aces: 'ACESFilmicToneMapping', neutral: 'NeutralToneMapping', agx: 'AgXToneMapping' }[opts.toneMapping == null || opts.toneMapping === true ? 'aces' : opts.toneMapping];
      if (!tm) throw new Error(`CV.three: toneMapping "${opts.toneMapping}" is not one of 'aces', 'neutral', 'agx' or false`);
      renderer.toneMapping = THREE[tm];
      renderer.toneMappingExposure = opts.exposure ?? 1;
    }
    if (opts.shadows) {
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    }
    const textures = new Map();
    const studios = new Map();
    const maps = new Map(), hdris = new Map(), addons = new Map();
    let pmrem = null;
    // three.js add-ons (loaders) come from the composition's import map
    const addon = (file) => {
      if (!addons.has(file)) addons.set(file, import(`three/addons/${file}`).catch((e) => {
        throw new Error(`CV.three: could not import three/addons/${file}. Add "three/addons/" to the import map (docs/three-d.md). ${e.message}`);
      }));
      return addons.get(file);
    };
    // queue an asset load; the renderer waits for it, and a failure is recorded
    const pending = (src, p) => imagePromises.push(p.catch((e) => {
      assetErrors.push(src);
      console.error(`[video-gaga] asset failed: ${src} (${e?.message || e})`);
    }));
    // three's loaders fetch(), which can't read file:// (how compositions are
    // opened and rendered); XHR can, so files are read here and handed over as
    // blob: URLs
    const readFile = (src) => new Promise((res, rej) => {
      const x = new XMLHttpRequest();
      x.open('GET', src);
      x.responseType = 'arraybuffer';
      x.onload = () => (x.status === 0 || (x.status >= 200 && x.status < 300)) && x.response?.byteLength ? res(x.response) : rej(new Error(`not found (${x.status})`));
      x.onerror = () => rej(new Error('not found'));
      x.send();
    });
    const blobURL = async (src) => URL.createObjectURL(new Blob([await readFile(src)]));
    const loadImage = (src) => new Promise((res, rej) => {
      const img = new Image();
      img.decoding = 'sync';
      img.onload = () => res(img);
      img.onerror = () => rej(new Error('not found or not an image'));
      img.src = src;
    });
    // Unit vector for azimuth/elevation in degrees: az 0 = the camera side (+z),
    // 90 = right (+x), 180 = behind; el 0 = horizon, 90 = overhead.
    const dirOf = (az, el) => {
      const a = (az * Math.PI) / 180, e = (el * Math.PI) / 180;
      return new THREE.Vector3(Math.cos(e) * Math.sin(a), Math.sin(e), Math.cos(e) * Math.cos(a));
    };
    // An image file as a texture (a map from `gaga asset`/`gaga texture`, a
    // generated label or a matcap). Cached per src and options; the renderer
    // waits for it. color: true for colour (albedo, matcap, emissive: sRGB),
    // false for data (normal, roughness, ao, metalness: linear).
    // repeat: n or [u, v] tiles across the UVs.
    function mapTex(src, o = {}) {
      const color = o.color ?? true, rep = Array.isArray(o.repeat) ? o.repeat : [o.repeat ?? 1, o.repeat ?? 1];
      const key = JSON.stringify([src, color, rep, o.flipY ?? true]);
      if (maps.has(key)) return maps.get(key);
      const tex = new THREE.Texture();
      tex.colorSpace = color ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
      tex.repeat.set(rep[0], rep[1]);
      tex.flipY = o.flipY ?? true;
      tex.anisotropy = Math.min(o.anisotropy ?? 8, renderer.capabilities.getMaxAnisotropy());
      maps.set(key, tex);
      pending(src, loadImage(src).then((img) => { tex.image = img; tex.needsUpdate = true; }));
      return tex;
    }
    function buildStudio(spec) {
      const R = 10, scene = new THREE.Scene();
      // the dome: ground colour below the horizon, sky colour above, blended over ±10°
      const sky = new THREE.Color(spec.sky ?? '#202020'), ground = new THREE.Color(spec.ground ?? spec.sky ?? '#202020');
      const domeGeo = new THREE.SphereGeometry(R, 64, 32);
      const pos = domeGeo.attributes.position, cols = new Float32Array(pos.count * 3), c = new THREE.Color();
      for (let i = 0; i < pos.count; i++) {
        const el = (Math.asin(clamp(pos.getY(i) / R, -1, 1)) * 180) / Math.PI;
        c.copy(ground).lerp(sky, clamp((el + 10) / 20));
        cols.set([c.r, c.g, c.b], i * 3);
      }
      domeGeo.setAttribute('color', new THREE.BufferAttribute(cols, 3));
      scene.add(new THREE.Mesh(domeGeo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, toneMapped: false })));
      // panels: softboxes, strips and black flags, each a patch of the sphere
      // w x h degrees wide (exact at any size); one that reaches the zenith is a
      // round cap. A later panel covers an earlier one.
      const D = Math.PI / 180;
      (spec.panels || []).forEach((p, i) => {
        const az = p.az ?? 0, el = p.el ?? 0, w = Math.min(360, p.w ?? 20), h = p.h ?? 20, r = R * (0.9 - i * 0.004);
        const top = el + h / 2, bottom = el - h / 2;
        const cap = top >= 90;
        const t0 = Math.max(0, 90 - top), t1 = Math.min(180, 90 - bottom);
        const geo = cap
          ? new THREE.SphereGeometry(r, 64, 16, 0, 2 * Math.PI, 0, (90 - bottom) * D)
          : new THREE.SphereGeometry(r, Math.max(2, Math.ceil(w / 3)), Math.max(2, Math.ceil(h / 3)), (az + 90 - w / 2) * D, w * D, t0 * D, (t1 - t0) * D);
        const col = new THREE.Color(p.color ?? '#ffffff').multiplyScalar(p.intensity ?? 1);
        const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: col, side: THREE.DoubleSide, toneMapped: false }));
        if (p.tilt && !cap) m.rotateOnWorldAxis(dirOf(az, el), p.tilt * D);
        scene.add(m);
      });
      return scene;
    }
    return {
      THREE, renderer, canvas, W, H,
      // Render a scene and composite it onto the 2D frame (transparent where
      // the 3D scene has no background). rect = [x, y, w, h] in design px
      // renders into a region; set the camera aspect to match.
      render(ctx, scene, camera, rect) {
        const pw = canvas.width, ph = canvas.height;
        if (rect) {
          const [x, y, w, h] = rect.map((v) => Math.round(v * scale));
          renderer.setScissorTest(true);
          renderer.setViewport(x, ph - y - h, w, h);
          renderer.setScissor(x, ph - y - h, w, h);
          renderer.clear();
          renderer.render(scene, camera);
          ctx.drawImage(canvas, x, y, w, h, rect[0], rect[1], rect[2], rect[3]);
        } else {
          renderer.setScissorTest(false);
          renderer.setViewport(0, 0, pw, ph);
          renderer.clear();
          renderer.render(scene, camera);
          ctx.drawImage(canvas, 0, 0, W, H);
        }
      },
      // A studio built in code, for reflections you direct: a dome (sky above the
      // horizon, ground below) and panels placed by azimuth/elevation in degrees.
      // spec = { sky, ground, panels: [{ az, el, w, h, intensity, color, tilt }], size, key }
      // Returns a PMREM texture for scene.environment or material.envMap. Cached
      // per key (default: the spec itself); calling it with a changed spec under
      // the same key rebuilds it, so a strip can sweep (a glint) as a pure function of t.
      studio(spec = {}) {
        const sig = JSON.stringify(spec), key = spec.key ?? sig;
        const e = studios.get(key);
        if (e && e.sig === sig) return e.target.texture;
        pmrem = pmrem || new THREE.PMREMGenerator(renderer);
        const scene = buildStudio(spec);
        const target = pmrem.fromScene(scene, 0, 0.1, 100, { size: spec.size ?? 256 });
        scene.traverse((o) => { o.geometry?.dispose(); o.material?.dispose(); });
        e?.target.dispose();
        studios.set(key, { sig, target });
        return target.texture;
      },
      // Screen position [x, y] in design px of a world point, for 2D labels that
      // ride a 3D object and for match cuts between a 3D object and its 2D shape.
      project(x, y, z, camera) {
        camera.updateMatrixWorld();
        const v = new THREE.Vector3(x, y, z).project(camera);
        return [((v.x + 1) / 2) * W, ((1 - v.y) / 2) * H];
      },
      // Where a studio panel must sit for a surface to reflect it into the camera:
      // { az, el } in degrees for a world-space normal (and the point on the
      // surface, default the origin). Put a glint strip there and sweep it across.
      mirror(normal, camera, point = new THREE.Vector3()) {
        camera.updateMatrixWorld();
        const n = new THREE.Vector3().copy(normal).normalize();
        const v = new THREE.Vector3().setFromMatrixPosition(camera.matrixWorld).sub(point).normalize();
        const r = n.multiplyScalar(2 * n.dot(v)).sub(v); // v reflected about n
        return { az: (Math.atan2(r.x, r.z) * 180) / Math.PI, el: (Math.asin(clamp(r.y, -1, 1)) * 180) / Math.PI };
      },
      // An image file as a texture (a map from `gaga asset`/`gaga texture`, a
      // generated label or a matcap). Cached per src and options; the renderer
      // waits for it. color: true for colour (albedo, matcap, emissive, sRGB),
      // false for data (normal, roughness, ao, metalness: linear).
      // repeat: n or [u, v] tiles across the UVs.
      map: mapTex,
      // A PBR set in one folder, as `gaga asset` and `gaga texture` write it:
      // albedo.jpg, normal.jpg, roughness.jpg, ao.jpg (+ metalness.jpg with
      // { metalness: true }). Returns material props to spread:
      //   new THREE.MeshPhysicalMaterial({ ...gl.pbr('assets/oak', { repeat: 2 }) })
      // A roughness or metalness map multiplies the material's value: leave
      // roughness at 1 (the default) unless you mean to scale it.
      pbr(dir, o = {}) {
        const f = (n, color) => mapTex(`${dir.replace(/\/$/, '')}/${n}.jpg`, { ...o, color });
        const m = { map: f('albedo', true), normalMap: f('normal', false), roughnessMap: f('roughness', false) };
        if (o.ao !== false) m.aoMap = f('ao', false);
        if (o.metalness) { m.metalnessMap = f('metalness', false); m.metalness = 1; }
        if (o.normalScale != null) m.normalScale = new THREE.Vector2(o.normalScale, o.normalScale);
        return m;
      },
      // An equirectangular .hdr (`gaga asset <project> polyhaven:<id>`) as a
      // PMREM environment for scene.environment or a material's envMap. The
      // first call starts the download; it returns null until the file is in
      // (the renderer waits for it), then the cached texture. So call it once
      // at load and assign it where the world is posed:
      //   world.environment = gl.hdri('assets/studio_small_09.hdr');
      hdri(src) {
        const e = hdris.get(src);
        if (e) return e.tex;
        const entry = { tex: null };
        hdris.set(src, entry);
        pending(src, addon('loaders/HDRLoader.js').then(async (mod) => {
          const Loader = mod.HDRLoader || mod.RGBELoader;
          const eq = await new Loader().loadAsync(await blobURL(src));
          eq.mapping = THREE.EquirectangularReflectionMapping;
          pmrem = pmrem || new THREE.PMREMGenerator(renderer);
          entry.tex = pmrem.fromEquirectangular(eq).texture;
          eq.dispose();
        }));
        return null;
      },
      // A glTF/GLB model. Returns a Group at once (add it, place it); the
      // model's scene is put inside it when it loads, before the first frame.
      // Its animation clips are on group.userData.animations: drive them with
      // an AnimationMixer and mixer.setTime(s.t) in draw, never update(dt).
      // { shadows: true } makes every mesh cast and receive shadows.
      model(src, o = {}) {
        const group = new THREE.Group();
        group.name = src;
        pending(src, addon('loaders/GLTFLoader.js').then(async ({ GLTFLoader }) => {
          const base = src.slice(0, src.lastIndexOf('/') + 1), buf = await readFile(src);
          const manager = new THREE.LoadingManager();
          if (!/\.glb$/i.test(src)) {
            // a .gltf names its buffers and images: read each one, map its URL to a blob
            const json = JSON.parse(new TextDecoder().decode(buf)), urls = new Map();
            const uris = [...(json.buffers || []), ...(json.images || [])].map((r) => r.uri).filter((u) => u && !u.startsWith('data:'));
            await Promise.all(uris.map(async (u) => urls.set(decodeURI(u), await blobURL(base + u))));
            manager.setURLModifier((url) => {
              const d = decodeURI(url);
              for (const [u, b] of urls) if (d.endsWith(u)) return b;
              return url;
            });
          }
          const gltf = await new GLTFLoader(manager).parseAsync(buf, base);
          if (o.shadows) gltf.scene.traverse((m) => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });
          group.add(gltf.scene);
          group.userData.animations = gltf.animations;
        }));
        return group;
      },
      // A CanvasTexture painted with the 2D API (text and labels in 3D). Cached
      // per key and repainted once webfonts are ready. paint(g, w, h) must be pure.
      texture(key, w, h, paint) {
        let e = textures.get(key);
        if (!e || e.epoch !== fontEpoch) {
          const c = e?.canvas || document.createElement('canvas');
          c.width = w;
          c.height = h;
          const g = c.getContext('2d');
          g.clearRect(0, 0, w, h);
          paint(g, w, h);
          if (e) { e.tex.needsUpdate = true; e.epoch = fontEpoch; }
          else {
            const tex = new THREE.CanvasTexture(c);
            tex.colorSpace = THREE.SRGBColorSpace;
            tex.anisotropy = 4;
            e = { canvas: c, tex, epoch: fontEpoch };
            textures.set(key, e);
          }
        }
        return e.tex;
      },
    };
  }

  // ===========================================================================
  // Isometric figures (optional): paints the geometry of the anatomy kit
  // (github.com/wheresryan22/anatomy, MIT) onto the 2D frame. The composition
  // imports the kit itself from a pinned CDN; its builders return SVG path
  // strings, which this painter draws with Path2D in the kit's own order and
  // tones. Lines keep a fixed width on screen however far the camera pushes in,
  // like the kit's non-scaling strokes.
  //   import * as k from 'https://cdn.jsdelivr.net/gh/wheresryan22/anatomy@<commit>/kit/iso-kit.mjs';
  //   const iso = CV.iso({ paper: T.bg, ink: T.ink, lit: T.accent });
  //   iso.solid(ctx, k.slabOf(plan, 0, 12, P, 8, 1.2), { tone: 'mid' });
  // ===========================================================================
  // How far each tone sits from paper toward ink, and how far each fill sits
  // from paper toward black (−) or white (+), measured from the kit's themes.
  const ISO_RAMP = {
    dark: { hi: 0.82, mid: 0.38, lo: 0.18, faint: 0.09, face: 0.03, top: 0.035, shades: [-0.22, -0.06, 0.012, 0.025], litTop: 0.08, litShade: 0.045, halo: 0.9 },
    light: { hi: 0.94, mid: 0.53, lo: 0.33, faint: 0.17, face: 1, top: 1, shades: [-0.12, -0.085, -0.055, -0.03], litTop: 1, litShade: -0.05, halo: 0.32 },
  };
  function iso(opts = {}) {
    const paper = opts.paper ?? '#131313';
    const ink = opts.ink ?? (luma(paper) < 0.4 ? '#e6e6e6' : '#18181a');
    const mode = opts.mode ?? (luma(paper) < 0.4 ? 'dark' : 'light');
    const R = ISO_RAMP[mode];
    const toward = (amt) => (amt < 0 ? color.mix(paper, '#000', -amt) : color.mix(paper, '#fff', amt));
    const tones = {
      paper,
      hi: color.mix(paper, ink, R.hi), mid: color.mix(paper, ink, R.mid), lo: color.mix(paper, ink, R.lo), faint: color.mix(paper, ink, R.faint),
      lit: mode === 'dark' ? '#ffffff' : '#000000',
      face: toward(R.face), top: toward(R.top), shades: R.shades.map(toward),
      litTop: toward(R.litTop), litShade: toward(R.litShade),
      halo: mode === 'dark' ? '#050505' : color.mix(paper, '#4a4a40', 0.5), haloAlpha: R.halo,
      dot: color.mix(paper, ink, 0.95),
      red: mode === 'dark' ? '#ff6b6b' : '#e5484d', green: mode === 'dark' ? '#6be0a0' : '#30a46c', blue: mode === 'dark' ? '#6b9bff' : '#3e63dd',
      ...opts.tones,
    };
    if (opts.lit) tones.lit = opts.lit;
    const weight = opts.weight ?? 1.5; // line width in design px of the frame
    const renderScale = Number(params.get('scale') || 1);
    const cache = new Map();
    const path = (d) => {
      let p = cache.get(d);
      if (!p) {
        if (cache.size > 20000) cache.clear();
        p = new Path2D(d);
        cache.set(d, p);
      }
      return p;
    };
    // user units per design px under the current transform
    const unit = (ctx) => {
      const m = ctx.getTransform();
      return renderScale / (Math.hypot(m.a, m.b) || 1);
    };
    const DOT_ALPHA = { hi: 0.85, mid: 0.45, lo: 0.22, faint: 0.12 };
    function line(ctx, d, { tone = 'lo', dotted = false, dashed = false, width, alpha = 1 } = {}) {
      if (!d) return;
      const u = unit(ctx);
      ctx.save();
      ctx.globalAlpha *= alpha;
      ctx.strokeStyle = tones[tone] ?? tone;
      ctx.lineWidth = (width ?? (dotted ? weight * 1.6 : weight)) * u;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      if (dotted) ctx.setLineDash([0.01 * u, weight * 5.5 * u]);
      else if (dashed) ctx.setLineDash([weight * 5 * u, weight * 5 * u]);
      ctx.stroke(path(d));
      ctx.restore();
    }
    // blur and dy in figure units: a shadow grows with its object when the
    // camera pushes in (a canvas blur is in device px, so it is scaled here)
    function halo(ctx, d, { blur = 9, dy = 3, alpha = 1 } = {}) {
      if (!d) return;
      const m = ctx.getTransform();
      ctx.save();
      ctx.globalAlpha *= tones.haloAlpha * alpha;
      ctx.filter = `blur(${(blur * Math.hypot(m.a, m.b)).toFixed(2)}px)`;
      ctx.translate(0, dy);
      ctx.fillStyle = tones.halo;
      ctx.fill(path(d));
      ctx.restore();
    }
    // The kit's solidSvg, painted: halo, paper fill, four side shades, top,
    // crease, bevel, then the outline in the part's tone. `lit` marks the one
    // part the viewer should watch.
    function solid(ctx, paths, { tone = 'hi', crease = 'faint', halo: withHalo = false, lit = false, flat = false, alpha = 1, inner } = {}) {
      ctx.save();
      ctx.globalAlpha *= alpha;
      if (withHalo) halo(ctx, paths.fill);
      ctx.fillStyle = lit ? tones.face : tones.paper;
      ctx.fill(path(paths.fill));
      if (!flat) {
        const seam = paths.seamless ? 0.4 * unit(ctx) : 0;
        paths.shades.forEach((d, i) => {
          if (!d) return;
          ctx.fillStyle = lit ? tones.litShade : tones.shades[i];
          ctx.fill(path(d));
          if (seam) { ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = seam; ctx.lineJoin = 'round'; ctx.stroke(path(d)); }
        });
        ctx.fillStyle = lit ? tones.litTop : tones.top;
        ctx.fill(path(paths.top));
        if (seam) { ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = seam; ctx.stroke(path(paths.top)); }
      }
      if (crease !== 'none') { line(ctx, paths.crease, { tone: crease }); line(ctx, paths.bevel, { tone: crease }); }
      if (inner) inner(ctx);
      line(ctx, paths.outline, { tone: lit ? 'lit' : tone });
      ctx.restore();
    }
    // points: screen [x, y, alpha?] from k.iso / k.pointsAt; size in figure units
    function dots(ctx, points, { size = 0.5, tone = 'mid', alpha = 1 } = {}) {
      ctx.save();
      const outer = ctx.globalAlpha;
      ctx.fillStyle = tones.dot;
      for (const [x, y, a = 1] of points) {
        ctx.globalAlpha = outer * alpha * (DOT_ALPHA[tone] ?? 0.32) * Math.max(0, a);
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }
    function wire(ctx, from, to, { via = [], tone = 'lo', ends = 'both', size = 1.2, ...style } = {}) {
      const pts = [from, ...via, to];
      ctx.save();
      line(ctx, 'M' + pts.map(([x, y]) => `${x} ${y}`).join('L'), { tone, ...style });
      const end = ([x, y]) => {
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fillStyle = tones.paper;
        ctx.fill();
        ctx.lineWidth = weight * unit(ctx);
        ctx.strokeStyle = tones[tone] ?? tone;
        ctx.stroke();
      };
      if (ends === 'both' || ends === 'from') end(from);
      if (ends === 'both' || ends === 'to') end(to);
      ctx.restore();
    }
    // ribsOf / dotsOf with fade: [[d, alpha], …] or [{ d, alpha }, …]
    function faded(ctx, list, style = {}) {
      for (const e of list) {
        const [d, a] = Array.isArray(e) ? e : [e.d, e.alpha];
        if (d && a > 0.02) line(ctx, d, { ...style, alpha: (style.alpha ?? 1) * Math.min(1, a) });
      }
    }
    // a piece from tube.mjs's tubePieces
    function tube(ctx, piece, { tone = 'hi', alpha = 1 } = {}) {
      ctx.save();
      ctx.globalAlpha *= alpha;
      ctx.fillStyle = tones.shades[2];
      ctx.fill(path(piece.body));
      if (piece.wide) {
        ctx.fillStyle = tones.top; ctx.fill(path(piece.shine));
        ctx.fillStyle = tones.shades[0]; ctx.fill(path(piece.shade));
      }
      faded(ctx, piece.rings ?? [], { tone: piece.ringTone ?? 'lo', width: weight * 0.75 });
      line(ctx, piece.edges, { tone });
      ctx.restore();
    }
    return { tones, weight, path, unit, solid, line, halo, dots, wire, faded, tube };
  }
  function luma(c) {
    const [r, g, b] = parseColor(c);
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  }

  const CV = {
    create, ease, spring, progress, tween, springTrack, stagger, clamp, lerp, invLerp, remap,
    rand, noise, noise2, color, text, draw, fx, transitions, image, drawCover, three, iso,
    subtitles: { build: buildCues, draw: drawSubtitles, estimate: estimateSpeech, align: alignWords },
    speech: { end: speechEnd, find: findPhrase },
    RENDER, version: '0.2.0',
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = CV;
  root.CV = CV;
})(typeof window !== 'undefined' ? window : globalThis);
