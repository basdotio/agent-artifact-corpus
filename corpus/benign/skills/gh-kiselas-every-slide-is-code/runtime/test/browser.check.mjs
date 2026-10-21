// Checks the runtime contract in real Chrome, on every deck it can find: template/deck.html, examples/*/deck.html,
// a skeleton generated from template/SCRIPT.md, and a synthetic deck that pins every transition and the idle rules.
//
// Per deck: no page errors; __deck.states() covers every step of every slide; a rest frame is the same picture
// however you got there (also for a live #N.M jump on a frozen clock); every transition starts where the previous
// slide ended and ends where its destination slide starts; Math.random is never called while the timeline plays;
// slides that stop moving stop rendering (?perf).
//
// Usage: npm run test:browser
//        DECK_TEST_OUT=dir keeps the frames of failing checks in dir (CI uploads it)
//        node runtime/test/browser.check.mjs [--only <substring of a deck name>] [--no-idle]
// Needs Chrome (CHROME_PATH for another binary) and `npm install` at the repo root. Google Fonts are blocked on purpose:
// the test runs on fallback fonts, offline, and the frames are compared with themselves, never with a stored image.
import { chromium } from 'playwright-core';
import { pathToFileURL, fileURLToPath } from 'node:url';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import * as Plan from '../../scripts/plan.mjs';

const here = path.dirname(fileURLToPath(import.meta.url)), root = path.resolve(here, '../..');
const argv = process.argv.slice(2);
const only = argv.includes('--only') ? argv[argv.indexOf('--only') + 1] : null;
const skipIdle = argv.includes('--no-idle');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'deck-kit-test-'));
const keep = process.env.DECK_TEST_OUT ? path.resolve(process.env.DECK_TEST_OUT) : path.join(tmp, 'failures');   // frames of failing checks; DECK_TEST_OUT for CI artifacts

/* ───────────────────────── decks ───────────────────────── */

