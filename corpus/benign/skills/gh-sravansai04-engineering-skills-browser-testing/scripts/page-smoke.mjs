#!/usr/bin/env node
// page-smoke.mjs - one-shot browser smoke check for a single URL.
//
// Loads the page at one or more viewport widths and reports, as JSON on stdout:
//   - console errors and warnings, uncaught page errors
//   - failed requests (network errors) and HTTP responses >= 400
//   - horizontal overflow (page wider than the viewport) plus the elements where it starts
//   - a screenshot per width
//
// Playwright is resolved from the CURRENT WORKING DIRECTORY (your project), not from
// this file's location, so run it from a directory where `playwright` or
// `@playwright/test` is installed. Nothing is installed by this script.
//
// This is a verification aid for a human or agent looking at a change. It is NOT a
// substitute for a real test: it waits for "network idle" as a heuristic, which is
// fine for a one-off look and wrong for an assertion in a test suite.
//
// Self-test (--selftest): first checks the argument parser, the request classifiers,
// and the problem counting without a browser. Then, when Playwright resolves from the
// current directory, it loads three pages headless: fixtures/overflow.html (a clipped
// carousel, an off-canvas fixed drawer, a scrolling strip, and one genuinely too-wide
// table - at 375 px the table must be the only culprit, at 1280 px the page is clean),
// a local page with one console error, one 404 fetch and one uncaught exception (each
// counted once), and a closed port (verdict "unreachable").
//
// Exit codes: 0 = no problems found, 1 = problems found,
//             2 = could not run (bad arguments, Playwright or browser missing,
//                 or the URL did not load at any width - usually a server that is down).
// With --selftest: 0 = every check passed, 1 = a check failed, 2 = the parser checks
// passed but the browser half could not run (Playwright or the browser is missing).

import { createRequire } from 'node:module';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const USAGE = `Usage: node page-smoke.mjs <url> [options]
       node page-smoke.mjs --selftest [--browser <name>] [--channel <name>]

Options:
  --widths <list>          comma-separated viewport widths (default: 375,768,1280)
  --height <px>            viewport height (default: 900)
  --out <dir>              screenshot directory (default: ./smoke-artifacts)
  --browser <name>         chromium | firefox | webkit (default: chromium)
  --channel <name>         use an installed branded browser, e.g. chrome or msedge
  --storage-state <file>   start from a saved login state (cookies + localStorage)
  --wait-for-text <text>   wait until this text is visible before checking
  --timeout <ms>           navigation / wait timeout (default: 15000)
  --full-page              capture full-page screenshots
  --color-scheme <scheme>  light | dark
  --ignore <regex>         drop console/network entries matching this regex (repeatable)
  --headed                 show the browser window (needs a display; agents should not use it)
  --selftest               check this script against its bundled fixtures (run it from a
                           directory where Playwright resolves; --browser and --channel apply)
  -h, --help               print this help

Output: JSON with a per-width result and a "problems" count. A missing /favicon.ico is
listed under "notes" and not counted: browsers request it on their own, often for one
width only, and it says nothing about the page under test.

Exit codes: 0 clean, 1 problems found, 2 could not run (bad arguments, Playwright or
browser missing, or the URL never loaded at any width). With --selftest: 0 all checks
passed, 1 a check failed, 2 the browser half could not run.`;

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));

// Usage errors are thrown, not exited on the spot, so --selftest can check them.
class UsageError extends Error {}

function fail(message) {
  process.stderr.write(`page-smoke: ${message}\n`);
  process.exit(2);
}

function usageError(message) {
  throw new UsageError(message);
}

function positiveInt(flag, value) {
  const n = Number(value);
  if (!Number.isInteger(n) || n <= 0) usageError(`bad ${flag}: ${value} (expected a positive integer)`);
  return n;
}

