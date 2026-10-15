#!/usr/bin/env node
/**
 * ethora-admin.mjs — terminal client for the Ethora admin API
 * (the same API that https://app.chat.ethora.com uses).
 *
 * Zero dependencies. Node >= 18 (uses global fetch).
 *
 * Commands
 *   setup                       interactive: server -> account -> app -> profile
 *   login      [--email X]      log in to an existing Ethora account (handles MFA)
 *   register                    create a new Ethora account, then log in
 *   apps [--search <text>]      list apps the logged-in account can manage (newest first)
 *   create-app --name "X" [--domain myapp]
 *   use <appId> [--profile name]  save an app as the active profile
 *   profile    [--reveal]       print the active profile
 *   set-secret <secret>         store the app secret manually (copied from the admin panel)
 *   logout                      forget the admin session
 *
 * Passwords and MFA codes are only ever typed by the user at a hidden prompt in a real terminal.
 * They are never read from environment variables, flags or files, and never stored.
 * Non-secret choices can be passed as flags to skip their prompts:
 *   node ethora-admin.mjs setup --email you@x.com --app <appId>          (existing app)
 *   node ethora-admin.mjs setup --email you@x.com --create-app "My App"  (new app)
 *
 * Network: talks only to the Ethora API origin (default https://api.chat.ethora.com, or --api <url>).
 *
 * Global flags
 *   --api <url>          API origin, default https://api.chat.ethora.com (self-hosted: your API)
 *   --base-domain <d>    domainName of the base app used for admin login (default "app")
 *   --json               machine-readable output (secrets masked unless --reveal)
 *   --reveal             include secrets in output
 *
 * State
 *   ~/.ethora/profiles.json   same format as `npx @ethora/setup` (shared with it)
 *   ~/.ethora/session.json    admin user session (token/refreshToken) per API origin
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import readline from 'node:readline';

// ---------------------------------------------------------------- args
const argv = process.argv.slice(2);
const flags = {};
const positional = [];
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a.startsWith('--')) {
    const key = a.slice(2);
    const next = argv[i + 1];
    if (next !== undefined && !next.startsWith('--')) {
      flags[key] = next;
      i++;
    } else {
      flags[key] = true;
    }
  } else {
    positional.push(a);
  }
}
const command = positional.shift() || 'help';
const JSON_OUT = !!flags.json;
const REVEAL = !!flags.reveal;

const DEFAULT_API = 'https://api.chat.ethora.com';
const API_ORIGIN = String(flags.api || DEFAULT_API).replace(/\/v[12]\/?$/, '').replace(/\/+$/, '');
const BASE_DOMAIN = String(flags['base-domain'] || 'app');

// ---------------------------------------------------------------- state files
const CONFIG_DIR = process.env.ETHORA_HOME || join(homedir(), '.ethora');
const PROFILES_FILE = join(CONFIG_DIR, 'profiles.json');
const SESSION_FILE = join(CONFIG_DIR, 'session.json');

function readJson(file, fallback) {
  try {
    return JSON.parse(readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}
function writeJson(file, data) {
  if (!existsSync(CONFIG_DIR)) mkdirSync(CONFIG_DIR, { recursive: true });
  writeFileSync(file, JSON.stringify(data, null, 2) + '\n', { mode: 0o600 });
}
const loadProfiles = () => readJson(PROFILES_FILE, { activeProfile: null, profiles: {} });
const saveProfiles = (store) => writeJson(PROFILES_FILE, store);
const loadSessions = () => readJson(SESSION_FILE, {});
const saveSessions = (s) => writeJson(SESSION_FILE, s);

// ---------------------------------------------------------------- output helpers
const log = (...a) => { if (!JSON_OUT) console.log(...a); };
const err = (...a) => console.error(...a);
const short = (v, n = 60) => { const t = String(v ?? ''); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
function mask(v) {
  if (!v) return '';
  const s = String(v);
  return s.length <= 12 ? '***' : s.slice(0, 8) + '…' + s.slice(-4);
}
function die(msg, code = 1) {
  if (JSON_OUT) console.log(JSON.stringify({ ok: false, error: msg }));
  else err('✖ ' + msg);
  process.exit(code);
}

// ---------------------------------------------------------------- prompts
const INTERACTIVE = process.stdin.isTTY && process.stdout.isTTY;
function needTty(what) {
  die(`No interactive terminal available to ask for "${what}". Run this command yourself in a real terminal window (passwords and MFA codes are only accepted at a hidden prompt).`);
}
function createRl() {
  return readline.createInterface({ input: process.stdin, output: process.stdout, terminal: true });
}
function ask(question, { defaultValue } = {}) {
  if (!INTERACTIVE) needTty(question);
  return new Promise((resolve) => {
    const rl = createRl();
    const suffix = defaultValue ? ` (${defaultValue})` : '';
    rl.question(`${question}${suffix}: `, (answer) => {
      rl.close();
      resolve((answer || '').trim() || defaultValue || '');
    });
  });
}
function askHidden(question) {
  if (!INTERACTIVE) needTty(question);
  return new Promise((resolve) => {
    const rl = createRl();
    const stdout = process.stdout;
    let muted = false;
    const origWrite = rl._writeToOutput;
    rl._writeToOutput = function (str) {
      if (muted) {
        // keep newline so the cursor moves after Enter
        if (str.includes('\n')) origWrite.call(rl, '\n');
        return;
      }
      origWrite.call(rl, str);
    };
    rl.question(`${question}: `, (answer) => {
      rl.close();
      stdout.write('\n');
      resolve((answer || '').trim());
    });
    muted = true;
  });
}
async function askChoice(question, options) {
  log(question);
  options.forEach((o, i) => log(`  ${i + 1}) ${o.label}${o.hint ? '  — ' + o.hint : ''}`));
  for (;;) {
    const a = await ask('Choose', { defaultValue: '1' });
    const n = Number(a);
    if (n >= 1 && n <= options.length) return options[n - 1].value;
  }
}
async function askRequired(question, opts) {
  for (;;) {
    const v = await ask(question, opts);
    if (v) return v;
  }
}

// ---------------------------------------------------------------- http
async function api(path, { method = 'GET', body, headers = {}, auth } = {}) {
  const url = API_ORIGIN + path;
  const h = { 'Content-Type': 'application/json', ...headers };
  if (auth) h.Authorization = auth;
  let res;
  try {
    res = await fetch(url, { method, headers: h, body: body ? JSON.stringify(body) : undefined });
  } catch (e) {
    throw new Error(`Network error calling ${url}: ${e.message}`);
  }
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
  if (!res.ok) {
    const msg = data?.message || data?.error || data?.msg || data?.reason || text || res.statusText;
    const e = new Error(`${method} ${path} → ${res.status}: ${typeof msg === 'string' ? msg : JSON.stringify(msg)}`);
    e.status = res.status;
    e.data = data;
    throw e;
  }
  return data;
}

function decodeJwt(token) {
  try {
    const raw = String(token).replace(/^(JWT|Bearer)\s+/i, '');
    const payload = raw.split('.')[1];
    return JSON.parse(Buffer.from(payload.replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8'));
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------- base app (admin login context)
let baseAppCache = null;
async function getBaseApp() {
  if (baseAppCache) return baseAppCache;
  try {
    const data = await api(`/v1/apps/get-config?domainName=${encodeURIComponent(BASE_DOMAIN)}`);
    baseAppCache = data.result || data;
    return baseAppCache;
  } catch (e) {
    die(
      `Could not resolve the base app "${BASE_DOMAIN}" on ${API_ORIGIN} (${e.message}).\n` +
        `  For a self-hosted server pass --api <your API origin> and, if the base app has another domainName, --base-domain <name>.`
    );
  }
}

function endpointsFromBaseApp(baseApp) {
  const xmppHost = baseApp.xmppHost || new URL(API_ORIGIN).hostname.replace(/^api\./, 'xmpp.');
  return {
    apiUrl: API_ORIGIN + '/v1', // kept with /v1 for compatibility with @ethora/setup profiles
    xmppWebSocket: `wss://${xmppHost}/ws`,
    xmppBosh: `https://${xmppHost}/bosh`,
    xmppHost,
    xmppConference: `conference.${xmppHost}`,
  };
}

// ---------------------------------------------------------------- session
function getSession() {
  const s = loadSessions()[API_ORIGIN];
  return s || null;
}
function setSession(session) {
  const all = loadSessions();
  if (session) all[API_ORIGIN] = session;
  else delete all[API_ORIGIN];
  saveSessions(all);
}
async function refreshSession(session) {
  if (!session?.refreshToken) return null;
  try {
    const data = await api('/v1/users/login/refresh', { method: 'POST', auth: session.refreshToken });
    const updated = { ...session, token: data.token, refreshToken: data.refreshToken || session.refreshToken };
    setSession(updated);
    return updated;
  } catch {
    return null;
  }
}
async function requireSession() {
  let s = getSession();
  if (!s) die(`Not logged in on ${API_ORIGIN}. Run: node ethora-admin.mjs login`);
  const payload = decodeJwt(s.token);
  const expMs = payload?.exp ? payload.exp * 1000 : 0;
  if (expMs && expMs < Date.now() + 30_000) {
    s = await refreshSession(s);
    if (!s) die('Admin session expired. Run: node ethora-admin.mjs login');
  }
  return s;
}
async function withSession(fn) {
  let s = await requireSession();
  try {
    return await fn(s);
  } catch (e) {
    if (e.status === 401) {
      s = await refreshSession(s);
      if (!s) die('Admin session expired. Run: node ethora-admin.mjs login');
      return fn(s);
    }
    throw e;
  }
}

// ---------------------------------------------------------------- auth commands
async function finishLogin(data, email) {
  const session = {
    email: data.user?.email || email,
    userId: data.user?._id,
    firstName: data.user?.firstName,
    lastName: data.user?.lastName,
    token: data.token,
    refreshToken: data.refreshToken,
    loggedInAt: new Date().toISOString(),
  };
  setSession(session);
  return session;
}

async function doLogin({ email, password } = {}) {
  const baseApp = await getBaseApp();
  email = email || flags.email || (await askRequired('Email'));
  password = password || (await askHidden('Password'));
  let data;
  try {
    data = await api('/v2/users/login-with-email', {
      method: 'POST',
      body: { email, password, appId: baseApp._id },
      auth: baseApp.appToken,
    });
  } catch (e) {
    if (e.status === 401 || e.status === 400) {
      throw new Error(`Login failed: ${e.message}. Check the email/password, or register with: node ethora-admin.mjs register`);
    }
    throw e;
  }
  if (data.mfaRequired) {
    log('This account has multi-factor authentication enabled.');
    const code = (await askRequired('Enter the 6-digit code from your authenticator app (or a backup code)'));
    data = await api('/v2/users/login/mfa', {
      method: 'POST',
      body: { mfaToken: data.mfaToken, code, appId: baseApp._id },
      auth: baseApp.appToken,
    });
  }
  if (!data.token) throw new Error('Login response had no token: ' + JSON.stringify(data).slice(0, 300));
  const session = await finishLogin(data, email);
  log(`✔ Logged in as ${session.firstName || ''} ${session.lastName || ''} <${session.email}> on ${API_ORIGIN}`);
  return session;
}

async function doRegister() {
  const baseApp = await getBaseApp();
  log('Create a new Ethora account (the same account works at https://app.chat.ethora.com).');
  const email = flags.email || (await askRequired('Email'));
  const firstName = flags['first-name'] || (await askRequired('First name'));
  const lastName = flags['last-name'] || (await askRequired('Last name'));
  let password = '';
  while (!password) {
    password = await askHidden('Password (8+ characters)');
    if (password.length < 8) { log('  Password must be at least 8 characters.'); continue; }
    const again = await askHidden('Repeat password');
    if (again !== password) { log('  Passwords do not match, try again.'); continue; }
    break;
  }
  try {
    await api('/v2/users/sign-up-with-email', {
      method: 'POST',
      body: { email, firstName, lastName, password, appId: baseApp._id },
      auth: baseApp.appToken,
    });
  } catch (e) {
    if (/exist|already|taken|duplicate/i.test(e.message)) {
      log('An account with this email already exists — logging in instead.');
      return doLogin({ email, password });
    }
    if (/cfToken|turnstile|captcha/i.test(e.message)) {
      die(
        'The server requires a browser captcha for registration. Please register at https://app.chat.ethora.com/register, ' +
          'then run: node ethora-admin.mjs login'
      );
    }
    throw e;
  }
  log('✔ Account created.');
  try {
    return await doLogin({ email, password });
  } catch (e) {
    if (/verif|confirm/i.test(e.message)) {
      die(`Registration succeeded but the account needs email verification. Check ${email}, click the link, then run: node ethora-admin.mjs login --email ${email}`);
    }
    throw e;
  }
}

// ---------------------------------------------------------------- app commands
function normalizeApp(a) {
  if (!a) return null;
  return {
    _id: a._id || a.id || a.appId,
    displayName: a.displayName,
    domainName: a.domainName,
    appToken: a.appToken,
    appSecret: a.appSecret,
    isBaseApp: !!a.isBaseApp,
    createdAt: a.createdAt,
    defaultRooms: a.defaultRooms,
    primaryColor: a.primaryColor,
  };
}

async function listApps({ all = false } = {}) {
  return withSession(async (s) => {
    const apps = [];
    let offset = 0;
    for (;;) {
      const data = await api(`/v1/apps?limit=200&offset=${offset}&order=desc&orderBy=createdAt`, { auth: s.token });
      const page = (data.apps || data.items || []).map(normalizeApp).filter((a) => a && a._id);
      apps.push(...page);
      const total = Number(data.total || 0);
      offset += page.length;
      if (!all || page.length === 0 || offset >= total) break;
    }
    return apps;
  });
}

async function getApp(appId) {
  return withSession(async (s) => {
    // The list carries appSecret; a direct GET is used as a fallback.
    const apps = await listApps();
    let app = apps.find((a) => a._id === appId);
    if (!app || !app.appSecret) {
      try {
        const data = await api(`/v1/apps/${encodeURIComponent(appId)}`, { auth: s.token });
        const raw = data.app || (Array.isArray(data.apps) ? data.apps.find((a) => a._id === appId) : null) || data;
        const direct = normalizeApp(raw);
        if (direct && direct._id) app = { ...(app || {}), ...direct, appSecret: direct.appSecret || app?.appSecret };
      } catch { /* ignore */ }
    }
    if (!app) throw new Error(`App ${appId} not found among the apps of ${s.email}`);
    return app;
  });
}

