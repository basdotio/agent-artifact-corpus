// Determinism: a frame must be identical no matter what was rendered before it
// or in which page. Renders sample frames of every preset forward and in a
// shuffled order in two separate pages and compares pixel hashes.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let chromium;
try { ({ chromium } = await import('playwright')); } catch { /* skipped below */ }

const compositions = (dir) => (fs.existsSync(path.join(ROOT, dir)) ? fs.readdirSync(path.join(ROOT, dir)) : [])
  .filter((d) => fs.existsSync(path.join(ROOT, dir, d, 'video.html'))).map((d) => `${dir}/${d}`);
const presets = [...compositions('presets'), ...compositions('examples')];
// a fresh clone keeps only the manifest and the original pictures: rebuild assets/ first
const { restoreAssets } = await import('../scripts/assets.mjs');

test('frames are pure functions of time', { skip: !chromium && 'playwright not installed', timeout: 180000 }, async (t) => {
  let browser;
  try { browser = await chromium.launch({ args: ['--allow-file-access-from-files'] }); }
  catch (e) { t.skip(`chromium unavailable: ${e.message.split('\n')[0]}`); return; }
  try {
    for (const slug of presets) {
      const { failed } = await restoreAssets(path.join(ROOT, slug));
      assert.deepEqual(failed, [], `${slug}: assets could not be restored`);
      const url = `${pathToFileURL(path.join(ROOT, slug, 'video.html')).href}?render=1&scale=0.25`;
      const open = async () => {
        const p = await browser.newPage();
        const errors = [];
        p.on('pageerror', (e) => errors.push(e.message));
        p.on('requestfailed', (r) => errors.push(`request failed: ${r.url()} (${r.failure()?.errorText})`));
        await p.goto(url);
        await p.waitForFunction(() => !!window.__CV, null, { timeout: 60000 }).catch(() => { throw new Error(`${slug}: CV.create never ran — ${errors.join('; ') || 'no page errors'}`); });
        await p.evaluate(() => window.__CV.ready());
        // a font that failed to download falls back in one page only: report it as the cause
        const missing = await p.evaluate(() => window.__CV.missingFonts);
        assert.deepEqual(missing, [], `${slug}: fonts fell back (${missing.join(', ')}) ${errors.join('; ')}`);
        return p;
      };
      const [a, b] = [await open(), await open()];
      const total = await a.evaluate(() => window.__CV.totalFrames);
      const frames = Array.from({ length: 12 }, (_, i) => Math.floor((i * (total - 1)) / 11));
      const shot = (p, f) => p.evaluate(async (f) => { await window.__CV.renderFrame(f); return window.__CV.capture('image/png'); }, f);
      const hash = (s) => crypto.createHash('sha1').update(s).digest('hex');
      const fwd = {};
      for (const f of frames) fwd[f] = hash(await shot(a, f));
      const shuffled = [...frames].sort((x, y) => ((x * 7919) % 13) - ((y * 7919) % 13));
      for (const f of shuffled) {
        const got = await shot(b, f);
        if (hash(got) === fwd[f]) continue;
        // keep the evidence: both frames and both pages' font state
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gaga-determinism-'));
        const png = (d) => Buffer.from(d.slice(d.indexOf(',') + 1), 'base64');
        fs.writeFileSync(path.join(dir, `${path.basename(slug)}-${f}-forward.png`), png(await shot(a, f)));
        fs.writeFileSync(path.join(dir, `${path.basename(slug)}-${f}-shuffled.png`), png(got));
        const fonts = (p) => p.evaluate(() => ({ status: document.fonts.status, pending: Array.from(document.fonts).filter((x) => x.status !== 'loaded' && x.status !== 'unloaded').map((x) => `${x.family} ${x.status}`) }));
        assert.fail(`${slug}: frame ${f} differs between pages/orders. Frames saved in ${dir}. Fonts: forward ${JSON.stringify(await fonts(a))}, shuffled ${JSON.stringify(await fonts(b))}`);
      }
      await a.close();
      await b.close();
    }
  } finally {
    await browser.close();
  }
});