function parseArgs(argv) {
  const opts = {
    url: null,
    widths: [375, 768, 1280],
    height: 900,
    out: 'smoke-artifacts',
    browser: 'chromium',
    channel: undefined,
    storageState: undefined,
    waitForText: undefined,
    timeout: 15000,
    fullPage: false,
    colorScheme: undefined,
    ignore: [],
    headed: false,
    help: false,
    selftest: false,
  };
  const takesValue = new Set([
    '--widths', '--height', '--out', '--browser', '--channel', '--storage-state',
    '--wait-for-text', '--timeout', '--color-scheme', '--ignore',
  ]);
  for (let i = 0; i < argv.length; i++) {
    let arg = argv[i];
    let value;
    if (arg.startsWith('--') && arg.includes('=')) {
      [arg, value] = [arg.slice(0, arg.indexOf('=')), arg.slice(arg.indexOf('=') + 1)];
    }
    if (takesValue.has(arg) && value === undefined) {
      value = argv[++i];
      if (value === undefined) usageError(`${arg} needs a value\n\n${USAGE}`);
    }
    switch (arg) {
      case '-h':
      case '--help':
        opts.help = true;
        return opts;
      case '--selftest':
        opts.selftest = true;
        break;
      case '--widths':
        opts.widths = value.split(',').map((w) => Number(w.trim()));
        if (opts.widths.some((w) => !Number.isInteger(w) || w < 200)) usageError(`bad --widths: ${value}`);
        break;
      case '--height':
        opts.height = positiveInt('--height', value);
        break;
      case '--out':
        opts.out = value;
        break;
      case '--browser':
        if (!['chromium', 'firefox', 'webkit'].includes(value)) usageError(`bad --browser: ${value}`);
        opts.browser = value;
        break;
      case '--channel':
        opts.channel = value;
        break;
      case '--storage-state':
        if (!fs.existsSync(value)) usageError(`storage state file not found: ${value}`);
        opts.storageState = value;
        break;
      case '--wait-for-text':
        opts.waitForText = value;
        break;
      case '--timeout':
        opts.timeout = positiveInt('--timeout', value);
        break;
      case '--full-page':
        opts.fullPage = true;
        break;
      case '--color-scheme':
        if (!['light', 'dark'].includes(value)) usageError(`bad --color-scheme: ${value}`);
        opts.colorScheme = value;
        break;
      case '--ignore':
        try {
          opts.ignore.push(new RegExp(value));
        } catch {
          usageError(`bad --ignore regex: ${value}`);
        }
        break;
      case '--headed':
        opts.headed = true;
        break;
      default:
        if (arg.startsWith('-')) usageError(`unknown option ${arg}\n\n${USAGE}`);
        if (opts.url) usageError(`only one URL is supported (got ${opts.url} and ${arg})`);
        opts.url = arg;
    }
  }
  if (opts.selftest) return opts; // the self-test brings its own URLs
  if (!opts.url) usageError(`missing <url>\n\n${USAGE}`);
  let parsed;
  try {
    parsed = new URL(opts.url);
  } catch {
    parsed = null;
  }
  if (!parsed || !['http:', 'https:', 'file:'].includes(parsed.protocol)) {
    usageError(`not an absolute http(s) or file URL: ${opts.url} (include the scheme, e.g. http://localhost:3000/)`);
  }
  opts.requestedUrl = parsed.href;
  return opts;
}

const PLAYWRIGHT_HINT =
  'Run this from a project that has playwright or @playwright/test installed, or make a scratch dir:\n' +
  '  mkdir -p /tmp/pw-smoke && cd /tmp/pw-smoke && npm init -y && npm i -D playwright && npx playwright install chromium';

function resolvePlaywright() {
  const requireFromCwd = createRequire(path.join(process.cwd(), '__page_smoke__.cjs'));
  for (const name of ['playwright', '@playwright/test', 'playwright-core']) {
    try {
      return requireFromCwd(name);
    } catch {
      // try the next candidate
    }
  }
  return null;
}

function loadPlaywright() {
  return resolvePlaywright() ?? fail(`could not resolve Playwright from ${process.cwd()}.\n${PLAYWRIGHT_HINT}`);
}

