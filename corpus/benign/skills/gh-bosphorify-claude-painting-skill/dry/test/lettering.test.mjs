import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { fileURLToPath } from 'node:url';
import { openPage } from '../testing/harness.mjs';

// Lettering.paths and width are plain JS: load the file as the page does, without a browser
const src = readFileSync(fileURLToPath(new URL('../lettering.js', import.meta.url)), 'utf8');
const Lettering = runInNewContext(src + '\n;Lettering', {});
const plain = v => JSON.parse(JSON.stringify(v));
const SIZE = 100; // cap height; y is down, the baseline is at 0
const ink = (str, opts = {}) => plain(Lettering.paths(str, 0, 0, { size: SIZE, jitter: 0, ...opts })).flatMap(s => s.pts);
const box = (str, opts) => {
  const pts = ink(str, opts), xs = pts.map(p => p[0]), ys = pts.map(p => -p[1]); // ys: height above the baseline
  return { x0: Math.min(...xs), x1: Math.max(...xs), bottom: Math.min(...ys) / SIZE, top: Math.max(...ys) / SIZE };
};

test('every character the brief lists is drawn, each as a glyph of its own', () => {
  const chars = [...new Set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?\'"-–—/()[]&+=%#@*°·_<>çğıiöşüÇĞİÖŞÜ')];
  const shapes = new Set();
  for (const ch of chars) {
    const strokes = plain(Lettering.paths(ch, 0, 0, { size: SIZE, jitter: 0 }));
    assert.ok(strokes.length >= 1 && strokes.every(s => s.pts.length >= 2), `${ch} has no drawable stroke`);
    shapes.add(JSON.stringify(strokes));
  }
  assert.equal(shapes.size, chars.length, 'two characters share one drawing');
  assert.equal(Lettering.paths(' ', 0, 0).length, 0, 'a space draws nothing');
});

test('letters have the right proportions: capitals to the cap line, lowercase to the x-height, descenders below', () => {
  const tall = [...'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'], small = [...'acemnorsuvwxz'], rise = [...'bdfhkl'], drop = [...'gjpqy'];
  for (const ch of tall) { const b = box(ch); assert.ok(b.top > 0.95 && b.top < 1.05, `${ch} reaches ${b.top.toFixed(2)} of the cap height`); assert.ok(Math.abs(b.bottom) < 0.12, `${ch} ends at ${b.bottom.toFixed(2)}, not on the baseline`); }
  for (const ch of small) { const b = box(ch); assert.ok(b.top > 0.6 && b.top < 0.7, `${ch} reaches ${b.top.toFixed(2)}, the x-height is about 0.64`); assert.ok(Math.abs(b.bottom) < 0.06, `${ch} ends at ${b.bottom.toFixed(2)}, not on the baseline`); }
  for (const ch of rise) assert.ok(box(ch).top > 0.93, `${ch} has an ascender`);
  for (const ch of drop) assert.ok(box(ch).bottom < -0.3, `${ch} has a descender`);
  assert.ok(box('t').top > 0.8 && box('t').top < 0.93, 't is a short ascender');
});

test('the Turkish letters differ from their plain forms in the right place', () => {
  const t = c => box(c);
  assert.ok(t('i').top > 0.8 && t('ı').top < 0.7, 'i has a dot and ı has none');
  assert.ok(t('İ').top > 1.15 && t('I').top < 1.05, 'İ has a dot above the capital and I has none');
  for (const [turkish, plain] of [['ç', 'c'], ['ş', 's'], ['Ç', 'C'], ['Ş', 'S']]) assert.ok(t(turkish).bottom < -0.1 && t(plain).bottom > -0.06, `${turkish} has a cedilla under the baseline`);
  assert.ok(t('ğ').top > 0.75 && t('g').top < 0.7, 'ğ has a breve over the x-height');
  assert.ok(t('Ğ').top > 1.15 && t('G').top < 1.05, 'Ğ has a breve over the capital');
  for (const [turkish, plain] of [['ö', 'o'], ['ü', 'u']]) assert.ok(t(turkish).top > 0.8 && t(plain).top < 0.7, `${turkish} has two dots`);
  for (const [turkish, plain] of [['Ö', 'O'], ['Ü', 'U']]) assert.ok(t(turkish).top > 1.15 && t(plain).top < 1.05, `${turkish} has two dots`);
});

