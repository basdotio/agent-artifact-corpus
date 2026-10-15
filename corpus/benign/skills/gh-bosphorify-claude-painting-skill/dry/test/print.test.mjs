import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { openPage } from '../testing/harness.mjs';

// print.js works on an RGBA buffer, so a bare page with paper.js is enough (white paper, no p5)
const bare = await openPage({ body: '<script>var PAPER = "#ffffff";</script>', scripts: ['paper.js', 'print.js'] });
after(bare.close);
const run = (fn, arg) => bare.page.evaluate(fn, arg);

// a fresh sheet of white paper: W x H pixels, Paper.init called, and the buffer
const SETUP = `
  const sheet = (W, H, seed = 1) => { Paper.init(W, H, seed, { kind: 'cold' }); const b = new Uint8ClampedArray(W * H * 4); b.fill(255); return b; };
  const at = (b, W, x, y) => [b[4 * (y * W + x)], b[4 * (y * W + x) + 1], b[4 * (y * W + x) + 2]];
`;

test('each ink prints as a flat colour, and overprints multiply', async () => {
  const r = await run(new Function(SETUP + `
    const W = 256, H = 64, buf = sheet(W, H), flat = { texture: 0, rough: 0, opacity: 1 };
    Print.init({ misregister: 0 });
    Print.ink(buf, { ...flat, color: '#c03020', mask: g => g.fillRect(0, 0, 160, H), register: [0, 0, 0] });
    Print.ink(buf, { ...flat, color: '#2060c0', mask: g => g.fillRect(96, 0, 160, H), register: [0, 0, 0] });
    return { red: at(buf, W, 40, 30), overlap: at(buf, W, 128, 30), blue: at(buf, W, 220, 30) };`));
  const near = (got, want, tol = 2) => got.forEach((v, i) => assert.ok(Math.abs(v - want[i]) <= tol, `got ${got}, wanted ${want}`));
  near(r.red, [0xc0, 0x30, 0x20]);
  near(r.blue, [0x20, 0x60, 0xc0]);
  near(r.overlap, [0xc0 * 0x20 / 255, 0x30 * 0x60 / 255, 0x20 * 0xc0 / 255]);
});

test('the ink has texture: mottle, grain and pinholes, and it stays ink', async () => {
  const r = await run(new Function(SETUP + `
    const W = 600, H = 400, buf = sheet(W, H);
    Print.ink(buf, { color: 'black', mask: g => g.fillRect(50, 50, 500, 300) });
    const v = []; let specks = 0;
    for (let y = 100; y < 300; y++) for (let x = 100; x < 500; x++) { const p = buf[4 * (y * W + x)]; v.push(p); if (p > 130) specks++; }
    const m = v.reduce((a, b) => a + b) / v.length;
    return { mean: m, sd: Math.sqrt(v.reduce((a, b) => a + (b - m) ** 2, 0) / v.length), specks: specks / v.length, outside: at(buf, W, 10, 10) };`));
  assert.ok(r.mean < 90, `the block is dark ink (mean ${r.mean.toFixed(0)})`);
  assert.ok(r.sd > 12, `the ink is flat (sd ${r.sd.toFixed(1)})`);
  assert.ok(r.specks > 0.01 && r.specks < 0.35, `paper shows through in ${(r.specks * 100).toFixed(1)}% of the block`);
  assert.deepEqual(r.outside, [255, 255, 255]);
});

test('plates after the first print off register; the first, and an explicit register, do what they say', async () => {
  const r = await run(new Function(SETUP + `
    const W = 2048, H = 64, flat = { texture: 0, rough: 0, opacity: 1, color: 'black', mask: g => g.fillRect(400, 0, 600, H) };
    const centre = b => { let s = 0, n = 0; for (let x = 0; x < W; x++) { const d = 1 - b[4 * (32 * W + x)] / 255; s += d * x; n += d; } return s / n; };
    Print.init({ misregister: 4 });
    const first = sheet(W, H), second = sheet(W, H), shifted = sheet(W, H);
    Print.ink(first, flat);                       // plate 0 of a run
    Print.ink(second, flat);                      // plate 1: off register by itself
    Print.init({ misregister: 4 });
    Print.ink(shifted, { ...flat, register: [6, 0, 0] });
    return { first: centre(first), second: centre(second), shifted: centre(shifted) };`));
  assert.ok(Math.abs(r.first - 699.5) < 0.6, `the first plate sits on its mask (${r.first})`);
  assert.ok(Math.abs(r.shifted - r.first - 6) < 0.6, `register [6, 0] moves the plate 6 px (${r.shifted - r.first})`);
  const moved = Math.abs(r.second - r.first);   // only the x part of a seeded offset of about 4 px shows on a horizontal centre
  assert.ok(moved > 0.01 && moved < 4.3, `the second plate is off by ${moved.toFixed(2)} px in x`);
});

