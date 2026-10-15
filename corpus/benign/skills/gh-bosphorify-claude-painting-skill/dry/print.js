// print.js: flat-ink printing, for a relief print (linocut, woodcut) or a risograph. For sketches built on template.html.
//
// Each ink is a mask printed as a flat colour, then given the texture of the process: roller mottle and paper grain showing
// through, pinholes and a little squash at the edge; gouge marks that follow a direction field (relief); grain and halftone
// (riso). Plates after the first print slightly off register, and inks combine by multiply, so an overprint is darker.
// It works on the pixels like Paper.stroke, on the sheet that Paper.init made (its grain shows through the ink).
//
//   Paper.paint(buf => {
//     Print.ink(buf, { color: 'black', mask: sky, kind: 'relief', gouge: { field: Print.fields.radial([900, 600]) } });
//     Print.ink(buf, { color: 'red', mask: sun, kind: 'relief' });     // prints off register by itself
//   });
//
//   Print.ink(buf, plate)   prints one ink onto buf. plate:
//     color       '#rrggbb' or a name of Print.inks ('black', 'red', 'teal', 'fluoOrange', ...)
//     mask        what the ink prints: a polygon [[x, y], ...], a list of polygons, a function (ctx) => {} that draws the shapes
//                 in white on a 2D canvas context, or a Float32Array(W * H) of 0..1. See Print.mask.
//     kind        'relief' (default) or 'riso': the process's defaults for the options below
//     opacity     how much ink lies on the paper (relief 0.96, riso 0.88)
//     texture     0..1 multiplier on all the ink's texture (default 1; 0 is a perfectly flat ink)
//     mottle      roller mottle: patchy lay of the ink (relief 0.22, riso 0.12)
//     load        how much ink reaches the paper's pits: low lets the grain show through (relief 0.75, riso 0.65)
//     pinholes    specks the ink missed (relief 0.35, riso 0.35)
//     squash      ink squeezed out to a darker rim at the edge (relief 0.35, riso 0)
//     rough       ragged, uneven edge, in px at 2048 (relief 1.2, riso 0.7)
//     gouge       { field, spacing, length: [min, max], width, tone }: carved marks that remove ink along a direction field
//                 (angle in degrees, or Print.fields.*); spacing, length, width in px at 2048 (default 11, [40, 110], 6); tone
//                 (x, y) => 0..1, how light the place should be cut: more and wider gouges where it is high, none at 0 (default 0.5)
//     halftone    { tone, cell, angle, shape }: prints tone (x, y) => 0..1 (or a Float32Array) as dots (shape 'dot', the
//                 default), 'line' or 'grain'; cell in px at 2048 (default 10), angle in degrees. The mask still bounds the ink.
//     register    [dx, dy, rotation in degrees] offset of the plate; the default is none for the first plate of a sheet and a
//                 small seeded offset for each later one (Print.init({ misregister }) sets its size in px at 2048, default 4)
//   Print.mask(src)   the mask of a polygon, polygons, a drawing function or an array, as a Float32Array(W * H)
//   Print.fields      direction fields for gouges: constant(deg), radial([x, y]), vortex([x, y], twist), noise(scale, seed),
//                     contour(mask, sigma): each (x, y) => degrees, counter-clockwise as in brush.hatch (90 = up), only the
//                     orientation matters
//   Print.init({ seed, misregister })   optional; every Paper.init starts a new sheet (plates count from the first again)
//   Print.inks    the ink colours by name
//
// Seeded and deterministic (nothing comes from p5's random stream); sizes scale with the canvas width.
const Print = (() => {
  const INKS = {
    black: '#1b1815', red: '#b3261e', blue: '#23407a', brown: '#5a3a24', green: '#2f5d3a',           // relief inks
    teal: '#00838a', fluoOrange: '#ff6c2f', riso_blue: '#0078bf', fluoPink: '#ff48b0', yellow: '#ffe800', riso_green: '#00a95c',
    risoRed: '#f15060', purple: '#765ba7', risoBlack: '#2a2a2e',                                        // riso drums
  };
  const DEFAULTS = {
    relief: { opacity: 0.96, mottle: 0.22, load: 0.75, pinholes: 0.35, squash: 0.35, rough: 1.2 },
    riso: { opacity: 0.88, mottle: 0.12, load: 0.65, pinholes: 0.35, squash: 0, rough: 0.7 },
  };
  let opts = { seed: 1, misregister: 4 }, plates = 0, epoch = -1;
  const clamp = (x, a, b) => x < a ? a : x > b ? b : x;
  const smooth = (e0, e1, x) => { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); };
  const hexRGB = hex => { const s = (INKS[hex] ?? hex).replace('#', ''); return [0, 2, 4].map(k => parseInt(s.slice(k, k + 2), 16)); };

  function init(o = {}) { opts = { seed: 1, misregister: 4, ...o }; plates = 0; epoch = Paper.epoch; }

  // ---- masks ----
  function mask(src) {
    const { W, H } = Paper.size;
    if (src instanceof Float32Array) {
      if (src.length !== W * H) throw new Error(`Print.mask: a Float32Array of ${W * H} values (the whole canvas) was expected, got ${src.length}`);
      return src;
    }
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
    g.fillStyle = '#fff'; g.strokeStyle = '#fff';
    if (typeof src === 'function') src(g, W, H);
    else {
      const polys = Array.isArray(src[0]?.[0]) ? src : [src];
      for (const pp of polys) { g.beginPath(); pp.forEach(([x, y], k) => k ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); g.fill(); }
    }
    const d = g.getImageData(0, 0, W, H).data, out = new Float32Array(W * H);
    for (let i = 0; i < out.length; i++) out[i] = d[4 * i] / 255;
    return out;
  }

  // Two passes of a box blur of radius r (a triangle filter) over a W x H array
  function blur(a, r) {
    const { W, H } = Paper.size;
    r = Math.max(1, Math.round(r));
    let src = a, dst = new Float32Array(W * H);
    const inv = 1 / (2 * r + 1);
    for (let pass = 0; pass < 2; pass++) {
      for (let y = 0; y < H; y++) {
        let acc = 0;
        for (let k = -r; k <= r; k++) acc += src[y * W + clamp(k, 0, W - 1)];
        for (let x = 0; x < W; x++) { dst[y * W + x] = acc * inv; acc += src[y * W + Math.min(W - 1, x + r + 1)] - src[y * W + Math.max(0, x - r)]; }
      }
      src = dst; dst = new Float32Array(W * H);
      for (let x = 0; x < W; x++) {
        let acc = 0;
        for (let k = -r; k <= r; k++) acc += src[clamp(k, 0, H - 1) * W + x];
        for (let y = 0; y < H; y++) { dst[y * W + x] = acc * inv; acc += src[Math.min(H - 1, y + r + 1) * W + x] - src[Math.max(0, y - r) * W + x]; }
      }
      src = dst; dst = new Float32Array(W * H);
    }
    return src;
  }

  // ---- direction fields: (x, y) => degrees, counter-clockwise, 90 = up ----
  const deg = (dx, dy) => Math.atan2(-dy, dx) * 180 / Math.PI;   // screen vector -> counter-clockwise degrees
  const fields = {
    constant: a => () => a,
    radial: ([cx, cy]) => (x, y) => deg(x - cx, y - cy),
    vortex: ([cx, cy], twist = 0.8) => (x, y) => deg(x - cx, y - cy) + 90 * twist,
    noise: (scale, seed = 1, { angle = 0, spread = 180 } = {}) => { const n = Paper.noise(seed, scale); return (x, y) => angle + spread * (n(x, y) - 0.5) * 2; },
    // strokes run along the edges of a mask and echo them inside and outside
    contour: (src, sigma = 6) => {
      const { W, H } = Paper.size, b = blur(mask(src), sigma * 2.5), at = (x, y) => b[clamp(Math.round(y), 0, H - 1) * W + clamp(Math.round(x), 0, W - 1)];
      return (x, y) => deg(-(at(x, y + 2) - at(x, y - 2)), at(x + 2, y) - at(x - 2, y));   // the tangent: the gradient turned a quarter
    },
  };

  // ---- gouges: lens-shaped cuts along a field, drawn on a canvas; returns their coverage 0..1 ----
  function gouges(M, g, R) {
    const { W, H, S } = Paper.size;
    const field = typeof g.field === 'function' ? g.field : fields.constant(g.field ?? 0), tone = g.tone ?? (() => 0.5);
    const step = (g.spacing ?? 11) * S, [l0, l1] = (g.length ?? [40, 110]).map(v => v * S), wmax = (g.width ?? 6) * S;
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const ctx = c.getContext('2d', { willReadFrequently: true });
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#fff';
    for (let gy = step / 2; gy < H; gy += step) for (let gx = step / 2; gx < W; gx += step) {
      const x0 = gx + (R() - 0.5) * step, y0 = gy + (R() - 0.5) * step;
      if (x0 < 0 || y0 < 0 || x0 >= W || y0 >= H || M[Math.floor(y0) * W + Math.floor(x0)] < 0.5) continue;
      const t = clamp(tone(x0, y0), 0, 1);
      if (t < 0.04 || R() > 0.08 + 0.92 * t * t) continue;
      const len = l0 + (l1 - l0) * R(), wid = wmax * (0.3 + 0.7 * t) * (0.7 + 0.6 * R());
      // trace along the field, keeping one heading along the stroke
      let x = x0, y = y0, dx = 0, dy = 0;
      const a0 = field(x, y) * Math.PI / 180;
      dx = Math.cos(a0); dy = -Math.sin(a0);
      const pts = [[x, y]];
      for (let s = 2; s <= len; s += 2) {
        const a = field(x, y) * Math.PI / 180;
        let fx = Math.cos(a), fy = -Math.sin(a);
        if (fx * dx + fy * dy < 0) { fx = -fx; fy = -fy; }
        dx = 0.7 * dx + 0.3 * fx; dy = 0.7 * dy + 0.3 * fy;
        const n = Math.hypot(dx, dy) || 1; dx /= n; dy /= n;
        x += 2 * dx; y += 2 * dy;
        if (x < 0 || y < 0 || x >= W || y >= H || M[Math.floor(y) * W + Math.floor(x)] < 0.3) break;
        pts.push([x, y]);
      }
      if (pts.length < 3) continue;
      const left = [], right = [];
      pts.forEach(([px, py], k) => {
        const q = pts[Math.min(pts.length - 1, k + 1)], o = pts[Math.max(0, k - 1)];
        let tx = q[0] - o[0], ty = q[1] - o[1];
        const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
        const u = k / (pts.length - 1), w = 0.5 * wid * Math.pow(Math.sin(Math.PI * u), 0.6);
        left.push([px - ty * w, py + tx * w]); right.push([px + ty * w, py - tx * w]);
      });
      ctx.beginPath();
      [...left, ...right.reverse()].forEach(([px, py], k) => k ? ctx.lineTo(px, py) : ctx.moveTo(px, py));
      ctx.closePath(); ctx.fill();
    }
    const d = ctx.getImageData(0, 0, W, H).data, out = new Float32Array(W * H);
    for (let i = 0; i < out.length; i++) out[i] = d[4 * i] / 255;
    return out;
  }

  // A halftone screen: the coverage of tone (0..1) at (x, y), 0..1, with a soft edge
  function screen(shape, cell, angle, seed) {
    const a = angle * Math.PI / 180, ca = Math.cos(a), sa = Math.sin(a);
    if (shape === 'grain') { const n1 = Paper.noise(seed, cell * 0.35), n2 = Paper.noise(seed + 3, cell * 0.12); return (x, y, t) => clamp((1.18 * t - 0.09 - (0.6 * n1(x, y) + 0.4 * n2(x, y))) / 0.2 + 0.5, 0, 1); }
    return (x, y, t) => {
      const u = (x * ca + y * sa) / cell, v = (-x * sa + y * ca) / cell;
      // threshold 0..1: dots grow from the cell centres (a dot at 0.5, a chequer beyond), lines from the line centres
      const th = shape === 'line' ? 0.5 + 0.5 * Math.cos(2 * Math.PI * v) : 0.5 + 0.25 * (Math.cos(2 * Math.PI * u) + Math.cos(2 * Math.PI * v));
      return clamp((1.18 * t - 0.09 - (1 - th)) / 0.18 + 0.5, 0, 1);   // tone 0 prints nothing and tone 1 is solid
    };
  }

  // ---- printing one ink onto buf ----
  function ink(buf, plate) {
    const { W, H, S, seed } = Paper.size, h = Paper.height, kind = plate.kind ?? 'relief', D = DEFAULTS[kind];
    if (!D) throw new Error(`Print.ink: kind must be 'relief' or 'riso', got '${kind}'`);
    if (epoch !== Paper.epoch) init(opts);
    const k = plates++, tex = plate.texture ?? 1, col = hexRGB(plate.color ?? 'black');
    const o = Object.fromEntries(['opacity', 'mottle', 'load', 'pinholes', 'squash', 'rough'].map(n => [n, plate[n] ?? D[n]]));
    const R = Paper.rng(seed * 6007 + opts.seed * 131 + k * 977 + 5), M = mask(plate.mask), N = W * H;

    // the plate's shape: its edge ragged where the roller and the press are uneven, then the gouges cut into it
    let cov = M;
    if (o.rough > 0 && tex > 0) {
      const b = blur(M, Math.max(1, 1.4 * S)), n1 = Paper.noise(seed + k * 11 + 1, 5 * S), n2 = Paper.noise(seed + k * 11 + 2, 1.6 * S);
      cov = new Float32Array(N);
      for (let y = 0, i = 0; y < H; y++) for (let x = 0; x < W; x++, i++) {
        if (M[i] === 0 && b[i] < 0.02) continue;
        const wob = (0.6 * (n1(x, y) - 0.5) + 0.4 * (n2(x, y) - 0.5)) * Math.min(1, o.rough * S) * 1.6;
        cov[i] = smooth(0.5 + wob - 0.22, 0.5 + wob + 0.22, b[i]);
      }
    }
    if (plate.halftone) {
      const ht = plate.halftone, T = ht.tone, scr = screen(ht.shape ?? 'dot', (ht.cell ?? 10) * S, ht.angle ?? 45, seed + k * 17 + 9), out = new Float32Array(N);
      for (let y = 0, i = 0; y < H; y++) for (let x = 0; x < W; x++, i++) if (cov[i] > 0.002) out[i] = cov[i] * scr(x, y, T instanceof Float32Array ? T[i] : T(x, y));
      cov = out;
    }
    if (plate.gouge) {
      const cut = gouges(M, plate.gouge, R);
      cov = Float32Array.from(cov, (v, i) => v * (1 - cut[i]));
    }

    // registration: the plate's shape moves as a whole (bilinear), the paper does not
    let reg = plate.register;
    if (!reg) {
      if (k === 0) reg = [0, 0, 0];
      else { const a = R() * 2 * Math.PI, m = opts.misregister * S * (0.7 + 0.3 * R()); reg = [m * Math.cos(a), m * Math.sin(a), (R() - 0.5) * 0.06]; }
    }
    if (reg[0] || reg[1] || reg[2]) {
      const [dx, dy, rot = 0] = reg, c = Math.cos(-rot * Math.PI / 180), s = Math.sin(-rot * Math.PI / 180), moved = new Float32Array(N);
      for (let y = 0, i = 0; y < H; y++) for (let x = 0; x < W; x++, i++) {
        // where this pixel came from
        const rx = x - W / 2 - dx, ry = y - H / 2 - dy, sx = rx * c - ry * s + W / 2, sy = rx * s + ry * c + H / 2;
        const x0 = Math.floor(sx), y0 = Math.floor(sy);
        if (x0 < 0 || y0 < 0 || x0 + 1 >= W || y0 + 1 >= H) continue;
        const fx = sx - x0, fy = sy - y0, j = y0 * W + x0;
        moved[i] = (cov[j] * (1 - fx) + cov[j + 1] * fx) * (1 - fy) + (cov[j + W] * (1 - fx) + cov[j + W + 1] * fx) * fy;
      }
      cov = moved;
    }

    // the ink's texture: roller streaks and blotches, paper grain showing through, pinholes, a darker squashed rim
    const mot1 = Paper.noise(seed + k * 13 + 3, 38 * S), mot2 = Paper.noise(seed + k * 13 + 4, 7 * S), pin = Paper.noise(seed + k * 13 + 5, 1.4 * S);
    const rim = o.squash > 0 && tex > 0 ? blur(cov, Math.max(1, 2.2 * S)) : null;
    const streak = kind === 'riso' ? Paper.noise(seed + k * 13 + 6, 160 * S) : null;   // the drum's banding runs across the sheet
    for (let y = 0, i = 0; y < H; y++) for (let x = 0; x < W; x++, i++) {
      const c = cov[i];
      if (c <= 0.003) continue;
      let d = c * o.opacity;
      if (tex > 0) {
        // the roller lays the ink on in streaks along the roll, so the mottle is stretched along x
        const m = 0.6 * mot1(x * 0.5, y) + 0.4 * mot2(x * 0.3, y) - 0.5;
        d *= 1 - tex * o.mottle * clamp(0.5 - m, 0, 1) * 1.6;
        // the pits of the paper take ink only under a heavy load
        const reach = smooth(0.28, 0.6, 0.5 + (h[i] - 0.5) * 1.5 + m * 0.5 + (o.load - 0.5) * 1.2);
        d *= 1 - tex * (1 - reach) * 0.65;
        if (o.pinholes > 0) d *= 1 - tex * o.pinholes * smooth(0.86, 0.94, pin(x, y));
        if (rim) d *= 1 + tex * o.squash * 1.5 * clamp(c - rim[i], 0, 0.5);
        if (streak) d *= 1 - tex * 0.08 * streak(x * 0.04, y * 0.004);
      }
      d = clamp(d, 0, 1);
      for (let j = 0; j < 3; j++) buf[4 * i + j] *= 1 - d * (1 - col[j] / 255);
    }
  }

  return { ink, mask, fields, init, inks: INKS };
})();
