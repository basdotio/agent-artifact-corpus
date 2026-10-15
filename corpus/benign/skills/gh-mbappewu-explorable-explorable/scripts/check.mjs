#!/usr/bin/env node
// Static checks for an explorable page. Usage: node check.mjs page.html
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const file = process.argv[2];
if (!file) {
  console.error('usage: node check.mjs page.html');
  process.exit(2);
}
const html = readFileSync(file, 'utf8');
const problems = [];
const fail = (msg) => problems.push(msg);

if (!/<title[^>]*>[^<]+<\/title>/.test(html)) fail('missing <title>');
if (!/<meta name="viewport"/.test(html)) fail('missing viewport meta tag');

// Scripts must parse.
const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
if (!scripts.length) fail('no inline <script>: figures need code');
const dir = mkdtempSync(join(tmpdir(), 'explorable-'));
scripts.forEach((code, i) => {
  const path = join(dir, `script${i}.js`);
  writeFileSync(path, code);
  const r = spawnSync(process.execPath, ['--check', path], { encoding: 'utf8' });
  if (r.status !== 0) fail(`script ${i + 1} does not parse:\n${(r.stderr || '').split('\n').slice(0, 6).join('\n')}`);
});

// Only Google Fonts may be fetched from the network.
const allowed = /^https:\/\/fonts\.(googleapis|gstatic)\.com(\/|$)/;
for (const m of html.matchAll(/\b(?:src|href)=["'](https?:\/\/[^"']+)["']/g)) {
  if (!allowed.test(m[1])) fail(`external request: ${m[1]}`);
}
for (const m of html.matchAll(/\b(?:fetch|import)\(\s*["'](https?:\/\/[^"']+)["']/g)) fail(`external request in script: ${m[1]}`);
for (const m of html.matchAll(/url\(\s*["']?(https?:\/\/[^"')]+)/g)) {
  if (!allowed.test(m[1])) fail(`external request in CSS: ${m[1]}`);
}

// Every color token in the light scheme must be redefined for dark mode.
const tokens = (block) => new Map([...block.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
const light = html.match(/:root\s*\{([^}]*)\}/);
const darkBlock = html.match(/prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{([^}]*)\}/);
if (!light) fail('no :root color tokens');
else if (!darkBlock) fail('no dark-mode :root block (@media (prefers-color-scheme: dark))');
else {
  const dark = tokens(darkBlock[1]);
  for (const [name, value] of tokens(light[1])) {
    if (/^(#|rgb|hsl)/.test(value) && !dark.has(name)) fail(`color token ${name} has no dark-mode value`);
  }
}

// Figures need captions; ids used from JS must exist.
const figures = [...html.matchAll(/<figure\b[^>]*>([\s\S]*?)<\/figure>/g)];
if (figures.length < 3) fail(`only ${figures.length} figure(s): an explorable needs 4–7`);
figures.forEach((m, i) => { if (!/<figcaption/.test(m[1])) fail(`figure ${i + 1} has no <figcaption>`); });
const ids = new Set([...html.matchAll(/\bid=["']([^"']+)["']/g)].map((m) => m[1]));
for (const m of html.matchAll(/getElementById\(\s*['"]([^'"]+)['"]\s*\)/g)) {
  if (!ids.has(m[1])) fail(`getElementById('${m[1]}') but no element has that id`);
}

// Prose that names a color that flips in dark mode.
const prose = html.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/g, '');
for (const m of prose.matchAll(/\b(black|white) (curve|line|dot|bar|wave|arrow)s?\b/gi)) {
  fail(`prose says "${m[0]}", which is wrong in the other color scheme`);
}

if (problems.length) {
  console.log(`FAIL ${file}\n` + problems.map((p) => '  - ' + p).join('\n'));
  process.exit(1);
}
console.log(`PASS ${file} (${figures.length} figures, ${scripts.length} script block${scripts.length > 1 ? 's' : ''})`);
