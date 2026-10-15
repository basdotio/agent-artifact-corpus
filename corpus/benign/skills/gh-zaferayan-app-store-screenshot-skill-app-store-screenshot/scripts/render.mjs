#!/usr/bin/env node
/*
Render store screenshots from an HTML template with headless Chrome.

Each image is an HTML page (assets/template.html, or your own copy of it)
opened at the exact canvas size and screenshotted. The app screenshot is a
plain <img> in that page, so the UI is never regenerated, only resized.

Needs Node 18+ and a Chromium-based browser (Chrome, Chromium, Edge, Brave).
Set CHROME_PATH if it is not found. No npm packages.

Usage:
    node render.mjs set.json

set.json:
    {
      "size": "1290x2796",
      "out_dir": "stores",
      "template": "optional/path/to/custom-template.html",
      "theme": {
        "bg": "#1b1145", "bg2": "#0d0824",
        "accent": "#7c3aed", "accent2": "#f3c969",
        "text": "#ffffff", "line": "rgba(255,255,255,.2)",
        "headline_font": "\"Didot\", \"Playfair Display\", Georgia, serif",
        "headline_weight": 700, "em_style": "italic",
        "font_links": ["https://fonts.googleapis.com/css2?family=..."],
        "platform": "ios", "cutout": true, "frame": "black",
        "headline_lines": 2, "sub_lines": 2, "device_max_w": 0.73,
        "scene": "scene.html", "scene_vars": {"seed": 1}
      },
      "images": [
        {"screenshot": "raw/home.png", "headline": "Art history,\n*made playable.*",
         "sub": "Optional one-sentence subheadline.",
         "pattern": "rings", "scene_vars": {"seed": 4}, "out": "01-home.png"}
      ]
    }

Headline markup: "\n" is a line break, *text* gets the accent treatment.
Any theme key can be overridden per image. Paths may be absolute, start with
"~", or be relative to the config file.

Backgrounds, pick one:
  "scene"             HTML fragment injected into the background layer. It may
                      contain <style>, markup, inline <svg> and <script>.
                      "scene_vars" (theme and image, merged) reach it as
                      window.SCENE. After layout the page sets window.LAYOUT and
                      fires a "store:layout" event with the canvas, device and
                      screen boxes in pixels.
  "background_image"  photo, artwork or illustration; "scrim" (0..1) tints it
                      toward bg, "background_position" is a CSS position.
  "pattern"           rings, dots, grid, rays, arcs, diagonal, frames, none.
*/

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const BROWSERS = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
];
const BROWSER_COMMANDS = ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser',
                          'microsoft-edge', 'brave-browser'];

const THEME_DEFAULTS = {
  bg: '#15151c', bg2: null, accent: '#6d5efc', accent2: null, text: null, line: null,
  headline_font: '"SF Pro Display", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  headline_weight: 700, em_style: 'normal', font_links: [],
  platform: 'ios', cutout: true, headline_lines: 2, device_max_w: 0.73,
  frame: 'black', sub_lines: 0, scrim: 0.35,
  background_image: null, background_position: 'center', scene: null,
};

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function fail(message) {
  console.error(message);
  process.exit(1);
}

function findBrowser() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  for (const candidate of BROWSERS) if (fs.existsSync(candidate)) return candidate;
  for (const dir of (process.env.PATH || '').split(path.delimiter)) {
    for (const name of BROWSER_COMMANDS) {
      const candidate = path.join(dir, name);
      if (fs.existsSync(candidate)) return candidate;
    }
  }
  fail('No Chromium-based browser found. Install Chrome or set CHROME_PATH.');
}

function resolvePath(value, baseDir) {
  const expanded = value.startsWith('~') ? path.join(os.homedir(), value.slice(1)) : value;
  return path.isAbsolute(expanded) ? expanded : path.join(baseDir, expanded);
}

const escapeHtml = text => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function isDark(color) {
  const m = /^#?([0-9a-f]{6})$/i.exec(color.trim());
  if (!m) return true;
  const [r, g, b] = [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16));
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 < 0.5;
}

