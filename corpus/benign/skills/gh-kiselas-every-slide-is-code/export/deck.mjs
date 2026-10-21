#!/usr/bin/env node
// deck-kit exporter. The HTML deck is the source; every other format is a view of it.
// Usage: node deck.mjs <command> <deck.html> [out] [options]   (run with no args for help)
// Chrome: the installed Google Chrome by default; another binary via CHROME_PATH.
//
// Speed: frames are captured with CDP Page.captureScreenshot (optimizeForSpeed) instead of
// page.screenshot, and gif / mp4 / check / png / sheet / strip / still run on a pool of browsers
// (one worker thread + one Chrome each). Chunk boundaries depend only on the frame range, never on
// the number of workers, so any --workers value renders the same frames in the same order.
//
// Narrated video: mp4 --timings t.json --voice v.wav [--loudnorm] [--captions o.srt]; timings --from-notes | --check.
// The timings file is resolved against the natural timeline in every worker, which rewrites the live timeline object.
// Reference analysis: analyze REF... lives in ../scripts/analyze-reference.mjs (pdf.js inside the same Chrome).

import { chromium } from 'playwright-core';
import { spawn, spawnSync } from 'node:child_process';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const HELP = `deck-kit export

  node deck.mjs pdf    deck.html [out.pdf]    vector PDF, one page per slide (final step)
                                              --steps   one page per step   --raster  image pages
  node deck.mjs pptx   deck.html [out.pptx]   static PowerPoint: full-bleed image per page + speaker notes
                                              --steps   one slide per step
  node deck.mjs png    deck.html [dir]        rest frame of every step as PNG   --last  final steps only
                                              --jpg --width 960  small JPEG previews
  node deck.mjs sheet  deck.html [sheet.png]  contact sheet of every rest frame --cols 5
  node deck.mjs strip  deck.html [strip.png]  frames across the transition into --slide N (--frames 8)
  node deck.mjs still  deck.html SPEC... --out dir [--width 960]
                                              exactly the named states as PNG; prints the paths.
                                              SPEC: 6.2 = slide 6 step 2 at rest (6 = its last step),
                                              6.2@0.4 = 0.4 s into that step's animation (the time
                                              check --timeline prints), 6.2@rest = rest frame
  node deck.mjs gif    deck.html [out.gif]    animated GIF of the timeline  --from s --to s --fps 12 --width 960
                                              --hold 1.2  same hold for every step (short teasers; mp4 too)
  node deck.mjs mp4    deck.html [out.mp4]    MP4 of the timeline (needs ffmpeg)  --from --to --fps 30
                                              gif and mp4 render in parallel: --workers N (default min(4, cpus/4))
                                              --draft    half size and frame rate (mp4 15, gif 8), JPEG frames,
                                                         ffmpeg veryfast, 64-colour gif
                                              --profile  10 slowest frames by timecode + mean cost per second
                                              narrated video (mp4; --timings and --captions also gif):
                                              --timings t.json   step holds from a file: the second each state starts,
                                                                 {"1.0": 0, "1.1": 4.2, "2.0": 9.8, ..., "end": 93.5}
                                              --voice v.wav      voice-over muxed in, padded/trimmed to the video
                                                                 (video ends at the voice + --tail 0.6 s unless "end" is set)
                                              --loudnorm         voice at -14 LUFS with a -3 dB limiter; prints the measured level
                                              --captions o.srt   subtitles: each slide's speaker notes spread over its window
  node deck.mjs timings deck.html [out.json]  --from-notes  starter timings from the notes' word count (--wpm 150 --pause 0.5)
                                              --check t.json  resolve a file: the hold every state gets, and what does not fit
                                                              (--voice v.wav compares lengths, --captions o.srt writes subtitles)
  node deck.mjs analyze REF... [--out dir]    reference -> report.md, analysis.json, contact-sheet.png: palette and roles, accent
                                              share, words and text sizes per slide, title regularity. REF: a PDF, a folder or
                                              list of images, or a deck.html
  node deck.mjs check deck.html              lint rest frames: overflow, text escaping its box, safe area,
                                              tiny text, overlaps, low-contrast (WCAG 2 gate, APCA shown)
                                              --timeline  also lint frames mid-animation (prints a still spec)
                                              --no-webfonts  with fallback fonts   --workers N
  node deck.mjs perf   deck.html              cost of a frame per slide and per transition (script + style + layout)
  node deck.mjs fonts  deck.html [out.html]   metric-matched fallback @font-face for every Google font (capsize);
                                              prints the CSS. --write  insert it into the deck (or into out.html)
  node deck.mjs bundle deck.html [out.html]   inline CDN scripts, stylesheets and Google Fonts: one offline file
                                              (also adds the fonts fallback block)

  palette (no browser): node ../scripts/palette.mjs --accent "#dd4428" [--bg light|dark|HEX] [--second auto|HEX] [--html out.html]

  debug: --signatures file.txt  write a 16x9 luma signature of every captured frame; node deck.mjs sigdiff a.txt b.txt
         compares two of them (frames may differ by +-2 levels between runs, never in order)
`;

const argv = process.argv.slice(2);
const flag = n => { const i = argv.indexOf(n); if (i < 0) return false; argv.splice(i, 1); return true; };
const opt = (n, d) => { const i = argv.indexOf(n); return i < 0 ? d : argv.splice(i, 2)[1]; };

const CHROME_ARGS = ['--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
  '--force-color-profile=srgb', '--hide-scrollbars'];
const launchOpts = process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: 'chrome' };
const buf = u8 => (Buffer.isBuffer(u8) ? u8 : Buffer.from(u8.buffer, u8.byteOffset, u8.byteLength));

// A frame's signature: mean luma of a 16x9 grid, one hex byte per block. Two renders of the same time
// differ by +-2 levels in a few dozen pixels (GPU rounding), so exact hashes never match; signatures do.
async function frameSig(b, format) {
  const cjs = m => m.default || m;
  const img = format === 'jpeg' ? cjs(await import('jpeg-js')).decode(b, { useTArray: true, formatAsRGBA: true }) : cjs(await import('pngjs')).PNG.sync.read(b);
  const sum = new Float64Array(144), cnt = new Uint32Array(144), d = img.data;
  for (let y = 0; y < img.height; y++) {
    const gy = Math.min(8, Math.floor(y * 9 / img.height)) * 16;
    for (let x = 0; x < img.width; x++) {
      const g = gy + Math.min(15, Math.floor(x * 16 / img.width)), o = (y * img.width + x) * 4;
      sum[g] += .2126 * d[o] + .7152 * d[o + 1] + .0722 * d[o + 2]; cnt[g]++;
    }
  }
  return Array.from(sum, (s, g) => Math.round(s / cnt[g]).toString(16).padStart(2, '0')).join('');
}

/* ═════════════════════ worker: one thread, one Chrome, tasks from the pool ═════════════════════ */