// Launches the requested browser, or returns { error } with an install hint.
async function launchBrowser(pw, opts) {
  const browserType = pw[opts.browser];
  if (!browserType) return { error: `this Playwright build has no ${opts.browser} support` };
  try {
    return { browser: await browserType.launch({ headless: !opts.headed, channel: opts.channel }) };
  } catch (err) {
    return {
      error:
        `could not launch ${opts.channel ?? opts.browser}: ${String(err?.message ?? err).split('\n')[0]}\n` +
        `Install the browser with: npx playwright install ${opts.browser}` +
        (opts.browser === 'chromium' ? ' (or pass --channel chrome to use an installed Chrome)' : ''),
    };
  }
}

const isAborted = (errorText) => /ERR_ABORTED|NS_BINDING_ABORTED|cancelled/i.test(errorText ?? '');
const stripLine = (source) => (source ?? '').replace(/:\d+$/, '');
const isFaviconMiss = (entry) =>
  entry.text.startsWith('Failed to load resource') && /\/favicon\.ico$/.test(stripLine(entry.source));

// Runs inside the page. Finds where horizontal overflow STARTS, ignoring boxes that stick
// out of the viewport but cannot widen the document.
function measureOverflow() {
  const root = document.documentElement;
  const body = document.body;
  const limit = root.clientWidth + 1;
  const CLIPPING = new Set(['hidden', 'clip', 'auto', 'scroll']);
  const memo = new Map();

  // True when el cannot widen the document: it is position:fixed, or it sits inside a
  // fixed element, or inside an ancestor below <body> that clips or scrolls horizontally
  // (carousel tracks, overflow-x:auto table wrappers). The clipping ancestor itself is
  // still measured, so a container that is too wide is reported in place of its content.
  const contained = (el) => {
    if (!el || el === body || el === root) return false;
    if (memo.has(el)) return memo.get(el);
    let verdict = getComputedStyle(el).position === 'fixed';
    const parent = el.parentElement;
    if (!verdict && parent && parent !== body && parent !== root) {
      verdict = CLIPPING.has(getComputedStyle(parent).overflowX) || contained(parent);
    }
    memo.set(el, verdict);
    return verdict;
  };

  // A locatable selector: from the nearest ancestor with an id (or up to 6 levels),
  // with :nth-of-type wherever a tag repeats among siblings.
  const segment = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) return `${s}#${CSS.escape(el.id)}`;
    const classes = typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter(Boolean) : [];
    for (const c of classes.slice(0, 2)) s += `.${CSS.escape(c)}`;
    const siblings = el.parentElement ? [...el.parentElement.children].filter((c) => c.tagName === el.tagName) : [];
    if (siblings.length > 1) s += `:nth-of-type(${siblings.indexOf(el) + 1})`;
    return s;
  };
  const selectorFor = (el) => {
    const parts = [];
    for (let cur = el; cur && parts.length < 6; cur = cur.parentElement) {
      parts.unshift(segment(cur));
      if (cur.id || cur === body || cur === root) break;
    }
    return parts.join(' > ');
  };
  // innerText (not textContent): rendered text only, with spaces between blocks, no <script> bodies.
  const label = (el) =>
    ((el.innerText ?? el.textContent ?? '').replace(/\s+/g, ' ').trim() ||
      el.getAttribute('aria-label') ||
      el.getAttribute('alt') ||
      '').slice(0, 40);

  const candidates = [root, ...(body ? [body, ...body.querySelectorAll('*')] : [])];
  const over = new Set();
  for (const el of candidates) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > limit && !contained(el)) over.add(el);
  }
  // Report where the overflow begins: an overflowing element whose parent fits. Its own
  // box is too wide or pushed too far; its overflowing descendants only ride along.
  const starts = [...over]
    .filter((el) => !over.has(el.parentElement))
    .map((el) => ({ el, rect: el.getBoundingClientRect() }))
    .sort((a, b) => b.rect.right - a.rect.right);

  return {
    overflowing: root.scrollWidth > limit,
    scrollWidth: root.scrollWidth,
    clientWidth: root.clientWidth,
    culprits: starts.slice(0, 5).map(({ el, rect }) => {
      const entry = { selector: selectorFor(el), right: Math.round(rect.right), width: Math.round(rect.width) };
      const text = label(el);
      if (text) entry.text = text;
      const testId = el.getAttribute('data-testid');
      if (testId) entry.testId = testId;
      return entry;
    }),
  };
}