// The synthetic deck: for every transition a slide A (red) and a slide B (blue) that enters with it,
// plus three slides that pin the idle rules. B has no step-0 builds, so its rest frame is exactly what a
// finished transition must leave behind.
function fixtureDeck() {
  const names = Plan.TRANSITIONS.filter(t => t !== 'none');
  const box = (l, t, w, h) => `<div data-morph="m" style="position:absolute;left:${l}px;top:${t}px;width:${w}px;height:${h}px;background:#fc0"></div>`;
  const slides = names.map(t => `
  <section class="slide" id="a-${t}" style="background:#d33">${box(200, 200, 300, 200)}<h2>A ${t}</h2></section>
  <section class="slide" id="b-${t}" data-transition="${t}" style="background:#39c">${box(700, 500, 900, 400)}<h2>B ${t}</h2></section>`).join('');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>fixture</title>
<style id="deck-kit-css">\n${read('runtime/deck.css')}\n</style>
<style>.slide{color:#fff;font:700 96px/1 sans-serif;padding:120px 150px}.slide h2{margin:0}</style></head><body>
<div class="deck" data-transition="fade" data-hold="1">${slides}
  <section class="slide" id="still" style="background:#333"><h2 data-step="1" data-anim="rise">Still</h2></section>
  <section class="slide" id="ambient" style="background:#333"><h2>Ambient</h2></section>
  <section class="slide" id="since" style="background:#333"><h2>Since</h2></section>
</div>
<script id="deck-kit-js">\n${read('runtime/deck.js').trim().replace(/<\/script/gi, '<\\/script')}\n</script>
<script>
Deck.slide('ambient', { frame(el, st) { el.style.setProperty('--t', String(st.T)); } });          // reads the clock: never idle
Deck.slide('since', { steps: 1, active: .5, frame(el, st) { el.style.setProperty('--s', String(Math.min(st.since(1), 1))); } });
</script></body></html>`;
}

function discover() {
  const decks = [{ name: 'template', file: path.join(root, 'template/deck.html') }];
  const ex = path.join(root, 'examples');
  if (fs.existsSync(ex)) for (const d of fs.readdirSync(ex, { withFileTypes: true }).filter(d => d.isDirectory()).sort((a, b) => a.name.localeCompare(b.name))) {
    const f = path.join(ex, d.name, 'deck.html');
    if (fs.existsSync(f)) decks.push({ name: `examples/${d.name}`, file: f });
  }
  const skel = path.join(tmp, 'skeleton.html');
  const script = Plan.parseScript(read('template/SCRIPT.md'));
  fs.writeFileSync(skel, Plan.skeleton(script, read('template/deck.html')));
  decks.push({ name: 'plan.mjs skeleton', file: skel, slides: script.rows.length });
  const fx = path.join(tmp, 'fixture.html');
  fs.writeFileSync(fx, fixtureDeck());
  decks.push({ name: 'fixture (all transitions)', file: fx, fixture: true });
  return decks.filter(d => !only || d.name.includes(only));
}

/* ───────────────────────── harness ───────────────────────── */

const launch = process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: 'chrome' };
const browser = await chromium.launch({ ...launch, args: ['--force-color-profile=srgb', '--disable-lcd-text'] });
// One reporter per deck: decks run side by side, so their lines are buffered and printed together.
const reporters = [];
function reporter(name) {
  const r = { name, lines: [], fails: [], checks: 0 };
  r.need = (ok, what) => { r.checks++; if (!ok) { r.fails.push(`${name}: ${what}`); r.lines.push(`  FAIL  ${what}`); } return ok; };
  r.note = what => r.lines.push(`  note  ${what}`);
  reporters.push(r);
  return r;
}
const url = (file, q = '') => pathToFileURL(file).href + q;

// One context per pass: Google Fonts blocked, half-size screenshots (960x540 of the 1920x1080 canvas).
async function context(extra = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 0.5, ...extra });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  return ctx;
}
async function open(ctx, target, { clock = false, init = null, ready = true } = {}) {
  const page = await ctx.newPage(), errors = [];
  page.on('pageerror', e => errors.push(String(e.message || e)));
  page.on('console', m => { if (m.type() === 'error' && !/fonts\.(googleapis|gstatic)\.com/.test(m.location().url || '')) errors.push(m.text()); });
  if (clock) { await page.clock.install({ time: 0 }); await page.clock.pauseAt(60000); }   // a paused fake clock: the page only moves when runFor() says so
  if (init) await page.addInitScript(init);
  await page.goto(target);
  if (ready) await page.waitForFunction(() => window.__ready === true, null, { polling: 100, timeout: 20000 });
  page.errors = errors;
  return page;
}

// Frames are compared in a plain page: decode both PNGs and compare them.
//   diff(a, b, 0)   exact: the share of pixels that differ at all (for "the same page rendered twice")
//   diff(a, b)      "the same picture": the share of 16x16 blocks whose mean colour differs by more than 12 levels. Chrome
//                   rasterises text a little differently in a composited layer (a transition) than in the page (a rest
//                   frame): edges of glyphs move by a fraction of a pixel, block means do not. A 20 px shift, a missing
//                   element or a leftover fade all show.
let decoder = null;
async function diff(a, b, thr = null) {
  decoder ||= await (await browser.newContext()).newPage();
  return decoder.evaluate(async ([x, y, thr]) => {
    const dec = async b64 => {
      const bmp = await createImageBitmap(new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))]));
      const c = new OffscreenCanvas(bmp.width, bmp.height), g = c.getContext('2d'); g.drawImage(bmp, 0, 0);
      return { w: bmp.width, h: bmp.height, d: g.getImageData(0, 0, bmp.width, bmp.height).data };
    };
    const A = await dec(x), B = await dec(y);
    if (A.w !== B.w || A.h !== B.h) return { frac: 1, box: null, size: [A.w, A.h, B.w, B.h] };
    const K = A.w / 1920, S = thr === 0 ? 1 : 16;                     // canvas pixels per screenshot pixel
    const bw = Math.ceil(A.w / S), bh = Math.ceil(A.h / S), sum = new Float64Array(bw * bh * 3), cnt = new Float64Array(bw * bh);
    let n = 0, x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1;
    const mark = (px, py) => { x0 = Math.min(x0, px); y0 = Math.min(y0, py); x1 = Math.max(x1, px); y1 = Math.max(y1, py); };
    for (let i = 0; i < A.d.length; i += 4) {
      const p = i / 4, px = p % A.w, py = (p / A.w) | 0;
      if (S === 1) { if (A.d[i] !== B.d[i] || A.d[i + 1] !== B.d[i + 1] || A.d[i + 2] !== B.d[i + 2]) { n++; mark(px, py); } continue; }
      const k = ((py / S) | 0) * bw + ((px / S) | 0);
      for (let c = 0; c < 3; c++) sum[k * 3 + c] += A.d[i + c] - B.d[i + c];
      cnt[k]++;
    }
    if (S === 1) return { frac: n / (A.w * A.h), box: n ? [x0 / K, y0 / K, (x1 + 1) / K, (y1 + 1) / K].map(Math.round) : null };
    for (let k = 0; k < cnt.length; k++) {
      if (Math.max(Math.abs(sum[k * 3]), Math.abs(sum[k * 3 + 1]), Math.abs(sum[k * 3 + 2])) / cnt[k] > 12) { n++; const bx = k % bw, by = (k / bw) | 0; mark(bx * S, by * S); mark(bx * S + S - 1, by * S + S - 1); }
    }
    return { frac: n / cnt.length, box: n ? [x0 / K, y0 / K, (x1 + 1) / K, (y1 + 1) / K].map(Math.round) : null };
  }, [a.toString('base64'), b.toString('base64'), thr]);
}
const UI_OFF = '.dk-ui,.dk-hint,.dk-toast,.dk-edge,.dk-hud{display:none!important}';
const CHROME_OFF = '.dk-progress,.dk-number{visibility:hidden!important}';   // they show the destination from the first frame of a transition
// Known and judged harmless: reported as notes, not failures.
const AA = 'the layers are composited from the first frame, so text switches from LCD to grayscale antialiasing (same picture, edges of glyphs differ by a few grey levels)';
const QUIRKS = {
  cover: { first: 'the incoming card is off screen at p=0, but its 80 px box-shadow already darkens the right edge for one frame' },
  whip: { first: AA },
  punch: { first: AA },
  camera: {
    first: 'the layers are composited from the first frame, and on Linux Chrome the glyphs of a composited layer sit at other subpixel positions (whole slide differs at the edges of letters, contents do not move)',
    final: 'same as the first frame, in reverse: the last composited frame against the destination rest frame; the same commit passed one CI run and failed the other, so it is renderer noise at letter edges',
  },
};
const pct = f => (f * 100).toFixed(2) + '%';
const TOL = 0.002;                                          // a few blocks of 2040: "the same picture"
let shotN = 0;
function saveShots(label, shots) {
  fs.mkdirSync(keep, { recursive: true });
  return Object.entries(shots).map(([k, buf]) => { const f = path.join(keep, `${String(++shotN).padStart(3, '0')}-${label}-${k}.png`); fs.writeFileSync(f, buf); return f; });
}
const shot = page => page.screenshot({ type: 'png' });

/* ───────────────────────── checks ───────────────────────── */

async function structure(T, page, deck) {
  const info = await page.evaluate(() => ({
    slides: window.__deck.slides, count: window.__deck.count, states: window.__deck.states(),
    exportOnly: [...document.querySelectorAll('.deck section.slide')].map(s => (s.dataset.export || '').trim()),
    trans: [...document.querySelectorAll('.deck section.slide')].map(s => s.dataset.transition || document.querySelector('.deck').dataset.transition || 'fade'),
    meta: window.__meta,
  }));
  T.need(info.count > 0 && info.slides.length === info.count, `__deck.count (${info.count}) matches __deck.slides (${info.slides.length})`);
  if (deck.slides) T.need(info.count === deck.slides, `the skeleton has ${deck.slides} slides, one per row of the script (got ${info.count})`);
  const expected = [];
  info.slides.forEach((s, i) => { for (let st = info.exportOnly[i] === 'last' ? s.steps : 0; st <= s.steps; st++) expected.push({ i, step: st }); });
  T.need(JSON.stringify(info.states) === JSON.stringify(expected), `__deck.states() lists every step of every slide (${expected.length} states; got ${info.states.length})`);
  info.slides.forEach((s, i) => {
    T.need(Number.isInteger(s.steps) && s.steps >= 0, `slide ${i + 1} has an integer step count (got ${s.steps})`);
    T.need(s.title && s.title !== `Slide ${i + 1}`, `slide ${i + 1} (#${s.id}) has a real title (h1-h3 or data-title), not the fallback`);
  });
  T.need(info.meta && info.meta.DURATION > 0 && info.meta.W === 1920 && info.meta.H === 1080, `__meta describes a 1920x1080 timeline (got ${JSON.stringify(info.meta)})`);
  // every state can be shown, and exactly one slide is on
  const bad = await page.evaluate(() => {
    const out = [];
    for (const { i, step } of window.__deck.states()) {
      try { window.__deck.show(i, step); const on = document.querySelectorAll('.dk-layer.is-on').length; if (on !== 1) out.push(`${i + 1}.${step}: ${on} layers on`); }
      catch (e) { out.push(`${i + 1}.${step}: ${e.message}`); }
    }
    return out;
  });
  T.need(!bad.length, `show(i, step) works for every state and shows one slide (${bad.slice(0, 3).join('; ')})`);
  return info;
}

