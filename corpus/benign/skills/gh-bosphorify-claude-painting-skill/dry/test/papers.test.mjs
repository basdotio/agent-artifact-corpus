import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { openPage } from '../testing/harness.mjs';

// paper.js alone, on a bare page: Paper.sheet and the mark functions work on an RGBA buffer, so no p5 is needed
const bare = await openPage({ body: '<script>var PAPER = "#f4efe4";</script>', scripts: ['paper.js'] });
after(bare.close);
const run = (fn, arg) => bare.page.evaluate(fn, arg);

test('every preset keeps its stock colour and has a grain of its own', async () => {
  const rows = await run(() => Object.keys(Paper.presets).map(name => {
    const W = 2048, H = 64, buf = new Uint8ClampedArray(W * H * 4);
    Paper.init(W, H, 3, { preset: name });
    Paper.sheet(buf);
    const mean = [0, 0, 0], lum = [];
    for (let i = 0; i < W * H; i++) {
      for (let c = 0; c < 3; c++) mean[c] += buf[4 * i + c] / (W * H);
      lum.push(buf[4 * i] + buf[4 * i + 1] + buf[4 * i + 2]);
    }
    const m = lum.reduce((a, b) => a + b) / lum.length;
    return { name, color: Paper.presets[name].color, mean, sd: Math.sqrt(lum.reduce((a, b) => a + (b - m) ** 2, 0) / lum.length) / 3 };
  }));
  for (const name of ['blue-black', 'kraft', 'warm-grey', 'cool-grey', 'graph']) assert.ok(rows.some(r => r.name === name), `preset ${name} is part of the API`);
  for (const { name, color, mean, sd } of rows) {
    const want = [1, 3, 5].map(k => parseInt(color.slice(k, k + 2), 16));
    // lift, margin and finish use the flat colour, so the textured sheet must average to it (a printed grid is a few % darker)
    want.forEach((w, c) => assert.ok(Math.abs(mean[c] - w) <= Math.max(2, 0.05 * w), `${name}: channel ${c} averages ${mean[c].toFixed(1)}, stock ${w}`));
    assert.ok(sd > 0.4, `${name}: the sheet is flat (sd ${sd.toFixed(2)})`);
  }
});

test('graph paper prints a fine grid with a stronger line every few squares', async () => {
  const { step, every, minima } = await run(() => {
    const W = 2048, H = 160, buf = new Uint8ClampedArray(W * H * 4), g = Paper.presets.graph.grid;
    Paper.init(W, H, 5, { preset: 'graph' });
    Paper.sheet(buf);
    // the green channel dips where the pale blue-green ink lies: average each column over the rows to see the vertical lines
    const col = Array.from({ length: W }, (_, x) => { let s = 0; for (let y = 0; y < H; y++) s += buf[4 * (y * W + x) + 0]; return s / H; });
    const med = [...col].sort((a, b) => a - b)[W >> 1];
    const minima = [];
    for (let x = 1; x < W - 1; x++) if (col[x] < med - 6 && col[x] <= col[x - 1] && col[x] < col[x + 1]) minima.push({ x, depth: med - col[x] });
    return { step: g.step, every: g.every, minima };
  });
  assert.ok(minima.length > 60, `found ${minima.length} vertical lines`);
  const gaps = minima.slice(1).map((m, i) => m.x - minima[i].x);
  assert.ok(gaps.every(d => Math.abs(d - step) <= 1), `the squares are ${step} px apart, got ${[...new Set(gaps)]}`);
  const cut = (Math.max(...minima.map(m => m.depth)) + Math.min(...minima.map(m => m.depth))) / 2;
  const strong = minima.map((m, i) => [m.depth > cut, i]).filter(([s]) => s).map(([, i]) => i);
  assert.ok(strong.length > 10 && strong.slice(1).every((i, k) => i - strong[k] === every), `a stronger line every ${every}: at ${strong}`);
});

test('the same seed prints the same sheet, another seed a different one', async () => {
  const [a, b, c] = await run(() => [1, 1, 2].map(seed => {
    const W = 256, H = 192, buf = new Uint8ClampedArray(W * H * 4);
    Paper.init(W, H, seed, { preset: 'kraft' });
    Paper.sheet(buf);
    return Array.from(buf);
  }));
  assert.deepEqual(a, b);
  assert.notDeepEqual(a, c);
});