async function workerMain() {
  const cfg = workerData;
  const errs = [];
  const browser = await chromium.launch({ ...launchOpts, args: CHROME_ARGS });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push(String(e)));
  if (cfg.nofonts) await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto(pathToFileURL(cfg.inputAbs).href + '?render' + (cfg.hold ? `&hold=${cfg.hold}` : ''));
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  // --timings: the step holds come from a timings file (a voice-over's onsets). The runtime's timeline() returns the
  // live object that __draw reads, so resolving the holds here and rewriting its segments in place changes every
  // frame this worker draws. Every worker resolves the same file against the same natural timeline: same result.
  let timing = null;
  if (cfg.timings) {
    const nat = await page.evaluate(() => ({ segs: window.__deck.timeline().segs.map(s => ({ kind: s.kind, i: s.i, step: s.step, dur: s.dur })), slides: window.__deck.slides.map(s => ({ steps: s.steps })) }));
    timing = resolveTimings(nat.segs, nat.slides, cfg.timings, { defaultEnd: cfg.defaultEnd });
    await page.evaluate(holds => {
      const tl = window.__deck.timeline(); let T = 0, k = 0;
      for (const s of tl.segs) { if (s.kind === 'hold') s.dur = holds[k++]; s.t0 = T; T += s.dur; }
      tl.duration = T; window.__meta.DURATION = T;
    }, timing.holds);
  }
  const info = await page.evaluate(() => ({ meta: { ...window.__meta }, deck: window.__deck.slides, title: document.title,
    all: window.__deck.states('all'), last: window.__deck.states('last'), tl: window.__deck.timeline() }));
  info.timing = timing;
  const { meta } = info;
  await page.setViewportSize({ width: meta.W, height: meta.H });
  if (cfg.pointerAuto) await page.addStyleTag({ content: '*{pointer-events:auto!important}' });
  const cdp = await page.context().newCDPSession(page);
  const rAF2 = () => page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));

  // CDP capture: no element lookup, no scroll, no wait for a stable frame; clip.scale renders at that size.
  async function capture(format, quality, scale) {
    const { data } = await cdp.send('Page.captureScreenshot', { format, ...(format === 'jpeg' ? { quality } : {}), optimizeForSpeed: true,
      fromSurface: true, captureBeyondViewport: false, clip: { x: 0, y: 0, width: meta.W, height: meta.H, scale } });
    return Buffer.from(data, 'base64');
  }
  // draw the timeline at T and capture; returns the bytes and what each part cost
  async function frameAt(T, t) {
    const draw = await page.evaluate(T => { const a = performance.now(); window.__draw(T); return performance.now() - a; }, T);
    const b = performance.now();
    const png = await capture(t.format, t.quality, t.scale);
    return { png, draw, cap: performance.now() - b };
  }
  const progress = n => parentPort.postMessage({ type: 'progress', n });

  const tasks = {
    async render(t) {   // a list of items, each a rest frame {i, step} or a timeline time {T}
      const out = [], hashes = [];
      for (const it of t.items) {
        let png;
        if (it.T != null) png = (await frameAt(it.T, t)).png;
        else {
          await page.evaluate(({ i, step }) => window.__deck.show(i, step), it);
          await rAF2();
          png = await capture(t.format, t.quality, t.scale);
        }
        out.push(png); if (cfg.hashes) hashes.push(await frameSig(png, t.format));
      }
      return { frames: out, hashes };
    },

    async gif(t) {
      const cjs = m => m.default || m;   // both packages are CommonJS
      const { GIFEncoder, quantize, applyPalette } = cjs(await import('gifenc'));
      const decode = t.format === 'jpeg' ? cjs(await import('jpeg-js')) : cjs(await import('pngjs')).PNG;
      const dec = b => (t.format === 'jpeg' ? decode.decode(b, { useTArray: true, formatAsRGBA: true }) : decode.sync.read(b));
      // Frame differencing: pixels the viewer already sees are written as transparent, and each
      // frame's palette is built from the changed pixels only. Holds cost almost nothing.
      // Every chunk starts with a full frame; chunks after the first carry no header (auto: false),
      // so the parts join by concatenation.
      const gif = GIFEncoder({ auto: false });
      if (t.head) gif.writeHeader();
      let shown = null, first = true;
      const times = [], hashes = [];
      // capture of the next frame overlaps the encoding of this one (not with --profile: it would blur the timings)
      let pending = cfg.profile ? null : frameAt(t.a / t.fps, t);
      for (let i = t.a; i < t.b; i++) {
        const cur = cfg.profile ? await frameAt(i / t.fps, t) : await pending;
        if (!cfg.profile && i + 1 < t.b) pending = frameAt((i + 1) / t.fps, t);
        const e0 = performance.now();
        if (cfg.hashes) hashes.push(await frameSig(cur.png, t.format));
        const img = dec(cur.png), px = img.data, n = px.length / 4, changed = new Uint8Array(n);
        let count = 0;
        const thr = t.thr;
        for (let k = 0; k < n; k++) {
          const o = k * 4;
          if (!shown || Math.abs(px[o] - shown[o]) > thr || Math.abs(px[o + 1] - shown[o + 1]) > thr || Math.abs(px[o + 2] - shown[o + 2]) > thr) { changed[k] = 1; count++; }
        }
        // palette from at most ~120k changed pixels (an even stride), so a full-frame change stays cheap
        const stride = Math.max(1, Math.ceil(count / 120000));
        const sample = new Uint8Array(Math.max(1, Math.ceil(count / stride)) * 4);
        for (let k = 0, j = 0, c = 0; k < n; k++) if (changed[k] && (c++ % stride) === 0) { sample.set(px.subarray(k * 4, k * 4 + 4), j); j += 4; }
        const palette = quantize(sample, t.colors);
        const T = palette.length; palette.push([0, 0, 0]);
        const index = applyPalette(px, palette.slice(0, T));
        if (!shown) shown = new Uint8Array(px.length);
        for (let k = 0; k < n; k++) {
          if (!changed[k]) { index[k] = T; continue; }
          const c = palette[index[k]]; shown[k * 4] = c[0]; shown[k * 4 + 1] = c[1]; shown[k * 4 + 2] = c[2];
        }
        gif.writeFrame(index, img.width, img.height, { first: t.head && first, palette, delay: Math.round(1000 / t.fps), transparent: true, transparentIndex: T, dispose: 1 });
        first = false;
        times.push([i / t.fps, cur.draw, cur.cap, performance.now() - e0]);
        if ((i - t.a) % 4 === 3) progress(4);
      }
      progress((t.b - t.a) % 4);
      return { bytes: gif.bytes(), times, hashes };
    },

    async mp4(t) {
      const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-c:v', t.format === 'png' ? 'png' : 'mjpeg', '-framerate', String(t.fps), '-i', '-',
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', t.crf, '-preset', t.preset, t.file], { stdio: ['pipe', 'ignore', 'inherit'] });
      const ffDone = new Promise((res, rej) => { ff.on('error', rej); ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg exit ' + c)))); });
      ffDone.catch(() => {});
      const times = [], hashes = [];
      for (let i = t.a; i < t.b; i++) {
        const cur = await frameAt(i / t.fps, t);
        if (cfg.hashes) hashes.push(await frameSig(cur.png, t.format));
        times.push([i / t.fps, cur.draw, cur.cap, 0]);
        if (!ff.stdin.write(cur.png)) await new Promise(r => ff.stdin.once('drain', r));
        if ((i - t.a) % 4 === 3) progress(4);
      }
      progress((t.b - t.a) % 4);
      ff.stdin.end(); await ffDone;
      return { times, hashes };
    },

    async lint(t) {   // rest frames of the given slides, and (with timeline) their mid-animation frames
      const out = { rest: [], tl: [] };
      for (const i of t.slides) {
        for (const st of info.all.filter(s => s.i === i)) {
          await page.evaluate(({ i, step }) => window.__deck.show(i, step), st);
          out.rest.push({ st, found: await page.evaluate(lint, { contrast: true }) });
        }
        if (!t.timeline) continue;
        // Mid-animation frames: things that are fine at rest can spill out while they move or count.
        const seen = new Map();
        for (const g of info.tl.segs.filter(x => x.kind === 'hold' && x.i === i)) {
          for (let dt = .15; dt < Math.min(g.dur, 3); dt += .15) {
            await page.evaluate(T => window.__draw(T), g.t0 + dt);
            for (const x of await page.evaluate(lint, { contrast: false })) {
              if (!/escapes-box|off-canvas|overflow/.test(x.kind)) continue;
              // one line per element, not one per value it passes through; the line shows its worst frame
              const k = `${g.i}|${x.kind}|${x.msg.replace(/^"[^"]*"/, '').replace(/ by \d+px/, '')}`, at = seen.get(k), hit = { g: { i: g.i, step: g.step }, t: dt + (g.entry || 0), x };
              if (at === undefined) { seen.set(k, out.tl.length); out.tl.push(hit); }
              else if ((x.px || 0) > (out.tl[at].x.px || 0)) out.tl[at] = hit;
            }
          }
        }
      }
      return out;
    },
  };

  parentPort.on('message', async m => {
    if (m.type === 'close') { await browser.close().catch(() => {}); process.exit(0); }
    try {
      const result = await tasks[m.task.type](m.task);
      parentPort.postMessage({ type: 'result', id: m.id, result, errs: errs.splice(0) });
    } catch (e) { parentPort.postMessage({ type: 'error', id: m.id, error: String(e && e.stack || e) }); }
  });
  parentPort.postMessage({ type: 'ready', info });
}

/* ═════════════════════ pool (main thread) ═════════════════════ */

class Pool {
  constructor(cfg) { this.cfg = cfg; this.workers = []; this.cur = null; this.errors = []; this.done = 0; this.onProgress = null; this.info = null; }
  spawn() {
    const w = { th: new Worker(new URL(import.meta.url), { workerData: this.cfg }), ready: false, busy: false };
    w.ready$ = new Promise((res, rej) => {
      w.th.on('message', m => {
        if (m.type === 'ready') { w.ready = true; this.info ||= m.info; res(); this.cur?.feed(w); }
        else if (m.type === 'progress') { this.done += m.n; this.onProgress?.(this.done); }
        else if (m.type === 'result') { w.busy = false; this.errors.push(...m.errs); this.cur?.ok(w, m); }
        else if (m.type === 'error') { w.busy = false; this.cur?.fail(new Error(m.error)); }
      });
      w.th.on('error', e => { rej(e); this.cur?.fail(e); });
      w.th.on('exit', c => { if (!w.closing) { const e = new Error(`worker exited with ${c}`); rej(e); this.cur?.fail(e); } });
    });
    w.ready$.catch(() => {});
    this.workers.push(w);
    return w;
  }
  async start(n) {   // n browsers start at once; tasks are planned as soon as the first one is up
    const ws = Array.from({ length: n }, () => this.spawn());
    await Promise.race(ws.map(w => w.ready$));
    return this.info;
  }
  run(tasks) {
    return new Promise((resolve, reject) => {
      const results = new Array(tasks.length); let next = 0, left = tasks.length, dead = false;
      const feed = w => { if (dead || w.busy || !w.ready || next >= tasks.length) return; const id = next++; w.busy = true; w.th.postMessage({ type: 'task', id, task: tasks[id] }); };
      this.cur = {
        feed,
        ok: (w, m) => { results[m.id] = m.result; if (--left === 0) resolve(results); else feed(w); },
        fail: e => { if (!dead) { dead = true; reject(e); } },
      };
      if (!tasks.length) resolve(results);
      for (const w of this.workers) feed(w);
    });
  }
  async close() {
    await Promise.all(this.workers.map(w => new Promise(res => { w.closing = true; w.th.once('exit', res); w.th.postMessage({ type: 'close' }); })));
  }
  kill() { for (const w of this.workers) { w.closing = true; w.th.terminate(); } }
}

const defaultWorkers = () => Math.min(4, Math.max(1, Math.floor(os.cpus().length / 4)));

/* ═════════════════════ main ═════════════════════ */

async function main() {
  const cmd = argv.shift();
  if (!cmd || cmd === '-h' || cmd === '--help') { console.log(HELP); process.exit(0); }

  if (cmd === 'sigdiff') {   // debug: compare two --signatures files
    const read = f => fs.readFileSync(f, 'utf8').trim().split('\n').map(l => l.split(' ')[1]);
    const [A, B] = [read(argv[0]), read(argv[1])];
    let worst = 0, bad = 0;
    for (let i = 0; i < Math.max(A.length, B.length); i++) {
      if (!A[i] || !B[i]) { bad++; continue; }
      let m = 0; for (let k = 0; k < A[i].length; k += 2) m = Math.max(m, Math.abs(parseInt(A[i].slice(k, k + 2), 16) - parseInt(B[i].slice(k, k + 2), 16)));
      worst = Math.max(worst, m); if (m > 1) bad++;
    }
    console.log(`sigdiff: ${A.length} vs ${B.length} frames, largest block difference ${worst} level(s), ${bad} frame(s) beyond tolerance 1`);
    process.exitCode = bad ? 1 : 0; return;
  }
  const widthArg = opt('--width', null);
  const O = {
    steps: flag('--steps'), raster: flag('--raster'), last: flag('--last'), jpg: flag('--jpg'), nofonts: flag('--no-webfonts'), timeline: flag('--timeline'),
    draft: flag('--draft'), profile: flag('--profile'), write: flag('--write'), hold: opt('--hold', null), hashes: opt('--signatures', null),
    workers: opt('--workers', 'auto'), outDir: opt('--out', null),
    voice: opt('--voice', null), timings: opt('--timings', null), captions: opt('--captions', null), loudnorm: flag('--loudnorm'),
    tail: +opt('--tail', .6), fromNotes: flag('--from-notes'), checkTimings: opt('--check', null), wpm: +opt('--wpm', 150), pause: +opt('--pause', .5),
    cols: +opt('--cols', 5), slide: +opt('--slide', 2), frames: +opt('--frames', 8),
    from: +opt('--from', 0), to: opt('--to', null), fps: opt('--fps', null), width: +(widthArg ?? 960),
  };
  const [input, ...rest] = argv;
  const outArg = rest[0];
  if (!input) { console.error(HELP); process.exit(1); }
  if (cmd === 'analyze') {   // reference analysis: a PDF, a folder or list of images, or a deck.html (scripts/analyze-reference.mjs)
    let mod;
    try { mod = await import('../scripts/analyze-reference.mjs'); }
    catch (e) { if (e.code === 'ERR_MODULE_NOT_FOUND' && /analyze-reference/.test(e.message)) throw new Error('analyze needs scripts/analyze-reference.mjs next to export/ (it is not in this copy of the kit)'); throw e; }
    await mod.analyze({ inputs: [input, ...rest], out: O.outDir, chromium, launchOpts, chromeArgs: CHROME_ARGS, exportDir: path.dirname(fileURLToPath(import.meta.url)), nofonts: O.nofonts });
    return;
  }
  const inputAbs = path.resolve(input);
  const base = path.basename(input, path.extname(input));
  const out = outArg || { pdf: `${base}.pdf`, pptx: `${base}.pptx`, png: `${base}-frames`, sheet: `${base}-sheet.png`,
    strip: `${base}-strip.png`, gif: `${base}.gif`, mp4: `${base}.mp4`, bundle: `${base}.bundle.html` }[cmd];
  // A rest-frame check is about two seconds of work: extra browsers cost more to start than they save (only --timeline pays).
  const nWorkers = O.workers === 'auto' ? (cmd === 'check' && !O.timeline ? 1 : defaultWorkers()) : Math.max(1, parseInt(O.workers, 10) || 1);

  if (cmd === 'bundle') { await bundle(inputAbs, out); return; }
  if (cmd === 'fonts') { await fonts(inputAbs, outArg, O.write); return; }

  // narrated video: --timings (step holds from a file) and --voice (audio mixed into the mp4)
  const video = cmd === 'gif' || cmd === 'mp4';
  if ((O.voice || O.captions) && !video && cmd !== 'timings') throw new Error('--voice and --captions belong to mp4 (--captions also to gif and to timings --check)');
  if (O.voice && cmd === 'gif') throw new Error('--voice is for mp4: a GIF has no sound');
  if (O.voice && !fs.existsSync(O.voice)) throw new Error(`voice file not found: ${O.voice}`);
  if (O.timings && !video) throw new Error('--timings belongs to mp4 and gif (to only check a file: timings deck.html --check timings.json)');
  const timingsData = video && O.timings ? readTimings(O.timings) : null;
  const voiceDur = O.voice ? probeDuration(O.voice) : null;

  if (cmd === 'timings') { await timingsCmd(); return; }

  if (['png', 'sheet', 'strip', 'still', 'gif', 'mp4', 'check'].includes(cmd)) { await parallel(cmd); return; }

  /* ───── single-browser commands: pdf, pptx, perf ───── */
  const browser = await chromium.launch(launchOpts);
  const errors = [];
  async function open(scale = 1) {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: scale });
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto(pathToFileURL(inputAbs).href + '?render' + (O.hold ? `&hold=${O.hold}` : ''));
    await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
    const meta = await page.evaluate(() => ({ ...window.__meta, deck: window.__deck.slides, title: document.title }));
    await page.setViewportSize({ width: meta.W, height: meta.H });
    return { page, meta };
  }
  const states = (page, which) => page.evaluate(w => window.__deck.states(w), which);
  const shot = (page, meta, type = 'png') => page.screenshot({ type, clip: { x: 0, y: 0, width: meta.W, height: meta.H }, ...(type === 'jpeg' ? { quality: 90 } : {}) });
  async function showShot(page, meta, st, type) {
    await page.evaluate(({ i, step }) => window.__deck.show(i, step), st);
    await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
    return shot(page, meta, type);
  }
  const done = msg => { if (errors.length) console.warn(`page errors:\n  ${[...new Set(errors)].join('\n  ')}`); console.log(msg); };

  try {
    const { page, meta } = await open();

    if (cmd === 'pdf') {
      const list = await states(page, O.steps ? 'all' : 'last');
      if (O.raster) {
        const imgs = [];
        for (const st of list) imgs.push((await showShot(page, meta, st, 'jpeg')).toString('base64'));
        await page.setContent(`<style>@page{size:${meta.W}px ${meta.H}px;margin:0}body{margin:0}img{display:block;width:${meta.W}px;height:${meta.H}px;break-after:page}</style>` +
          imgs.map(b => `<img src="data:image/jpeg;base64,${b}">`).join(''));
      } else {
        await page.evaluate(list => window.__deck.buildPrint(list), list);
        await page.addStyleTag({ content: `@page{size:${meta.W}px ${meta.H}px;margin:0}` });
        await page.evaluate(() => document.fonts.ready);
      }
      await page.pdf({ path: out, width: meta.W + 'px', height: meta.H + 'px', printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
      done(`pdf: ${out} (${list.length} pages, ${O.raster ? 'raster' : 'vector'})`);
    }

    else if (cmd === 'pptx') {
      const { default: PptxGenJS } = await import('pptxgenjs');
      const pptx = new PptxGenJS();
      const wIn = 13.333, hIn = wIn * meta.H / meta.W;
      pptx.defineLayout({ name: 'DECK', width: wIn, height: hIn }); pptx.layout = 'DECK';
      pptx.title = meta.title || base;
      const list = await states(page, O.steps ? 'all' : 'last');
      for (const st of list) {
        const png = await showShot(page, meta, st, 'png');
        const s = pptx.addSlide();
        s.addImage({ data: 'data:image/png;base64,' + png.toString('base64'), x: 0, y: 0, w: wIn, h: hIn, altText: meta.deck[st.i].title });
        const n = meta.deck[st.i].notes; if (n) s.addNotes(n);
      }
      await pptx.writeFile({ fileName: out });
      done(`pptx: ${out} (${list.length} slides, static)`);
    }

    else if (cmd === 'perf') {
      // Main-thread cost of one frame: the runtime's JS plus the style and layout it causes.
      // Paint and compositing are not included; check heavy filters with ?perf in a real window.
      const tl = await page.evaluate(() => window.__deck.timeline());
      const rows = [];
      for (const g of tl.segs) {
        if (g.dur <= 0) continue;
        const n = g.kind === 'tr' ? 10 : 8, span = g.kind === 'tr' ? g.dur : Math.min(g.dur, 2.4), ms = [];
        for (let k = 0; k < n; k++) ms.push(await page.evaluate(T => { const a = performance.now(); window.__draw(T); void document.body.offsetHeight; return performance.now() - a; }, g.t0 + span * (k + .5) / n));
        const info = await page.evaluate(() => { const l = document.querySelectorAll('.deck:not(.dk-print) .dk-layer.is-on'); let nodes = 0, filters = 0;
          for (const x of l) { nodes += x.getElementsByTagName('*').length; for (const e of x.querySelectorAll('*')) if (e.style.filter && e.style.filter !== 'none') filters++; } return { nodes, filters }; });
        ms.sort((a, b) => a - b);
        rows.push({ what: g.kind === 'tr' ? `→ ${g.to.i + 1}  ${meta.deck[g.to.i].id}` : `${g.i + 1}.${g.step}  ${meta.deck[g.i].id}`, kind: g.kind,
          med: ms[Math.floor(n / 2)], max: ms[n - 1], ...info });
      }
      let bad = 0;
      console.log('frame cost, main thread (median / worst ms), DOM nodes on screen, live filters');
      for (const r of rows) {
        const flag = r.max > 16 ? 'ERR ' : r.max > 8 ? 'warn' : '    ';
        if (r.max > 16) bad++;
        console.log(`${flag}  ${r.what.padEnd(26)} ${r.med.toFixed(1).padStart(6)} / ${r.max.toFixed(1).padStart(6)} ms   ${String(r.nodes).padStart(5)} nodes${r.filters ? `   ${r.filters} filtered` : ''}`);
      }
      const worst = rows.reduce((a, b) => (b.max > a.max ? b : a));
      done(`perf: ${rows.length} segments, worst ${worst.max.toFixed(1)} ms at ${worst.what.trim()}; budget 8 ms (warn), 16 ms (error)`);
      process.exitCode = bad ? 1 : 0;
    }

    else throw new Error(`unknown command: ${cmd}`);
  } finally {
    await browser.close();
  }

  /* ───── commands on the worker pool ───── */
  async function parallel(cmd) {
    const pool = new Pool({ inputAbs, nofonts: O.nofonts, hold: O.hold, hashes: !!O.hashes, profile: O.profile, pointerAuto: cmd === 'check',
      timings: timingsData, defaultEnd: voiceDur != null ? voiceDur + O.tail : undefined });
    const info = await pool.start(cmd === 'still' ? Math.max(1, Math.min(nWorkers, Math.ceil(rest.filter(Boolean).length / 3))) : cmd === 'strip' ? Math.min(nWorkers, Math.ceil(O.frames / 2)) : nWorkers);
    const { meta } = info;
    const label = (i, step) => `${i + 1}${info.deck[i].steps ? '.' + step : ''}`;
    const fmtT = s => `${Math.floor(s / 60)}:${(s % 60).toFixed(2).padStart(5, '0')}`;
    const finish = msg => {
      if (pool.errors.length) console.warn(`page errors:\n  ${[...new Set(pool.errors)].join('\n  ')}`);
      console.log(msg);
    };
    const groups = (arr, n) => Array.from({ length: Math.ceil(arr.length / n) }, (_, k) => arr.slice(k * n, k * n + n));
    const writeHashes = list => { if (O.hashes) fs.writeFileSync(O.hashes, list.map((h, i) => `${i} ${h}`).join('\n') + '\n'); };
    try {
      if (cmd === 'png' || cmd === 'sheet') {
        const list = cmd === 'png' && O.last ? info.last : info.all;
        const small = cmd === 'sheet' || (cmd === 'png' && O.jpg);
        const scale = cmd === 'sheet' ? .5 : cmd === 'png' && O.jpg ? O.width / meta.W : 1;
        const t = groups(list, 4).map(items => ({ type: 'render', items, format: small ? 'jpeg' : 'png', quality: 90, scale }));
        const res = await pool.run(t);
        const frames = res.flatMap(r => r.frames).map(buf), hashes = res.flatMap(r => r.hashes);
        writeHashes(hashes);
        if (cmd === 'png') {
          fs.mkdirSync(out, { recursive: true });
          list.forEach((st, k) => fs.writeFileSync(path.join(out, `${String(st.i + 1).padStart(2, '0')}-${st.step}.${O.jpg ? 'jpg' : 'png'}`), frames[k]));
          finish(`png: ${list.length} frames in ${out}/`);
        } else {
          await contactSheet(frames.map((b, k) => ({ b64: b.toString('base64'), label: `${label(list[k].i, list[k].step)} · ${info.deck[list[k].i].id}` })), O.cols, out, meta);
          finish(`sheet: ${out} (${frames.length} frames)`);
        }
      }

      else if (cmd === 'strip') {
        const g = info.tl.segs.find(s => s.kind === 'tr' && s.to.i === O.slide - 1);
        if (!g) throw new Error(`no transition into slide ${O.slide}`);
        const items = [], labels = [];
        for (let k = 0; k < O.frames; k++) {
          const p = k / (O.frames - 1);
          items.push({ T: g.t0 + Math.min(g.dur * p, g.dur - 1e-3) }); labels.push(`p ${p.toFixed(2)}`);
        }
        const t = groups(items, 2).map(items => ({ type: 'render', items, format: 'jpeg', quality: 90, scale: .5 }));
        const frames = (await pool.run(t)).flatMap(r => r.frames).map(buf);
        await contactSheet(frames.map((b, k) => ({ b64: b.toString('base64'), label: labels[k] })), Math.min(4, O.frames), out, meta);
        finish(`strip: ${out} (${frames.length} frames)`);
      }

      else if (cmd === 'still') {
        // SPEC: S | S.T | S.T@sec | S.T@rest   (slide S, step T, 1-based slide as in the check output)
        const specs = rest.filter(Boolean);
        if (!specs.length) throw new Error('still: name at least one state, e.g. 6.2 or 6.2@0.4 (see --help)');
        const dir = O.outDir || `${base}-stills`, scale = widthArg ? +widthArg / meta.W : 1;
        const items = [], names = [], notes = [];
        for (const spec of specs) {
          const m = /^(\d+)(?:\.(\d+))?(?:@(rest|\d*\.?\d+))?$/.exec(spec);
          if (!m) throw new Error(`still: cannot read "${spec}" (use 6.2, 6.2@0.4 or 6.2@rest)`);
          const i = +m[1] - 1;
          if (i < 0 || i >= info.deck.length) throw new Error(`still: "${spec}": the deck has slides 1-${info.deck.length}`);
          const step = m[2] == null ? info.deck[i].steps : +m[2];
          if (step > info.deck[i].steps) throw new Error(`still: "${spec}": slide ${i + 1} has steps 0-${info.deck[i].steps}`);
          let note = `slide ${i + 1} step ${step}, rest frame`;
          if (m[3] && m[3] !== 'rest') {
            // t is the step's own animation clock: the same "+0.45s" that check --timeline prints.
            // Step 0 of a slide after the first begins with the transition into it, so 0 <= t < entry lands inside it.
            const g = info.tl.segs.find(x => x.kind === 'hold' && x.i === i && x.step === step), t = +m[3], entry = g.entry || 0;
            let T = g.t0 + t - entry;
            if (t > g.dur + entry - 1e-3) { T = g.t0 + g.dur - 1e-3; note = `slide ${i + 1} step ${step}, clamped to the end of its ${g.dur}s hold`; }
            else note = `slide ${i + 1} step ${step}, ${t}s into the animation (timeline T = ${T.toFixed(2)} s${T < g.t0 ? ', still inside the incoming transition' : ''})`;
            items.push({ T });
          } else items.push({ i, step });
          names.push(`still-${spec.replace(/[^\w.@-]/g, '_')}.png`); notes.push(note);
        }
        fs.mkdirSync(dir, { recursive: true });
        const t = groups(items, 3).map(items => ({ type: 'render', items, format: 'png', scale }));
        const frames = (await pool.run(t)).flatMap(r => r.frames).map(buf);
        frames.forEach((b, k) => { const f = path.join(dir, names[k]); fs.writeFileSync(f, b); console.log(`${f}  (${notes[k]})`); });
        finish(`still: ${frames.length} frame(s) in ${dir}/`);
      }

      else if (cmd === 'gif' || cmd === 'mp4') {
        if (cmd === 'mp4' && spawnSync('ffmpeg', ['-version']).error) throw new Error('ffmpeg not found in PATH (needed for mp4; gif works without it)');
        // a draft also halves the frame rate (mp4 15, gif 8) unless --fps says otherwise
        const fps = +(O.fps || (cmd === 'gif' ? (O.draft ? 8 : 12) : O.draft ? Math.min(meta.FPS || 30, 15) : meta.FPS || 30));
        const to = O.to != null ? +O.to : meta.DURATION, first = Math.round(O.from * fps), last = Math.round(to * fps), total = last - first;
        if (total <= 0) throw new Error('empty range: --from must be before --to');
        if (info.timing) {
          const tm = info.timing;
          console.log(`timings: ${tm.states.length} states, video ${fmtT(tm.end)}${voiceDur != null ? `, voice ${fmtT(voiceDur)}${voiceDur > tm.end + 1e-3 ? ' (trimmed to the video)' : ''}` : ''}`);
          warnList(tm.warnings, 'timings: ');
        }
        // Draft: half the size, JPEG frames, faster encoder settings.
        const gifWidth = O.draft ? O.width / 2 : O.width;
        const T = { format: O.draft ? 'jpeg' : 'png', quality: 80, fps,
          scale: cmd === 'gif' ? gifWidth / meta.W : O.draft ? .5 : 1,
          crf: O.draft ? '26' : '18', preset: O.draft ? 'veryfast' : 'slow',
          colors: O.draft ? 63 : 255, thr: O.draft ? 12 : 6 };
        // Chunk length depends on the range only (never on the worker count), so any --workers gives identical output.
        const len = Math.max(fps, Math.min(4 * fps, Math.ceil(total / 8)));
        const tmp = cmd === 'mp4' ? fs.mkdtempSync(path.join(os.tmpdir(), 'dk-')) : null;
        const chunks = [];
        for (let a = first; a < last; a += len) chunks.push({ type: cmd, a, b: Math.min(last, a + len), ...T, head: a === first, file: tmp && path.join(tmp, `c${String(chunks.length).padStart(4, '0')}.mp4`) });
        const usedWorkers = Math.min(nWorkers, chunks.length);
        console.log(`${cmd}: ${total} frames ${Math.round(meta.W * T.scale)}x${Math.round(meta.H * T.scale)} @ ${fps} fps, ${T.format}, ${usedWorkers} worker(s), ${chunks.length} chunks${O.draft ? ', draft' : ''}`);
        const t0 = Date.now();
        pool.onProgress = n => { const el = (Date.now() - t0) / 1000, f = n / Math.max(el, .001); process.stdout.write(`\rframe ${n}/${total}  ${f.toFixed(1)} fps  eta ${Math.round((total - n) / Math.max(f, .001))}s   `); };
        const res = await pool.run(chunks);
        const elapsed = (Date.now() - t0) / 1000;
        process.stdout.write(`\rframe ${total}/${total}  ${(total / elapsed).toFixed(1)} fps  ${elapsed.toFixed(1)}s                 \n`);
        if (cmd === 'gif') {
          fs.writeFileSync(out, Buffer.concat([...res.map(r => buf(r.bytes)), Buffer.from([0x3b])]));
        } else {
          const list = path.join(tmp, 'list.txt');
          fs.writeFileSync(list, chunks.map(c => `file '${c.file.replace(/\\/g, '/')}'`).join('\n'));
          // Join the chunks without re-encoding. With --voice the audio is cut at --from, filtered, padded with silence
          // (apad) and trimmed (-t) to exactly the video's length, and muxed in the same call.
          const dur = total / fps, args = ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', list];
          if (O.voice) {
            args.push('-ss', String(first / fps), '-t', String(dur), '-i', path.resolve(O.voice));
            const af = ['aresample=48000', 'aformat=channel_layouts=stereo',
              ...(O.loudnorm ? ['loudnorm=I=-14:TP=-1.5:LRA=11', 'alimiter=limit=0.72:attack=5:release=60:level=disabled', 'aresample=48000'] : []),
              `apad=whole_dur=${dur.toFixed(3)}`].join(',');
            args.push('-filter_complex', `[1:a]${af}[a]`, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', dur.toFixed(3));
          } else args.push('-c', 'copy');
          args.push('-movflags', '+faststart', path.resolve(out));
          const r = spawnSync('ffmpeg', args, { stdio: ['ignore', 'ignore', 'inherit'] });
          fs.rmSync(tmp, { recursive: true, force: true });
          if (r.status !== 0) throw new Error(O.voice ? 'ffmpeg failed while joining the chunks and the voice-over' : 'ffmpeg concat failed');
        }
        writeHashes(res.flatMap(r => r.hashes));
        if (O.captions) {
          const tm = info.timing || naturalTiming(info);
          const n = writeSrt(O.captions, captionCues(info.deck, tm, first / fps, last / fps));
          console.log(`captions: ${O.captions} (${n} cues from the speaker notes)`);
        }
        if (O.voice) { const l = measureLoudness(out); if (l) console.log(`audio: integrated ${l.I} LUFS, true peak ${l.tp} dBFS${O.loudnorm ? ' (--loudnorm targets -14 LUFS with a -3 dB limiter)' : ''}`); }
        finish(`${cmd}: ${out} (${(total / fps).toFixed(1)} s at ${fps} fps, ${(fs.statSync(out).size / 1024 / 1024).toFixed(2)} MB, ${elapsed.toFixed(1)} s wall${O.voice ? ', with voice-over' : ''})`);
        if (O.profile) profile(res.flatMap(r => r.times), new Set(chunks.map(c => c.a / fps)), info, fmtT, label, cmd === 'gif');
      }

      else if (cmd === 'check') {
        const slides = info.deck.map((_, i) => i);
        const res = await pool.run(slides.map(i => ({ type: 'lint', slides: [i], timeline: O.timeline })));
        let errs = 0, warns = 0, worst = 0, worstAt = '';
        const px = (x, tag) => { if (x.px > worst) { worst = x.px; worstAt = `${tag.trim()} ${x.kind}`; } };
        for (const r of res) {
          const grown = new Map();   // steps of one slide repeat the same colour findings: print a group again only when it gains texts
          for (const { st, found } of r.rest) {
            const tag = `${label(st.i, st.step).padEnd(5)} ${info.deck[st.i].id}`;
            for (const x of found) {
              if (x.gkey) { if ((grown.get(x.gkey) || 0) >= x.n) continue; grown.set(x.gkey, x.n); }
              x.level === 'error' ? errs++ : warns++; px(x, tag); console.log(`${x.level === 'error' ? 'ERR ' : 'warn'}  ${tag}  ${x.kind}: ${x.msg}`);
            }
          }
        }
        const specs = [];
        if (O.timeline) for (const r of res) for (const { g, t, x } of r.tl) {
          errs++;
          const spec = `${label(g.i, g.step)}@${+t.toFixed(2)}`, tag = `${label(g.i, g.step).padEnd(5)} ${info.deck[g.i].id}`;
          px(x, tag); specs.push(spec);
          console.log(`ERR   ${tag}  ${x.kind} (while animating, +${t.toFixed(2)}s): ${x.msg}   [still ${spec}]`);
        }
        for (const [i, s] of info.deck.entries()) if (!s.notes) { warns++; console.log(`warn  ${String(i + 1).padEnd(5)} ${s.id}  notes: slide has no speaker notes`); }
        if (specs.length) console.log(`to look at the timeline findings: node deck.mjs still ${input} ${[...new Set(specs)].join(' ')} --out ${base}-stills`);
        finish(`check: ${info.all.length} rest frames, ${errs} errors, ${warns} warnings${worst > 0 ? `; worst overflow ${Math.round(worst)} px (${worstAt})` : ''}`);
        process.exitCode = errs ? 1 : 0;
      }
    } catch (e) {
      pool.kill(); throw e;
    }
    await pool.close();
  }

  /* ───── timings: a starter file from the speaker notes, or a dry run of a file ───── */
  async function timingsCmd() {
    const pool = new Pool({ inputAbs, nofonts: O.nofonts, hold: O.hold });
    try {
      const info = await pool.start(1);
      const defaultEnd = voiceDur != null ? voiceDur + O.tail : undefined;
      let timing;
      if (O.fromNotes) {
        const r = timingsFromNotes(info, O.wpm, O.pause);
        const file = outArg || `${base}-timings.json`;
        fs.writeFileSync(file, r.json);
        timing = r.timing;
        console.log(`timings: ${file}  (${info.deck.length} slides, ${timing.states.length} states, ${O.wpm} words per minute, ${fmtTimeShort(timing.end)} in all)`);
        console.log('slide  words  speaking  window');
        info.deck.forEach((s, i) => { const w = r.slides[i]; console.log(`${String(i + 1).padStart(5)}  ${String(w.words).padStart(5)}  ${w.words ? (w.words / (O.wpm / 60)).toFixed(1).padStart(7) + 's' : '  (no notes: the deck\'s own holds)'}  ${w.window.toFixed(1)}s`); });
        console.log('edit the numbers to the real narration (a stopwatch, or the timestamps of a TTS run), then: node deck.mjs mp4 ' + input + ' --timings ' + file + ' --voice narration.wav');
      } else if (O.checkTimings) {
        timing = resolveTimings(info.tl.segs, info.deck, readTimings(O.checkTimings), { defaultEnd });
        printTiming(timing, info.deck);
        if (voiceDur != null) console.log(`voice ${fmtTimeShort(voiceDur)}, video ${fmtTimeShort(timing.end)}${voiceDur > timing.end + 1e-3 ? ': the voice is longer and would be trimmed' : ''}`);
        warnList(timing.warnings, 'warning: ');
        process.exitCode = timing.warnings.length ? 1 : 0;
      } else throw new Error('timings: --from-notes [out.json] writes a starter file (--wpm 150 --pause 0.5); --check timings.json resolves a file and lists the holds it gives');
      if (O.captions) console.log(`captions: ${O.captions} (${writeSrt(O.captions, captionCues(info.deck, timing, 0, timing.end))} cues from the speaker notes)`);
    } catch (e) { pool.kill(); throw e; }
    await pool.close();
  }

  async function contactSheet(tiles, cols, file, meta) {
    const tw = 480, th = Math.round(tw * meta.H / meta.W);
    const b = await chromium.launch(launchOpts);
    try {
      const sheet = await b.newPage({ viewport: { width: cols * (tw + 12) + 12, height: 400 } });
      await sheet.setContent(`<style>body{margin:0;background:#161616;font:600 15px/1 ui-monospace,monospace;color:#ddd}
        .g{display:grid;grid-template-columns:repeat(${cols},${tw}px);gap:12px;padding:12px}
        figure{margin:0}img{display:block;width:${tw}px;height:${th}px;outline:1px solid #333}figcaption{padding:6px 2px 0}</style>
        <div class="g">${tiles.map(t => `<figure><img src="data:image/jpeg;base64,${t.b64}"><figcaption>${t.label}</figcaption></figure>`).join('')}</div>`);
      await sheet.screenshot({ path: file, fullPage: true });
    } finally { await b.close(); }
  }
}

/* ───────── --profile report ───────── */
function profile(times, chunkStarts, info, fmtT, label, withEncode) {
  const seg = t => info.tl.segs.find(g => t >= g.t0 && t < g.t0 + g.dur) || info.tl.segs.at(-1);
  const name = t => { const g = seg(t); return g.kind === 'tr' ? `-> ${g.to.i + 1}` : label(g.i, g.step); };
  const cost = r => r[1] + r[2] + r[3];
  console.log('slowest frames (the first frame of a chunk also pays for encoder start-up and is skipped):');
  for (const r of [...times].filter(r => !chunkStarts.has(r[0])).sort((a, b) => cost(b) - cost(a)).slice(0, 10))
    console.log(`  ${fmtT(r[0])}  ${name(r[0]).padEnd(6)} total ${cost(r).toFixed(0).padStart(5)} ms  (draw call ${r[1].toFixed(1)}, capture ${r[2].toFixed(0)}${withEncode ? `, gif encode ${r[3].toFixed(0)}` : ''})`);
  const sec = {};
  for (const r of times) (sec[Math.floor(r[0])] ??= []).push(cost(r));
  console.log('mean cost per frame, by second of the timeline (ms):');
  console.log('  ' + Object.entries(sec).map(([k, v]) => `${k}s:${(v.reduce((a, b) => a + b, 0) / v.length).toFixed(0)}`).join('  '));
  const avg = k => times.reduce((s, r) => s + r[k], 0) / times.length;
  console.log(`mean per frame: draw call ${avg(1).toFixed(1)} ms, capture ${avg(2).toFixed(0)} ms${withEncode ? `, gif encode ${avg(3).toFixed(0)} ms` : ''}`);
}

/* ───────── lint (runs inside the page on one frame) ───────── */
function lint(opt = {}) {
  const { W, H } = window.__deck, M = Math.round(Math.min(W, H) * .035), out = [];
  const layer = document.querySelector('.deck:not(.dk-print) .dk-layer.is-on');
  const add = (level, kind, msg, px, extra) => out.push({ level, kind, msg, px, ...extra });
  const alpha = el => { let a = 1; for (let e = el; e && e !== layer; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none') return 0; a *= +cs.opacity; } return a; };
  const short = s => JSON.stringify(s.length > 42 ? s.slice(0, 40) + '…' : s);
  const boxes = [], texts = []; let words = 0;
  const tw = document.createTreeWalker(layer, NodeFilter.SHOW_TEXT);
  for (let n; (n = tw.nextNode());) {
    const txt = n.textContent.replace(/\s+/g, ' ').trim(), el = n.parentElement;
    if (!txt || el.closest('.notes,[data-lint-skip]') || alpha(el) < .05) continue;
    if (!el.closest('[data-code]')) words += txt.split(' ').length;   // every code token is its own text node; code is dense by nature (14-code-slides.md)
    const cs = getComputedStyle(el);
    const k = el instanceof SVGElement && el.getScreenCTM ? Math.hypot(el.getScreenCTM().a, el.getScreenCTM().b) : 1;
    const size = parseFloat(cs.fontSize) * k;
    if (size < 20) add('error', 'tiny-text', `${size.toFixed(0)}px ${short(txt)} (min 20px at 1080p; 24+ for body)`);
    const rg = document.createRange(); rg.selectNodeContents(n);
    const rects = [];
    for (const r of rg.getClientRects()) {
      if (r.width < 2 || r.height < 2) continue;
      rects.push(r);
      if (!el.closest('[data-bleed]') && (r.left < M || r.top < M || r.right > W - M || r.bottom > H - M))
        add('error', 'safe-area', `${short(txt)} is within ${M}px of the edge`);
      // the font's content box is taller than the glyphs; compare glyph bands instead
      const pad = r.height * .2;
      boxes.push({ el, txt, r: { left: r.left, right: r.right, top: r.top + pad, bottom: r.bottom - pad, width: r.width, height: r.height - pad * 2 } });
    }
    if (rects.length) texts.push({ el, txt, size, rects });
  }
  for (let a = 0; a < boxes.length; a++) for (let b = a + 1; b < boxes.length; b++) {
    const A = boxes[a], B = boxes[b];
    if (A.el === B.el || A.el.contains(B.el) || B.el.contains(A.el)) continue;
    const ix = Math.min(A.r.right, B.r.right) - Math.max(A.r.left, B.r.left), iy = Math.min(A.r.bottom, B.r.bottom) - Math.max(A.r.top, B.r.top);
    if (ix > 2 && iy > 2 && ix * iy > .15 * Math.min(A.r.width * A.r.height, B.r.width * B.r.height))
      add('error', 'overlap', `${short(A.txt)} overlaps ${short(B.txt)}`);
  }
  for (const el of layer.querySelectorAll('*')) {
    if (el instanceof SVGElement || alpha(el) < .05) continue;
    const cs = getComputedStyle(el);
    if (/hidden|clip/.test(cs.overflow) && el.clientHeight > 0 && (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2) && !el.matches('.slide,.dk-mask-i') && !el.closest('[data-bleed]')) {
      const px = Math.max(el.scrollHeight - el.clientHeight, el.scrollWidth - el.clientWidth);
      add('error', 'overflow', `<${el.tagName.toLowerCase()}${el.className ? '.' + String(el.className).split(' ')[0] : ''}> content is clipped by ${px}px`, px);
    }
  }
  // Containment: text must stay inside the visible box it sits in (a card, a node, a pill),
  // whether or not that box clips. HTML boxes are elements with a background or a border;
  // in SVG, a rect or circle in the same group whose area holds the text's centre.
  const isBox = e => {
    if (!(e instanceof HTMLElement) || e.matches('.slide,.dk-layer')) return false;
    const cs = getComputedStyle(e);
    if (cs.display === 'inline' || cs.display === 'contents') return false;
    const bg = !/^(transparent|rgba\(0, 0, 0, 0\))$/.test(cs.backgroundColor) || cs.backgroundImage !== 'none';
    const bd = ['Top', 'Right', 'Bottom', 'Left'].some(s => parseFloat(cs[`border${s}Width`]) > 0 && cs[`border${s}Style`] !== 'none');
    return bg || bd;
  };
  const tag = e => `<${e.tagName.toLowerCase()}${e.classList.length ? '.' + e.classList[0] : ''}>`;
  const reported = new Set();
  for (const { el, txt, r } of boxes) {
    if (el.closest('[data-bleed]')) continue;
    if (el instanceof SVGElement) {
      const t = el.closest('text'); if (!t || reported.has(t)) continue;
      const tb = t.getBoundingClientRect(), pad = tb.height * .2;
      const cx = (tb.left + tb.right) / 2, cy = (tb.top + tb.bottom) / 2;
      for (const s of t.parentNode.children) {
        if (!/^(rect|circle)$/.test(s.tagName)) continue;
        const sb = s.getBoundingClientRect();
        if (cx < sb.left || cx > sb.right || cy < sb.top || cy > sb.bottom) continue;
        let inside, px;
        if (s.tagName === 'circle') {
          const R = sb.width / 2, ox = (sb.left + sb.right) / 2, oy = (sb.top + sb.bottom) / 2;
          const d = [[tb.left, tb.top + pad], [tb.right, tb.top + pad], [tb.left, tb.bottom - pad], [tb.right, tb.bottom - pad]].map(([x, y]) => Math.hypot(x - ox, y - oy) - R);
          px = Math.max(...d); inside = px <= 1;
        } else {
          px = Math.max(sb.left - tb.left, tb.right - sb.right, sb.top - (tb.top + pad), (tb.bottom - pad) - sb.bottom);
          inside = px <= 1;
        }
        if (!inside) { reported.add(t); add('error', 'escapes-box', `${short(txt)} spills out of its <${s.tagName}> by ${Math.round(px)}px`, px); }
        break;
      }
      continue;
    }
    let b = el; while (b && b !== layer && !isBox(b)) b = b.parentElement;
    if (!b || b === layer || reported.has(b)) continue;
    const br = b.getBoundingClientRect(), cs = getComputedStyle(b);
    const L = br.left + parseFloat(cs.borderLeftWidth), R = br.right - parseFloat(cs.borderRightWidth);
    const T = br.top + parseFloat(cs.borderTopWidth), B = br.bottom - parseFloat(cs.borderBottomWidth);
    if (r.left < L - 1 || r.right > R + 1 || r.top < T - 1 || r.bottom > B + 1) {
      const px = Math.max(L - r.left, r.right - R, T - r.top, r.bottom - B);
      reported.add(b); add('error', 'escapes-box', `${short(txt)} spills out of ${tag(b)} by ${Math.round(px)}px`, px);
    }
  }
  for (const b of layer.querySelectorAll('*')) {
    if (!isBox(b) || alpha(b) < .05 || b.closest('[data-bleed]')) continue;
    const r = b.getBoundingClientRect();
    if (r.left < -1 || r.top < -1 || r.right > W + 1 || r.bottom > H + 1) {
      const px = Math.max(-r.left, -r.top, r.right - W, r.bottom - H);
      add('error', 'off-canvas', `${tag(b)} extends ${Math.round(px)}px past the slide edge (add data-bleed if intended)`, px);
    }
  }
  if (words > 60) add('warn', 'density', `${words} words on screen (aim for under 40)`);

  // Contrast of every text node against what is really behind it.
  // The backdrop is found from the paint stack at three points of each text line (elementsFromPoint,
  // with pointer-events forced on for the check), composited front to back until it is opaque.
  // Image, gradient, video and non-uniform canvas backdrops cannot be measured: contrast-unknown (warning).
  // Gate: WCAG 2 ratio, 4.5:1, or 3:1 for text of 40px and above (canvas pixels). APCA Lc is information only.
  if (opt.contrast) {
    const cvs = document.createElement('canvas'); cvs.width = cvs.height = 1;
    const c2 = cvs.getContext('2d', { willReadFrequently: true });
    const cache = new Map();
    const rgba = s => {   // any CSS colour -> [r, g, b, a 0..1]
      let v = cache.get(s); if (v) return v;
      const m = /^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+)(%?))?\s*\)$/.exec(s);
      if (m) v = [+m[1], +m[2], +m[3], m[4] == null ? 1 : m[5] ? +m[4] / 100 : +m[4]];
      else { c2.globalCompositeOperation = 'copy'; c2.fillStyle = s; c2.fillRect(0, 0, 1, 1); const d = c2.getImageData(0, 0, 1, 1).data; v = [d[0], d[1], d[2], d[3] / 255]; }
      cache.set(s, v); return v;
    };
    const over = (t, b) => {   // t over b
      const a = t[3] + b[3] * (1 - t[3]); if (a <= 0) return [0, 0, 0, 0];
      return [0, 1, 2].map(i => (t[i] * t[3] + b[i] * b[3] * (1 - t[3])) / a).concat(a);
    };
    // WCAG 2.x relative luminance and contrast ratio
    const lin = c => { c /= 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; };
    const lum = c => .2126 * lin(c[0]) + .7152 * lin(c[1]) + .0722 * lin(c[2]);
    const wcag = (a, b) => { const A = lum(a), B = lum(b); return (Math.max(A, B) + .05) / (Math.min(A, B) + .05); };
    // APCA (SAPC 0.0.98G-4g, W3 constants as published in Myndex/apca-w3, apca-w3.js, "APCA-W3" 0.1.9):
    // exponent 2.4, coefficients .2126729 / .7151522 / .0721750, normBG .56, normTXT .57, revTXT .62, revBG .65,
    // black clamp .022 ^ 1.414, scale 1.14, low-contrast offset .027, clip .1, deltaYmin .0005.
    const apca = (txt, bg) => {
      const Y = c => .2126729 * (c[0] / 255) ** 2.4 + .7151522 * (c[1] / 255) ** 2.4 + .0721750 * (c[2] / 255) ** 2.4;
      const clampY = y => (y > .022 ? y : y + (.022 - y) ** 1.414);
      const yt = clampY(Y(txt)), yb = clampY(Y(bg));
      if (Math.abs(yb - yt) < .0005) return 0;
      let s;
      if (yb > yt) { s = (yb ** .56 - yt ** .57) * 1.14; s = s < .1 ? 0 : s - .027; }
      else { s = (yb ** .65 - yt ** .62) * 1.14; s = s > -.1 ? 0 : s + .027; }
      return s * 100;
    };
    const hex = c => '#' + c.slice(0, 3).map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
    const unknownFor = new Map();
    // colour behind text at (x, y): { color } or { unknown: element } or null
    // A canvas is measured, not skipped, when the pixels under the text line are nearly uniform (a plain or
    // lightly grained stage): 5 x 3 samples within 24 levels per channel of each other. A photo or a
    // gradient fails that test and stays unknown.
    const canvasPx = (cv, rc) => {
      try {
        const b = cv.getBoundingClientRect(), sx = cv.width / b.width, sy = cv.height / b.height, ctx = cv.getContext('2d');
        if (!ctx) return null;
        const x0 = Math.max(0, Math.floor((rc.left - b.left) * sx)), y0 = Math.max(0, Math.floor((rc.top - b.top) * sy));
        const w = Math.max(1, Math.min(cv.width - x0, Math.ceil(rc.width * sx))), h = Math.max(1, Math.min(cv.height - y0, Math.ceil(rc.height * sy)));
        const d = ctx.getImageData(x0, y0, w, h).data, lo = [255, 255, 255, 255], hi = [0, 0, 0, 0];
        for (let iy = 0; iy < 3; iy++) for (let ix = 0; ix < 5; ix++) {
          const o = (Math.min(h - 1, Math.floor(h * (iy + .5) / 3)) * w + Math.min(w - 1, Math.floor(w * (ix + .5) / 5))) * 4;
          for (let c = 0; c < 4; c++) { lo[c] = Math.min(lo[c], d[o + c]); hi[c] = Math.max(hi[c], d[o + c]); }
        }
        if (Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], hi[3] - lo[3]) > 24) return null;
        const sum = [0, 0, 0, 0], n = w * h;   // the mean of the whole line box: grain averages out
        for (let o = 0; o < d.length; o += 4) for (let c = 0; c < 4; c++) sum[c] += d[o + c];
        return [sum[0] / n, sum[1] / n, sum[2] / n, sum[3] / n / 255];
      } catch { return null; }
    };
    const backdrop = (el, x, y, rc) => {
      const st = document.elementsFromPoint(x, y);
      let k = st.indexOf(el); if (k < 0) k = st.findIndex(e => e.contains(el)); if (k < 0) return null;
      let acc = [0, 0, 0, 0];
      for (let j = k; j < st.length && acc[3] < .995; j++) {
        const e = st[j], tg = e.tagName.toLowerCase(), svgChild = e instanceof SVGElement && tg !== 'svg';
        if (svgChild && /^(text|tspan|textpath)$/.test(tg)) continue;
        const a = alpha(e); if (a < .05) continue;
        const cs = getComputedStyle(e);
        if (svgChild) {
          if (tg === 'image') return { unknown: e };
          if (!/^(rect|circle|ellipse|path|polygon|polyline)$/.test(tg) || cs.fill === 'none') continue;
          if (cs.fill.startsWith('url(')) return { unknown: e };
          const c = rgba(cs.fill); acc = over(acc, [c[0], c[1], c[2], c[3] * +cs.fillOpacity * a]);
          continue;
        }
        if (tg === 'canvas') { const p = canvasPx(e, rc); if (!p) return { unknown: e }; acc = over(acc, [p[0], p[1], p[2], p[3] * a]); continue; }
        if (/^(img|video|picture|iframe|object|embed)$/.test(tg)) return { unknown: e };
        if (/text/.test(cs.backgroundClip)) continue;
        if (cs.backgroundImage !== 'none') return { unknown: e };
        const c = rgba(cs.backgroundColor);
        if (c[3] > 0) acc = over(acc, [c[0], c[1], c[2], c[3] * a]);
      }
      return { color: over(acc, [255, 255, 255, 1]) };
    };
    const unknown = (why, txt) => { const u = unknownFor.get(why) || { n: 0, txt, why }; u.n++; unknownFor.set(why, u); };
    const groups = new Map();   // one finding per text colour and size class, with a count and examples
    for (const { el, txt, size, rects } of texts) {
      const cs = getComputedStyle(el), svg = el instanceof SVGElement;
      let fg;
      if (svg) {
        if (cs.fill === 'none') continue;
        if (cs.fill.startsWith('url(')) { unknown('a gradient or pattern fill', txt); continue; }
        fg = rgba(cs.fill); fg = [fg[0], fg[1], fg[2], fg[3] * +cs.fillOpacity];
      } else {
        fg = rgba(cs.webkitTextFillColor || cs.color);
        if (fg[3] < .05 && /text/.test(cs.backgroundClip)) { unknown('gradient text (background-clip: text)', txt); continue; }
      }
      const al = alpha(el);
      if (al < .9) continue;   // deliberate de-emphasis (data-dim, greyed context, unfocused code lines): the rest frame keeps it on purpose
      fg = [fg[0], fg[1], fg[2], fg[3] * al];
      if (fg[3] < .05) continue;
      let worst = null, unk = null;
      for (const r of rects) for (const f of [.25, .5, .75]) {
        const bd = backdrop(el, r.left + r.width * f, r.top + r.height / 2, r);
        if (!bd) continue;
        if (bd.unknown) { unk = bd.unknown; continue; }
        const col = over(fg, bd.color), ratio = wcag(col, bd.color);
        if (!worst || ratio < worst.ratio) worst = { ratio, lc: apca(col, bd.color), col, bg: bd.color };
      }
      if (unk && !worst) { unknown(`<${unk.tagName.toLowerCase()}${unk.classList && unk.classList.length ? '.' + unk.classList[0] : ''}>`, txt); continue; }
      if (!worst) continue;
      const min = size >= 40 ? 3 : 4.5;
      if (worst.ratio >= min) continue;
      const hard = worst.ratio < 3;   // under 3:1 is unreadable on a projector: error; between 3:1 and the norm: warning
      const key = `${hex(worst.col)}|${min}|${hard}`, g = groups.get(key) || { min, hard, col: worst.col, n: 0, ex: [], sizes: new Set(), worst };
      if (hard) g.hard = true;
      g.n++; g.sizes.add(Math.round(size)); if (g.ex.length < 4) g.ex.push(short(txt));
      if (worst.ratio < g.worst.ratio) g.worst = worst;
      groups.set(key, g);
    }
    for (const g of groups.values()) {
      const w = g.worst, sz = [...g.sizes].sort((a, b) => a - b);
      add(g.hard ? 'error' : 'warn', 'low-contrast', `${g.n} text${g.n > 1 ? 's' : ''} in ${hex(g.col)}, ${sz.length > 1 ? `${sz[0]}-${sz.at(-1)}` : sz[0]}px, need ${g.min}:1; worst ${w.ratio.toFixed(2)}:1 on ${hex(w.bg)} (APCA Lc ${Math.abs(w.lc).toFixed(0)}): ${g.ex.join(', ')}${g.n > g.ex.length ? ', …' : ''}`, 0, { gkey: `c|${g.col}|${g.min}`, n: g.n });
    }
    for (const u of unknownFor.values())
      add('warn', 'contrast-unknown', `${u.n} text${u.n > 1 ? 's' : ''} over ${u.why} (e.g. ${short(u.txt)}): contrast not measurable`, 0, { gkey: `u|${u.why}`, n: u.n });
  }
  return out;
}