async function createApp({ name, domain } = {}) {
  return withSession(async (s) => {
    name = name || flags.name || (await askRequired('App display name', { defaultValue: 'My Chat App' }));
    domain = domain || flags.domain || '';
    const body = {
      displayName: name,
      createDefaultChat: true, // seeds a "Main chat" room so the first run shows something
      usersCanFree: true,
      defaultAccessProfileOpen: true,
      defaultAccessAssetsOpen: true,
    };
    if (domain) body.domainName = domain.toLowerCase().replace(/[^a-z0-9]/g, '');
    let data;
    try {
      data = await api('/v1/apps', { method: 'POST', body, auth: s.token });
    } catch (e) {
      if (/domain/i.test(e.message) && body.domainName) {
        throw new Error(`${e.message}\n  The domain "${body.domainName}" is probably taken. Try another --domain, or omit it.`);
      }
      throw e;
    }
    const app = normalizeApp(data.app || data);
    log(`✔ App created: ${app.displayName} (id ${app._id})`);
    return app;
  });
}

async function saveProfile(app, { profileName, email } = {}) {
  const baseApp = await getBaseApp();
  const endpoints = endpointsFromBaseApp(baseApp);
  const store = loadProfiles();
  const name =
    profileName ||
    flags.profile ||
    (app.domainName || app.displayName || app._id).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const isCloud = /\.ethora\.com$/.test(new URL(API_ORIGIN).hostname);
  const webDomain = isCloud ? new URL(API_ORIGIN).hostname.replace(/^api\./, '') : undefined;
  const profile = {
    name,
    type: isCloud ? 'cloud' : 'self-hosted',
    endpoints,
    appId: app._id,
    appToken: app.appToken || '',
    appSecret: app.appSecret || store.profiles[name]?.appSecret || '',
    displayName: app.displayName,
    domainName: app.domainName,
    email: email || getSession()?.email,
    webAppUrl: app.domainName && webDomain ? `https://${app.domainName}.${webDomain}` : undefined,
    adminUrl: isCloud ? `https://app.${webDomain}/app/admin/apps/${app._id}` : undefined,
    savedAt: new Date().toISOString(),
  };
  store.profiles[name] = profile;
  store.activeProfile = name;
  saveProfiles(store);
  return profile;
}