test('gouges run along their direction field', async () => {
  const r = await run(new Function(SETUP + `
    const W = 600, H = 600, out = {};
    const runs = (b, horizontal) => {   // mean length of the runs of paper-coloured pixels inside the block, along x or along y
      let total = 0, n = 0;
      for (let a = 100; a < 500; a++) { let len = 0; for (let c = 100; c < 500; c++) {
        const p = horizontal ? b[4 * (a * W + c)] : b[4 * (c * W + a)];
        if (p > 160) len++; else if (len) { total += len; n++; len = 0; } } }
      return n ? total / n : 0;
    };
    for (const [name, field] of [['horizontal', 0], ['vertical', 90], ['none', null]]) {
      const buf = sheet(W, H);
      Print.ink(buf, { color: 'black', texture: 0, rough: 0, opacity: 1, mask: g => g.fillRect(100, 100, 400, 400), ...(field === null ? {} : { gouge: { field, spacing: 10, length: [60, 100], width: 5 } }) });
      let cut = 0; for (let y = 100; y < 500; y++) for (let x = 100; x < 500; x++) if (buf[4 * (y * W + x)] > 160) cut++;
      out[name] = { alongX: runs(buf, true), alongY: runs(buf, false), cut: cut / 160000 };
    }
    return out;`));
  assert.equal(r.none.cut, 0, 'no gouge, no cuts');
  assert.ok(r.horizontal.cut > 0.03 && r.horizontal.cut < 0.6, `gouges remove ${(r.horizontal.cut * 100).toFixed(0)}% of the ink`);
  assert.ok(r.horizontal.alongX > 3 * r.horizontal.alongY, `horizontal field: cuts run ${r.horizontal.alongX.toFixed(1)} px along x and ${r.horizontal.alongY.toFixed(1)} along y`);
  assert.ok(r.vertical.alongY > 3 * r.vertical.alongX, `vertical field: cuts run ${r.vertical.alongY.toFixed(1)} px along y and ${r.vertical.alongX.toFixed(1)} along x`);
});

test('a halftone prints its tone as dots: none at 0, solid at 1, about half at 0.5', async () => {
  const r = await run(new Function(SETUP + `
    const W = 600, H = 600, out = [];
    for (const tone of [0, 0.5, 1]) {
      const buf = sheet(W, H);
      Print.ink(buf, { kind: 'riso', color: 'teal', texture: 0, rough: 0, opacity: 1, mask: g => g.fillRect(100, 100, 400, 400), halftone: { tone: () => tone, cell: 12, angle: 45 } });
      let ink = 0; for (let y = 100; y < 500; y++) for (let x = 100; x < 500; x++) ink += 1 - buf[4 * (y * W + x)] / 255 > 0.5 ? 1 : 0;
      out.push(ink / 160000);
    }
    return out;`));
  assert.ok(r[0] < 0.01, `tone 0 prints ${r[0]}`);
  assert.ok(r[1] > 0.38 && r[1] < 0.62, `tone 0.5 covers ${r[1].toFixed(2)} of the area`);
  assert.ok(r[2] > 0.98, `tone 1 covers ${r[2].toFixed(2)}`);
});

test('a print is seeded: the same run gives the same pixels, another seed another texture', async () => {
  const r = await run(new Function(SETUP + `
    const go = (seed, press) => { const W = 300, H = 200, b = sheet(W, H, seed); Print.init({ seed: press });
      Print.ink(b, { color: 'red', mask: g => g.fillRect(40, 40, 200, 100), gouge: { field: 30, spacing: 12 } }); return Array.from(b); };
    const a = go(1, 1), b = go(1, 1), c = go(2, 1), d = go(1, 2);
    return { same: JSON.stringify(a) === JSON.stringify(b), otherPaper: JSON.stringify(a) !== JSON.stringify(c), otherPress: JSON.stringify(a) !== JSON.stringify(d) };`));
  assert.deepEqual(r, { same: true, otherPaper: true, otherPress: true });
});
