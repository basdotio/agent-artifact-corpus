// Capture helpers for a user manual. Run against a LOCAL or test environment only — never production.
//
// Config: MANUAL_CONFIG=<workspace>/manual.json (default ./manual.json). Shots land in <workspace>/shots/.
// Passwords come ONLY from environment variables (MANUAL_PW_<ROLE>, falling back to MANUAL_PW). They are never
// read from or written to a file and never printed, so they cannot leak into the workspace, a deck or a chat.
// Every session checks who it is logged in as before use: a stale cookie or a wrong account is the classic way a
// manual ends up showing the wrong role.
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { createRequire } from 'module';
import path from 'path';
import { fileURLToPath } from 'url';

export const CONFIG = path.resolve(process.env.MANUAL_CONFIG ?? 'manual.json');
export const WS = path.dirname(CONFIG);
const cfg = JSON.parse(readFileSync(CONFIG, 'utf8'));
const C = cfg.capture ?? {};
const HERE = path.dirname(fileURLToPath(import.meta.url));

// Playwright is not bundled with the skill. Resolve it from the target app's repo (it is often a devDependency
// there), then the workspace, then the skill itself; createRequire also honours NODE_PATH.
function loadPlaywright() {
  const roots = [cfg.repo && path.resolve(WS, cfg.repo.replace(/^~(?=\/)/, process.env.HOME)), WS, HERE].filter(Boolean);
  for (const r of roots) {
    try { return createRequire(path.join(r, 'noop.js'))('playwright'); } catch { /* next root */ }
  }
  throw new Error('playwright not found. Install it where the capture can resolve it, e.g. in the workspace:\n'
    + `  cd ${WS} && npm i -D playwright && npx playwright install chromium\n`
    + '(or set "repo" in manual.json to a project that already has it, or point NODE_PATH at a node_modules)');
}
const { chromium } = loadPlaywright();

export const BASE = (process.env.MANUAL_BASE_URL ?? C.base_url ?? 'http://localhost:3000').replace(/\/$/, '');
// The session types passwords into the login form, so a base_url pointing at a remote host would send them there.
// Refuse anything that is not loopback unless the host is listed in capture.allow_hosts on purpose.
const LOOPBACK = ['localhost', '127.0.0.1', '[::1]'];
const host = new URL(BASE).hostname;
if (!LOOPBACK.includes(host) && !(C.allow_hosts ?? []).includes(host)) {
  throw new Error(`capture URL ${BASE} is not loopback — add "${host}" to capture.allow_hosts if it really is a test environment`);
}
const LOCALE = C.locale ?? 'en';
const TZ = C.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
const [VW, VH] = C.viewport ?? [1600, 900];
const LOGIN = { url: '/login', email: '#email', password: '#password', submit: 'button[type=submit]', ...(C.login ?? {}) };
// replay.mjs sets MANUAL_SHOTS=shots-new so a refresh never overwrites the accepted shots before diff_shots.py.
export const OUT = path.join(WS, process.env.MANUAL_SHOTS ?? 'shots') + '/';
mkdirSync(OUT, { recursive: true });

export const USERS = C.users ?? {};

const envName = (role) => `MANUAL_PW_${role.toUpperCase().replace(/[^A-Z0-9]/g, '_')}`;
function passwordFor(role) {
  const pw = process.env[envName(role)] ?? process.env.MANUAL_PW;
  if (!pw) throw new Error(`no password for role "${role}": set ${envName(role)} (or MANUAL_PW) in the environment`);
  return pw;
}

const dig = (obj, dotted) => dotted.split('.').reduce((o, k) => (o == null ? o : o[k]), obj);

let browser;
export async function session(role) {
  if (!USERS[role]) throw new Error(`no capture.users.${role} in manual.json`);
  const pw = passwordFor(role);
  browser ??= await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: VW, height: VH }, locale: LOCALE, timezoneId: TZ });
  const page = await ctx.newPage();
  const loginUrl = new URL(LOGIN.url, BASE + '/');
  await page.goto(loginUrl.href);
  await page.fill(LOGIN.email, USERS[role]);
  await page.fill(LOGIN.password, pw);
  await Promise.all([
    page.waitForURL((u) => u.pathname !== loginUrl.pathname, { timeout: 30000 }),
    page.click(LOGIN.submit),
  ]);
  if (LOGIN.whoami) {
    const me = await (await page.request.get(new URL(LOGIN.whoami, BASE + '/').href)).json();
    const email = LOGIN.whoami_email ? dig(me, LOGIN.whoami_email) : (me.email ?? me.user?.email);
    if (String(email ?? '').toLowerCase() !== USERS[role].toLowerCase()) throw new Error(`logged in as ${email}, wanted ${USERS[role]}`);
  }
  return page;
}

/** Wait for the page to settle, then screenshot the viewport and record rects of `marks` (1-based callouts). */
export async function shot(page, name, marks = [], opts = {}) {
  await page.waitForLoadState('networkidle').catch(() => {});
  if (C.loading_selector) {
    await page.waitForFunction((s) => !document.querySelector(s), C.loading_selector, { timeout: 15000 }).catch(() => {});
  }
  await page.waitForTimeout(400);
  if (C.toast_selector && !opts.keepToasts) await page.evaluate((s) => document.querySelectorAll(s).forEach((e) => e.remove()), C.toast_selector);
  const locs = marks.map((m) => (typeof m === 'string' ? page.locator(m).first() : m.first()));
  const read = async () => {
    const rects = [];
    for (const [i, loc] of locs.entries()) {
      const b = await loc.boundingBox().catch(() => null);
      if (!b) throw new Error(`${name}: callout target not found: #${i + 1} ${marks[i]}`);
      rects.push({ x: b.x, y: b.y, w: b.width, h: b.height });
    }
    return rects;
  };
  const out = (r) => r.y < 0 || r.y + r.h > VH || r.x < 0 || r.x + r.w > VW;
  let rects = await read();
  if (rects.some(out)) {
    await locs[rects.findIndex(out)].scrollIntoViewIfNeeded();  // scrolls both axes (e.g. a wide table)
    await page.waitForTimeout(300);
    rects = await read();
    const off = rects.findIndex(out);
    if (off >= 0) console.warn(`${name}: mark #${off + 1} still partly off-viewport — clamped`);
  }
  // Clamp to the viewport so a row wider than the screen still gets a drawable callout…
  rects = rects.map((r) => { const x = Math.max(0, r.x), y = Math.max(0, r.y); return { x, y, w: Math.min(VW, r.x + r.w) - x, h: Math.min(VH, r.y + r.h) - y }; });
  // …but a target with NOTHING on screen would be a box around something the picture does not show: fail.
  const gone = rects.findIndex((r) => r.w <= 0 || r.h <= 0);
  if (gone >= 0) throw new Error(`${name}: callout target #${gone + 1} (${marks[gone]}) is entirely outside the viewport`);
  // Per-mark badge hint ("left") where the placer's ink measure can't tell text from chrome: pass opts.badges.
  rects = rects.map((r, i) => (opts.badges?.[i] ? { ...r, badge: opts.badges[i] } : r));
  await page.screenshot({ path: `${OUT}${name}.png` });
  writeFileSync(`${OUT}${name}.json`, JSON.stringify({ w: VW, h: VH, marks: rects }));
  console.log('shot', name, rects.length, 'marks');
}

export async function done() { await browser?.close(); }