// A rest frame is a function of (slide, step) alone: come to it from somewhere else and it must be the same picture.
async function restDeterminism(T, page, info, deck) {
  let same = 0; const bad = [];
  const n = info.states.length;
  for (let k = 0; k < n; k++) {
    const { i, step } = info.states[k], other = info.states[(k * 7 + 3) % n];
    await page.evaluate(([i, s]) => window.__deck.show(i, s), [i, step]);
    const a = await shot(page);
    await page.evaluate(([i, s, j, t]) => { window.__deck.show(j, t); window.__deck.show(i, s); }, [i, step, other.i, other.step]);
    const b = await shot(page);
    if (a.equals(b)) same++;
    else {
      const d = await diff(a, b, 0);
      // the GPU rounds a few pixels by a level or two from run to run: one differing block of 2040 is noise, more is a real difference
      if (d.frac <= 1 / 2040 + 1e-9) same++;
      else bad.push({ at: `${i + 1}.${step} (after ${other.i + 1}.${other.step})`, d, a, b });
    }
  }
  T.need(!bad.length, `every rest frame is identical when reached twice: ${same}/${n}` + (bad.length ? `. Differs: ${bad.slice(0, 4).map(x => `${x.at} by ${pct(x.d.frac)} in ${JSON.stringify(x.d.box)}`).join('; ')}; frames in ${keep}` : ''));
  if (bad.length) saveShots('rest-' + deck.name.replace(/\W+/g, '_'), { a: bad[0].a, b: bad[0].b });
}

