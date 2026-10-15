#!/usr/bin/env node
/**
 * Renders an intro frame by frame in headless Chromium and encodes it with ffmpeg.
 *   node scripts/export-video.mjs brands/cheatgtm.json --out cheatgtm.mp4 [--width 1920 --height 1080 --fps 60]
 * Needs `npm i -D playwright` (plus `npx playwright install chromium`) and ffmpeg on PATH. Output can be .mp4 or .webm.
 */
import { readFile, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { buildHtml } from './build-html.mjs';

const args = process.argv.slice(2);
const opt = (name, fallback) => { const i = args.indexOf(`--${name}`); return i >= 0 ? args[i + 1] : fallback; };
const input = args.find((a, i) => !a.startsWith('--') && !args[i - 1]?.startsWith('--'));
if (!input) {
  console.error('Usage: node scripts/export-video.mjs <brand.json> [--out intro.mp4] [--width 1920] [--height 1080] [--fps 60]');
  process.exit(1);
}
const width = +opt('width', 1920), height = +opt('height', 1080), fps = +opt('fps', 60);
const out = path.resolve(opt('out', `${path.basename(input, '.json')}.mp4`));

let chromium;
try { ({ chromium } = await import('playwright')); } catch {
  console.error('Video export needs Playwright: npm i -D playwright && npx playwright install chromium');
  process.exit(1);
}

const brand = JSON.parse(await readFile(input, 'utf8'));
const dir = await mkdtemp(path.join(os.tmpdir(), 'logo-intro-'));
const page = path.join(dir, 'intro.html');
await writeFile(page, await buildHtml(brand, { controls: false }));

// Headless Chromium usually has no GPU; SwiftShader is slow but exact, which is all an offline render needs.
const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader'] });
try {
  const tab = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await tab.goto(`${pathToFileURL(page).href}#export`);
  await tab.waitForFunction(() => window.logoIntro);
  await tab.evaluate(() => window.logoIntro.ready);
  const total = Math.round(await tab.evaluate(() => window.logoIntro.duration) * fps);
  for (let i = 0; i < total; i++) {
    await tab.evaluate(t => window.logoIntro.seek(t), i / fps);
    await tab.screenshot({ path: path.join(dir, `f${String(i).padStart(5, '0')}.png`) });
    if (i % fps === 0) process.stdout.write(`\rframe ${i}/${total}`);
  }
  process.stdout.write(`\rframe ${total}/${total}\n`);
} finally {
  await browser.close();
}

const codec = out.endsWith('.webm')
  ? ['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '24', '-pix_fmt', 'yuv420p']
  : ['-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'];
await new Promise((resolve, reject) => {
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-framerate', String(fps), '-i', path.join(dir, 'f%05d.png'), ...codec, out], { stdio: 'inherit' });
  ff.on('error', reject);
  ff.on('exit', code => (code === 0 ? resolve() : reject(new Error(`ffmpeg exited with ${code}`))));
});
await rm(dir, { recursive: true, force: true });
console.log(`Wrote ${out}`);