/* ───────── fonts: metric-matched fallbacks (capsize) ───────── */
// A webfont that fails to load falls back to a system font with different widths and vertical metrics, so
// boxes overflow. A fallback @font-face on a local() system font, scaled with size-adjust and the three
// vertical overrides, makes the fallback occupy the same space as the webfont. Formulas as in Next.js
// next/font and Capsize: sizeAdjust = webfontAvgWidth / fallbackAvgWidth (xWidthAvg / unitsPerEm),
// ascent / descent / lineGap = metric / (unitsPerEm * sizeAdjust).
const FONT_ALIASES = { 'Big Shoulders Display': 'Big Shoulders', 'Big Shoulders Text': 'Big Shoulders' };   // renamed on Google Fonts
const FALLBACKS = {
  'sans-serif': { key: 'arial', locals: { 400: ['Arial', 'Liberation Sans', 'Arimo', 'Helvetica'], 700: ['Arial Bold', 'Arial-BoldMT', 'Liberation Sans Bold', 'Arimo Bold', 'Helvetica Bold'] } },
  serif: { key: 'timesNewRoman', locals: { 400: ['Times New Roman', 'Liberation Serif', 'Tinos', 'Times'], 700: ['Times New Roman Bold', 'TimesNewRomanPS-BoldMT', 'Liberation Serif Bold', 'Tinos Bold', 'Times Bold'] } },
  monospace: { key: 'courierNew', locals: { 400: ['Courier New', 'Liberation Mono', 'Cousine', 'Courier'], 700: ['Courier New Bold', 'CourierNewPS-BoldMT', 'Liberation Mono Bold', 'Cousine Bold', 'Courier Bold'] } },
};
const FB_MARK = ['/* deck-kit:font-fallbacks */', '/* /deck-kit:font-fallbacks */'];

