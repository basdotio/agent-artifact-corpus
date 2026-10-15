#!/usr/bin/env node
/**
 * ensure-user.mjs — create (or confirm) an end user inside the Ethora app, server-side.
 *
 * Uses POST /v1/users/batch with a server JWT (x-custom-token, data.type='server') — the documented
 * "synchronize your users" call. Idempotent enough for setup: an existing uuid/email is reported, not duplicated.
 *
 * Usage:
 *   node ensure-user.mjs --user-id <yourInternalUserId> --email <email> --first-name <f> --last-name <l> [--password <p>] [--profile name]
 *
 * `--user-id` must be the same value you later put into the client JWT (`data.userId`).
 * The chat username becomes `<appId>_<userId>` (JID local part).
 */
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { createHmac } from 'node:crypto';

const argv = process.argv.slice(2);
const flag = (n) => { const i = argv.indexOf('--' + n); return i >= 0 ? argv[i + 1] : undefined; };
const store = JSON.parse(readFileSync(join(process.env.ETHORA_HOME || join(homedir(), '.ethora'), 'profiles.json'), 'utf8'));
const p = store.profiles[flag('profile') || store.activeProfile];
if (!p?.appSecret) { console.error('Active profile has no appSecret. Run: node ethora-admin.mjs set-secret <secret>'); process.exit(1); }
const apiOrigin = String(p.endpoints.apiUrl).replace(/\/v[12]\/?$/, '');

const userId = flag('user-id'); const email = flag('email');
const firstName = flag('first-name') || 'Chat'; const lastName = flag('last-name') || 'User';
const password = flag('password');
if (!userId || !email) { console.error('Usage: --user-id <id> --email <email> [--first-name f --last-name l --password p]'); process.exit(1); }

const b64url = (b) => Buffer.from(b).toString('base64').replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
const now = Math.floor(Date.now() / 1000);
const sign = (payload) => { const h = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' })); const b = b64url(JSON.stringify(payload)); return `${h}.${b}.${b64url(createHmac('sha256', p.appSecret).update(`${h}.${b}`).digest())}`; };
const serverToken = sign({ data: { appId: p.appId, type: 'server' }, iat: now, exp: now + 3600 });

const user = { uuid: userId, email, firstName, lastName, ...(password ? { password } : {}) };
const res = await fetch(`${apiOrigin}/v1/users/batch`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'x-custom-token': serverToken },
  body: JSON.stringify({ bypassEmailConfirmation: true, usersList: [user] }),
});
const text = await res.text();
let data; try { data = JSON.parse(text); } catch { data = { raw: text }; }
if (!res.ok) {
  if (/exist|already|duplicate/i.test(text)) { console.log(`✔ user ${userId} (${email}) already exists in app ${p.appId}`); process.exit(0); }
  console.error(`✖ ${res.status} ${text.slice(0, 500)}`); process.exit(1);
}
const created = data.results?.[0] || data.users?.[0] || data;
console.log(`✔ user ready: uuid=${userId} email=${email} xmppUsername=${created?.xmppUsername || `${p.appId}_${userId}`}`);
if (argv.includes('--json')) console.log(JSON.stringify(data, null, 2));