async function checkWidth(browser, opts, width) {
  const contextOptions = { viewport: { width, height: opts.height } };
  if (opts.storageState) contextOptions.storageState = opts.storageState;
  if (opts.colorScheme) contextOptions.colorScheme = opts.colorScheme;
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();

  const keep = (text) => !opts.ignore.some((re) => re.test(text));
  const result = {
    width,
    finalUrl: null,
    status: null,
    title: null,
    problems: 0,
    consoleErrors: [],
    consoleWarnings: [],
    pageErrors: [],
    failedRequests: [],
    abortedRequests: [],
    httpErrors: [],
    horizontalOverflow: null,
    overflowCulprits: [],
    notes: [],
    screenshot: null,
    error: null,
  };
  let documentUrl = null;

  page.on('console', (msg) => {
    const type = msg.type();
    if (type !== 'error' && type !== 'warning') return;
    const loc = msg.location();
    const entry = { text: msg.text(), source: loc?.url ? `${loc.url}:${loc.lineNumber}` : undefined };
    if (!keep(`${entry.text} ${entry.source ?? ''}`)) return;
    (type === 'error' ? result.consoleErrors : result.consoleWarnings).push(entry);
  });
  page.on('pageerror', (err) => {
    if (keep(err.message)) result.pageErrors.push(err.message);
  });
  page.on('requestfailed', (req) => {
    const errorText = req.failure()?.errorText;
    const entry = { method: req.method(), url: req.url(), error: errorText };
    if (!keep(`${entry.url} ${errorText}`)) return;
    (isAborted(errorText) ? result.abortedRequests : result.failedRequests).push(entry);
  });
  page.on('response', (res) => {
    if (res.status() < 400) return;
    const entry = { method: res.request().method(), url: res.url(), status: res.status() };
    if (keep(`${entry.url} ${entry.status}`)) result.httpErrors.push(entry);
  });

  try {
    const response = await page.goto(opts.url, { waitUntil: 'load', timeout: opts.timeout });
    result.status = response ? response.status() : null;
    documentUrl = response ? response.url() : null;
    if (opts.waitForText) {
      await page.getByText(opts.waitForText).first().waitFor({ state: 'visible', timeout: opts.timeout });
    }
    // Heuristic settle for late XHRs and lazy chunks. Acceptable for a one-off look;
    // never copy this into a test (assert on a user-visible outcome instead).
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    result.finalUrl = page.url();
    result.title = await page.title();

    const overflow = await page.evaluate(measureOverflow);
    result.horizontalOverflow = overflow.overflowing
      ? { scrollWidth: overflow.scrollWidth, clientWidth: overflow.clientWidth }
      : false;
    result.overflowCulprits = overflow.overflowing ? overflow.culprits : [];

    fs.mkdirSync(opts.out, { recursive: true });
    const slug =
      new URL(opts.url).pathname.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').slice(-60) || 'root';
    result.screenshot = path.resolve(opts.out, `${slug}-${width}.png`);
    await page.screenshot({ path: result.screenshot, fullPage: opts.fullPage });
  } catch (err) {
    result.error = String(err?.message ?? err).split('\n')[0];
  } finally {
    await context.close();
  }

  // Chromium also logs every failed HTTP response as a console error ("Failed to load
  // resource: ..."). Drop those when the same URL is already reported as a network
  // problem, so one broken request is counted once.
  const reported = new Set([...result.httpErrors, ...result.failedRequests].map((e) => e.url));
  result.consoleErrors = result.consoleErrors.filter(
    (e) => !(e.text.startsWith('Failed to load resource') && reported.has(stripLine(e.source))),
  );
  // The browser fetches /favicon.ico by itself; that request never reaches the page's
  // 'response' event and is usually made once per browser, so it would show up as a
  // console error at one width only. Report it, but do not count it.
  for (const e of result.consoleErrors.filter(isFaviconMiss)) {
    result.notes.push(`favicon not found: ${stripLine(e.source)} (browser-initiated request; not counted)`);
  }
  result.consoleErrors = result.consoleErrors.filter((e) => !isFaviconMiss(e));

  result.problems = countProblems(result, documentUrl, opts.requestedUrl);
  return result;
}