test('lift and margin return to the preset sheet, and to the flat colour without one', async () => {
  const r = await run(() => {
    const W = 320, H = 240, inner = (b, x0, y0, x1, y1) => { const o = []; for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) o.push(b[4 * (y * W + x)], b[4 * (y * W + x) + 1], b[4 * (y * W + x) + 2]); return o; };
    const maxDiff = (p, q) => p.reduce((m, v, i) => Math.max(m, Math.abs(v - q[i])), 0);
    const box = [[40, 40], [280, 40], [280, 200], [40, 200]], whole = [[0, 0], [W, 0], [W, H], [0, H]];
    const plain = { rough: 0, mottle: 0, settle: 0, edge: 0 };
    const out = {};
    for (const preset of ['kraft', null]) {
      Paper.init(W, H, 4, preset ? { preset } : {});
      const buf = new Uint8ClampedArray(W * H * 4);
      if (preset) Paper.sheet(buf); else for (let i = 0; i < W * H; i++) buf.set([244, 239, 228, 255], 4 * i);
      const bare = Uint8ClampedArray.from(buf);
      Paper.shape(buf, box, '#101010', { ...plain, strength: 1.5 });
      const dark = inner(buf, 100, 100, 200, 160);
      Paper.shape(buf, box, '#ffffff', { ...plain, mode: 'lift', strength: 4 });
      const lifted = maxDiff(inner(buf, 100, 100, 200, 160), inner(bare, 100, 100, 200, 160));
      Paper.shape(buf, whole, '#101010', { ...plain, strength: 1.5, soft: 0 });
      Paper.margin(buf, { width: [24, 24, 24, 24], rough: 0 });
      out[preset ?? 'flat'] = { darkened: dark.every(v => v < 100), lifted, margin: maxDiff(inner(buf, 0, 0, 12, 12), inner(bare, 0, 0, 12, 12)) };
    }
    return out;
  });
  for (const [kind, { darkened, lifted, margin }] of Object.entries(r)) {
    assert.ok(darkened, `${kind}: the wash went on`);
    assert.ok(lifted <= 2, `${kind}: lifting left ${lifted} levels of the wash`);
    assert.ok(margin <= 2, `${kind}: the margin is ${margin} levels off the sheet`);
  }
});

test('an unknown preset is refused', async () => {
  await assert.rejects(run(() => Paper.init(64, 64, 1, { preset: 'papyrus' })), /unknown preset 'papyrus'/);
});

// p5 and p5.brush on a dark sheet, through the real pipeline: do the light media read?
const SKETCH = `
  window.__rows = [];
  const W = 640, H = 420, SEED = 3;
  const steps = [
    ['blue-black', 'whiteink', 0, 1.2], ['blue-black', 'whitepencil', 0.8, 1.2], ['blue-black', 'chalk', 0.9, 1.4], ['warm-grey', 'chalk', 0.6, 1.5],
  ];
  let step = 0, phase = 0, before = null;
  function setup() { pixelDensity(1); createCanvas(W, H, WEBGL).parent('stage'); angleMode(DEGREES); brush.scaleBrushes(W / 200); }
  // luminance of the brightest marks on the line, and of the bare paper above it
  function measure(preset, medium) {
    const d = Paper.read(), at = (x, y) => 0.2126 * d[4 * (y * W + x)] + 0.7152 * d[4 * (y * W + x) + 1] + 0.0722 * d[4 * (y * W + x) + 2];
    const line = [], paper = [];
    for (let x = 100; x < 540; x++) { for (let y = 190; y <= 230; y++) line.push(at(x, y)); for (let y = 40; y < 80; y++) paper.push(at(x, y)); }
    line.sort((a, b) => b - a);
    const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
    window.__rows.push({ preset, medium, marks: mean(line.slice(0, 300)), paper: mean(paper) });
  }
  function draw() {
    if (phase === 1) { if (steps[step][2]) Paper.tooth(before, steps[step][2]); measure(steps[step][0], steps[step][1]); step++; phase = 0; }
    if (step === steps.length) { noLoop(); window.__done = true; return; }
    const [preset, medium, , weight] = steps[step];
    Paper.init(W, H, SEED, { preset });
    before = Paper.read();
    translate(-W / 2, -H / 2);
    brush.set(medium, '#ffffff', weight);
    brush.spline([[100, 210], [260, 195], [420, 225], [540, 210]], 0.5);
    phase = 1;
  }
`;

test('white ink, white pencil and chalk read on dark paper; chalk reads on grey', async () => {
  const p = await openPage({
    body: `<div id="stage"></div><script>${SKETCH}</script>`,
    scripts: ['node_modules/p5/lib/p5.min.js', 'node_modules/p5.brush/dist/p5.brush.js', 'paper.js'],
  });
  after(p.close);
  await p.done();
  assert.deepEqual(p.errors, []);
  const rows = await p.page.evaluate(() => window.__rows);
  assert.equal(rows.length, 4);
  for (const { preset, medium, marks, paper } of rows) {
    const need = preset === 'blue-black' ? 90 : 25;
    assert.ok(marks - paper >= need, `${medium} on ${preset}: marks ${marks.toFixed(0)} against paper ${paper.toFixed(0)}`);
  }
});