function printProfile(profile) {
  const out = { ...profile };
  if (!REVEAL) {
    out.appToken = mask(out.appToken);
    out.appSecret = out.appSecret ? mask(out.appSecret) : '';
  }
  if (JSON_OUT) {
    console.log(JSON.stringify({ ok: true, profile: out, profilesFile: PROFILES_FILE }, null, 2));
    return;
  }
  log('');
  log(`Active profile: ${profile.name}  (${PROFILES_FILE})`);
  log(`  app:        ${profile.displayName}  id=${profile.appId}`);
  log(`  api:        ${profile.endpoints.apiUrl}`);
  log(`  xmpp:       ${profile.endpoints.xmppHost}  ws=${profile.endpoints.xmppWebSocket}`);
  log(`  conference: ${profile.endpoints.xmppConference}`);
  log(`  appToken:   ${out.appToken}`);
  log(`  appSecret:  ${out.appSecret || '(missing — see below)'}`);
  if (profile.adminUrl) log(`  admin:      ${profile.adminUrl}`);
  if (!profile.appSecret) {
    log('');
    log('  The app secret was not returned by the API. Copy it from the admin panel:');
    log(`    ${profile.adminUrl || 'https://app.chat.ethora.com'} → Settings → API → Secret`);
    log('  then store it with:  node ethora-admin.mjs set-secret <secret>');
  }
}