function detectFonts(html) {
  const found = new Map();   // family -> Set of weights (empty = unknown)
  const add = (f, ws = []) => { f = f.trim(); if (!f || / Fallback$/.test(f)) return; const s = found.get(f) || new Set(); ws.forEach(w => s.add(w)); found.set(f, s); };
  for (const m of html.matchAll(/<link[^>]+href=["'](https?:\/\/fonts\.googleapis\.com\/[^"']+)["']/g)) {
    const url = m[1].replace(/&amp;/g, '&');
    for (const p of url.split(/[?&]/).filter(x => x.startsWith('family='))) {
      const [name, spec = ''] = decodeURIComponent(p.slice(7).replace(/\+/g, ' ')).split(':');
      const ws = [];
      if (spec.includes('@')) {   // wght@700;800  or  ital,wght@0,400;1,700
        const axes = spec.split('@')[0].split(','), wi = axes.indexOf('wght');
        for (const tuple of spec.split('@')[1].split(';')) { const v = tuple.split(',')[wi]; if (v) v.split('..').forEach(x => +x && ws.push(+x)); }
      } else for (const w of spec.split(',')) if (/^\d+/.test(w)) ws.push(parseInt(w, 10));
      add(name, ws);
    }
  }
  for (const m of html.matchAll(/@font-face\s*\{[^}]*\}/g)) {   // already inlined (bundle) or self-hosted
    const fam = /font-family\s*:\s*(["']?)([^;"']+)\1/.exec(m[0]), w = /font-weight\s*:\s*(\d+)(?:\s+(\d+))?/.exec(m[0]);
    if (fam) add(fam[2], w ? [+w[1], w[2] ? +w[2] : +w[1]] : []);
  }
  return found;
}

async function fontPlan(html) {
  const { fontFamilyToCamelCase } = await import('@capsizecss/metrics');
  const load = async name => { try { return (await import(`@capsizecss/metrics/${fontFamilyToCamelCase(name)}`)).default; } catch { return null; } };
  const plan = [], skipped = [];
  for (const [family, weights] of detectFonts(html)) {
    const m = await load(FONT_ALIASES[family] || family);
    if (!m) { skipped.push(family); continue; }
    const fb = FALLBACKS[m.category] || FALLBACKS['sans-serif'], f = await load(fb.key);
    const em = m.unitsPerEm, adjust = (m.xWidthAvg / em) / (f.xWidthAvg / f.unitsPerEm);
    const pct = v => `${+(v * 100).toFixed(2)}%`;
    const ws = [...weights], regular = !ws.length || ws.some(w => w < 600), bold = !ws.length || ws.some(w => w >= 600);
    const faces = [];
    const body = `size-adjust: ${pct(adjust)}; ascent-override: ${pct(m.ascent / (em * adjust))}; descent-override: ${pct(Math.abs(m.descent) / (em * adjust))}; line-gap-override: ${pct(m.lineGap / (em * adjust))};`;
    const src = names => names.map(n => `local('${n}')`).join(', ');
    if (regular) faces.push(`@font-face { font-family: '${family} Fallback'; src: ${src(fb.locals[400])}; font-weight: 100 599; ${body} }`);
    if (bold) faces.push(`@font-face { font-family: '${family} Fallback'; src: ${src(fb.locals[700])}; font-weight: 600 900; ${body} }`);
    plan.push({ family, metricsAs: m.familyName, fallback: f.familyName, category: m.category, sizeAdjust: adjust, css: faces.join('\n') });
  }
  return { plan, skipped };
}

// Insert (or replace) the fallback block and put "<family> Fallback" right after each family in the font stacks.
function applyFontPlan(html, plan) {
  if (!plan.length) return { html, stacks: 0 };
  const block = `${FB_MARK[0]}\n${plan.map(p => p.css).join('\n')}\n${FB_MARK[1]}`;
  const re = new RegExp(`<style id="dk-font-fallbacks">[\\s\\S]*?</style>\\n?`);
  html = html.replace(re, '');
  const tagged = `<style id="dk-font-fallbacks">\n${block}\n</style>\n`;
  const at = html.search(/<style[\s>]/i) >= 0 ? html.search(/<style[\s>]/i) : html.search(/<\/head>/i);
  html = at < 0 ? tagged + html : html.slice(0, at) + tagged + html.slice(at);
  // protect every @font-face rule (a fallback name in its font-family descriptor would break it)
  const keep = []; html = html.replace(/@font-face\s*\{[^}]*\}/g, m => { keep.push(m); return `@@dkff${keep.length - 1}@@`; });
  let stacks = 0;
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  for (const { family } of plan) {
    const fbName = `${family} Fallback`;
    html = html.replace(new RegExp(`(?<!\\\\)(["'])${esc(family)}\\1(?!\\s*,\\s*(["'])${esc(fbName)}\\2)`, 'g'), (m, q) => { stacks++; return `${m}, ${q}${fbName}${q}`; });
    if (!/\s/.test(family)) html = html.replace(new RegExp(`(font-family\\s*:\\s*(?:[^;{}"',@]+,\\s*)*)${esc(family)}(?=\\s*[,;}!])(?!\\s*,\\s*["']${esc(fbName)})`, 'g'), (m, pre) => { stacks++; return `${pre}${family}, '${fbName}'`; });
  }
  html = html.replace(/@@dkff(\d+)@@/g, (_, k) => keep[+k]);
  return { html, stacks };
}

