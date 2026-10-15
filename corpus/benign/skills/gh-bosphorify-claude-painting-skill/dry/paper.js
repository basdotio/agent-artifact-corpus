// paper.js: the sheet under dry media, and the marks that need to know about it. For sketches built on template.html.
//
// Charcoal, conté, pastel and a dry brush catch on the peaks of the paper's grain and skip its pits; watercolor
// pools at the edge of a stroke as it dries and settles into the pits. p5.brush knows nothing about the paper, and
// its watercolor fill suits compact washes but folds long brush strokes into cellophane ribbons. This module adds:
//
//   Paper.init(W, H, SEED, { kind: 'cold', grain: 1 })   in setup(), after createCanvas() and background()
//     kind: 'cold' (cold-pressed watercolor), 'rough' (bigger, stronger bumps), 'hot' (smooth: hot-pressed, bristol),
//           'laid' (Ingres / Michallet charcoal paper: fine grain plus laid and chain lines).
//     grain: scales the bump size (1 = about 1 mm on a sheet 50 cm wide).
//
//   Paper.init(W, H, SEED, { preset: 'kraft' })   a named sheet: 'blue-black', 'kraft', 'warm-grey', 'cool-grey' or 'graph'.
//     It sets the colour, the grain and the sheet's own look (tone clouds, fibres, flecks, a printed grid), paints it, and
//     registers the light media below. Paper.presets is the table; Paper.presets['kraft'].color is the colour for
//     background(). Paper.media() registers the p5.brush brushes 'whiteink', 'whitepencil' and 'chalk'.
//
//   layerFn.tooth = 0.6   a p5.brush layer whose marks catch only on the grain (charcoal, conté, pastel, pencil).
//     0 = no effect, 0.5 = only the deepest pits stay clean, 0.8 = only the top of the peaks. Heavier marks reach
//     further into the pits, like pressure on a crayon. template.html's draw() does the bookkeeping.
//
//   Paper.paint(buf => { ... })   a layer of marks computed on the pixels (RGBA bytes of the whole canvas):
//     Paper.stroke(buf, pts, width, color, opts)   a loaded watercolor or ink brush: swells and tapers along a
//                                                  Catmull-Rom path through pts [x, y, pressure?]; tail: 0.3 lets the
//                                                  last 30% run dry into a dry-brush end
//     Paper.shape(buf, polygon, color, opts)       a wash over a polygon [[x, y], ...], over several as one wash,
//                                                  or over a raster mask { mask: Float32Array 0..1, x0, y0, w, h }
//        strength: film strength (1 = the color itself where the pigment is even; 0.3 = a pale tint)
//        edge: pigment pooled at the rim as it dries (0.3-0.6 on dry paper, 0 wet-in-wet)
//        soft: edge blur in px (about 1 on dry paper, 10-40 wet-in-wet); rough: ragged edge (0..1)
//        feather: how much a soft edge creeps out in irregular fingers instead of a smooth blur (0..1)
//        mottle: uneven pigment inside (0..1); settle: granulation into the pits (0..1)
//        mode: 'glaze' (transparent watercolor, the default), 'opaque' (gouache, body color), 'lift' (back to paper)
//        holes: polygons left out (reserved whites, the rocks a water stroke must not cross)
//        clip: a polygon the mark stays inside, with that polygon's own crisp edge (strokes that model a rock)
//        charge: [color, amount 0..1, blotch size px] a second color dropped into the wet wash (charging)
//        simplify: px; rounds away teeth and notches smaller than about this (e.g. a union of mesh triangles)
//        grade: [top, bottom] strength multipliers, a graded wash; gravity: 0..1, the dried rim heavier at the bottom
//     Paper.dryBrush(buf, pts, width, color, { load, streak, mode, strength })   a dragged brush that skips over
//        the grain: load 0.9 nearly solid, 0.6 broken, 0.4 only the peaks; the paint runs out along the stroke.
//     Paper.outline(pts, width, { taper })   the polygon of a stroke, for p5.brush or Paper.shape.
//     Paper.mix(['#3d5fae', 2], ['#c4506e', 1])   pigments mixed as glazes combine (geometric mean), -> '#rrggbb'.
//     Paper.roughen(polygon, amp, seed)   a polygon with a ragged edge (amp px), e.g. a reserved white of broken foam.
//     Paper.noise(seed, cell)   smooth value noise (x, y) => 0..1 with features about `cell` px, for masks and wobbles.
//     Paper.margin(buf, { width: [top, right, bottom, left] })   washes stopping short of the sheet's edge, raggedly.
//     Don't put p5.brush calls in the same layer: they are drawn when the frame ends, after the pixel marks.
//
//   Paper.finish({ granulation: 0.1, relief: 0.02 })   the last layer: pigment settles into the pits of the heavier washes
//     (pale tints stay smooth; about 0.05 for graphite and charcoal) and the sheet's relief is lit from the upper left.
//
// Everything is deterministic for a seed, draws no numbers from p5's random stream, and scales with W.
const Paper = (() => {
  let W = 0, H = 0, S = 1, h = null, work = null, img = null, SEEDV = 1, marks = 0;
  let paperRGB = [255, 255, 255];
  let epoch = 0; // counts Paper.init calls, so helpers built on it (print.js) know a new sheet has begun
  let spec = null, sheetPx = null; // the preset in use, and its bare sheet as RGBA bytes (what lift and margin go back to)

  // mulberry32: a small seeded PRNG, so the paper never draws from p5's random stream
  const rng = seed => () => {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
  const clamp = (x, a, b) => x < a ? a : x > b ? b : x;
  const smooth = (e0, e1, x) => { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); };
  const hexRGB = hex => { const s = hex.replace('#', ''); return [0, 2, 4].map(k => parseInt(s.slice(k, k + 2), 16)); };
  const noise = rand => { const a = new Float32Array(W * H); for (let i = 0; i < a.length; i++) a[i] = rand() - 0.5; return a; };
  const nextRand = salt => rng(SEEDV * 1013 + salt * 7919 + 31 * ++marks);

  // Smooth 2D value noise in 0..1 with cells of `cell` px
  function vnoise(R, cell) {
    const N = 64, g = Float32Array.from({ length: N * N }, () => R());
    const f = t => t * t * (3 - 2 * t);
    return (x, y) => {
      const gx = x / cell + 1000, gy = y / cell + 1000, i = Math.floor(gx), j = Math.floor(gy);
      const fx = f(gx - i), fy = f(gy - j), q = (a, b) => g[((b % N) * N) + (a % N)];
      return (q(i, j) * (1 - fx) + q(i + 1, j) * fx) * (1 - fy) + (q(i, j + 1) * (1 - fx) + q(i + 1, j + 1) * fx) * fy;
    };
  }

  // Three box blurs of radius r approximate a Gaussian
  function blur(src, r) {
    r = Math.max(1, Math.round(r));
    const a = Float32Array.from(src), b = new Float32Array(W * H);
    const pass = (from, to, n, m, stride, step) => {
      const inv = 1 / (2 * r + 1);
      for (let i = 0; i < n; i++) {
        const o = i * stride;
        let acc = 0;
        for (let k = -r; k <= r; k++) acc += from[o + clamp(k, 0, m - 1) * step];
        for (let j = 0; j < m; j++) {
          to[o + j * step] = acc * inv;
          acc += from[o + Math.min(m - 1, j + r + 1) * step] - from[o + Math.max(0, j - r) * step];
        }
      }
    };
    for (let k = 0; k < 3; k++) { pass(a, b, H, W, W, 1); pass(b, a, W, H, 1, W); }
    return a;
  }

  function normalize(a, mean = 0.5, sd = 0.17) {
    let s = 0, s2 = 0;
    for (let i = 0; i < a.length; i++) { s += a[i]; s2 += a[i] * a[i]; }
    const m = s / a.length, d = Math.sqrt(Math.max(1e-12, s2 / a.length - m * m));
    for (let i = 0; i < a.length; i++) a[i] = (a[i] - m) / d * sd + mean;
    return a;
  }

  function init(width, height, seed = 1, { kind, grain, preset = null } = {}) {
    if (preset && !PRESETS[preset]) throw new Error(`Paper.init: unknown preset '${preset}' (${Object.keys(PRESETS).join(', ')})`);
    spec = preset ? PRESETS[preset] : null; sheetPx = null;
    kind = kind ?? spec?.kind ?? 'cold'; grain = grain ?? spec?.grain ?? 1;
    W = width; H = height; S = W / 2048; SEEDV = seed; marks = 0; epoch++;
    const rand = rng(seed * 7919 + 17);
    const g = grain * S * 1.3; // bump radius in px: bumps about 1.5 mm across on a 50 cm sheet at 2048 px
    const a = new Float32Array(W * H);
    const fiber = noise(rand);
    if (kind === 'laid') {
      const fine = normalize(blur(noise(rand), Math.max(1, 0.6 * g)), 0, 1), coarse = normalize(blur(noise(rand), 2.5 * g), 0, 1);
      const wav = normalize(blur(noise(rand), 16 * g), 0, 1);
      const period = Math.max(3, 2.0 * g), chain = 120 * S;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const i = y * W + x;
        const laid = Math.sin(2 * Math.PI * (y + 0.6 * wav[i] * period) / period);
        const cx = ((x + 3 * wav[i]) % chain + chain) % chain;
        const ch = Math.exp(-((cx - chain / 2) ** 2) / (2 * (1.5 * g) ** 2));
        a[i] = 0.8 * fine[i] + 0.6 * coarse[i] + 0.55 * laid - 0.5 * ch + 0.25 * fiber[i];
      }
    } else {
      const r1 = kind === 'rough' ? 1.7 * g : kind === 'hot' ? 0.6 * g : g;
      const n = noise(rand);
      const b1 = normalize(blur(n, r1), 0, 1), b2 = normalize(blur(n, 2.6 * r1), 0, 1);
      const low = normalize(blur(noise(rand), 12 * r1), 0, 1);
      for (let i = 0; i < a.length; i++) {
        const bump = b1[i] - 0.6 * b2[i];
        // cold-pressed paper is mostly broad tops with scattered pits: flatten the tops, keep the pits deep
        a[i] = (bump > 0 ? bump * 0.7 : bump * 1.25) + 0.3 * low[i] + 0.12 * fiber[i];
      }
    }
    h = normalize(a, 0.5, kind === 'hot' ? 0.1 : 0.17);
    for (let i = 0; i < h.length; i++) h[i] = clamp(h[i], 0, 1);
    work = document.createElement('canvas');
    work.width = W; work.height = H;
    paperRGB = hexRGB(spec ? spec.color : typeof PAPER === 'string' ? PAPER : '#ffffff');
    if (spec) {
      media();
      if (typeof drawingContext !== 'undefined') paint(sheet);
    }
    return h;
  }

  // The current picture (the p5 WEBGL canvas) as RGBA bytes
  function read() {
    const g = work.getContext('2d', { willReadFrequently: true });
    g.clearRect(0, 0, W, H);
    g.drawImage(drawingContext.canvas, 0, 0, W, H);
    return g.getImageData(0, 0, W, H).data;
  }

  // RGBA bytes back onto the p5 canvas, so later p5.brush marks mix with them
  function write(data) {
    if (!img) img = createImage(W, H);
    img.loadPixels();
    img.pixels.set(data);
    img.updatePixels();
    push();
    resetMatrix();
    noStroke();
    image(img, -W / 2, -H / 2, W, H);
    pop();
  }

  const lum = (d, i) => 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];

  // Keep what a p5.brush layer added only where it caught on the grain
  function tooth(before, dry, { pressure = 0.8, soft = 0.06 } = {}) {
    const after = read();
    const thr0 = 1.1 * dry - 0.25;
    for (let p = 0, i = 0; p < h.length; p++, i += 4) {
      const d = Math.abs(lum(before, i) - lum(after, i)) / 255;
      if (d === 0) continue;
      const thr = thr0 - pressure * d;
      const m = smooth(thr - soft, thr + soft, h[p]);
      for (let c = 0; c < 3; c++) after[i + c] = before[i + c] + (after[i + c] - before[i + c]) * m;
    }
    write(after);
  }

  // A layer computed on the pixels: fn(buf) edits the RGBA bytes, which then go back onto the canvas
  function paint(fn) {
    const buf = read();
    fn(buf);
    write(buf);
  }

  // Put k (coverage times strength) of a color into pixel i of buf
  function deposit(buf, i, k, col, mode) {
    if (k <= 0) return;
    if (mode === 'glaze') {
      // a transparent film (Beer-Lambert): k = 1 turns white paper into the color itself
      for (let j = 0; j < 3; j++) buf[i + j] *= Math.pow(Math.max(col[j], 1) / 255, k);
    } else {
      const a = Math.min(1, k);
      for (let j = 0; j < 3; j++) buf[i + j] += ((mode !== 'lift' ? col[j] : sheetPx ? sheetPx[i + j] : paperRGB[j]) - buf[i + j]) * a;
    }
  }

  // Catmull-Rom path through control points [x, y, pressure?], sampled about every `step` px
  function path(pts, step = 1) {
    const P = pts.map(p => [p[0], p[1], p[2] ?? 1]);
    if (P.length === 1) return [P[0]];
    const cr = (a, b, c, d, t) => 0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t * t * t);
    const out = [];
    for (let i = 0; i < P.length - 1; i++) {
      const a = P[Math.max(0, i - 1)], b = P[i], c = P[i + 1], d = P[Math.min(P.length - 1, i + 2)];
      const n = Math.max(2, Math.ceil(Math.hypot(c[0] - b[0], c[1] - b[1]) / step));
      for (let k = 0; k < n; k++) {
        const t = k / n;
        out.push([cr(a[0], b[0], c[0], d[0], t), cr(a[1], b[1], c[1], d[1], t), b[2] + (c[2] - b[2]) * t]);
      }
    }
    out.push(P[P.length - 1]);
    return out;
  }

  // The polygon of a brush stroke: width (px at pressure 1) swells over taper[0] of the length and thins over taper[1]
  function outline(pts, width, { taper = [0.2, 0.45] } = {}, rails = null) {
    const pp = path(pts, Math.max(1, width / 6));
    const L = [0];
    for (let i = 1; i < pp.length; i++) L.push(L[i - 1] + Math.hypot(pp[i][0] - pp[i - 1][0], pp[i][1] - pp[i - 1][1]));
    const tot = L[L.length - 1] || 1, left = [], right = [];
    for (let i = 0; i < pp.length; i++) {
      const a = pp[Math.max(0, i - 1)], b = pp[Math.min(pp.length - 1, i + 1)];
      let dx = b[0] - a[0], dy = b[1] - a[1];
      const dl = Math.hypot(dx, dy) || 1; dx /= dl; dy /= dl;
      const s = L[i] / tot;
      const ta = taper[0] > 0 ? Math.min(1, s / taper[0]) : 1, tb = taper[1] > 0 ? Math.min(1, (1 - s) / taper[1]) : 1;
      const r = 0.5 * width * pp[i][2] * Math.sqrt(Math.max(0.04, ta)) * Math.sqrt(Math.max(0.04, tb));
      left.push([pp[i][0] - dy * r, pp[i][1] + dx * r]);
      right.push([pp[i][0] + dy * r, pp[i][1] - dx * r]);
    }
    if (rails) { rails.left = left; rails.right = right; rails.s = L.map(l => l / tot); }
    return pts.length === 1 ? circle(pts[0][0], pts[0][1], 0.5 * width * (pts[0][2] ?? 1)) : left.concat(right.slice().reverse());
  }

  // A lookup of where each pixel lies in a stroke: s along it (0..1) and u across it (-1..1), rasterized from the
  // outline's rails as quads with a gradient across; returns (x, y) => [s, u] or null outside
  function strokeCoords(rails, pad = 4) {
    const { left, right, s: sv } = rails;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const [x, y] of [...left, ...right]) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    x0 = Math.floor(x0 - pad); y0 = Math.floor(y0 - pad); x1 = Math.ceil(x1 + pad); y1 = Math.ceil(y1 + pad);
    const bw = x1 - x0 + 1, bh = y1 - y0 + 1;
    if (bw < 2 || bh < 2 || bw * bh > 4e7) return () => null;
    const c = document.createElement('canvas'); c.width = bw; c.height = bh;
    const g = c.getContext('2d', { willReadFrequently: true });
    for (let i = 0; i + 1 < left.length; i++) {
      const a = left[i], b = left[i + 1], cR = right[i + 1], d = right[i];
      const mx0 = (a[0] + b[0]) / 2 - x0, my0 = (a[1] + b[1]) / 2 - y0, mx1 = (d[0] + cR[0]) / 2 - x0, my1 = (d[1] + cR[1]) / 2 - y0;
      const grad = g.createLinearGradient(mx0, my0, mx1, my1), sr = Math.round(255 * (sv[i] + sv[i + 1]) / 2);
      grad.addColorStop(0, `rgb(${sr},0,0)`); grad.addColorStop(1, `rgb(${sr},255,0)`);
      g.fillStyle = grad;
      g.beginPath(); g.moveTo(a[0] - x0, a[1] - y0); g.lineTo(b[0] - x0, b[1] - y0); g.lineTo(cR[0] - x0, cR[1] - y0); g.lineTo(d[0] - x0, d[1] - y0); g.closePath();
      g.fill();
      // widen by half a pixel so neighbouring quads leave no seam
      g.strokeStyle = grad; g.lineWidth = 1.5; g.stroke();
    }
    const d = g.getImageData(0, 0, bw, bh).data;
    return (x, y) => {
      const xi = Math.round(x) - x0, yi = Math.round(y) - y0;
      if (xi < 0 || yi < 0 || xi >= bw || yi >= bh) return null;
      const i = 4 * (yi * bw + xi);
      return d[i + 3] ? [d[i] / 255, d[i + 1] / 127.5 - 1] : null;
    };
  }
  const circle = (x, y, r, n = 24) => Array.from({ length: n }, (_, k) => [x + r * Math.cos(2 * Math.PI * k / n), y + r * Math.sin(2 * Math.PI * k / n)]);

  // Resample a closed polygon every ~3 px and push each point in or out along the normal with smooth noise
  function roughen(poly, amp, R) {
    const pts = [];
    for (let i = 0; i < poly.length; i++) {
      const [ax, ay] = poly[i], [bx, by] = poly[(i + 1) % poly.length];
      const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) / (3 * S)));
      for (let k = 0; k < n; k++) pts.push([ax + (bx - ax) * k / n, ay + (by - ay) * k / n]);
    }
    const nz = vnoise(R, 1), nz2 = vnoise(R, 1), f1 = 1 / (14 * S), f2 = 1 / (4 * S);
    let s = 0;
    return pts.map((p, i) => {
      const q = pts[(i + 1) % pts.length], o = pts[(i - 1 + pts.length) % pts.length];
      let dx = q[0] - o[0], dy = q[1] - o[1];
      const dl = Math.hypot(dx, dy) || 1; dx /= dl; dy /= dl;
      s += Math.hypot(q[0] - p[0], q[1] - p[1]);
      const d = amp * (1.4 * (nz(s * f1, 0.5) - 0.5) + 0.6 * (nz2(s * f2, 3.5) - 0.5));
      return [p[0] - dy * d, p[1] + dx * d];
    });
  }

  // The polygon filled white (minus its holes) on a canvas the size of a box, blurred by `soft` px: its alpha (0..1)
  function coverage(poly, holes, clip, x0, y0, bw, bh, soft, simplify = 0) {
    const mk = () => { const c = document.createElement('canvas'); c.width = bw; c.height = bh; return c; };
    const trace = (g, pts) => { g.beginPath(); pts.forEach(([x, y], k) => k ? g.lineTo(x - x0, y - y0) : g.moveTo(x - x0, y - y0)); g.closePath(); };
    let sharp = mk();
    const gs = sharp.getContext('2d');
    gs.fillStyle = '#fff';
    if (poly.mask) {
      const m = document.createElement('canvas'); m.width = poly.w; m.height = poly.h;
      const gm = m.getContext('2d'), im = gm.createImageData(poly.w, poly.h);
      for (let i = 0; i < poly.mask.length; i++) { im.data[4 * i] = im.data[4 * i + 1] = im.data[4 * i + 2] = 255; im.data[4 * i + 3] = 255 * clamp(poly.mask[i], 0, 1); }
      gm.putImageData(im, 0, 0);
      gs.drawImage(m, poly.x0 - x0, poly.y0 - y0);
    } else for (const pp of poly) { trace(gs, pp); gs.fill(); }
    if (holes.length) {
      gs.globalCompositeOperation = 'destination-out';
      for (const hole of holes) { trace(gs, hole); gs.fill(); }
    }
    if (simplify > 0.3) {
      // blur and threshold at half: small teeth and notches melt away, the big shape keeps its size
      const b = mk(), gb = b.getContext('2d', { willReadFrequently: true });
      gb.filter = `blur(${simplify}px)`;
      gb.drawImage(sharp, 0, 0);
      const im = gb.getImageData(0, 0, bw, bh), d = im.data;
      for (let i = 3; i < d.length; i += 4) { const t = clamp((d[i] / 255 - 0.42) / 0.16, 0, 1); d[i] = 255 * t * t * (3 - 2 * t); }
      gb.filter = 'none';
      gb.putImageData(im, 0, 0);
      sharp = b;
    }
    let out = sharp;
    if (soft > 0.3) {
      out = mk();
      const go = out.getContext('2d');
      go.filter = `blur(${soft}px)`;
      go.drawImage(sharp, 0, 0);
    }
    if (clip) {
      // clipped after the blur: the clip edge stays as crisp as the clip polygon (a rock's silhouette)
      const go = out.getContext('2d');
      go.filter = 'none';
      go.globalCompositeOperation = 'destination-in';
      go.fillStyle = '#fff';
      trace(go, clip); go.fill();
    }
    const d = out.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, bw, bh).data, a = new Float32Array(bw * bh);
    for (let i = 0; i < a.length; i++) a[i] = d[4 * i + 3] / 255;
    return a;
  }

  function shape(buf, poly, color, { strength = 0.8, edge = 0.4, soft = 1.2, rough = 0.4, mottle = 0.2, settle = 0.12,
    pool = 6, mode = 'glaze', grainEdge = 0.6, holes = [], clip = null, charge = null, feather = 0.6, simplify = 0, dry = null,
    grade = null, gravity = 0 } = {}) {
    const R = nextRand(1), col = mode === 'lift' ? paperRGB : hexRGB(color);
    // one polygon, several painted as one wash (their union), or a raster mask { mask, x0, y0, w, h } (values 0..1)
    const isMask = !!poly.mask;
    const polys = isMask ? [] : Array.isArray(poly[0]?.[0]) ? poly : [poly];
    const P = isMask ? poly : polys.map(pp => rough > 0 ? roughen(pp, rough * (4 * S + 0.3 * soft), R) : pp);
    const Hs = rough > 0 ? holes.map(hp => roughen(hp, rough * 3 * S, R)) : holes;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    if (isMask) { x0 = poly.x0; y0 = poly.y0; x1 = poly.x0 + poly.w; y1 = poly.y0 + poly.h; }
    else for (const pp of P) for (const [x, y] of pp) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    const pad = Math.ceil(3 * soft + 2 * pool * S) + 2;
    x0 = Math.max(0, Math.floor(x0 - pad)); y0 = Math.max(0, Math.floor(y0 - pad));
    x1 = Math.min(W - 1, Math.ceil(x1 + pad)); y1 = Math.min(H - 1, Math.ceil(y1 + pad));
    const bw = x1 - x0 + 1, bh = y1 - y0 + 1;
    if (bw < 2 || bh < 2) return;
    const a = coverage(P, Hs, clip, x0, y0, bw, bh, soft, simplify);
    const ab = edge > 0 ? coverage(P, Hs, clip, x0, y0, bw, bh, soft + pool * S, simplify) : null;
    const mot = vnoise(R, 45 * S), fz1 = vnoise(R, Math.max(3, 0.8 * soft)), fz2 = vnoise(R, Math.max(2, 0.3 * soft));
    // charging: a second color dropped into the wet wash, blooming through part of it
    const ch = charge ? hexRGB(charge[0]) : null, chAmt = charge ? charge[1] ?? 0.5 : 0, chN = charge ? vnoise(R, (charge[2] ?? 60) * S) : null;
    const mixed = [0, 0, 0];
    for (let y = 0; y < bh; y++) for (let x = 0; x < bw; x++) {
      const q = y * bw + x;
      let c = a[q];
      if (c <= 0.003) continue;
      const p = (y + y0) * W + (x + x0);
      // the wet edge stops against the bumps of the paper, and a soft (wet-in-wet) edge creeps out in fingers
      if (c < 0.999) {
        let d = grainEdge / (1 + 0.15 * soft) * (h[p] - 0.5) * 2;
        if (soft > 2 && feather > 0) d += feather * ((fz1(x, y) - 0.5) * 1.4 + (fz2(x, y) - 0.5) * 0.8);
        c = clamp(c + 4 * c * (1 - c) * d, 0, 1);
      }
      const e = ab ? clamp(a[q] - ab[q], 0, 1) : 0;
      // graded wash: strength runs from grade[0] at the top of the shape to grade[1] at its bottom; with gravity the
      // pigment pools along the lower rim, as on a tilted board
      const fy = (y - pad) / Math.max(1, bh - 2 * pad);
      const g = grade ? grade[0] + (grade[1] - grade[0]) * clamp(fy, 0, 1) : 1;
      const eg = gravity ? 1 + gravity * (2 * clamp(fy, 0, 1) - 1) : 1;
      let k = c * g * (1 + edge * 2.5 * e * eg) * (1 + mottle * 2 * (mot(x, y) - 0.5)) * (1 + settle * 2 * (0.5 - h[p]));
      if (dry) { k *= dry(x + x0, y + y0, h[p]); if (k <= 0) continue; }
      let cc = col;
      if (ch) {
        const t = chAmt * smooth(0.3, 0.7, chN(x, y));
        for (let j = 0; j < 3; j++) mixed[j] = Math.pow(Math.max(col[j], 1), 1 - t) * Math.pow(Math.max(ch[j], 1), t);
        cc = mixed;
      }
      deposit(buf, 4 * p, k * strength, cc, mode);
    }
  }

  function stroke(buf, pts, width, color, opts = {}) {
    const { tail = 0 } = opts;
    if (!(tail > 0) || pts.length < 2) return shape(buf, outline(pts, width, opts), color, opts);
    // the brush runs dry over the last `tail` of the stroke: the paint catches only on the grain, in bristle tracks
    const rails = {}, poly = outline(pts, width, opts, rails), at = strokeCoords(rails, Math.ceil(2 + (opts.soft ?? 1.2) * 2));
    const R = nextRand(4), nb = clamp(Math.round(width / (4 * S)), 5, 40);
    const lanes = Array.from({ length: 5 }, () => Array.from({ length: nb + 2 }, () => R()));
    const track = (sv, u) => {
      const x = clamp(u * 0.5 + 0.5, 0, 1) * nb, i = Math.min(nb, Math.floor(x)), f = x - i, fs = f * f * (3 - 2 * f);
      const z = clamp(sv, 0, 1) * 3.99, k = Math.floor(z), fz = z - k;
      const lane = l => l[i] + (l[i + 1] - l[i]) * fs;
      return lane(lanes[k]) * (1 - fz) + lane(lanes[k + 1]) * fz;
    };
    const start = 1 - tail;
    const dry = (x, y, hp) => {
      const su = at(x, y);
      if (!su) return 1;
      const [sv, u] = su;
      if (sv <= start) return 1;
      const t = (sv - start) / tail, load = 1 - 0.8 * t;
      const thr = 1.08 - 1.1 * load + 0.3 * u * u;
      return smooth(thr - 0.06, thr + 0.06, 0.5 + (hp - 0.5) * 1.3 + 0.5 * (track(sv, u) - 0.5));
    };
    shape(buf, poly, color, { ...opts, dry });
  }

  // A dragged brush that skips over the grain. pts: control points [x, y, pressure?]; width in px.
  //   load: paint in the brush (0.9 nearly solid, 0.6 broken, 0.4 only the peaks), running out by `depletion` along
  //   the stroke. streak: bristle tracks (0..1). smear: how far the skips stretch along the stroke, in px.
  function dryBrush(buf, pts, width, color, { load = 0.6, depletion = 0.35, streak = 0.6, taper = [0.08, 0.3], mode = 'glaze',
    strength = 1, soft = 0.05, edge = 0.35, smear = 4 } = {}) {
    const R = nextRand(2), col = mode === 'lift' ? paperRGB : hexRGB(color);
    const pp = path(pts, 0.5);
    const L = [0];
    for (let i = 1; i < pp.length; i++) L.push(L[i - 1] + Math.hypot(pp[i][0] - pp[i - 1][0], pp[i][1] - pp[i - 1][1]));
    const tot = L[L.length - 1] || 1;
    const nb = clamp(Math.round(width / (4 * S)), 5, 48), lanes = Array.from({ length: 5 }, () => Array.from({ length: nb + 2 }, () => R()));
    const track = (s, u) => {
      const x = clamp(u * 0.5 + 0.5, 0, 1) * nb, i = Math.min(nb, Math.floor(x)), f = x - i, fs = f * f * (3 - 2 * f);
      const z = s * 3.99, k = Math.floor(z), fz = z - k;
      const at = lane => lane[i] + (lane[i + 1] - lane[i]) * fs;
      return at(lanes[k]) * (1 - fz) + at(lanes[k + 1]) * fz;
    };
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of pp) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); }
    const pad = Math.ceil(width) + 2;
    x0 = Math.max(0, Math.floor(x0 - pad)); y0 = Math.max(0, Math.floor(y0 - pad));
    x1 = Math.min(W - 1, Math.ceil(x1 + pad)); y1 = Math.min(H - 1, Math.ceil(y1 + pad));
    if (x1 < x0 || y1 < y0) return; // entirely off the sheet
    const bw = x1 - x0 + 1, cov = new Float32Array(bw * (y1 - y0 + 1));
    const hAt = (x, y) => h[clamp(Math.round(y), 0, H - 1) * W + clamp(Math.round(x), 0, W - 1)];
    for (let k = 0; k < pp.length; k++) {
      const a = pp[Math.max(0, k - 1)], b = pp[Math.min(pp.length - 1, k + 1)];
      let dx = b[0] - a[0], dy = b[1] - a[1];
      const dl = Math.hypot(dx, dy) || 1; dx /= dl; dy /= dl;
      const s = L[k] / tot;
      const env = Math.sqrt(taper[0] > 0 ? Math.min(1, s / taper[0] + 0.05) : 1) * Math.sqrt(taper[1] > 0 ? Math.min(1, (1 - s) / taper[1] + 0.05) : 1);
      const r = 0.5 * width * pp[k][2] * env, ld = load * (1 - depletion * s), sm = smear * S;
      for (let u = -r; u <= r; u += 0.5) {
        const fx = pp[k][0] - dy * u, fy = pp[k][1] + dx * u, x = Math.round(fx), y = Math.round(fy);
        if (x < x0 || x > x1 || y < y0 || y > y1) continue;
        const e = Math.abs(u) / Math.max(r, 1e-6);
        // the grain seen along the drag: skips stretch out behind each pit
        const v = 0.3 * hAt(fx, fy) + 0.2 * (hAt(fx - dx * sm, fy - dy * sm) + hAt(fx + dx * sm, fy + dy * sm))
          + 0.15 * (hAt(fx - 2 * dx * sm, fy - 2 * dy * sm) + hAt(fx + 2 * dx * sm, fy + 2 * dy * sm));
        const thr = 1.08 - 1.1 * ld + edge * e * e;
        const c = smooth(thr - soft, thr + soft, 0.5 + (v - 0.5) * 1.6 + streak * 0.35 * (track(s, u / Math.max(r, 1e-6)) - 0.5));
        const q = (y - y0) * bw + (x - x0);
        if (c > cov[q]) cov[q] = c;
      }
    }
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      const c = cov[(y - y0) * bw + (x - x0)];
      if (c > 0) deposit(buf, 4 * (y * W + x), c * strength, col, mode);
    }
  }

  // Mix watercolor pigments the way glazes combine: a weighted geometric mean of their transmittances in linear light.
  //   Paper.mix(['#3d5fae', 2], ['#c4506e', 1]) -> '#rrggbb' (a cobalt-rose violet)
  const toLin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const toEnc = c => { const v = c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055; return Math.round(255 * clamp(v, 0, 1)); };
  function mix(...pairs) {
    const acc = [0, 0, 0];
    let tw = 0;
    for (const [hex, w = 1] of pairs) {
      const rgb = hexRGB(hex);
      for (let j = 0; j < 3; j++) acc[j] += w * Math.log(Math.max(1e-4, toLin(rgb[j])));
      tw += w;
    }
    return '#' + acc.map(a => toEnc(Math.exp(a / tw)).toString(16).padStart(2, '0')).join('');
  }

  // An unpainted margin: the washes stop short of the sheet's edge along a ragged line, pooling a little where they stop.
  //   width: [top, right, bottom, left] in px (0 = painted to the edge); rough: how ragged the line is (px).
  function margin(buf, { width = [20, 20, 20, 20], rough = 14, pool = 0.25 } = {}) {
    const R = nextRand(3), nz0 = vnoise(R, 160 * S), nz = vnoise(R, 40 * S), nz2 = vnoise(R, 12 * S), [wt, wr, wb, wl] = width;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const i = 4 * (y * W + x);
      // distance inside the painted area, the smallest over the four sides that have a margin
      let d = Infinity;
      // brush-made, not torn: broad swings along the side, smaller wobbles, a little fine raggedness
      const j = rough * ((nz0(x, y) - 0.5) * 2.6 + (nz(x, y) - 0.5) * 0.35 + (nz2(x, y) - 0.5) * 0.08);
      if (wt > 0) d = Math.min(d, y - wt + j);
      if (wb > 0) d = Math.min(d, H - 1 - y - wb + j);
      if (wl > 0) d = Math.min(d, x - wl + j);
      if (wr > 0) d = Math.min(d, W - 1 - x - wr + j);
      if (d === Infinity || d > 3 * S + 2) continue;
      if (d <= 0) { for (let c = 0; c < 3; c++) buf[i + c] = sheetPx ? sheetPx[i + c] : paperRGB[c]; continue; }
      // just inside the stopped edge the pigment is a little denser (the dried rim)
      const k = 1 + pool * (1 - d / (3 * S + 2));
      for (let c = 0; c < 3; c++) { const t = buf[i + c] / paperRGB[c]; if (t < 1) buf[i + c] = paperRGB[c] * Math.pow(Math.max(t, 1e-3), k); }
    }
  }

  // Granulation (pigment settles into the pits) and the sheet's relief under a light from the upper left
  function finish({ granulation = 0.1, relief = 0.02 } = {}) {
    const d = read();
    const P = paperRGB, s = Math.max(1, Math.round(S)), pl = 0.2126 * P[0] + 0.7152 * P[1] + 0.0722 * P[2];
    for (let y = 0, p = 0; y < H; y++) for (let x = 0; x < W; x++, p++) {
      const i = 4 * p;
      // granulation shows in the heavy washes; a pale tint lies smooth on the paper
      const dark = 1 - lum(d, i) / pl, g = 1 + granulation * 2 * (0.5 - h[p]) * smooth(0.12, 0.6, dark);
      const xa = Math.max(0, x - s), xb = Math.min(W - 1, x + s), ya = Math.max(0, y - s), yb = Math.min(H - 1, y + s);
      const shade = 1 + relief * 4 * (h[ya * W + xa] - h[yb * W + xb]);
      for (let c = 0; c < 3; c++) {
        let v = d[i + c];
        const t = v / P[c];
        if (t < 1) v = P[c] * Math.pow(Math.max(t, 1e-3), g); // Beer-Lambert: absorbance scaled by g
        d[i + c] = v * shade;
      }
    }
    write(d);
  }

  // ---- papers: named sheets, with the look of the stock ----
  // color: the stock's mean colour; clouds: tone patches; tooth: the grain's own light and shade (both relative to the colour);
  // fibres (per megapixel) and flecks: light/dark strands and specks; tint: per-channel colour drift; grid: a printed grid
  // (step and width in px at 2048, a stronger line every `every`, density 0..1 of the ink over the paper).
  const PRESETS = {
    'blue-black': { color: '#161e2d', kind: 'cold', grain: 0.75, clouds: 0.3, tooth: 0.14, fibres: 260, fibreDir: 0, fibreSpread: 180, fibreAmp: 0.3, flecks: 0, tint: [0, 0.05, 0.12] },
    kraft: { color: '#b48f63', kind: 'rough', grain: 0.55, clouds: 0.1, tooth: 0.07, fibres: 900, fibreDir: 5, fibreSpread: 70, fibreAmp: 0.1, flecks: 14, tint: [0.03, 0, -0.06] },
    'warm-grey': { color: '#b5aea2', kind: 'cold', grain: 0.8, clouds: 0.05, tooth: 0.06, fibres: 240, fibreDir: 0, fibreSpread: 180, fibreAmp: 0.05, flecks: 2, tint: [0.015, 0, -0.02] },
    'cool-grey': { color: '#a7afb5', kind: 'cold', grain: 0.8, clouds: 0.05, tooth: 0.06, fibres: 240, fibreDir: 0, fibreSpread: 180, fibreAmp: 0.05, flecks: 2, tint: [-0.015, 0, 0.02] },
    graph: { color: '#f3edd8', kind: 'hot', grain: 1, clouds: 0.03, tooth: 0.04, fibres: 120, fibreDir: 0, fibreSpread: 180, fibreAmp: 0.04, flecks: 1, tint: [0.01, 0, -0.03],
      grid: { step: 22, every: 5, ink: '#6db6a6', width: 1.1, minor: 0.42, major: 0.72 } },
  };

  // The sheet's look written into buf (RGBA bytes, the whole canvas): the stock colour with tone clouds, fibres, flecks and
  // the tooth's light and shade, all centred on the stock colour; then the printed grid. Paper.init with a preset calls
  // it; the result is kept as the bare sheet that lift and margin return to.
  function sheet(buf) {
    if (!spec) throw new Error('Paper.sheet: call Paper.init with a preset first');
    const R = rng(SEEDV * 4099 + 11), N = W * H, f = new Float32Array(N), tone = new Float32Array(N);
    const c1 = vnoise(R, 260 * S), c2 = vnoise(R, 70 * S), c3 = vnoise(R, 16 * S), hue = vnoise(R, 320 * S);
    for (let y = 0, i = 0; y < H; y++) for (let x = 0; x < W; x++, i++) {
      f[i] = 1 + spec.clouds * 2 * (0.55 * (c1(x, y) - 0.5) + 0.3 * (c2(x, y) - 0.5) + 0.15 * (c3(x, y) - 0.5)) + spec.tooth * 2 * (h[i] - 0.5);
      tone[i] = hue(x, y) - 0.5;
    }
    const splat = (x, y, v) => { // bilinear, so a strand is about a pixel wide
      const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi;
      if (xi < 0 || yi < 0 || xi + 1 >= W || yi + 1 >= H) return;
      const i = yi * W + xi;
      f[i] += v * (1 - fx) * (1 - fy); f[i + 1] += v * fx * (1 - fy); f[i + W] += v * (1 - fx) * fy; f[i + W + 1] += v * fx * fy;
    };
    for (let k = 0, n = Math.round(spec.fibres * N / 1e6); k < n; k++) {
      let x = R() * W, y = R() * H, a = (spec.fibreDir + (R() - 0.5) * spec.fibreSpread) * Math.PI / 180;
      const len = (8 + R() * 26) * S, bend = (R() - 0.5) * 0.08 / S, amp = (0.4 + 0.6 * R()) * spec.fibreAmp * (R() < 0.6 ? 1 : -1);
      for (let d = 0; d < len; d += 0.6) {
        splat(x, y, amp * Math.sin(Math.PI * d / len) * 0.6);
        x += Math.cos(a) * 0.6; y += Math.sin(a) * 0.6; a += bend * 0.6;
      }
    }
    for (let k = 0, n = Math.round(spec.flecks * N / 1e6); k < n; k++) {
      const cx = R() * W, cy = R() * H, r = (0.8 + R() * 1.8) * S, am = 0.18 + 0.3 * R();
      for (let y = Math.max(0, Math.floor(cy - 2 * r)); y <= Math.min(H - 1, Math.ceil(cy + 2 * r)); y++)
        for (let x = Math.max(0, Math.floor(cx - 2 * r)); x <= Math.min(W - 1, Math.ceil(cx + 2 * r)); x++)
          f[y * W + x] -= am * Math.exp(-1.2 * ((x - cx) ** 2 + (y - cy) ** 2) / (r * r));
    }
    for (let i = 0; i < N; i++) {
      for (let c = 0; c < 3; c++) buf[4 * i + c] = clamp(Math.round(paperRGB[c] * f[i] * (1 + spec.tint[c] * tone[i])), 0, 255);
      buf[4 * i + 3] = 255;
    }
    if (spec.grid) printGrid(buf, spec.grid);
    sheetPx = Uint8ClampedArray.from(buf);
  }

  // A printed grid: fine lines in a pale ink, a stronger one every `every` squares, centred on the sheet. The ink sits on
  // the peaks of the grain and thins a little along the line, as printed lines do.
  function printGrid(buf, g) {
    const step = g.step * S, lw = Math.max(1, g.width * S), ink = hexRGB(g.ink), R = rng(SEEDV * 6151 + 5), wob = vnoise(R, 90 * S);
    const axis = (n, size) => { // per pixel along one axis: the nearest line's coverage times its density
      const o = (size % step) / 2, out = new Float32Array(n);
      for (let p = 0; p < n; p++) {
        const t = (p + 0.5 - o) / step, k = Math.round(t), major = ((k % g.every) + g.every) % g.every === 0;
        out[p] = clamp((major ? 1.5 * lw : lw) / 2 + 0.5 - Math.abs(t - k) * step, 0, 1) * (major ? g.major : g.minor);
      }
      return out;
    };
    const cols = axis(W, W), rows = axis(H, H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const a = Math.max(cols[x], rows[y]);
      if (a <= 0) continue;
      const i = y * W + x, k = a * (0.7 + 0.6 * h[i]) * (0.85 + 0.3 * wob(x, y));
      for (let c = 0; c < 3; c++) buf[4 * i + c] *= 1 - k * (1 - ink[c] / 255);
    }
  }

  // Light media for dark paper, as p5.brush brushes: 'whiteink' (opaque, crisp, pen-fine), 'whitepencil' (waxy, catches on the
  // grain) and 'chalk' (wide, dusty). Use them like the built-ins: brush.set('whiteink', '#f3f0e8', 1). Pencil and chalk
  // break up on the grain only under a high layer tooth (0.8 and 0.9): on dark paper a white mark is high contrast, so a
  // low tooth lets it through everywhere. Safe to call again.
  function media() {
    if (typeof brush === 'undefined' || typeof brush.add !== 'function') return;
    const have = brush.box();
    const defs = {
      whiteink: { type: 'default', weight: 0.25, scatter: 0.03, sharpness: 0.95, grain: 12, opacity: 255, spacing: 0.05, pressure: { curve: [0.25, 0.3], min_max: [1.12, 0.95] }, noise: 0.08 },
      whitepencil: { type: 'default', weight: 0.45, scatter: 1.2, sharpness: 0.6, grain: 0.8, opacity: 170, spacing: 0.06, pressure: { curve: [0.15, 0.2], min_max: [0.95, 1.1] }, noise: 0.3 },
      chalk: { type: 'default', weight: 0.9, scatter: 3.4, sharpness: 0.35, grain: 1.2, opacity: 255, spacing: 0.03, pressure: { curve: [0.15, 0.4], min_max: [1.1, 0.95] }, noise: 0.4 },
    };
    for (const [name, def] of Object.entries(defs)) if (!have.includes(name)) brush.add(name, def);
  }


  return { init, read, write, tooth, paint, shape, stroke, dryBrush, outline, path, mix, margin, finish, rng, sheet, media, presets: PRESETS,
    get size() { return { W, H, S, seed: SEEDV }; }, get epoch() { return epoch; },
    roughen: (poly, amp, seed = 1) => roughen(poly, amp, rng(seed)), noise: (seed, cell) => vnoise(rng(seed), cell), get height() { return h; } };
})();
