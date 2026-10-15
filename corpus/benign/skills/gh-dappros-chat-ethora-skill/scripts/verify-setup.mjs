#!/usr/bin/env node
/**
 * verify-setup.mjs — check the Ethora configuration from the terminal before running the app.
 *
 * Usage: node verify-setup.mjs [--profile name] [--user-id <id>] [--email <email>]
 *
 * 1. API reachable (GET /v1/apps/get-config)         2. app token decodes and matches the profile's appId
 * 3. (if appSecret) sign a client JWT for --user-id and exchange it at POST /v1/users/client → proves the
 *    "user without login" flow works end to end. If the user does not exist yet it is created first via
 *    /v1/users/batch when --email is given (same thing ensure-user.mjs does).
 * 4. XMPP host resolves (DNS) and the WebSocket endpoint answers.
 */
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { createHmac } from 'node:crypto';
import { promises as dns } from 'node:dns';
import tls from 'node:tls';

const argv = process.argv.slice(2);
const flag = (n) => { const i = argv.indexOf('--' + n); return i >= 0 ? argv[i + 1] : undefined; };
const store = (() => { try { return JSON.parse(readFileSync(join(process.env.ETHORA_HOME || join(homedir(), '.ethora'), 'profiles.json'), 'utf8')); } catch { return null; } })();
const p = store?.profiles?.[flag('profile') || store?.activeProfile];
if (!p) { console.error('✖ No active profile. Run: node ethora-admin.mjs setup'); process.exit(1); }
const apiOrigin = String(p.endpoints.apiUrl).replace(/\/v[12]\/?$/, '');
const ok = (m) => console.log('✔ ' + m); const bad = (m) => console.log('✖ ' + m); const warn = (m) => console.log('⚠ ' + m);
let failures = 0;

// 1. API
try {
  const r = await fetch(`${apiOrigin}/v1/apps/get-config?domainName=app`);
  if (r.ok) ok(`API reachable: ${apiOrigin}`); else { warn(`API answered ${r.status} for get-config (base app may use another domainName) — continuing`); }
} catch (e) { bad(`API unreachable: ${apiOrigin} (${e.message})`); failures++; }

// 2. app token
const decode = (t) => { try { return JSON.parse(Buffer.from(String(t).replace(/^(JWT|Bearer)\s+/i, '').split('.')[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString()); } catch { return null; } };
const tok = decode(p.appToken);
if (!tok) { bad('appToken is not a JWT'); failures++; }
else if ((tok.data?._id || tok.data?.appId) && (tok.data._id || tok.data.appId) !== p.appId) { bad(`appToken belongs to app ${tok.data._id || tok.data.appId}, profile says ${p.appId}`); failures++; }
else ok(`appToken decodes (app "${tok.data?.displayName || p.displayName}", id ${p.appId})`);

// 3. client JWT exchange
if (!p.appSecret) {
  warn('No appSecret in profile → cannot test the client-JWT ("user without login") flow. Copy the secret from the admin panel (Settings → API) and run: node ethora-admin.mjs set-secret <secret>');
} else {
  const b64url = (b) => Buffer.from(b).toString('base64').replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  const sign = (payload) => { const h = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' })); const b = b64url(JSON.stringify(payload)); return `${h}.${b}.${b64url(createHmac('sha256', p.appSecret).update(`${h}.${b}`).digest())}`; };
  const now = Math.floor(Date.now() / 1000);
  const userId = flag('user-id') || 'ethora-skill-check';
  const email = flag('email');
  const exchange = async () => {
    const r = await fetch(`${apiOrigin}/v1/users/client`, { method: 'POST', headers: { 'x-custom-token': sign({ data: { type: 'client', appId: p.appId, userId }, iat: now, exp: now + 600 }) } });
    const t = await r.text(); let d; try { d = JSON.parse(t); } catch { d = { raw: t }; }
    return { r, d, t };
  };
  let { r, d, t } = await exchange();
  if (!r.ok && email) {
    warn(`client JWT exchange answered ${r.status} — creating user "${userId}" via /v1/users/batch and retrying`);
    const srv = sign({ data: { appId: p.appId, type: 'server' }, iat: now, exp: now + 600 });
    const c = await fetch(`${apiOrigin}/v1/users/batch`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'x-custom-token': srv }, body: JSON.stringify({ bypassEmailConfirmation: true, usersList: [{ uuid: userId, email, firstName: 'Skill', lastName: 'Check' }] }) });
    if (!c.ok) { bad(`user creation failed: ${c.status} ${(await c.text()).slice(0, 300)}`); failures++; }
    else ({ r, d, t } = await exchange());
  }
  if (r.ok && d.user) ok(`client JWT exchange works: userId "${userId}" → xmppUsername ${d.user.xmppUsername || d.user.defaultWallet?.walletAddress || '(n/a)'} — the chat will open without a login screen`);
  else if (d.code === 'USER_NOT_FOUND') { bad(`user "${userId}" does not exist in app ${p.appId} (USER_NOT_FOUND). /v1/users/client never creates users: your backend must sync them first via /v1/users/batch (templates do it) — or re-run this check with --email <email> to create "${userId}" now.`); failures++; }
  else if (r.status === 401 || r.status === 403) { bad(`client JWT rejected (${r.status}): the appSecret is probably wrong or rotated. ${t.slice(0, 200)}`); failures++; }
  else if (d.code === 'APP_NOT_FOUND') { bad(`the API does not know app ${p.appId} (APP_NOT_FOUND) — wrong API origin for this app, or the profile is stale. Re-run: node ethora-admin.mjs use <appId> [--api …]`); failures++; }
  else { bad(`client JWT exchange failed (${r.status}): ${t.slice(0, 300)}. If the user must pre-exist, re-run with --email <email> or use ensure-user.mjs.`); failures++; }
}

// 4. XMPP
try {
  await dns.lookup(p.endpoints.xmppHost);
  ok(`XMPP host resolves: ${p.endpoints.xmppHost}`);
  const u = new URL(p.endpoints.xmppWebSocket);
  const port = Number(u.port || (u.protocol === 'wss:' ? 443 : 80));
  await new Promise((resolve, reject) => {
    const s = tls.connect({ host: u.hostname, port, servername: u.hostname, timeout: 8000 }, () => { s.end(); resolve(); });
    s.on('error', reject); s.on('timeout', () => { s.destroy(); reject(new Error('timeout')); });
  });
  ok(`XMPP WebSocket port open (TLS ok): ${p.endpoints.xmppWebSocket}`);
} catch (e) { bad(`XMPP endpoint problem for ${p.endpoints.xmppWebSocket}: ${e.message} (self-hosted: try wss://host:5443/ws)`); failures++; }

console.log(failures ? `\n${failures} problem(s) found.` : '\nAll checks passed.');
process.exit(failures ? 1 : 0);
