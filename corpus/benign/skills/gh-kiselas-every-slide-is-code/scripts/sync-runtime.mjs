#!/usr/bin/env node
// Inlines runtime/deck.css and runtime/deck.js into decks, so every deck stays one self-contained file.
// A deck marks the slots with <style id="deck-kit-css"></style> and <script id="deck-kit-js"></script>.
//   node scripts/sync-runtime.mjs                     refresh the template and the examples
//   node scripts/sync-runtime.mjs my-deck.html        refresh one deck
//   node scripts/sync-runtime.mjs --new my-deck.html  start a new deck from the template
//   node scripts/sync-runtime.mjs --code-cache deck.html  store highlighted code in the deck for offline use (14-code-slides.md)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const css = fs.readFileSync(path.join(root, 'runtime/deck.css'), 'utf8').trim();
const js = fs.readFileSync(path.join(root, 'runtime/deck.js'), 'utf8').trim().replace(/<\/script/gi, '<\\/script');

// Optional plugins: runtime/<name>.js and runtime/<name>.css, synced only into decks that carry their slots,
// <style id="deck-kit-<name>-css"></style> and <script id="deck-kit-<name>-js"></script> (either slot may be absent).
// Adding a plugin is one line here. 14-code-slides.md: code. 15-sketch-and-morph.md: sketch.
const PLUGINS = ['code', 'sketch'];
const plugin = (file, tx = s => s) => {
  const p = path.join(root, 'runtime', file);
  return fs.existsSync(p) ? tx(fs.readFileSync(p, 'utf8').trim()) : null;
};
const plugins = PLUGINS.map(name => ({ name, css: plugin(`${name}.css`), js: plugin(`${name}.js`, s => s.replace(/<\/script/gi, '<\\/script')) }));

const args = process.argv.slice(2);
// --code-cache deck.html: run the deck once (needs export/ installed and network for Shiki), and store the highlighted
// tokens in <script type="application/json" id="deck-kit-code-cache"> so the deck (and `bundle`) works offline with the same colours.
if (args[0] === '--code-cache') {
  const f = path.resolve(args[1] || '');
  if (!args[1] || !fs.existsSync(f)) { console.error('usage: sync-runtime.mjs --code-cache deck.html'); process.exit(1); }
  const { chromium } = await import(pathToFileURL(path.join(root, 'export/node_modules/playwright-core/index.mjs')).href);
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: 'chrome' });
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await page.goto(pathToFileURL(f).href + '?render');
    await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
    const [engine, json] = await page.evaluate(() => [Deck.code.engine, Deck.code.dump()]);
    if (!/shiki|cache/.test(engine)) { console.error(`Shiki did not load (engine: ${engine || 'none'}); nothing cached. Check the network.`); process.exit(1); }
    let h = fs.readFileSync(f, 'utf8');
    const tag = `<script type="application/json" id="deck-kit-code-cache">${json}</script>`;
    const old = /^<script type="application\/json" id="deck-kit-code-cache">[\s\S]*?<\/script>/m;   // line start: never matches text inside the plugin
    h = old.test(h) ? h.replace(old, () => tag) : h.replace(/^<script id="deck-kit-code-js">/m, () => `${tag}\n<script id="deck-kit-code-js">`);
    fs.writeFileSync(f, h);
    console.log(`code cache: ${Object.keys(JSON.parse(json)).length} highlighted states stored in ${path.relative(process.cwd(), f)} (${(json.length / 1024).toFixed(1)} KB)`);
  } finally { await browser.close(); }
  process.exit(0);
}
if (args[0] === '--new') {
  const dst = args[1];
  if (!dst) { console.error('usage: sync-runtime.mjs --new my-deck.html'); process.exit(1); }
  if (fs.existsSync(dst)) { console.error(`${dst} already exists`); process.exit(1); }
  fs.copyFileSync(path.join(root, 'template/deck.html'), dst);
  args.splice(0, 2, dst);
}
const files = args.length ? args : [path.join(root, 'template/deck.html'),
  ...fs.readdirSync(path.join(root, 'examples'), { withFileTypes: true }).filter(d => d.isDirectory())
    .map(d => path.join(root, 'examples', d.name, 'deck.html')).filter(f => fs.existsSync(f))];

for (const f of files) {
  let h = fs.readFileSync(f, 'utf8');
  const before = h;
  h = h.replace(/<style id="deck-kit-css">[\s\S]*?<\/style>/, () => `<style id="deck-kit-css">\n${css}\n</style>`);
  h = h.replace(/<script id="deck-kit-js">[\s\S]*?<\/script>/, () => `<script id="deck-kit-js">\n${js}\n</script>`);
  for (const { name, css: pc, js: pj } of plugins) {
    if (pc != null) h = h.replace(new RegExp(`<style id="deck-kit-${name}-css">[\\s\\S]*?</style>`), () => `<style id="deck-kit-${name}-css">\n${pc}\n</style>`);
    if (pj != null) h = h.replace(new RegExp(`<script id="deck-kit-${name}-js">[\\s\\S]*?</script>`), () => `<script id="deck-kit-${name}-js">\n${pj}\n</script>`);
  }
  if (!/id="deck-kit-js"/.test(h)) { console.warn(`skip ${f}: no <script id="deck-kit-js"> slot`); continue; }
  fs.writeFileSync(f, h);
  console.log(`${h === before ? 'up to date' : 'synced    '}  ${path.relative(process.cwd(), f)}`);
}