// One defect, one count: a 4xx/5xx document is already in httpErrors, and a navigation
// that failed outright is already in failedRequests.
function countProblems(r, documentUrl, requestedUrl) {
  const documentInHttpErrors = documentUrl !== null && r.httpErrors.some((e) => e.url === documentUrl);
  const failed = r.error ? r.failedRequests.filter((e) => e.url !== requestedUrl) : r.failedRequests;
  return (
    (r.error ? 1 : 0) +
    (r.status !== null && r.status >= 400 && !documentInHttpErrors ? 1 : 0) +
    r.consoleErrors.length +
    r.pageErrors.length +
    failed.length +
    r.httpErrors.length +
    (r.horizontalOverflow ? 1 : 0)
  );
}

// Nothing loaded anywhere: an environment problem, not a page problem.
function summarize(opts, results) {
  const unreachable = results.every((r) => r.status === null && r.error !== null);
  const problems = results.reduce((n, r) => n + r.problems, 0);
  return {
    url: opts.url,
    browser: opts.channel ?? opts.browser,
    problems: unreachable ? null : problems,
    verdict: unreachable ? 'unreachable' : problems === 0 ? 'clean' : 'problems-found',
    results,
  };
}

// ---------------------------------------------------------------------------
// Self-test
// ---------------------------------------------------------------------------