function headlineHtml(text) {
  return escapeHtml(text.replace(/\\n/g, '\n'))
    .replace(/\*([\s\S]+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

function buildPage(template, theme, image, baseDir, size) {
  const t = { ...THEME_DEFAULTS, ...theme };
  for (const key of Object.keys(THEME_DEFAULTS)) if (key in image) t[key] = image[key];
  const dark = isDark(t.bg);
  t.bg2 ??= `color-mix(in srgb, ${t.bg} 72%, ${dark ? '#000' : '#fff'})`;
  t.accent2 ??= t.accent;
  t.text ??= dark ? '#ffffff' : '#111114';
  t.line ??= dark ? 'rgba(255,255,255,.2)' : 'rgba(0,0,0,.1)';

  const shot = resolvePath(image.screenshot, baseDir);
  if (!fs.existsSync(shot)) fail(`screenshot not found: ${shot}`);

  let bgImage = 'none';
  if (t.background_image) {
    const bgPath = resolvePath(t.background_image, baseDir);
    if (!fs.existsSync(bgPath)) fail(`background image not found: ${bgPath}`);
    bgImage = `url("${pathToFileURL(bgPath).href}")`;
  }

  // An HTML scene fragment is injected first so it can use the same {{PLACEHOLDERS}}.
  let sceneHtml = '';
  if (t.scene) {
    const scenePath = resolvePath(t.scene, baseDir);
    if (!fs.existsSync(scenePath)) fail(`scene not found: ${scenePath}`);
    const sceneVars = { ...(theme.scene_vars || {}), ...(image.scene_vars || {}) };
    sceneHtml = `<script>window.SCENE = ${JSON.stringify(sceneVars)};</script>\n${fs.readFileSync(scenePath, 'utf8')}`;
  }

  const values = {
    WIDTH: size[0], HEIGHT: size[1],
    BG: t.bg, BG2: t.bg2, ACCENT: t.accent, ACCENT2: t.accent2, TEXT: t.text, LINE: t.line,
    HEADLINE_FONT: t.headline_font, HEADLINE_WEIGHT: t.headline_weight, EM_STYLE: t.em_style,
    HEADLINE_LINES: t.headline_lines, DEVICE_MAX_W: t.device_max_w,
    FONT_LINKS: t.font_links.map(u => `<link rel="stylesheet" href="${escapeHtml(u)}">`).join('\n'),
    PATTERN: image.pattern || 'none',
    BG_IMAGE_CSS: bgImage, BG_POSITION: t.background_position,
    PHOTO_CLASS: t.background_image ? 'has-photo' : '', SCENE_CLASS: t.scene ? 'has-scene' : '',
    SCRIM: t.scrim, FRAME: t.frame,
    SUB_LINES: t.sub_lines || (image.sub ? 2 : 0), SUB_HTML: escapeHtml(image.sub || ''),
    PLATFORM: t.platform, CUTOUT_CLASS: t.cutout ? '' : 'no-cutout',
    EYEBROW: escapeHtml(image.eyebrow || ''), HEADLINE_HTML: headlineHtml(image.headline || ''),
    SCREENSHOT: pathToFileURL(shot).href,
  };
  let page = template.split('{{SCENE_HTML}}').join(sceneHtml);
  for (const [key, value] of Object.entries(values)) page = page.split(`{{${key}}}`).join(String(value));
  return { page, theme: t };
}

/*
Screenshot url to out and return the dumped DOM plus any page script errors.

One run does both, so the reported geometry belongs to the captured frame.
Chrome finishes the work but does not always exit on its own (seen on macOS
and in sandboxed shells), so poll for the result instead of waiting for exit.
*/
async function chrome(browser, workDir, size, url, out, timeoutMs = 90000) {
  const domPath = path.join(workDir, 'chrome-stdout.txt');
  const errPath = path.join(workDir, 'chrome-stderr.txt');
  const stdout = fs.openSync(domPath, 'w');
  const stderr = fs.openSync(errPath, 'w');
  const proc = spawn(browser, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
    '--allow-file-access-from-files', '--enable-logging=stderr', `--user-data-dir=${path.join(workDir, 'profile')}`,
    '--force-device-scale-factor=1', `--window-size=${size[0]},${size[1]}`, '--virtual-time-budget=10000',
    `--screenshot=${out}`, '--dump-dom', url,
  ], { stdio: ['ignore', stdout, stderr] });
  let exited = false;
  proc.on('exit', () => { exited = true; });
  proc.on('error', error => fail(`could not start the browser: ${error.message}`));

  const sizes = [];
  const deadline = Date.now() + timeoutMs;
  while (!exited && Date.now() < deadline) {
    await sleep(250);
    sizes.push(fs.existsSync(out) ? fs.statSync(out).size : 0);
    const settled = sizes.length >= 3 && sizes.at(-1) > 0 && sizes.at(-1) === sizes.at(-2) && sizes.at(-1) === sizes.at(-3);
    if (settled && fs.readFileSync(domPath, 'utf8').includes('</html>')) break;
  }
  if (!exited) {
    proc.kill('SIGTERM');
    for (let i = 0; i < 20 && !exited; i++) await sleep(250);
    if (!exited) proc.kill('SIGKILL');
  }
  fs.closeSync(stdout);
  fs.closeSync(stderr);
  // JavaScript errors from the page (a broken scene or template) show up as console lines
  const jsErrors = [...fs.readFileSync(errPath, 'utf8').matchAll(/CONSOLE[:(]\d+\)?\] "((?:Uncaught|Error)[^"]*)"/g)].map(m => m[1]);
  return { dom: fs.readFileSync(domPath, 'utf8'), jsErrors };
}

// Both stores reject transparency. Chrome writes opaque pages as RGB; confirm it, and the size.
function checkPng(file, size) {
  const header = fs.readFileSync(file).subarray(0, 26);
  const [width, height, colorType] = [header.readUInt32BE(16), header.readUInt32BE(20), header[25]];
  const warnings = [];
  if (width !== size[0] || height !== size[1]) warnings.push(`browser produced ${width}x${height}, expected ${size[0]}x${size[1]}`);
  if (colorType === 4 || colorType === 6) warnings.push('PNG has an alpha channel; give the page an opaque background and re-render');
  return warnings;
}

async function main() {
  const arg = process.argv[2];
  if (!arg || arg === '-h' || arg === '--help') {
    const source = fs.readFileSync(fileURLToPath(import.meta.url), 'utf8');
    console.log(source.slice(source.indexOf('/*') + 3, source.indexOf('*/')).trim());
    process.exit(arg ? 0 : 1);
  }
  const configPath = path.resolve(resolvePath(arg, process.cwd()));
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const baseDir = path.dirname(configPath);
  const skillDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

  const templatePath = config.template ? resolvePath(config.template, baseDir) : path.join(skillDir, 'assets', 'template.html');
  const template = fs.readFileSync(templatePath, 'utf8');
  const size = (config.size || '1290x2796').toLowerCase().split('x').map(Number);
  const outDir = resolvePath(config.out_dir || 'stores', baseDir);
  fs.mkdirSync(outDir, { recursive: true });

  const browser = findBrowser();
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'store-shots-'));
  const results = [];
  try {
    for (const [index, image] of config.images.entries()) {
      const { page, theme } = buildPage(template, config.theme || {}, image, baseDir, size);
      const pagePath = path.join(workDir, `page-${index + 1}.html`);
      fs.writeFileSync(pagePath, page);
      const out = path.join(outDir, image.out || `${String(index + 1).padStart(2, '0')}.png`);
      fs.rmSync(out, { force: true });

      const { dom, jsErrors } = await chrome(browser, workDir, size, pathToFileURL(pagePath).href, out);
      if (!fs.existsSync(out)) fail(`browser produced no screenshot for ${path.basename(out)}`);
      const match = /data-meta="([^"]+)"/.exec(dom);
      const meta = match ? JSON.parse(match[1].replace(/&quot;/g, '"').replace(/&amp;/g, '&')) : {};

      const warnings = [...checkPng(out, size), ...jsErrors.map(e => `page script error: ${e}`)];
      if (!match) warnings.push('page never reported ready; check the screenshot path, fonts, and page script errors');
      if ((meta.screenshot_scale || 0) > 1.05) warnings.push('screenshot was upscaled; use a higher-resolution source or a smaller device_max_w');
      if (theme.platform === 'android' && Math.max(...size) > 2 * Math.min(...size)) {
        warnings.push('Google Play rejects images whose long side exceeds 2x the short side; try size 1080x1920');
      }
      results.push({ out, canvas: size, ...meta, warnings });
      if (config.keep_html) fs.copyFileSync(pagePath, out.replace(/\.png$/i, '.html'));
    }
  } finally {
    fs.rmSync(workDir, { recursive: true, force: true });
  }
  console.log(JSON.stringify(results, null, 2));
}

main();
