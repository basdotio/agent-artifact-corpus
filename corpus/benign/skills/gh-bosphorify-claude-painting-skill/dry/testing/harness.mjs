// A browser page for tests: the dry kit's scripts are served from /dry/ as render.mjs serves them, with no network.
import { chromium } from 'playwright-core';
import { readFile } from 'node:fs/promises';
import { dirname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const dry = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ORIGIN = 'http://dry.test';

// Open a page with `body` (HTML) and the given /dry/-relative `scripts` loaded in order. Returns { page, errors, done, close }:
// `errors` collects uncaught page errors, and done() waits for the page to set window.__done (or fails at the first page error).
export async function openPage({ body = '', scripts = [] } = {}) {
  const args = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'];
  const browser = await chromium.launch({ channel: 'chrome', args }).catch(() => chromium.launch({ args }));
  const page = await browser.newPage({ deviceScaleFactor: 1 });
  const errors = [];
  const crashed = new Promise((_, reject) => page.on('pageerror', e => { errors.push(e.message); reject(new Error(`page error: ${e.message}`)); }));
  crashed.catch(() => {});
  const html = `<!doctype html><meta charset="utf-8"><body>${body}${scripts.map(s => `<script src="/dry/${s}"></script>`).join('')}</body>`;
  await page.route(`${ORIGIN}/**`, async route => {
    const path = decodeURIComponent(new URL(route.request().url()).pathname);
    if (path === '/') return route.fulfill({ contentType: 'text/html', body: html });
    const file = resolve(dry, path.slice('/dry/'.length));
    if (!path.startsWith('/dry/') || !file.startsWith(dry + sep)) return route.fulfill({ status: 404 });
    try { await route.fulfill({ contentType: 'text/javascript', body: await readFile(file) }); } catch { await route.fulfill({ status: 404 }); }
  });
  await page.goto(`${ORIGIN}/`);
  return {
    page, errors,
    done: (timeout = 120_000) => Promise.race([page.waitForFunction(() => window.__done === true, null, { timeout, polling: 100 }), crashed]),
    close: () => browser.close(),
  };
}