async function chooseOrCreateApp(session) {
  if (flags.app) return getApp(String(flags.app));
  if (flags['create-app']) return createApp({ name: flags['create-app'] === true ? undefined : String(flags['create-app']) });
  if (!INTERACTIVE) needTty('which app to use (--app <appId> or --create-app "<name>")');
  const apps = (await listApps({ all: true })).filter((a) => !a.isBaseApp);
  if (apps.length === 0) {
    log(`No apps yet for ${session.email}. Let's create one.`);
    return finishApp(await createApp());
  }
  const fmt = (a) => ({ label: `${short(a.displayName)}  (${a._id})`, value: a._id, hint: a.createdAt ? 'created ' + a.createdAt.slice(0, 10) : a.domainName });
  // newest first (listApps orders by createdAt desc); keep the menu short for accounts with many apps
  let pool = apps;
  for (;;) {
    const shown = pool.slice(0, 10);
    const options = shown.map(fmt);
    if (pool.length > shown.length) options.push({ label: `Search by name… (${pool.length} apps in total)`, value: '__search__' });
    options.push({ label: 'Enter an app id', value: '__id__' });
    options.push({ label: '+ Create a new app', value: '__new__' });
    const choice = await askChoice(pool === apps ? `Which app should the chat connect to? (showing the ${shown.length} most recent)` : `Matches (${pool.length}):`, options);
    if (choice === '__new__') return finishApp(await createApp());
    if (choice === '__id__') { const id = await askRequired('App id'); return finishApp(await getApp(id.trim())); }
    if (choice === '__search__') {
      const q = (await askRequired('Name contains')).toLowerCase();
      const found = apps.filter((a) => (a.displayName || '').toLowerCase().includes(q) || (a.domainName || '').toLowerCase().includes(q) || a._id.includes(q));
      if (!found.length) { log('  No app matches, try again.'); pool = apps; continue; }
      pool = found; continue;
    }
    return finishApp(await getApp(choice));
  }
}
async function finishApp(app) {
  if (!app.appSecret) app = await getApp(app._id);
  return app;
}