async function fonts(src, outArg, write) {
  const html = fs.readFileSync(src, 'utf8');
  const { plan, skipped } = await fontPlan(html);
  for (const p of plan) console.log(`${p.family}: metrics of ${p.metricsAs} (${p.category}), fallback on ${p.fallback}, size-adjust ${(p.sizeAdjust * 100).toFixed(1)}%`);
  for (const f of skipped) console.log(`${f}: not in @capsizecss/metrics, skipped (no fallback block; keep its stack tight or add slack)`);
  if (!plan.length) { console.log(skipped.length ? 'no family with known metrics' : 'no webfonts found (Google Fonts links or @font-face)'); return; }
  console.log(`\n${FB_MARK[0]}\n${plan.map(p => p.css).join('\n')}\n${FB_MARK[1]}\n`);
  const { html: next, stacks } = applyFontPlan(html, plan);
  if (!write) { console.log(`dry run: --write would add this block and extend ${stacks} font stack(s)${outArg ? ` in ${outArg}` : ''}`); return; }
  const dst = outArg || src;
  fs.writeFileSync(dst, next);
  console.log(`fonts: ${dst} (fallback block for ${plan.length} famil${plan.length > 1 ? 'ies' : 'y'}, ${stacks} font stack(s) extended)`);
}

/* ───────── bundle: make the deck work offline as one file ───────── */
async function bundle(src, dst) {
  const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';
  const get = async (url, as = 'text') => { const r = await fetch(url, { headers: { 'user-agent': UA } }); if (!r.ok) throw new Error(`${r.status} ${url}`); return as === 'text' ? r.text() : Buffer.from(await r.arrayBuffer()); };
  const mime = u => (/\.woff2(\?|$)/.test(u) ? 'font/woff2' : /\.woff(\?|$)/.test(u) ? 'font/woff' : /\.ttf(\?|$)/.test(u) ? 'font/ttf' : /\.svg/.test(u) ? 'image/svg+xml' : /\.png/.test(u) ? 'image/png' : /\.jpe?g/.test(u) ? 'image/jpeg' : 'application/octet-stream');
  let h = fs.readFileSync(src, 'utf8'), n = 0;
  const { plan, skipped } = await fontPlan(h);   // from the Google Fonts links, before they are inlined
  const swap = async (re, fn) => { const found = [...h.matchAll(re)]; for (const m of found) { h = h.replace(m[0], await fn(m)); n++; } };
  await swap(/<link[^>]+rel=["']preconnect["'][^>]*>\s*/g, async () => '');
  await swap(/<link[^>]+href=["'](https?:\/\/[^"']+)["'][^>]*rel=["']stylesheet["'][^>]*>|<link[^>]+rel=["']stylesheet["'][^>]*href=["'](https?:\/\/[^"']+)["'][^>]*>/g, async m => {
    const url = m[1] || m[2]; let css = await get(url);
    for (const u of [...new Set([...css.matchAll(/url\((['"]?)(https?:[^)'"]+)\1\)/g)].map(x => x[2]))])
      css = css.split(u).join(`data:${mime(u)};base64,${(await get(u, 'buf')).toString('base64')}`);
    return `<style>/* ${url} */\n${css}</style>`;
  });
  await swap(/<script([^>]*)\ssrc=["'](https?:\/\/[^"']+)["']([^>]*)><\/script>/g, async m => {
    const code = (await get(m[2])).replace(/<\/script/gi, '<\\/script');
    return `<script${m[1]}${m[3]}>/* ${m[2]} */\n${code}</script>`;
  });
  await swap(/<img([^>]*)\ssrc=["'](https?:\/\/[^"']+)["']/g, async m => `<img${m[1]} src="data:${mime(m[2])};base64,${(await get(m[2], 'buf')).toString('base64')}"`);
  if (/import\s[^;]*from\s*["']https?:/.test(h) || /"imports"\s*:/.test(h)) console.warn('warning: ES module imports from a CDN are not inlined; use a UMD <script src> build for offline decks');
  const fb = applyFontPlan(h, plan); h = fb.html;
  for (const f of skipped) console.warn(`fonts: ${f} is not in @capsizecss/metrics: no fallback block for it`);
  fs.writeFileSync(dst, h);
  console.log(`bundle: ${dst} (${n} resources inlined, ${plan.length} font fallback block(s), ${(fs.statSync(dst).size / 1024).toFixed(0)} KB)`);
}

/* ───────── narrated video: timings, captions, audio ───────── */
// A timings file maps states to the second the voice-over reaches them:
//   { "1.0": 0, "1.1": 4.2, "2.0": 9.8, ..., "end": 93.5 }
// "S.T" is slide S, step T (1-based slide, as in check and still); "S" alone means "S.0". The number is when
// the state STARTS: for step 0 of a slide after the first that is the moment the transition into it begins
// (the build clock starts with it), for the other steps the moment the step's builds begin. A state's hold is
// what remains until the next start, minus the transition into it. States left out share the gap between the
// states around them in proportion to their own data-hold. "end" is the length of the video (default: the voice's
// length plus --tail, or the last state's own hold without a voice). Keys starting with "_" are comments.
const MIN_HOLD = .25;   // seconds a step must keep on screen after its transition

function readTimings(file) {
  let j;
  try { j = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { throw new Error(`timings: cannot read ${file}: ${e.message}`); }
  if (!j || typeof j !== 'object' || Array.isArray(j)) throw new Error(`timings: ${file} must be a JSON object such as {"1.0": 0, "2.0": 9.8, "end": 60}`);
  const states = {}; let end;
  for (const [k, v] of Object.entries(j)) {
    if (k[0] === '_') continue;
    if (typeof v !== 'number' || !Number.isFinite(v) || v < 0) throw new Error(`timings: "${k}" must be a number of seconds (got ${JSON.stringify(v)})`);
    if (k === 'end') end = v;
    else if (/^\d+(\.\d+)?$/.test(k)) states[k] = v;
    else throw new Error(`timings: "${k}" is not a state: use "slide.step" (1.0, 2.3) or "end"`);
  }
  return { states, end };
}

// segs: the natural timeline (hold and tr segments), slides: [{ steps }]. Returns the holds to play.
function resolveTimings(segs, slides, T, o = {}) {
  const st = [];
  segs.forEach((g, k) => { if (g.kind === 'hold') st.push({ i: g.i, step: g.step, tr: segs[k - 1]?.kind === 'tr' ? segs[k - 1].dur : 0, nat: g.dur }); });
  const at = new Map(st.map((s, k) => [`${s.i + 1}.${s.step}`, k]));
  const anchor = new Map();
  for (const [key, t] of Object.entries(T.states)) {
    const [S, step = '0'] = key.split('.'), k = at.get(`${+S}.${+step}`);
    if (k === undefined) throw new Error(`timings: "${key}" is not a state of this deck (${slides.length} slides${slides[+S - 1] ? `; slide ${+S} has steps 0-${slides[+S - 1].steps}` : ''})`);
    if (anchor.has(k)) throw new Error(`timings: "${key}" repeats a state that is already given ("2" and "2.0" are the same state)`);
    anchor.set(k, t);
  }
  const name = k => `${st[k].i + 1}.${st[k].step}`;
  if (anchor.has(0) && anchor.get(0) !== 0) throw new Error(`timings: the video starts with ${name(0)} at 0 s (got ${anchor.get(0)}); lead-in silence belongs to its hold: give the NEXT state a later start`);
  anchor.set(0, 0);
  const marks = [...anchor.entries()].sort((a, b) => a[0] - b[0]);
  for (let m = 1; m < marks.length; m++) if (marks[m][1] <= marks[m - 1][1]) throw new Error(`timings: ${name(marks[m][0])} (${marks[m][1]} s) must start after ${name(marks[m - 1][0])} (${marks[m - 1][1]} s)`);
  const N = st.length, last = marks.at(-1);
  let end = T.end ?? o.defaultEnd;
  if (end == null) end = last[1] + st.slice(last[0]).reduce((a, s) => a + s.tr + s.nat, 0);   // from the last given state on, the deck plays as it would
  if (end <= last[1]) throw new Error(`timings: "end" (${end} s) must come after the last state (${name(last[0])} at ${last[1]} s)`);
  marks.push([N, end]);
  const holds = new Array(N), start = new Array(N), warnings = [], set = new Set(anchor.keys());
  let cursor = 0;
  for (let m = 0; m < marks.length - 1; m++) {
    const [ka] = marks[m], [kb, tb] = marks[m + 1], idx = Array.from({ length: kb - ka }, (_, q) => ka + q);
    const budget = tb - cursor, fixed = idx.reduce((a, k) => a + st[k].tr, 0);
    // spread what is left after the transitions over the holds, by their natural lengths, none under MIN_HOLD
    const free = new Set(idx); let rest = budget - fixed;
    for (;;) {
      const W = [...free].reduce((a, k) => a + st[k].nat, 0), share = k => rest * (W ? st[k].nat / W : 1 / free.size);
      const low = [...free].filter(k => share(k) < MIN_HOLD);
      if (!low.length) { for (const k of free) holds[k] = share(k); break; }
      for (const k of low) { holds[k] = MIN_HOLD; rest -= MIN_HOLD; free.delete(k); }
      if (!free.size) break;
    }
    for (const k of idx) if (holds[k] <= MIN_HOLD + 1e-9) {
      warnings.push(`${name(k)} gets only ${holds[k].toFixed(2)} s after its ${st[k].tr ? `${st[k].tr.toFixed(2)} s transition` : 'start'} (the gap it sits in is ${budget.toFixed(2)} s)`);
    }
    for (const k of idx) { start[k] = cursor; cursor += st[k].tr + holds[k]; }
    if (Math.abs(cursor - tb) > 1e-6) warnings.push(`${kb < N ? name(kb) : '"end"'} was asked for at ${tb.toFixed(2)} s and comes at ${cursor.toFixed(2)} s: the states before it do not fit`);
  }
  return { states: st.map((s, k) => ({ i: s.i, step: s.step, start: start[k], tr: s.tr, hold: holds[k], set: set.has(k) })), holds, end: cursor, warnings };
}

// the timeline as the deck plays it, in the shape of resolveTimings' result
function naturalTiming(info) {
  const states = []; let tr = null;
  for (const g of info.tl.segs) {
    if (g.kind === 'tr') { tr = g; continue; }
    states.push({ i: g.i, step: g.step, start: tr ? tr.t0 : g.t0, tr: tr ? tr.dur : 0, hold: g.dur, set: false }); tr = null;
  }
  return { states, holds: states.map(s => s.hold), end: info.tl.duration, warnings: [] };
}

function warnList(list, prefix) {   // a file that is far too tight warns for every state: show the first few
  for (const w of list.slice(0, 6)) console.warn(prefix + w);
  if (list.length > 6) console.warn(`${prefix}... and ${list.length - 6} more`);
}

const fmtTimeShort = s => { const t = Math.round(s * 10) / 10; return `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`; };

function printTiming(t, deck) {
  console.log('state  slide         start     transition  hold');
  for (const s of t.states) console.log(`${`${s.i + 1}.${s.step}`.padEnd(6)} ${String(deck[s.i].id).slice(0, 12).padEnd(12)} ${s.start.toFixed(2).padStart(7)}s  ${s.tr ? s.tr.toFixed(2).padStart(6) + 's  ' : '        -  '} ${s.hold.toFixed(2).padStart(6)}s  ${s.set ? '' : '(between two given states)'}`);
  console.log(`end ${t.end.toFixed(2)} s (${fmtTimeShort(t.end)})`);
}

// A starter timings file: each slide takes its speaker notes' word count at wpm words per minute plus a pause,
// but never less than its transitions and 1 s per step. The steps of a slide split its time evenly.
function timingsFromNotes(info, wpm, pause) {
  const segs = info.tl.segs, slides = info.deck, cps = wpm / 60;
  const natBlock = i => segs.filter(g => (g.kind === 'hold' && g.i === i) || (g.kind === 'tr' && g.to.i === i)).reduce((a, g) => a + g.dur, 0);
  const trOf = i => segs.filter(g => g.kind === 'tr' && g.to.i === i).reduce((a, g) => a + g.dur, 0);
  const rows = []; let t = 0; const states = {};
  slides.forEach((s, i) => {
    const words = (s.notes.match(/\S+/g) || []).length;
    const window = Math.max(words ? words / cps + pause : natBlock(i), trOf(i) + (s.steps + 1));
    rows.push({ words, window }); states[`${i + 1}.0`] = +t.toFixed(2); t += window;
  });
  const end = +t.toFixed(2);
  const timing = resolveTimings(segs, slides, { states, end }, {});
  const out = { _comment: 'Start of each state in seconds of the voice-over: slide.step (1-based slide). Edit the numbers, keep the keys; end is the length of the video. See export/README.md.', _wpm: wpm };
  for (const s of timing.states) out[`${s.i + 1}.${s.step}`] = +s.start.toFixed(1);
  out.end = +timing.end.toFixed(1);
  return { json: JSON.stringify(out, null, 2) + '\n', timing, slides: rows };
}

/* captions: the speaker notes of each slide, cut into cues and spread over the slide's time window */
function splitCue(s, max) {
  s = s.trim();
  if (s.length <= max) return [s];
  const mid = s.length / 2, best = (re, min = 8) => { let b = -1; for (const m of s.matchAll(re)) { const p = m.index + m[0].length; if (p >= min && s.length - p >= min && (b < 0 || Math.abs(p - mid) < Math.abs(b - mid))) b = p; } return b; };
  let cut = best(/[,;:–—]\s+/g); if (cut < 0) cut = best(/\s+/g); if (cut < 0) return [s];
  return [...splitCue(s.slice(0, cut), max), ...splitCue(s.slice(cut), max)];
}
function captionCues(deck, timing, from, to) {
  const cues = [], slideStart = new Map(timing.states.filter(s => s.step === 0).map(s => [s.i, s.start]));
  deck.forEach((s, i) => {
    const text = (s.notes || '').replace(/\s+/g, ' ').trim();
    if (!text) return;
    const a = slideStart.get(i), b = slideStart.get(i + 1) ?? timing.end;
    const parts = (text.match(/[^.!?…]+(?:[.!?…]+["'”’)\]]*|$)/g) || [text]).flatMap(x => splitCue(x, 84)).filter(x => x.trim());
    const chars = parts.reduce((n, p) => n + Math.max(p.length, 12), 0), span = Math.max(.5, b - a - .12);
    let t = a;
    for (const p of parts) { const d = span * Math.max(p.length, 12) / chars; cues.push({ a: t, b: t + d, text: p.trim() }); t += d; }
  });
  return cues.filter(c => c.b > from && c.a < to).map(c => ({ a: Math.max(0, c.a - from), b: Math.min(to, c.b) - from, text: c.text }));
}
function writeSrt(file, cues) {
  const ts = s => { const ms = Math.round(s * 1000), p = (n, w = 2) => String(n).padStart(w, '0'); return `${p(Math.floor(ms / 3600000))}:${p(Math.floor(ms / 60000) % 60)}:${p(Math.floor(ms / 1000) % 60)},${p(ms % 1000, 3)}`; };
  const wrap = s => { if (s.length <= 42) return s; const mid = s.length / 2; let b = -1; for (const m of s.matchAll(/\s/g)) if (b < 0 || Math.abs(m.index - mid) < Math.abs(b - mid)) b = m.index; return b < 0 ? s : `${s.slice(0, b)}\n${s.slice(b + 1)}`; };
  fs.writeFileSync(file, cues.map((c, k) => `${k + 1}\n${ts(c.a)} --> ${ts(c.b)}\n${wrap(c.text)}\n`).join('\n'));
  return cues.length;
}

function probeDuration(file) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path.resolve(file)], { encoding: 'utf8' });
  if (r.error) throw new Error('ffprobe not found in PATH (it comes with ffmpeg; --voice needs it)');
  const d = parseFloat(r.stdout);
  if (!(d > 0)) throw new Error(`cannot read the duration of ${file}: ${(r.stderr || 'no audio?').trim()}`);
  return d;
}
function measureLoudness(file) {   // EBU R128 integrated loudness and true peak of the finished file
  const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', path.resolve(file), '-map', '0:a', '-af', 'ebur128=peak=true', '-f', 'null', '-'], { encoding: 'utf8' });
  const tail = (r.stderr || '').split('Summary:').pop(), I = /I:\s+(-?[\d.]+)\s+LUFS/.exec(tail), P = /Peak:\s+(-?[\d.]+)\s+dBFS/.exec(tail);
  return I ? { I: I[1], tp: P ? P[1] : '?' } : null;
}

/* ───────── entry ───────── */
if (isMainThread) {
  try { await main(); }
  catch (e) { console.error(e.message || e); process.exit(1); }
} else await workerMain();