test('size, spacing, slant, angle and align place the text', () => {
  const w = (s, o) => Lettering.width(s, { size: 24, ...o });
  assert.ok(Math.abs(Lettering.width('Kadıköy', { size: 48 }) - 2 * Lettering.width('Kadıköy', { size: 24 })) < 1e-9, 'width scales with size');
  assert.ok(Math.abs(w('AB', { spacing: 0.5 }) - w('AB') - 12) < 1e-9, 'spacing adds spacing x size between two letters');
  // a slanted I leans right by tan(slant) x its height
  const lean = (() => { const p = ink('I', { slant: 20 }); return (p.find(q => q[1] === Math.min(...p.map(r => r[1])))[0] - p.find(q => q[1] === Math.max(...p.map(r => r[1])))[0]) / SIZE; })();
  assert.ok(Math.abs(lean - Math.tan(20 * Math.PI / 180)) < 0.02, `an I slanted 20 degrees leans ${lean.toFixed(3)}`);
  // angle is counter-clockwise on screen: 90 degrees sets the text running upwards from the anchor
  const up = plain(Lettering.paths('HH', 500, 500, { size: 40, jitter: 0, angle: 90 })).flatMap(s => s.pts);
  assert.ok(Math.max(...up.map(p => Math.abs(p[0] - 500))) < 45 && Math.min(...up.map(p => p[1])) < 500 - 50, 'the text runs up the page');
  // align: center puts the middle of the text at x, right its end
  const at = align => { const pts = plain(Lettering.paths('HHH', 1000, 0, { size: 40, jitter: 0, align })).flatMap(s => s.pts), xs = pts.map(p => p[0]); return [Math.min(...xs), Math.max(...xs)]; };
  const W = Lettering.width('HHH', { size: 40 });
  assert.ok(Math.abs(at('left')[0] - 1000) < 1 && Math.abs(at('center')[0] - (1000 - W / 2)) < 1 && Math.abs(at('right')[0] - (1000 - W)) < 1, 'align moves the start of the text');
  // along: the text follows a path, here a vertical one, so it runs down and stays on the path's line
  const down = plain(Lettering.paths('HH', 0, 0, { size: 20, jitter: 0, along: [[300, 100], [300, 400]] })).flatMap(s => s.pts);
  assert.ok(Math.min(...down.map(p => p[1])) >= 99 && Math.max(...down.map(p => p[1])) > 130 && Math.max(...down.map(p => Math.abs(p[0] - 300))) < 30, 'the text runs down the path');
});

test('the hand is seeded and slight: the same seed gives the same strokes, jitter 0 none at all', () => {
  const s = (o = {}) => plain(Lettering.paths('Kadıköy–Karaköy 06:40', 10, 50, { size: 40, ...o }));
  assert.deepEqual(s({ seed: 3 }), s({ seed: 3 }));
  assert.notDeepEqual(s({ seed: 3 }), s({ seed: 4 }));
  assert.deepEqual(s({ jitter: 0, seed: 3 }), s({ jitter: 0, seed: 4 }));
  const ruled = s({ jitter: 0 }).flatMap(x => x.pts), wild = s({ jitter: 1, seed: 9 }).flatMap(x => x.pts);
  assert.ok(ruled.length > 100, 'the strokes have points');
  assert.notDeepEqual(ruled, wild);
  // a wobble, not a scribble: the jittered strokes have the same number of points and stay within a fraction of the size of the ruled ones
  assert.equal(ruled.length, wild.length);
  assert.ok(Math.max(...wild.map((p, i) => Math.hypot(p[0] - ruled[i][0], p[1] - ruled[i][1]))) < 0.3 * 40, 'jitter 1 stays within 0.3 of the size');
});

// the real brush: the strokes land where paths() says they do
test('Lettering.text draws the planned strokes with the current brush', async () => {
  const p = await openPage({
    body: `<div id="stage"></div><script>
      window.__done = false;
      const W = 700, H = 300;
      function setup() { pixelDensity(1); createCanvas(W, H, WEBGL).parent('stage'); angleMode(DEGREES); brush.scaleBrushes(W / 200); background('#f4efe4'); noLoop(); }
      function draw() {
        translate(-W / 2, -H / 2);
        Lettering.brushes();
        brush.set('fineliner', '#1f1b17', 1.5);
        window.__width = Lettering.text('Kadıköy 06:40', 60, 200, { size: 50, seed: 2 });
        window.__plan = Lettering.paths('Kadıköy 06:40', 60, 200, { size: 50, seed: 2 }).flatMap(s => s.pts);
        window.__done = true;
      }</script>`,
    scripts: ['node_modules/p5/lib/p5.min.js', 'node_modules/p5.brush/dist/p5.brush.js', 'paper.js', 'lettering.js'],
  });
  after(p.close);
  await p.done();
  await p.page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  assert.deepEqual(p.errors, []);
  const { got, plan, width } = await p.page.evaluate(() => {
    const W = 700, H = 300;
    const g = document.createElement('canvas'); g.width = W; g.height = H;
    const c = g.getContext('2d'); c.drawImage(drawingContext.canvas, 0, 0, W, H);
    const px = c.getImageData(0, 0, W, H).data;
    let x0 = W, x1 = 0, y0 = H, y1 = 0, n = 0;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (px[4 * (y * W + x)] < 120) { n++; x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    const plan = window.__plan;
    return { got: { x0, x1, y0, y1, n }, width: window.__width, plan: { x0: Math.min(...plan.map(q => q[0])), x1: Math.max(...plan.map(q => q[0])), y0: Math.min(...plan.map(q => q[1])), y1: Math.max(...plan.map(q => q[1])) } };
  });
  assert.ok(got.n > 500, `${got.n} dark pixels: the word is drawn`);
  for (const k of ['x0', 'x1', 'y0', 'y1']) assert.ok(Math.abs(got[k] - plan[k]) <= 8, `${k}: drawn ${got[k]}, planned ${plan[k].toFixed(0)}`);
  assert.ok(Math.abs((got.x1 - got.x0) - width) < 0.12 * width, `text returns the width in px: ${width.toFixed(0)}, drawn ${got.x1 - got.x0}`);
});