// One defect of each kind the counter must count exactly once. The data: icon stops the
// browser from requesting /favicon.ico, so the expected counts do not depend on it.
const DEFECT_PAGE = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>page-smoke defects fixture</title>
<link rel="icon" href="data:,"></head>
<body><h1>Defects</h1><script>
console.warn('selftest warning');
console.error('selftest console error');
fetch('/missing.json').catch(() => {});
setTimeout(() => { throw new Error('selftest uncaught error'); }, 0);
</script></body></html>`;

function serveDefects(req, res) {
  if (req.url === '/') {
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    res.end(DEFECT_PAGE);
  } else {
    res.writeHead(404, { 'content-type': 'text/plain' });
    res.end('not found');
  }
}

function listen(server) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

async function closedPort() {
  const server = await listen(http.createServer());
  const { port } = server.address();
  await new Promise((resolve) => server.close(resolve));
  return port;
}

async function selftest(cliOpts) {
  const checks = [];
  const check = (name, ok, detail) => checks.push({ name, ok: Boolean(ok), detail });
  const rejects = (argv) => {
    try {
      parseArgs(argv);
      return false;
    } catch (err) {
      return err instanceof UsageError;
    }
  };

  // 1. Argument parsing.
  const defaults = parseArgs(['http://localhost:3000/']);
  check(
    'defaults to widths 375,768,1280 and ./smoke-artifacts',
    defaults.widths.join() === '375,768,1280' && defaults.out === 'smoke-artifacts',
    { widths: defaults.widths, out: defaults.out },
  );
  const custom = parseArgs(['--widths=320,1440', 'http://localhost:3000/x', '--ignore', 'ads\\.example', '--color-scheme', 'dark']);
  check(
    'accepts --flag=value, options after the URL, and an --ignore regex',
    custom.widths.join() === '320,1440' && custom.ignore.length === 1 && custom.ignore[0].test('ads.example') &&
      custom.colorScheme === 'dark',
  );
  check('-h and --help ask for usage', parseArgs(['-h']).help && parseArgs(['http://a.example/', '--help']).help);
  for (const [label, argv] of [
    ['a missing URL', []],
    ['a URL without a scheme', ['localhost:3000']],
    ['an unsupported scheme', ['ftp://a.example/']],
    ['two URLs', ['http://a.example/', 'http://b.example/']],
    ['an unknown option', ['--nope', 'http://a.example/']],
    ['an option with no value', ['http://a.example/', '--out']],
    ['a width under 200', ['--widths', '100', 'http://a.example/']],
    ['a bad --browser', ['--browser', 'safari', 'http://a.example/']],
    ['a bad --ignore regex', ['--ignore', '(', 'http://a.example/']],
    ['a missing --storage-state file', ['--storage-state', path.join(os.tmpdir(), 'no-such-auth-state.json'), 'http://a.example/']],
  ]) {
    check(`rejects ${label}`, rejects(argv));
  }

  // 2. Classifiers and counting, no browser needed.
  check(
    'treats ERR_ABORTED and NS_BINDING_ABORTED as aborted, a refused connection as failed',
    isAborted('net::ERR_ABORTED') && isAborted('NS_BINDING_ABORTED') && !isAborted('net::ERR_CONNECTION_REFUSED'),
  );
  const miss = (source) => ({ text: 'Failed to load resource: the server responded with a status of 404 (Not Found)', source });
  check(
    'recognizes a missing favicon and nothing else',
    isFaviconMiss(miss('http://x.example/favicon.ico:0')) && !isFaviconMiss(miss('http://x.example/app.js:0')),
  );
  const blank = { error: null, status: 200, consoleErrors: [], pageErrors: [], failedRequests: [], httpErrors: [], horizontalOverflow: false };
  const doc = 'http://x.example/';
  check('counts a clean result as 0', countProblems(blank, doc, doc) === 0);
  check('counts a 404 document once', countProblems({ ...blank, status: 404, httpErrors: [{ url: doc, status: 404 }] }, doc, doc) === 1);
  check(
    'counts a failed navigation once',
    countProblems({ ...blank, status: null, error: 'net::ERR_CONNECTION_REFUSED', failedRequests: [{ url: doc }] }, null, doc) === 1,
  );

  // 3. Real pages in a real browser, when one is available.
  let skipped = null;
  let browser = null;
  const pw = resolvePlaywright();
  if (!pw) {
    skipped = `Playwright did not resolve from ${process.cwd()}.\n${PLAYWRIGHT_HINT}`;
  } else {
    const launched = await launchBrowser(pw, cliOpts);
    if (launched.error) skipped = launched.error;
    else browser = launched.browser;
  }
  if (browser) {
    const out = fs.mkdtempSync(path.join(os.tmpdir(), 'page-smoke-selftest-'));
    const server = await listen(http.createServer(serveDefects));
    const optsFor = (url, extra = []) => ({ ...parseArgs([url, ...extra]), out });
    try {
      const fixture = optsFor(pathToFileURL(path.join(SCRIPT_DIR, 'fixtures', 'overflow.html')).href);
      const narrow = await checkWidth(browser, fixture, 375);
      check(
        'overflow fixture at 375 px: page measured 900 px wide',
        narrow.horizontalOverflow && narrow.horizontalOverflow.scrollWidth === 900,
        narrow.horizontalOverflow || narrow.error,
      );
      check(
        'overflow fixture at 375 px: the table is the only culprit',
        narrow.overflowCulprits.length === 1 &&
          narrow.overflowCulprits[0].selector === 'section#report > div > table.report-table',
        narrow.overflowCulprits,
      );
      check(
        'overflow fixture at 375 px: one problem and a screenshot on disk',
        narrow.problems === 1 && narrow.screenshot !== null && fs.existsSync(narrow.screenshot),
        { problems: narrow.problems, screenshot: narrow.screenshot },
      );
      const wide = await checkWidth(browser, fixture, 1280);
      check('overflow fixture at 1280 px: clean', wide.problems === 0 && wide.horizontalOverflow === false, {
        problems: wide.problems,
        error: wide.error,
      });

      const page = `http://127.0.0.1:${server.address().port}/`;
      const defects = await checkWidth(browser, optsFor(page), 375);
      check(
        'defects page: one console error, the 404 not counted twice',
        defects.consoleErrors.length === 1 && defects.consoleErrors[0].text === 'selftest console error',
        defects.consoleErrors,
      );
      check(
        'defects page: one uncaught error, one HTTP 404, warnings listed but not counted, 3 problems',
        defects.pageErrors.length === 1 &&
          defects.httpErrors.length === 1 &&
          defects.consoleWarnings.some((w) => w.text === 'selftest warning') &&
          defects.problems === 3,
        { pageErrors: defects.pageErrors, httpErrors: defects.httpErrors, problems: defects.problems },
      );
      const ignored = await checkWidth(browser, optsFor(page, ['--ignore', 'selftest console error']), 375);
      check('--ignore drops a matching console error', ignored.consoleErrors.length === 0 && ignored.problems === 2, {
        consoleErrors: ignored.consoleErrors,
        problems: ignored.problems,
      });

      const down = optsFor(`http://127.0.0.1:${await closedPort()}/`);
      const refused = await checkWidth(browser, down, 375);
      check(
        'closed port: the failed navigation counts once and the verdict is unreachable',
        refused.error !== null && refused.problems === 1 && summarize(down, [refused]).verdict === 'unreachable',
        { error: refused.error, problems: refused.problems },
      );
      check(
        'summary verdicts: clean, and problems-found when any width has a problem',
        summarize(fixture, [wide]).verdict === 'clean' && summarize(fixture, [narrow, wide]).verdict === 'problems-found',
      );
    } finally {
      await browser.close();
      await new Promise((resolve) => server.close(resolve));
      fs.rmSync(out, { recursive: true, force: true });
    }
  }

  for (const c of checks) {
    const detail = !c.ok && c.detail !== undefined ? `\n      got: ${JSON.stringify(c.detail)}` : '';
    process.stdout.write(`${c.ok ? 'ok  ' : 'FAIL'}  ${c.name}${detail}\n`);
  }
  const failed = checks.filter((c) => !c.ok).length;
  if (failed > 0) {
    process.stdout.write(`page-smoke selftest: ${failed} of ${checks.length} checks failed\n`);
    return 1;
  }
  if (skipped) {
    process.stdout.write(`page-smoke selftest: ${checks.length} parser and counting checks passed; browser checks NOT run\n`);
    process.stderr.write(`page-smoke: ${skipped}\n`);
    return 2;
  }
  process.stdout.write(`page-smoke selftest: all ${checks.length} checks passed\n`);
  return 0;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    if (err instanceof UsageError) fail(err.message);
    throw err;
  }
  if (opts.help) {
    process.stdout.write(`${USAGE}\n`);
    process.exit(0);
  }
  if (opts.selftest) process.exit(await selftest(opts));

  const pw = loadPlaywright();
  const launched = await launchBrowser(pw, opts);
  if (launched.error) fail(launched.error);
  const { browser } = launched;

  const results = [];
  try {
    for (const width of opts.widths) results.push(await checkWidth(browser, opts, width));
  } finally {
    await browser.close();
  }

  const summary = summarize(opts, results);
  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
  if (summary.verdict === 'unreachable') {
    process.stderr.write(`page-smoke: ${opts.url} did not load at any width (${results[0].error}). Is the server running?\n`);
    process.exit(2);
  }
  process.exit(summary.problems === 0 ? 0 : 1);
}

main().catch((err) => fail(String(err?.stack ?? err)));
