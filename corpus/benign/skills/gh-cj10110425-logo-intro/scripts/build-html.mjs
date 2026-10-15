#!/usr/bin/env node
/**
 * Builds a single self-contained HTML page (engine + optional playback bar + brand) that opens from disk.
 *   node scripts/build-html.mjs brands/cheatgtm.json --out cheatgtm.html [--no-controls]
 * Open it with #export in the URL to get a bare, paused player for frame-by-frame capture (scripts/export-video.mjs).
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

/** Wraps an ES module as an IIFE that returns its exports, so several modules can share one inline script. */
async function inlineModule(file) {
  const src = await readFile(path.join(root, file), 'utf8');
  const names = [...src.matchAll(/^export (?:async )?(?:function|const|let|class) (\w+)/gm)].map(m => m[1]);
  const body = src.replace(/^import .*$/gm, '').replace(/^export /gm, '');
  return `(() => {\n${body}\nreturn { ${names.join(', ')} };\n})()`;
}

export async function buildHtml(brand, { controls = true, title } = {}) {
  const bg = brand.theme?.background || '#fbfbf9';
  const engine = await inlineModule('src/logo-intro.js');
  const bar = controls ? await inlineModule('src/controls.js') : '';
  const json = JSON.stringify(brand).replace(/</g, '\\u003c');
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${esc(title || `${brand.name || 'Logo'} Intro`)}</title>
<style>html,body{height:100%;margin:0;background:${esc(bg)};overflow:hidden}#stage{position:relative;width:100%;height:100%}</style>
</head>
<body>
<div id="stage"></div>
<script type="module">
const LogoIntro = ${engine};
const { DURATION, TIMELINE } = LogoIntro;
${controls ? `const Controls = ${bar};` : ''}
const brand = ${json};
const exporting = location.hash === '#export';
const player = LogoIntro.mountLogoIntro(document.getElementById('stage'), brand, {
  autoplay: !exporting, allowSoftwareGL: exporting, reducedMotion: exporting ? 'ignore' : 'final',
});
${controls ? `if (!exporting) Controls.mountControls(player, { background: ${JSON.stringify(bg)} });` : ''}
window.logoIntro = player;
</script>
</body>
</html>
`;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const args = process.argv.slice(2);
  const input = args.find(a => !a.startsWith('--'));
  if (!input) {
    console.error('Usage: node scripts/build-html.mjs <brand.json> [--out file.html] [--no-controls]');
    process.exit(1);
  }
  const outIdx = args.indexOf('--out');
  const brand = JSON.parse(await readFile(input, 'utf8'));
  const out = outIdx >= 0 ? args[outIdx + 1] : path.join('dist', `${path.basename(input, '.json')}.html`);
  await mkdir(path.dirname(path.resolve(out)), { recursive: true });
  await writeFile(out, await buildHtml(brand, { controls: !args.includes('--no-controls') }));
  console.log(`Wrote ${out}`);
}
