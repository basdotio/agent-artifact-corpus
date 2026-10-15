// lettering.js: single-stroke lettering, so labels look hand-lettered and not typeset. For sketches built on template.html.
//
// Each letter is a few pen strokes (skeleton lines, in the manner of the Hershey single-stroke fonts: drawn for this kit,
// no third-party font data), laid out, slanted and jittered, then drawn with the CURRENT p5.brush brush: set it first with
// brush.set('pen', '#2b2622', 1) (or HB, cpencil, whiteink ...) and the weight of that brush is the pen's line.
//
//   Lettering.text(str, x, y, opts)    draw str with its baseline starting at (x, y); returns the width in px
//   Lettering.paths(str, x, y, opts)   the same strokes as [[x, y], ...] point lists in px, nothing drawn (masks, plotting)
//   Lettering.width(str, opts)         the width in px
//     opts.size      cap height in px (default 24); lowercase is about 0.64 of it, descenders fall 0.36 below the baseline
//     opts.slant     degrees, positive leans right (default 0)
//     opts.spacing   extra space between letters as a share of size (default 0; 0.25-0.4 for spaced map capitals)
//     opts.jitter    0..1, hand wobble, letter to letter and along each stroke (default 0.35; 0 is ruled)
//     opts.seed      the wobble's seed (default 1): same text and seed, same strokes; draws nothing from p5's random stream
//     opts.angle     degrees counter-clockwise, as in brush.hatch (default 0)
//     opts.align     'left' (default), 'center' or 'right': which part of the text sits at x
//     opts.along     [[x, y], ...] a path to set the text along, from its start (align applies along the path; x, y are ignored)
//   The built-in pen, rotring, HB and cpencil scatter and fade on strokes this short and turn small text to noise. Lettering
//   registers two fine brushes on its first use (Lettering.brushes()): 'fineliner' (an opaque, crisp pen: weight 1-2) and
//   'finepencil' (a pencil with little scatter: weight 0.8-1.8). 'whiteink' does the same in white on dark paper.
//   Characters: A-Z a-z 0-9, . , : ; ! ? ' " - – — / ( ) [ ] & + = % # @ * ° · _ < >, and the Turkish ç ğ ı İ ö ş ü with
//   their capitals. Anything else is skipped as a space.
//   p5.brush drops the strokes that come late in a heavy frame: put a block of lettering in a layer of its own.
const Lettering = (() => {
  // Path language: M x y (start a stroke), L x y, C x1 y1 x2 y2 x y (cubic), A cx cy rx ry a0 a1 (an elliptical arc, degrees
  // counter-clockwise, y up). Units: cap height 14, x-height 9, descender -5, baseline 0. The first number is the advance.
  const G = {
    A: [16, 'M 0 0 L 6.5 14 L 13 0 M 2.4 5 L 10.6 5'],
    B: [15, 'M 0 0 L 0 14 L 6.5 14 C 10.5 14 10.5 7.6 6.5 7.6 L 0 7.6 M 6.5 7.6 C 11.5 7.6 11.5 0 6.5 0 L 0 0'],
    C: [15, 'A 6.8 7 6.8 7 40 320'],
    D: [16, 'M 0 0 L 0 14 L 5 14 C 11 14 13 10 13 7 C 13 4 11 0 5 0 L 0 0'],
    E: [13, 'M 10.5 14 L 0 14 L 0 0 L 10.5 0 M 0 7.2 L 8.5 7.2'],
    F: [12.5, 'M 0 0 L 0 14 L 10.5 14 M 0 7.2 L 8.5 7.2'],
    G: [16, 'A 6.8 7 6.8 7 38 360 L 13.6 7 L 7.4 7'],
    H: [15, 'M 0 0 L 0 14 M 12 0 L 12 14 M 0 7 L 12 7'],
    I: [6, 'M 0 0 L 0 14'],
    J: [12, 'M 9 14 L 9 4 C 9 1 7.5 0 5 0 C 2.4 0 1 1.4 0.4 4'],
    K: [14, 'M 0 0 L 0 14 M 11 14 L 0 5.5 M 3.6 8.6 L 11.4 0'],
    L: [12.5, 'M 0 14 L 0 0 L 10 0'],
    M: [18, 'M 0 0 L 0 14 L 7 4 L 14 14 L 14 0'],
    N: [15, 'M 0 0 L 0 14 L 12 0 L 12 14'],
    O: [17, 'A 6.8 7 6.8 7 90 450'],
    P: [14.5, 'M 0 0 L 0 14 L 6.5 14 C 12.5 14 12.5 6.2 6.5 6.2 L 0 6.2'],
    Q: [17, 'A 6.8 7 6.8 7 90 450 M 8 4 L 13.4 -1.5'],
    R: [15, 'M 0 0 L 0 14 L 6.5 14 C 12.5 14 12.5 6.6 6.5 6.6 L 0 6.6 M 6 6.6 L 12 0'],
    S: [14.5, 'M 11.4 11.6 C 10.4 13.4 8.6 14 6.6 14 C 3.4 14 1.2 12.4 1.2 10.4 C 1.2 8 3.2 7.2 6.6 6.6 C 10 6 12 5.2 12 3.4 C 12 1.2 9.8 0 6.6 0 C 4.4 0 2.4 0.8 1 2.8'],
    T: [14, 'M 0 14 L 12 14 M 6 14 L 6 0'],
    U: [15, 'M 0 14 L 0 5 C 0 1.6 2.6 0 6 0 C 9.4 0 12 1.6 12 5 L 12 14'],
    V: [16, 'M 0 14 L 6.5 0 L 13 14'],
    W: [20, 'M 0 14 L 4 0 L 8.5 11 L 13 0 L 17 14'],
    X: [14.5, 'M 0 14 L 12 0 M 12 14 L 0 0'],
    Y: [14.5, 'M 0 14 L 6 6.6 L 12 14 M 6 6.6 L 6 0'],
    Z: [14.5, 'M 0 14 L 12 14 L 0 0 L 12 0'],
    a: [12.5, 'M 8.8 9 L 8.8 0 M 8.8 4.5 A 4.4 4.5 4.4 4.5 0 360'],
    b: [12.5, 'M 0 14 L 0 0 M 0 4.5 A 4.6 4.5 4.6 4.5 180 540'],
    c: [11, 'A 4.6 4.5 4.6 4.5 40 320'],
    d: [12.5, 'M 9.2 14 L 9.2 0 M 9.2 4.5 A 4.6 4.5 4.6 4.5 0 360'],
    e: [12, 'M 0 4.5 L 9.2 4.5 A 4.6 4.5 4.6 4.5 0 320'],
    f: [9, 'M 8.6 13.4 C 7 14.4 4.6 14.2 4.2 11.6 L 4.2 0 M 0.6 9 L 7.8 9'],
    g: [12.5, 'M 9.2 9 L 9.2 -1.2 C 9.2 -4.6 6.4 -5.2 4.4 -5 C 2.6 -4.8 1.6 -4 1 -3 M 9.2 4.5 A 4.6 4.5 4.6 4.5 0 360'],
    h: [12, 'M 0 14 L 0 0 M 0 5.6 C 0.6 8 2.6 9.2 4.8 9.2 C 7.6 9.2 8.8 7.4 8.8 5 L 8.8 0'],
    i: [5.5, 'M 0 9 L 0 0 A 0 12.6 0.5 0.5 0 360'],
    j: [5, 'M 0 9 L 0 -2.6 C 0 -4.4 -1.2 -5 -2.6 -4.8 A 0 12.6 0.5 0.5 0 360'],
    k: [10.5, 'M 0 14 L 0 0 M 8.4 9 L 0 3.6 M 3.2 5.6 L 8.6 0'],
    l: [5.5, 'M 0 14 L 0 0'],
    m: [17, 'M 0 9 L 0 0 M 0 5.6 C 0.4 8 2 9.2 3.8 9.2 C 6 9.2 7 7.4 7 5 L 7 0 M 7 5.6 C 7.4 8 9 9.2 10.8 9.2 C 13 9.2 14 7.4 14 5 L 14 0'],
    n: [12, 'M 0 9 L 0 0 M 0 5.6 C 0.6 8 2.6 9.2 4.8 9.2 C 7.6 9.2 8.8 7.4 8.8 5 L 8.8 0'],
    o: [12.5, 'A 4.8 4.5 4.8 4.5 90 450'],
    p: [12.5, 'M 0 9 L 0 -5 M 0 4.5 A 4.6 4.5 4.6 4.5 180 540'],
    q: [12.5, 'M 9.2 9 L 9.2 -5 M 9.2 4.5 A 4.6 4.5 4.6 4.5 0 360'],
    r: [9, 'M 0 9 L 0 0 M 0 5.4 C 0.6 8 2.4 9.2 4.4 9.2 C 5.4 9.2 6 9 6.6 8.6'],
    s: [10.5, 'M 8.2 7.6 C 7.4 8.8 6 9.2 4.6 9.2 C 2.4 9.2 1 8.2 1 6.8 C 1 5.2 2.6 4.8 4.6 4.3 C 6.6 3.8 8.2 3.4 8.2 2.2 C 8.2 0.8 6.6 0 4.4 0 C 2.8 0 1.4 0.6 0.6 1.8'],
    t: [8.5, 'M 3.4 12 L 3.4 1.6 C 3.4 0.4 4.2 0 5.6 0.2 M 0.4 9 L 6.8 9'],
    u: [12, 'M 0 9 L 0 3.6 C 0 1.4 1.8 0 4.4 0 C 7 0 8.8 1.4 8.8 3.8 M 8.8 9 L 8.8 0'],
    v: [11.5, 'M 0 9 L 4.4 0 L 8.8 9'],
    w: [15.5, 'M 0 9 L 3 0 L 6.4 7 L 9.8 0 L 12.8 9'],
    x: [11, 'M 0 9 L 8.6 0 M 8.6 9 L 0 0'],
    y: [11.5, 'M 0 9 L 4.4 0 M 8.8 9 L 4.4 0 L 2.6 -3.2 C 1.6 -4.6 0.6 -5 -0.6 -4.8'],
    z: [11, 'M 0 9 L 8.4 9 L 0 0 L 8.6 0'],
    '0': [12.5, 'A 5 7 5 7 90 450'],
    '1': [9, 'M 0 11 L 3.6 14 L 3.6 0'],
    '2': [12.5, 'M 0.4 10.6 C 0.8 13 2.8 14 5 14 C 7.6 14 9.2 12.6 9.2 10.6 C 9.2 8.6 7.6 7.2 5.6 5.4 L 0 0 L 9.6 0'],
    '3': [12.5, 'M 0.6 11.8 C 1.6 13.4 3.2 14 5 14 C 7.6 14 9 12.6 9 10.8 C 9 8.6 7.4 7.4 4.4 7.4 C 7.6 7.4 9.6 6 9.6 3.8 C 9.6 1.4 7.6 0 5 0 C 3 0 1.2 0.8 0.2 2.6'],
    '4': [12.5, 'M 7.6 0 L 7.6 14 L 0 4.4 L 10 4.4'],
    '5': [12.5, 'M 9 14 L 1.8 14 L 0.8 7.6 C 2 8.6 3.4 9 4.8 9 C 7.6 9 9.4 7.4 9.4 4.6 C 9.4 2 7.6 0 4.8 0 C 2.8 0 1.2 0.8 0.2 2.6'],
    '6': [12.5, 'M 8.6 12.4 C 7.6 13.6 6.4 14 5 14 C 2 14 0.2 11 0.2 7.6 C 0.2 3.2 2 0 5 0 C 7.6 0 9.4 2 9.4 4.6 C 9.4 7.2 7.6 9 5 9 C 2.6 9 0.8 7.6 0.2 5.6'],
    '7': [12.5, 'M 0 14 L 9.6 14 L 3.6 0'],
    '8': [12.5, 'A 4.8 10.6 4.2 3.4 270 630 A 4.8 3.8 4.8 3.8 90 450'],
    '9': [12.5, 'M 0.8 1.6 C 1.8 0.4 3 0 4.4 0 C 7.4 0 9.2 3 9.2 6.4 C 9.2 10.8 7.4 14 4.4 14 C 1.8 14 0 12 0 9.4 C 0 6.8 1.8 5 4.4 5 C 6.8 5 8.6 6.4 9.2 8.4'],
    ' ': [7, ''],
    '.': [5, 'A 0 0.6 0.5 0.5 0 360'],
    ',': [5, 'M 0.6 0.4 L -0.6 -3'],
    ':': [5, 'A 0 0.6 0.5 0.5 0 360 A 0 7.6 0.5 0.5 0 360'],
    ';': [5, 'A 0 7.6 0.5 0.5 0 360 M 0.6 0.4 L -0.6 -3'],
    '!': [5, 'M 0 14 L 0 4.6 A 0 0.6 0.5 0.5 0 360'],
    '?': [11, 'M 0.4 11 C 0.6 13 2.4 14 4.4 14 C 6.8 14 8.2 12.6 8.2 10.8 C 8.2 8.8 6.6 8 5 7 C 4.2 6.4 4.2 5.4 4.2 4.4 A 4.2 0.6 0.5 0.5 0 360'],
    "'": [4.5, 'M 0.3 14 L -0.4 10.6'],
    '"': [8, 'M 0.3 14 L -0.4 10.6 M 4 14 L 3.3 10.6'],
    '-': [8, 'M 0 6.4 L 5.4 6.4'],
    '–': [13, 'M 0 6.4 L 10 6.4'],
    '—': [18, 'M 0 6.4 L 15 6.4'],
    '/': [10, 'M 0 -1 L 7.4 14.5'],
    '(': [7, 'M 3.6 15 C 0.4 12 0.4 1.8 3.6 -1'],
    ')': [7, 'M 0 15 C 3.2 12 3.2 1.8 0 -1'],
    '[': [7, 'M 3.4 15 L 0 15 L 0 -1 L 3.4 -1'],
    ']': [7, 'M 0 15 L 3.4 15 L 3.4 -1 L 0 -1'],
    '&': [15, 'M 11 0 L 2.4 9.8 C 0.4 12.2 1.6 14 3.6 14 C 5.6 14 6.6 12.2 6 10.6 C 5.4 9 0.6 6.6 0.6 3.2 C 0.6 1 2.2 0 4 0 C 6.6 0 8.6 2.4 10.6 6'],
    '+': [12, 'M 0 6.4 L 8 6.4 M 4 2.4 L 4 10.4'],
    '=': [12, 'M 0 4.4 L 8 4.4 M 0 8.6 L 8 8.6'],
    '%': [18, 'M 12 14 L 1 0 A 2.6 11.6 2.6 2.4 270 630 A 11.4 2.4 2.6 2.4 90 450'],
    '#': [14, 'M 3.4 0 L 5 14 M 8.4 0 L 10 14 M 0.6 4.6 L 11.6 4.6 M 0.6 9.4 L 11.6 9.4'],
    '@': [20, 'M 14.6 4 C 13.6 1.2 11 0 8.6 0 C 4 0 1.2 3.4 1.2 7.4 C 1.2 11.4 4.2 14 8.6 14 C 13 14 15.6 11 15.6 7.6 C 15.6 4.8 14 3.4 12.6 3.4 C 11.2 3.4 10.6 4.4 10.4 5.4 A 8.4 6.4 2.6 2.6 0 360 M 11 9 L 10.6 3.8'],
    '*': [9, 'M 4 12 L 4 4 M 0.6 10 L 7.4 6 M 0.6 6 L 7.4 10'],
    '°': [8, 'A 2 12 2 2 90 450'],
    '·': [5, 'A 0 6.6 0.5 0.5 0 360'],
    _: [13, 'M 0 -1.6 L 11 -1.6'],
    '<': [11, 'M 8 11 L 0 6.4 L 8 1.8'],
    '>': [11, 'M 0 11 L 8 6.4 L 0 1.8'],
    'ı': [5.5, 'M 0 9 L 0 0'],
  };
  G['’'] = G["'"];
  // Accents are paths around (0, 0); a composed letter is the base letter plus an accent over (or under) its ink, at height y
  const MARKS = {
    cedilla: 'M 0 0 L -0.4 -1.8 C 1.6 -1.6 2 -3 0.8 -3.8',
    breve: 'M -2.6 0.8 C -1.6 -1.2 1.6 -1.2 2.6 0.8',
    diaeresis: 'A -1.9 0 0.5 0.5 0 360 A 1.9 0 0.5 0.5 0 360',
    dot: 'A 0 0 0.5 0.5 0 360',
  };
  const COMPOSE = {
    'ç': ['c', 'cedilla', 0], 'Ç': ['C', 'cedilla', 0], 'ş': ['s', 'cedilla', 0], 'Ş': ['S', 'cedilla', 0],
    'ğ': ['g', 'breve', 12], 'Ğ': ['G', 'breve', 17.5],
    'ö': ['o', 'diaeresis', 12], 'Ö': ['O', 'diaeresis', 17.5], 'ü': ['u', 'diaeresis', 12], 'Ü': ['U', 'diaeresis', 17.5],
    'İ': ['I', 'dot', 17.5],
  };

  // Parse a path into strokes of [x, y] points (curves and arcs sampled)
  function parse(src) {
    const t = src.split(/\s+/).filter(Boolean), strokes = [];
    let cur = null, i = 0;
    const num = () => parseFloat(t[i++]);
    const add = (x, y) => { const p = cur[cur.length - 1]; if (!p || Math.hypot(p[0] - x, p[1] - y) > 1e-6) cur.push([x, y]); };
    while (i < t.length) {
      const c = t[i++];
      if (c === 'M') { cur = []; strokes.push(cur); add(num(), num()); }
      else if (c === 'L') add(num(), num());
      else if (c === 'C') {
        const [x1, y1, x2, y2, x, y] = [num(), num(), num(), num(), num(), num()], [x0, y0] = cur[cur.length - 1];
        for (let k = 1; k <= 8; k++) {
          const u = k / 8, v = 1 - u;
          add(v * v * v * x0 + 3 * v * v * u * x1 + 3 * v * u * u * x2 + u * u * u * x, v * v * v * y0 + 3 * v * v * u * y1 + 3 * v * u * u * y2 + u * u * u * y);
        }
      } else if (c === 'A') {
        const [cx, cy, rx, ry, a0, a1] = [num(), num(), num(), num(), num(), num()], n = Math.max(2, Math.ceil(Math.abs(a1 - a0) / 12));
        const at = k => { const a = (a0 + (a1 - a0) * k / n) * Math.PI / 180; return [cx + rx * Math.cos(a), cy + ry * Math.sin(a)]; };
        // an arc carries on from the stroke's end when it starts there, and is a stroke of its own otherwise
        const last = cur && cur[cur.length - 1], [sx, sy] = at(0);
        if (!last || Math.hypot(last[0] - sx, last[1] - sy) > 0.05) { cur = []; strokes.push(cur); }
        for (let k = 0; k <= n; k++) add(...at(k));
      } else throw new Error(`lettering: bad path command '${c}'`);
    }
    return strokes.filter(st => st.length > 1);
  }

  const glyphs = new Map();
  function glyph(ch) {
    if (glyphs.has(ch)) return glyphs.get(ch);
    let g;
    if (COMPOSE[ch]) {
      const [base, mark, y] = COMPOSE[ch], b = glyph(base), xs = b.strokes.flat().map(p => p[0]);
      const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
      g = { adv: b.adv, strokes: [...b.strokes, ...parse(MARKS[mark]).map(s => s.map(([x, yy]) => [x + cx, yy + y]))] };
    } else if (G[ch]) g = { adv: G[ch][0], strokes: parse(G[ch][1]) };
    else g = glyph(' ');
    glyphs.set(ch, g);
    return g;
  }

  // mulberry32, so the hand never draws from p5's random stream
  const rng = seed => () => {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };

  const UNIT = 14; // cap height in glyph units
  function advances(str, spacing) { return [...str].map(ch => glyph(ch).adv + spacing * UNIT); }

  function width(str, { size = 24, spacing = 0 } = {}) {
    const a = advances(str, spacing);
    return a.length ? (a.reduce((s, v) => s + v, 0) - spacing * UNIT) * size / UNIT : 0;
  }

  // Strokes in px: [{ pts: [[x, y], ...] }]; y is the baseline
  function paths(str, x, y, { size = 24, slant = 0, spacing = 0, jitter = 0.35, seed = 1, angle = 0, align = 'left', along = null } = {}) {
    const R = rng(seed * 7919 + 13), k = size / UNIT, J = jitter, adv = advances(str, spacing);
    const total = (adv.reduce((s, v) => s + v, 0) - spacing * UNIT) * k;
    const shift = align === 'center' ? -total / 2 : align === 'right' ? -total : 0;
    const th = angle * Math.PI / 180, ca = Math.cos(th), sa = Math.sin(th);
    let place;
    if (along) {
      const L = [0];
      for (let i = 1; i < along.length; i++) L.push(L[i - 1] + Math.hypot(along[i][0] - along[i - 1][0], along[i][1] - along[i - 1][1]));
      place = (u, v) => {
        const s = Math.min(Math.max(u, 0), L[L.length - 1]);
        let i = 1;
        while (i < L.length - 1 && L[i] < s) i++;
        const a = along[i - 1], b = along[i], seg = (L[i] - L[i - 1]) || 1, f = (s - L[i - 1]) / seg, tx = (b[0] - a[0]) / seg, ty = (b[1] - a[1]) / seg;
        return [a[0] + (b[0] - a[0]) * f + ty * v, a[1] + (b[1] - a[1]) * f - tx * v];
      };
    } else place = (u, v) => [x + u * ca - v * sa, y - (u * sa + v * ca)];
    const out = [];
    let pen = 0, i = 0;
    for (const ch of str) {
      const g = glyph(ch), gs = 1 + J * 0.06 * (R() - 0.5) * 2, gdy = J * 0.4 * (R() - 0.5) * 2, gdx = J * 0.3 * (R() - 0.5) * 2;
      const rot = J * 2.2 * (R() - 0.5) * 2 * Math.PI / 180, sh = Math.tan((slant + J * 1.5 * (R() - 0.5) * 2) * Math.PI / 180);
      const cxg = g.adv / 2;
      for (const stroke of g.strokes) {
        // long straight runs get extra points so the wobble has something to bend
        const pts = [];
        stroke.forEach((p, n) => {
          if (n) { const q = stroke[n - 1], m = Math.ceil(Math.hypot(p[0] - q[0], p[1] - q[1]) / 2.5); for (let s = 1; s < m; s++) pts.push([q[0] + (p[0] - q[0]) * s / m, q[1] + (p[1] - q[1]) * s / m]); }
          pts.push(p);
        });
        const f1 = 0.9 + R() * 1.4, f2 = 0.9 + R() * 1.4, p1 = R() * 6.283, p2 = R() * 6.283, amp = J * 0.22, pr = 0.9 + J * 0.2 * (R() - 0.5);
        out.push({ pts: pts.map(([px, py], n) => {
          const t = pts.length > 1 ? n / (pts.length - 1) : 0;
          let lx = (px - cxg) * gs, ly = py * gs;
          [lx, ly] = [lx * Math.cos(rot) - ly * Math.sin(rot), lx * Math.sin(rot) + ly * Math.cos(rot)];
          lx += cxg + gdx + ly * sh + amp * Math.sin(6.283 * f1 * t + p1);
          ly += gdy + amp * Math.sin(6.283 * f2 * t + p2);
          const [X, Y] = place(shift + (pen + lx) * k, ly * k);
          return [X, Y, Math.min(1, 0.72 + 1.3 * Math.min(t, 1 - t)) * pr];
        }) });
      }
      pen += adv[i++];
    }
    return out;
  }

  // The two lettering brushes (p5.brush), added once
  function brushes() {
    if (typeof brush === 'undefined' || typeof brush.add !== 'function' || brush.box().includes('fineliner')) return;
    brush.add('fineliner', { type: 'default', weight: 0.2, scatter: 0.04, sharpness: 0.92, grain: 10, opacity: 255, spacing: 0.05, pressure: { curve: [0.25, 0.3], min_max: [1.05, 0.95] }, noise: 0.08 });
    brush.add('finepencil', { type: 'default', weight: 0.22, scatter: 0.1, sharpness: 0.6, grain: 0.9, opacity: 190, spacing: 0.07, pressure: { curve: [0.15, 0.2], min_max: [0.95, 1.05] }, noise: 0.2 });
  }

  // Draw with the current brush: one brush.spline per stroke. Returns the width in px
  function text(str, x, y, opts = {}) {
    if (typeof brush === 'undefined') throw new Error('Lettering.text needs p5.brush; Lettering.paths works without it');
    brushes();
    for (const { pts } of paths(str, x, y, opts)) brush.spline(pts, 0);
    return width(str, opts);
  }

  return { text, paths, width, brushes };
})();
