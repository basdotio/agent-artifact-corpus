#!/usr/bin/env node
/**
 * client-jwt.mjs — sign an Ethora *client* JWT (what `jwtLogin.token` expects).
 *
 * Payload: { data: { type: 'client', appId, userId }, iat, exp }   signed HS256 with the app secret.
 * The chat component exchanges it at POST /v1/users/client (header x-custom-token) for a chat user session.
 *
 * Usage:
 *   node client-jwt.mjs --user-id <yourInternalUserId> [--expires 36h] [--profile name]
 *   node client-jwt.mjs --user-id u1 --app-id <id> --secret <secret>        (no profile)
 *   node client-jwt.mjs --server [--expires 1h]                              (server token: data.type='server', for /v1/users/batch etc.)
 *
 * This is for the terminal / dev-time use. In production the SAME signing must happen on YOUR backend
 * (see assets/templates/backend/*), never in the browser or the mobile bundle.
 */
import { createHmac } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const argv = process.argv.slice(2);
const flag = (n) => { const i = argv.indexOf('--' + n); return i >= 0 ? argv[i + 1] : undefined; };
const has = (n) => argv.includes('--' + n);

let appId = flag('app-id');
let secret = flag('secret');
if (!appId || !secret) {
  try {
    const store = JSON.parse(readFileSync(join(process.env.ETHORA_HOME || join(homedir(), '.ethora'), 'profiles.json'), 'utf8'));
    const p = store.profiles[flag('profile') || store.activeProfile];
    appId = appId || p?.appId;
    secret = secret || p?.appSecret;
  } catch { /* no profiles */ }
}
if (!appId || !secret) { console.error('Need --app-id and --secret, or an active profile with an appSecret (node ethora-admin.mjs setup / set-secret).'); process.exit(1); }

function parseDuration(s) {
  const m = String(s || '36h').match(/^(\d+)\s*([smhd])?$/);
  if (!m) throw new Error('Bad --expires, use e.g. 30m, 12h, 7d');
  const mult = { s: 1, m: 60, h: 3600, d: 86400 }[m[2] || 's'];
  return Number(m[1]) * mult;
}
const b64url = (buf) => Buffer.from(buf).toString('base64').replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');

export function signHS256(payload, key) {
  const header = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = b64url(JSON.stringify(payload));
  const sig = b64url(createHmac('sha256', key).update(`${header}.${body}`).digest());
  return `${header}.${body}.${sig}`;
}

const now = Math.floor(Date.now() / 1000);
const exp = now + parseDuration(flag('expires'));
let payload;
if (has('server')) {
  payload = { data: { appId, type: 'server' }, iat: now, exp };
} else {
  const userId = flag('user-id');
  if (!userId) { console.error('--user-id is required (your app\'s own id for the user, e.g. "user-123")'); process.exit(1); }
  const data = { type: 'client', appId, userId };
  for (const k of ['first-name', 'last-name', 'email']) {
    const v = flag(k);
    if (v) data[k.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = v;
  }
  payload = { data, iat: now, exp };
}
const token = signHS256(payload, secret);
if (has('json')) console.log(JSON.stringify({ token, payload }));
else console.log(token);
