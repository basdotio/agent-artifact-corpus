#!/usr/bin/env node
// render.mjs: render a p5.brush sketch page to a PNG, headless and offline.
//
// Usage: node render.mjs <sketch.html> <out.png> [--no-review] [--timeout <seconds>] [--progress <dir>]
//
// Page contract (template.html follows it):
//   - it draws into the canvases inside #stage: the p5 WEBGL canvas, then an optional 2D label overlay;
//   - it sets window.__done = true once drawing has finished;
//   - optionally, when window.__progress is set, it pushes a [label, PNG data URL] frame onto
//     window.__frames after every layer.
// The PNG is the composite of the #stage canvases, at the pixel size of the first one.
// --progress <dir> writes those frames as <dir>/NN_<label>.png plus <dir>/contact_sheet.png.
//
// The sketch's folder is served at / and this dry/ folder at /dry/, so a sketch in any folder loads
// its libraries from /dry/node_modules/... Requests to anything but this local server are blocked:
// a render never touches the network.
//
// After writing the PNG it runs `uv run --project ../oil python -m atelier.studio review <png>`
// when the oil kit is there (skipped with a one-line note otherwise, or with --no-review).
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, readdir, unlink } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { resolve, dirname, basename, join, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const valued = new Set(['--timeout', '--progress']);
const flag = name => { const i = args.indexOf(name); return i < 0 ? undefined : args.splice(i, valued.has(name) ? 2 : 1).at(-1); };
const noReview = flag('--no-review') !== undefined;
const timeoutSec = Number(flag('--timeout') ?? 300);
const progressArg = flag('--progress');
const [sketchArg, outArg] = args;
if (!sketchArg || !outArg) { console.error('usage: node render.mjs <sketch.html> <out.png> [--no-review] [--timeout <seconds>] [--progress <dir>]'); process.exit(1); }
const progress = progressArg && resolve(progressArg);

const here = dirname(fileURLToPath(import.meta.url));
const sketch = resolve(sketchArg), root = dirname(sketch), out = resolve(outArg);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.map': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.otf': 'font/otf', '.woff2': 'font/woff2' };

const server = createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url, 'http://local').pathname);
  const [base, rel] = path.startsWith('/dry/') ? [here, path.slice(5)] : [root, path.slice(1)];
  const file = resolve(base, rel);
  if (!file.startsWith(base + sep)) return res.writeHead(403).end();
  try { res.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream' }).end(await readFile(file)); }
  catch { res.writeHead(404).end(); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const origin = `http://127.0.0.1:${server.address().port}`;

// SwiftShader: software WebGL, so the same seed gives the same pixels on every run
const launchArgs = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'];
let browser;
try { browser = await chromium.launch({ channel: 'chrome', args: launchArgs }); } catch { browser = await chromium.launch({ args: launchArgs }); }

const started = Date.now();
let frames = 0;
try {
  const page = await browser.newPage({ deviceScaleFactor: 1 });
  const blocked = [];
  await page.route('**/*', route => {
    const url = route.request().url();
    if (url.startsWith(origin + '/')) return route.continue();
    blocked.push(url);
    return route.abort();
  });
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  const crashed = new Promise((_, reject) => page.on('pageerror', reject));
  crashed.catch(() => {});
  if (progress) await page.addInitScript(() => { window.__progress = true; });

  await page.goto(`${origin}/${encodeURIComponent(basename(sketch))}`);
  await Promise.race([page.waitForFunction(() => window.__done === true, null, { timeout: timeoutSec * 1000, polling: 100 }), crashed]);

  const { png, width, height } = await page.evaluate(() => {
    const layers = [...document.querySelectorAll('#stage canvas')];
    if (!layers.length) throw new Error('no <canvas> inside #stage');
    const c = document.createElement('canvas');
    c.width = layers[0].width; c.height = layers[0].height;
    const g = c.getContext('2d');
    for (const layer of layers) g.drawImage(layer, 0, 0, c.width, c.height);
    return { png: c.toDataURL('image/png').split(',')[1], width: c.width, height: c.height };
  });
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, Buffer.from(png, 'base64'));
  console.log(`${out} (${width}x${height}, ${((Date.now() - started) / 1000).toFixed(1)}s)`);
  if (blocked.length) console.warn(`blocked ${blocked.length} network request(s); load everything from /dry/ or the sketch folder:\n  ${blocked.join('\n  ')}`);
  if (progress) frames = await writeFrames(await page.evaluate(() => window.__frames ?? []));
} finally {
  await browser.close();
  server.close();
}

// Progress frames as NN_label.png, replacing the old ones so a re-render does not mix in stale frames
async function writeFrames(list) {
  if (!list.length) { console.warn('progress: the page recorded no frames (see template.html: draw() keeps one per layer)'); return 0; }
  await mkdir(progress, { recursive: true });
  for (const f of await readdir(progress)) if (/^\d\d_.*\.png$/.test(f)) await unlink(join(progress, f));
  for (const [i, [label, url]] of list.entries()) {
    const name = String(label).replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '') || `layer_${i + 1}`;
    await writeFile(join(progress, `${String(i).padStart(2, '0')}_${name}.png`), Buffer.from(url.split(',')[1], 'base64'));
  }
  console.log(`progress: ${list.length} frames in ${progress}`);
  return list.length;
}

const oil = resolve(here, '..', 'oil');
const studio = cmd => {
  const r = spawnSync('uv', ['run', '--project', oil, 'python', '-m', 'atelier.studio', ...cmd], { stdio: ['ignore', 'inherit', 'pipe'], encoding: 'utf8', timeout: 180_000 });
  if (r.status !== 0) console.log(`${cmd[0]}: skipped (${(r.error?.message ?? r.stderr ?? '').trim().split('\n').at(-1) || `atelier.studio ${cmd[0]} failed`})`);
};
const hasStudio = existsSync(join(oil, 'atelier', 'studio.py'));
if (noReview) {
  // caller asked for the PNG only
} else if (!hasStudio) {
  console.log(`review: skipped (no atelier.studio in ${oil} yet)`);
} else {
  studio(['review', out]);
}
if (frames && hasStudio) studio(['contact', progress]);