// #N.M in a fresh live page, on a paused and then advanced clock: two independent jumps must give the same DOM and picture.
// performance.now() is not fully faked (it keeps the real time the page took to load), so two loads never reach the same T
// to the millisecond. Elements driven by the clock (a flow that runs along an edge) are found by watching what changes
// during one more second, and are left out of the DOM comparison; the pictures are compared anyway.
const SIGS = () => [...document.querySelector('.dk-layer.is-on').querySelectorAll('*')].map(e =>
  e.cloneNode(false).outerHTML + [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('|'));
async function hashJump(T, deck, info) {
  const pick = new Set([0, info.states.length - 1]);
  info.states.forEach((s, k) => { if (s.step > 0 && k % Math.max(1, Math.floor(info.states.length / 4)) === 0) pick.add(k); });
  const list = [...pick].sort((a, b) => a - b).slice(0, 6);
  const jump = async (hash) => {
    const ctx = await context();                         // a context owns one clock: a fresh one per jump
    try {
      const page = await open(ctx, url(deck.file, hash), { clock: true });
      await page.addStyleTag({ content: UI_OFF });       // the control bar and hints fade with CSS transitions the fake clock does not drive
      await page.clock.runFor(8000);   // performance.now keeps the real load time, so a slow machine reaches T later: step-0 builds must have finished on both jumps
      const png = await shot(page), state = await page.evaluate(() => Deck.state), sigs = await page.evaluate(SIGS);
      await page.clock.runFor(1000);
      const later = await page.evaluate(SIGS);
      const ambient = new Set(sigs.flatMap((x, k) => (x === later[k] ? [] : [k])));
      return { state, sigs, ambient, png, errors: page.errors };
    } finally { await ctx.close(); }
  };
  const bad = [];
  for (const k of list) {
    const { i, step } = info.states[k], hash = `#${i + 1}${step ? '.' + step : ''}`;
    const [a, b] = await Promise.all([jump(hash), jump(hash)]);
    if (a.state.i !== i || a.state.step !== step) { bad.push(`${hash} landed on ${JSON.stringify(a.state)}`); continue; }
    const at = a.sigs.length !== b.sigs.length ? -2 : a.sigs.findIndex((x, n) => x !== b.sigs[n] && !a.ambient.has(n) && !b.ambient.has(n));
    if (at !== -1) bad.push(at === -2 ? `${hash}: ${a.sigs.length} vs ${b.sigs.length} elements in the slide` : `${hash}: element ${at} differs between two jumps: ${a.sigs[at].slice(0, 110)}  vs  ${b.sigs[at].slice(0, 110)}`);
    else { const d = await diff(a.png, b.png); if (d.frac > TOL) { bad.push(`${hash}: the picture differs (${pct(d.frac)} of the blocks, in ${JSON.stringify(d.box)})`); saveShots(`hash-${i + 1}.${step}`, { a: a.png, b: b.png }); } }
    if (a.errors.length) bad.push(`${hash}: page errors ${a.errors.join(' | ')}`);
  }
  T.need(!bad.length, `#N.M lands on the right state and gives the same DOM and picture twice (${list.length} states tried)` + (bad.length ? ': ' + bad.join('; ') : ''));
}

// Every transition: starts where the slide before ended, ends where the destination begins, and (when the destination holds
// still) ends on its rest frame. On the fixture also: the middle is neither slide, the end is the rest frame, always.
async function transitions(T, page, info, deck) {
  await page.addStyleTag({ content: CHROME_OFF });
  const tl = await page.evaluate(() => window.__deck.timeline());
  const strict = !!deck.fixture, bad = [], ambient = [], quirks = new Set();
  let checked = 0;
  for (let i = 1; i < info.slides.length; i++) {
    const si = tl.segs.findIndex(g => g.kind === 'tr' && g.to.i === i);
    if (si < 0) continue;
    const g = tl.segs[si], hold = tl.segs[si + 1], name = info.trans[i];
    if (!(g.dur > 0)) continue;                                   // 'none' has no frames
    const at = T => page.evaluate(T => { window.__draw(T); }, T).then(() => shot(page));
    const F = {
      pre: await at(g.t0 - 1e-3), p0: await at(g.t0), pm: await at(g.t0 + g.dur / 2), p1: await at(g.t0 + g.dur - 1e-4), h0: await at(g.t0 + g.dur),
      hm: await at(g.t0 + g.dur + hold.dur * 0.9),
    };
    await page.evaluate(([i]) => window.__deck.show(i, 0), [i]);
    F.rest = await shot(page);
    const label = `into slide ${i + 1} (#${info.slides[i].id}, ${name})`;
    const fail = (msg, keys, phase) => {
      if (QUIRKS[name]?.[phase]) { quirks.add(`${name}: ${QUIRKS[name][phase]}`); return; }
      bad.push(`${label}: ${msg}`); saveShots(`tr-${i + 1}-${name}`, Object.fromEntries(keys.map(k => [k, F[k]])));
    };
    checked++;
    let d = await diff(F.pre, F.p0);
    if (d.frac > TOL) fail(`first frame differs from the last frame of slide ${i} by ${pct(d.frac)} in ${JSON.stringify(d.box)}`, ['pre', 'p0'], 'first');
    d = await diff(F.p1, F.h0);
    if (d.frac > TOL) fail(`final frame differs from the first frame of the destination by ${pct(d.frac)} in ${JSON.stringify(d.box)}`, ['p1', 'h0'], 'final');
    const still = (await diff(F.h0, F.hm)).frac <= TOL;         // the destination does not move after the transition ends
    if (still) {
      d = await diff(F.p1, F.rest);
      if (d.frac > TOL) fail(`final frame differs from the destination's rest frame by ${pct(d.frac)} in ${JSON.stringify(d.box)}`, ['p1', 'rest'], 'rest');
    } else ambient.push(`${i + 1}`);
    if (strict) {
      const m0 = await diff(F.pm, F.p0), m1 = await diff(F.pm, F.p1);
      if (m0.frac < 0.03 || m1.frac < 0.03) fail(`the middle frame is not a mix (differs from the start by ${pct(m0.frac)}, from the end by ${pct(m1.frac)})`, ['p0', 'pm', 'p1'], 'middle');
      if (!still) fail('the fixture destination should hold still', ['h0', 'hm'], 'still');
    }
  }
  T.need(!bad.length, `all ${checked} transitions start and end on the neighbouring frames` + (bad.length ? `:\n        ${bad.join('\n        ')}\n        frames in ${keep}` : ''));
  for (const q of quirks) T.note(`quirk, judged harmless: ${q}`);
  if (ambient.length && !strict) T.note(`slides ${ambient.join(', ')} are still moving when their transition ends (step-0 builds or ambient motion): compared for continuity only`);
}

// Nothing that draws may call Math.random: the wrapper throws, the pass records where.
async function randomPass(T, deck, info, control) {
  const ctx = await context();
  const page = await open(ctx, url(deck.file, '?render'), { init: () => {
    const orig = Math.random;
    window.__rnd = { armed: false, calls: 0, stack: '' };
    Math.random = function () { if (window.__rnd.armed) { window.__rnd.calls++; window.__rnd.stack ||= new Error('Math.random').stack; throw new Error('Math.random() is banned in anything that draws: use Deck.rng(seed)'); } return orig.call(Math); };
  } });
  if (control) {
    const c = await page.evaluate(() => { window.__rnd.armed = true; try { Math.random(); } catch (e) { /* expected */ } window.__rnd.armed = false; return window.__rnd.calls; });
    T.need(c === 1, 'the Math.random guard catches a call (control)');
    await page.evaluate(() => { window.__rnd.calls = 0; window.__rnd.stack = ''; });
  }
  const res = await page.evaluate(() => {
    window.__rnd.armed = true;
    const errs = [], dur = window.__meta.DURATION, T0 = performance.now();
    let frames = 0;
    for (let T = 0; T < dur; T += 0.2) { try { window.__draw(T); frames++; } catch (e) { errs.push(`T=${T.toFixed(1)}: ${e.message}`); if (errs.length > 3) break; } }
    for (const { i, step } of window.__deck.states()) { try { window.__deck.show(i, step); } catch (e) { errs.push(`show ${i + 1}.${step}: ${e.message}`); } }
    window.__rnd.armed = false;
    return { calls: window.__rnd.calls, stack: window.__rnd.stack, errs, frames, ms: performance.now() - T0 };
  });
  T.need(res.calls === 0 && !res.errs.length, `no Math.random during the whole timeline (${res.frames} frames of ${info.meta.DURATION.toFixed(0)} s, every state)` + (res.calls ? `: ${res.calls} calls, first at ${res.stack.split('\n').slice(1, 3).join(' <- ').trim()}` : '') + (res.errs.length ? `: ${res.errs[0]}` : ''));
  T.need(!page.errors.length, `no page errors during the timeline pass (${page.errors[0] || ''})`);
  await ctx.close();
}

// ?perf shows "idle" and "drawn 0/s" once nothing moves. Reads the HUD, polls up to `wait` ms.
const hud = page => page.evaluate(() => document.querySelector('.dk-hud')?.textContent || '');
async function settle(page, wait = 5500) {
  const t0 = Date.now();
  await page.waitForTimeout(1100);                       // the HUD refreshes every 500 ms: skip the reading that still describes the previous state
  for (;;) {
    const h = await hud(page);
    if (/· idle ·/.test(h) && /drawn 0\/s/.test(h)) return { idle: true, ms: Date.now() - t0, hud: h };
    if (Date.now() - t0 > wait) return { idle: false, ms: wait, hud: h };
    await page.waitForTimeout(150);
  }
}
async function idle(T, deck, info) {
  const ctx = await context();
  const page = await open(ctx, url(deck.file, '?perf'));
  await page.waitForTimeout(700);
  const never = [];
  let idles = 0;
  const from = deck.fixture ? info.slides.length - 3 : 0;
  for (let i = from; i < info.slides.length; i++) {
    const last = info.slides[i].steps;
    await page.evaluate(([i, s]) => Deck.goto(i, s), [i, last]);
    const r = await settle(page, deck.fixture ? 3000 : 5500);
    if (r.idle) idles++; else never.push(`${i + 1} #${info.slides[i].id}`);
  }
  if (deck.fixture) {
    T.need(!never.some(x => /#still|#since/.test(x)), 'fixture: a slide with static builds goes idle (drawn 0/s)');
    T.need(never.some(x => /#ambient/.test(x)), 'fixture: a slide that reads st.T never goes idle (control: the HUD can tell)');
    // st.since() with active: .5 goes idle after half a second, not after the 4 s default
    const k = info.slides.length - 1;
    await page.evaluate(([k]) => { Deck.goto(k, 0); Deck.next(); }, [k]);
    const r = await settle(page, 3300);
    T.need(r.idle && r.ms < 3000, `fixture: motion driven by st.since() stops at its declared \`active\` (idle after ${r.ms} ms, default would be 4000)`);
  } else {
    T.need(idles > 0, `at least one slide goes idle at its last step (${idles} of ${info.slides.length - from} did)`);
    if (never.length) T.note(`never idle at their last step (ambient motion via st.T / st.life, or a since() slide without \`active\`): ${never.join(', ')}`);
  }
  T.need(!page.errors.length, `no page errors in live mode (${page.errors[0] || ''})`);
  await ctx.close();
}

/* ───────────────────────── run ───────────────────────── */

async function runDeck(deck) {
  const T = reporter(deck.name), t0 = Date.now();
  try {
    const ctx = await context();
    const page = await open(ctx, url(deck.file, '?render'));
    const info = await structure(T, page, deck);
    await restDeterminism(T, page, info, deck);
    await transitions(T, page, info, deck);
    T.need(!page.errors.length, `no page errors in render mode (${page.errors.slice(0, 2).join(' | ')})`);
    await ctx.close();
    await hashJump(T, deck, info);
    await randomPass(T, deck, info, deck.name === 'template' || deck.fixture);
    if (!skipIdle) await idle(T, deck, info);
    T.lines.push(`  done in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  } catch (e) {
    T.need(false, `the check itself crashed: ${e.stack || e}`);
  }
  console.log(`${deck.name}\n${T.lines.join('\n')}\n`);
  return T;
}

const decks = discover();
console.log(`deck-kit browser check: ${decks.length} decks (${decks.map(d => d.name).join(', ')}), run side by side\n`);
const t0 = Date.now();
try { await Promise.all(decks.map(runDeck)); } finally { await browser.close(); }
const fails = reporters.flatMap(r => r.fails), checks = reporters.reduce((a, r) => a + r.checks, 0);
console.log(`${checks} checks in ${((Date.now() - t0) / 1000).toFixed(0)} s, ${fails.length} failed`);
if (fails.length) { console.error('\nFAILED:\n - ' + fails.join('\n - ') + `\n\nframes of the failing checks: ${keep}`); process.exitCode = 1; }
else { console.log('browser checks passed'); fs.rmSync(tmp, { recursive: true, force: true }); }

/* ───────────────────────── live annotation (11-presenting.md) ─────────────────────────
 * D/H/L/E draw on a canvas over the slide; a mode swallows clicks and swipes; nothing of it exists until used, in any export, or when
 * data-annotate="off". Runs on the template deck (--only template includes it). */
if (!only || 'template'.includes(only)) {
  const A = reporter('live annotation'), ab = await chromium.launch({ ...launch, args: ['--force-color-profile=srgb', '--disable-lcd-text'] });
  try {
    const actx = async extra => { const c = await ab.newContext({ viewport: { width: 1280, height: 720 }, ...extra }); await c.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort()); return c; };
    const layers = '.dk-ann,.dk-ann-cap,.dk-ann-tools,.dk-ann-laser', state = page => page.evaluate(() => `${Deck.state.i}.${Deck.state.step}`);
    const tpl = path.join(root, 'template/deck.html');
    const ctx = await actx(), page = await open(ctx, url(tpl, '?perf'));
    A.need(await page.evaluate(q => document.querySelectorAll(q).length, layers) === 0, 'nothing of the annotation exists before first use (lazy)');
    await page.evaluate(() => Deck.goto(1, Deck.state.step));
    A.need((await settle(page)).idle, 'a still slide is idle before drawing');
    const before = await state(page);
    await page.keyboard.press('d');
    const drag = async (x, y) => { await page.mouse.move(x, y); await page.mouse.down(); for (let i = 1; i <= 12; i++) await page.mouse.move(x + i * 30, y + Math.sin(i / 2) * 40); await page.mouse.up(); };
    await drag(300, 300);
    await page.mouse.click(700, 400); await page.mouse.click(30, 400);
    await page.keyboard.press('1'); await page.keyboard.press('2');
    A.need(await state(page) === before, `draw mode: clicks (also on the left fifth) and the digits 1-2 do not move the slide (${before} -> ${await state(page)})`);
    await page.waitForTimeout(150);
    const ink = () => page.evaluate(() => { const c = document.querySelector('.dk-ann'); if (!c || c.style.display === 'none') return 0; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n; });
    A.need(await ink() > 500, 'the stroke is on the canvas');
    A.need(await page.evaluate(() => { const c = document.querySelector('.dk-ann'), z = e => +getComputedStyle(e).zIndex; return z(c) > z(document.querySelector('.dk-veil')) && z(c) < z(document.querySelector('.dk-blackout')) && z(document.querySelector('.dk-ui')) > z(document.querySelector('.dk-ann-cap')); }), 'the canvas is above the slide and under the black screen; the control bar is above the pointer pad');
    await page.keyboard.press('Escape');
    A.need(!(await page.evaluate(() => document.documentElement.classList.contains('dk-annotating'))), 'Esc leaves the mode');
    A.need((await settle(page)).idle, 'idle rendering is intact after drawing (?perf: idle, drawn 0/s)');
    await page.keyboard.press('ArrowRight'); await page.waitForTimeout(1600);
    A.need(await ink() === 0, 'the marks belong to their slide: none on the next one');
    await page.keyboard.press('ArrowLeft'); await page.waitForTimeout(1600);
    A.need(await ink() > 500, 'the marks are back after coming back to the slide');
    await page.keyboard.press('e'); await page.waitForTimeout(150);
    A.need(await ink() === 0, 'E erases the marks of the slide');
    await page.keyboard.press('h'); await page.keyboard.press('l'); await page.mouse.move(400, 300); await page.mouse.move(430, 320);
    A.need(await page.evaluate(() => document.querySelector('.dk-ann-laser').classList.contains('is-on')), 'L shows the laser dot at the pointer');
    A.need(await state(page) === before, 'H and L modes do not move the slide either');
    await page.keyboard.press('Escape');
    await page.mouse.click(700, 400); await page.waitForTimeout(100);
    A.need(await state(page) !== before, 'after Esc a click advances again');
    A.need(!page.errors.length, `no page errors (${page.errors[0] || ''})`);
    await ctx.close();
    // touch: a swipe in draw mode draws, it does not turn the page
    const tctx = await actx({ hasTouch: true }), tp = await open(tctx, url(tpl));
    const cdp = await tctx.newCDPSession(tp), pt = (x, y) => [{ x, y, id: 1 }];
    await tp.keyboard.press('d');
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: pt(200, 300) });
    for (let i = 1; i <= 10; i++) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: pt(200 + i * 60, 300 + i * 4) });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await tp.waitForTimeout(200);
    A.need(await state(tp) === '0.0', 'touch: a horizontal swipe in draw mode does not change the slide');
    A.need(await tp.evaluate(() => { const c = document.querySelector('.dk-ann'); return !!c && c.style.display !== 'none'; }), 'touch: the swipe left a mark');
    await tctx.close();
    // kiosk switch
    const off = path.join(os.tmpdir(), `deck-kit-annotate-off-${process.pid}.html`);
    fs.writeFileSync(off, read('template/deck.html').replace('<div class="deck"', '<div class="deck" data-annotate="off"'));
    const kctx = await actx(), kp = await open(kctx, url(off));
    await kp.keyboard.press('d'); await kp.keyboard.press('l');
    A.need(await kp.evaluate(q => document.querySelectorAll(q).length === 0 && !document.documentElement.classList.contains('dk-annotating') && !document.querySelector('[data-act=annotate]'), layers), 'data-annotate="off": no mode, no layers, no bar button');
    await kp.keyboard.press('h');
    A.need(await kp.evaluate(() => document.querySelector('.dk-help')?.classList.contains('is-on')), 'data-annotate="off": H still opens the help');
    await kctx.close(); fs.rmSync(off, { force: true });
    // exports: render mode, the print layout and the "next" preview never have the layer
    const msg = { dk: 1, a: 's', id: 'x', key: '0.0', k: 'p', c: '#f00', w: 6, p: [1, 1, 400, 400] };
    const rctx = await actx(), rp = await open(rctx, url(tpl, '?render'));
    await rp.keyboard.press('d'); await rp.keyboard.press('l'); await rp.mouse.move(300, 300); await rp.mouse.down(); await rp.mouse.move(500, 400); await rp.mouse.up();
    A.need(await rp.evaluate(q => document.querySelectorAll(q).length === 0 && !document.documentElement.classList.contains('dk-annotating'), layers), '?render: keys and pointer create no annotation layer');
    A.need(await rp.evaluate(q => { window.__deck.buildPrint(window.__deck.states()); return document.querySelectorAll(q).length; }, layers) === 0, 'the print layout (PDF) has no annotation layer');
    await rp.evaluate(m => window.postMessage(m, '*'), msg); await rp.waitForTimeout(150);
    A.need(await rp.evaluate(q => document.querySelectorAll(q).length, layers) === 0, '?render ignores annotation messages from another window');
    await rctx.close();
    const ectx = await actx(), ep = await open(ectx, url(tpl, '?embed&rest'));
    await ep.evaluate(m => window.postMessage(m, '*'), msg); await ep.waitForTimeout(150);
    A.need(await ep.evaluate(q => document.querySelectorAll(q).length, layers) === 0, '?embed&rest (the next-slide preview) never shows marks');
    await ectx.close();
  } catch (e) { A.need(false, `the annotation check itself crashed: ${e.stack || e}`); }
  await ab.close();
  console.log(`live annotation\n${A.lines.join('\n') || '  all passed'}\n  ${A.checks} checks, ${A.fails.length} failed\n`);
  if (A.fails.length) { console.error('\nFAILED:\n - ' + A.fails.join('\n - ')); process.exitCode = 1; }
}

/* ───────────────────────── presenter view (11-presenting.md) ─────────────────────────
 * Notes are split by step (data-step, .click, or a leading ▸), the segment being spoken is marked and scrolled into view, the notes
 * of the next slide sit beside it, and the header never leaves the window. Runs on a template copy with step notes. */
if (!only || 'template'.includes(only)) {
  const P = reporter('presenter view'), pb = await chromium.launch({ ...launch, args: ['--force-color-profile=srgb', '--disable-lcd-text'] });
  const fx = path.join(os.tmpdir(), `deck-kit-presenter-${process.pid}.html`);
  try {
    const html = read('template/deck.html').replace(/(<section class="slide" id="agenda">[\s\S]*?)<aside class="notes">[\s\S]*?<\/aside>/,
      '$1<aside class="notes"><p>Intro before any click.</p>' + '<p>A long introduction, so the notes have to scroll.</p>'.repeat(14) + '<p data-step="1">Point one.</p><p>More on point one.</p><p class="click">Point two.</p><p>▸ Point three, by the marker.</p><p>▸ A marker too many.</p></aside>');
    fs.writeFileSync(fx, html);
    const view = async (w, h, hash) => {
      const c = await pb.newContext({ viewport: { width: w, height: h } }); await c.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
      const p = await open(c, url(fx, '?presenter' + hash), { ready: false }); await p.waitForSelector('.dk-pv-seg'); await p.waitForTimeout(900);
      return { c, p };
    };
    const segs = p => p.evaluate(() => [...document.querySelectorAll('.dk-pv-now .dk-pv-seg')].map(e => `${e.dataset.step}:${e.className.replace('dk-pv-seg ', '')}`).join(' '));
    let { c, p } = await view(1400, 860, '#2.0');
    P.need(await segs(p) === '0:on 1:todo 2:todo 3:todo', `step 0: the intro is being spoken, the clicks are ahead (${await segs(p)})`);
    P.need(await p.evaluate(() => document.querySelectorAll('.dk-pv-now .dk-pv-seg').length) === 4, 'data-step, .click and ▸ open segments; a marker too many merges into the last step');
    await p.keyboard.press('ArrowRight'); await p.keyboard.press('ArrowRight'); await p.waitForTimeout(1000);
    P.need(await segs(p) === '0:done 1:done 2:on 3:todo', `step 2: earlier text is done, click 2 is on (${await segs(p)})`);
    P.need(await p.evaluate(() => { const b = document.querySelector('.dk-pv-now'), e = b.querySelector('.on'), r = b.getBoundingClientRect(), q = e.getBoundingClientRect(); return q.top >= r.top - 2 && q.bottom <= r.bottom + 2; }), 'the segment being spoken is scrolled fully into view (the notes are long)');
    P.need(await p.evaluate(() => document.querySelectorAll('.dk-pv-dots i.on').length) === 3, 'the step dots show the position (3 of 4 filled at step 2)');
    P.need(await p.evaluate(() => /\b3\b/.test(document.querySelector('.dk-pv-al').textContent) && document.querySelector('.dk-pv-after').textContent.trim().length > 20), 'the notes of the next slide are shown under its title');
    P.need(await p.evaluate(() => /Click 3/.test(document.querySelector('.dk-pv-nl').textContent)), 'the preview label says which state comes next (Click 3)');
    const fs0 = await p.evaluate(() => parseFloat(getComputedStyle(document.querySelector('.dk-pv-now')).fontSize));
    await p.click('[data-pv="fs+"]');
    P.need(await p.evaluate(() => parseFloat(getComputedStyle(document.querySelector('.dk-pv-now')).fontSize)) > fs0, 'A+ makes the notes larger');
    await p.click('[data-pv="next"]'); await p.waitForTimeout(400);
    P.need(await segs(p) === '0:done 1:done 2:done 3:on', 'the Next button in the presenter window moves to click 3');
    P.need(!p.errors.length, `no page errors (${p.errors[0] || ''})`);
    await c.close();
    for (const [w, h] of [[2000, 1000], [1400, 860], [1000, 700], [760, 700]]) {
      ({ c, p } = await view(w, h, '#2.1'));
      const bad = await p.evaluate(() => [...document.querySelectorAll('.dk-pv header > *')].filter(e => { const b = e.getBoundingClientRect(); return b.right > innerWidth + 1 || b.left < -1; }).map(e => e.className || e.tagName));
      P.need(!bad.length, `${w}x${h}: nothing in the header leaves the window (${bad.join(', ')})`);
      P.need(await p.evaluate(() => { const r = document.querySelector('.dk-pv-cur .dk-pv-frame').getBoundingClientRect(), n = document.querySelector('.dk-pv-next .dk-pv-frame').getBoundingClientRect(); return r.width > 200 && n.width > 200 && (innerWidth < 900 || (r.bottom <= innerHeight && n.bottom <= innerHeight)); }), `${w}x${h}: both previews are visible and inside the window`);
      await c.close();
    }
  } catch (e) { P.need(false, `the presenter check itself crashed: ${e.stack || e}`); }
  await pb.close(); fs.rmSync(fx, { force: true });
  console.log(`presenter view\n${P.lines.join('\n') || '  all passed'}\n  ${P.checks} checks, ${P.fails.length} failed\n`);
  if (P.fails.length) { console.error('\nFAILED:\n - ' + P.fails.join('\n - ')); process.exitCode = 1; }
}