// ---------------------------------------------------------------- commands
const commands = {
  async help() {
    console.log(readFileSync(new URL(import.meta.url), 'utf8').split('*/')[0].replace(/^\/\*\*?/, '').replace(/^\s\*\s?/gm, ''));
  },

  async login() {
    const session = await doLogin();
    if (JSON_OUT) console.log(JSON.stringify({ ok: true, email: session.email, api: API_ORIGIN }));
  },

  async register() {
    const session = await doRegister();
    if (JSON_OUT) console.log(JSON.stringify({ ok: true, email: session.email, api: API_ORIGIN }));
  },

  async logout() {
    setSession(null);
    log('✔ Admin session removed for ' + API_ORIGIN);
  },

  async apps() {
    let apps = await listApps({ all: true });
    if (flags.search) { const q = String(flags.search).toLowerCase(); apps = apps.filter((a) => (a.displayName || '').toLowerCase().includes(q) || (a.domainName || '').toLowerCase().includes(q) || a._id.includes(q)); }
    if (JSON_OUT) {
      console.log(JSON.stringify({ ok: true, apps: apps.map((a) => ({ ...a, appToken: REVEAL ? a.appToken : mask(a.appToken), appSecret: REVEAL ? a.appSecret : mask(a.appSecret) })) }, null, 2));
      return;
    }
    if (!apps.length) { log('No apps. Create one with: node ethora-admin.mjs create-app --name "My App"'); return; }
    log(`Apps available to ${getSession()?.email}:`);
    for (const a of apps) log(`  ${a._id}  ${short(a.displayName)}${a.domainName ? '  [' + a.domainName + ']' : ''}${a.isBaseApp ? '  (base app)' : ''}`);
    log('\nSelect one with: node ethora-admin.mjs use <appId>');
  },

  async 'create-app'() {
    let app = await createApp();
    if (!app.appSecret) app = await getApp(app._id);
    const profile = await saveProfile(app);
    printProfile(profile);
  },

  async use() {
    const appId = positional[0] || flags.app || die('Usage: use <appId>');
    const app = await getApp(appId);
    const profile = await saveProfile(app);
    printProfile(profile);
  },

  async profile() {
    const store = loadProfiles();
    const name = flags.profile || store.activeProfile;
    const profile = name && store.profiles[name];
    if (!profile) die('No active profile. Run: node ethora-admin.mjs setup');
    printProfile(profile);
  },

  async 'set-secret'() {
    const secret = positional[0] || (await askHidden('App secret'));
    const store = loadProfiles();
    const name = flags.profile || store.activeProfile;
    if (!name || !store.profiles[name]) die('No active profile to attach the secret to.');
    store.profiles[name].appSecret = secret.trim();
    saveProfiles(store);
    log(`✔ Secret stored in profile ${name}`);
  },

  async setup() {
    log('Ethora chat setup');
    log(`API: ${API_ORIGIN}${API_ORIGIN === DEFAULT_API ? ' (Ethora Cloud)' : ' (self-hosted)'}`);
    await getBaseApp();
    let session = getSession();
    if (session && !INTERACTIVE) {
      session = await requireSession();
    } else if (session) {
      const keep = await askChoice(`You are logged in as ${session.email}. Continue with this account?`, [
        { label: 'Yes', value: 'yes' },
        { label: 'No, log in with another account', value: 'login' },
        { label: 'No, create a new account', value: 'register' },
      ]);
      if (keep === 'login') session = await doLogin();
      if (keep === 'register') session = await doRegister();
      if (keep === 'yes') {
        // make sure the token is still valid
        session = await requireSession();
      }
    } else if (!INTERACTIVE) {
      session = flags.register ? await doRegister() : await doLogin();
    } else {
      const has = await askChoice('Do you already have an Ethora account (app.chat.ethora.com)?', [
        { label: 'Yes, log in', value: 'login' },
        { label: 'No, create one', value: 'register' },
      ]);
      session = has === 'login' ? await doLogin() : await doRegister();
    }
    const app = await chooseOrCreateApp(session);
    const profile = await saveProfile(app, { email: session.email });
    printProfile(profile);
    if (!JSON_OUT) {
      log('');
      log('Next: write the project config from this profile:');
      log('  node write-env.mjs --target <vite|next|cra|expo|rn|backend> --dir <project>');
    }
  },
};

(async () => {
  const fn = commands[command];
  if (!fn) die(`Unknown command "${command}". Run with "help".`);
  try {
    await fn();
  } catch (e) {
    die(e.message || String(e));
  }
})();
