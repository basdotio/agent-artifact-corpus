// Shared helpers: errors, scrubbing, time, output contract, argument parsing.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const VERSION = '0.1.0';
export const SCHEMA = 'scratchpool/v1';

// ---------------------------------------------------------------- errors

export const EXIT = {
  USAGE: 1, CONFIRM_REQUIRED: 1, SECRETS_ENV: 1, NO_POOL: 1, NOT_A_PROJECT: 1, SERVICE_UNSUPPORTED: 1,
  LIMIT: 3, POOL_EMPTY: 4, NO_DEVHUB: 5, NOT_SCRATCH: 5, NOT_MINE: 5, NOT_MANAGED: 5, SF_MISSING: 127,
};

export class SpError extends Error {
  constructor(code, message, extra = {}) {
    super(message);
    this.code = code;
    Object.assign(this, extra);
  }
}
export const fail = (code, message, extra) => { throw new SpError(code, message, extra); };

export function exitCodeFor(err) {
  if (err.code === 'SF_ERROR') return Number.isInteger(err.sfExit) && err.sfExit > 0 && err.sfExit < 256 ? err.sfExit : 1;
  return EXIT[err.code] ?? 1;
}

// ---------------------------------------------------------------- scrubbing (SPEC 4)

const SECRET_RES = [
  /force:\/\/\S+/g,
  /00D\w{12,15}![\w.]+/g,
  /sid=\S+/g,
  /access_token=\S+/g,
  /frontdoor\.jsp\S*/g,
  /refresh_token\S*/g,
  // Defense in depth beyond the SPEC minimum: refresh tokens and key/value secrets in sf error text.
  /5Aep[\w.]+/g,
  /"?\b(?:refresh_?token|access_?token|password|sfdx_?auth_?url|client_?secret)"?\s*[:=]\s*"?[^\s",}]*"?/gi,
];
export function scrub(s) {
  if (s == null) return s;
  let out = String(s);
  for (const re of SECRET_RES) out = out.replace(re, '[REDACTED]');
  return out;
}
// Text from sf or the Dev Hub can carry content from files in a cloned repo (a def file, a project
// name), so it reaches an agent as data only: secrets scrubbed, control characters removed, short.
export const UNTRUSTED_MAX = 300;
export function clipUntrusted(s, max = UNTRUSTED_MAX) {
  if (s == null) return s;
  // eslint-disable-next-line no-control-regex
  const flat = scrub(s).replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]+/g, ' ').replace(/ {2,}/g, ' ').trim();
  return flat.length > max ? `${flat.slice(0, max - 1)}\u2026` : flat;
}
export function deepScrub(v) {
  if (typeof v === 'string') return scrub(v);
  if (Array.isArray(v)) return v.map(deepScrub);
  if (v && typeof v === 'object') {
    const o = {};
    for (const [k, x] of Object.entries(v)) o[k] = deepScrub(x);
    return o;
  }
  return v;
}

// ---------------------------------------------------------------- time

export function now() {
  const s = process.env.SCRATCHPOOL_NOW;
  if (s) {
    const d = new Date(s);
    if (!Number.isNaN(d.getTime())) return d;
  }
  return new Date();
}
export const nowIso = () => now().toISOString();

// Expiry is a date, not a time: treat the org as gone at the start (UTC) of its expiration date.
export function lifeLeftHours(expiresAt) {
  if (!expiresAt) return null;
  const t = Date.parse(String(expiresAt).slice(0, 10) + 'T00:00:00Z');
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.floor((t - now().getTime()) / 3600000));
}
export function isExpiredDate(expiresAt) {
  const h = lifeLeftHours(expiresAt);
  return h !== null && h <= 0;
}

export function randHex(n = 4) {
  let s = '';
  while (s.length < n) s += Math.floor(Math.random() * 16).toString(16);
  return s;
}

// ---------------------------------------------------------------- paths

export function platform() { return process.env.SCRATCHPOOL_PLATFORM || process.platform; }

export function homeDir() {
  if (process.env.SCRATCHPOOL_HOME) return path.resolve(process.env.SCRATCHPOOL_HOME);
  if (process.platform === 'win32' && process.env.APPDATA) return path.join(process.env.APPDATA, 'scratchpool');
  if (process.env.XDG_CONFIG_HOME) return path.join(process.env.XDG_CONFIG_HOME, 'scratchpool');
  return path.join(os.homedir(), '.config', 'scratchpool');
}

export function realpath(p) {
  try { return fs.realpathSync.native(p); } catch { return path.resolve(p); }
}

// ---------------------------------------------------------------- aliases

export const ALIAS_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/;
export function sanitizePoolName(s) {
  const n = String(s).toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
  return n || 'pool';
}

// ---------------------------------------------------------------- argument parsing

const VALUE_FLAGS = new Set(['--hub', '--size', '--def', '--snapshot', '--duration', '--interval', '--pool', '--alias']);
const BOOL_FLAGS = new Set(['--setup-hook', '--no-service', '--json', '--no-open', '--cold', '--any', '--pool-orgs',
  '--surplus', '--stale', '--orphans', '--yes', '--release-pool-orgs', '--version', '--help']);

export function parseArgs(argv) {
  const flags = {};
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    let a = argv[i];
    if (a === '-h') a = '--help';
    if (a === '-v' && positional.length === 0) a = '--version';
    if (a === '-y') a = '--yes';
    if (a.startsWith('--')) {
      let name = a;
      let val;
      const eq = a.indexOf('=');
      if (eq > 0) { name = a.slice(0, eq); val = a.slice(eq + 1); }
      const key = name.slice(2);
      if (VALUE_FLAGS.has(name)) {
        if (val === undefined) {
          val = argv[++i];
          if (val === undefined) fail('USAGE', `${name} needs a value`);
        }
        flags[key] = val;
      } else if (BOOL_FLAGS.has(name)) {
        if (val !== undefined) fail('USAGE', `${name} takes no value`);
        flags[key] = true;
      } else {
        fail('USAGE', `unknown option ${name}`);
      }
    } else {
      positional.push(a);
    }
  }
  return { flags, positional };
}

export function intArg(v, name, min, max) {
  const s = String(v).trim();
  if (!/^-?\d+$/.test(s)) fail('USAGE', `${name} must be an integer between ${min} and ${max} (got "${v}")`);
  const n = Number(s);
  if (n < min || n > max) fail('USAGE', `${name} must be an integer between ${min} and ${max} (got ${n})`);
  return n;
}

// ---------------------------------------------------------------- output (SPEC 5)

export function baseOutput(command) {
  return {
    schema: SCHEMA, command, status: 'ok', pool: null,
    source: null, alias: null, username: null, orgId: null, instanceUrl: null,
    expiresAt: null, lifeLeftHours: null, setupRan: null,
    counts: { ready: 0, creating: 0, claimed: 0, size: 0, paused: false },
    limits: { activeRemaining: null, dailyRemaining: null },
    warnings: [],
    error: { code: null, message: null, retryable: false },
  };
}

export function jsonMode(flags) {
  return !!flags.json || !process.stdout.isTTY;
}

export function emit(out, flags, human) {
  const clean = deepScrub(out);
  if (jsonMode(flags)) {
    process.stdout.write(JSON.stringify(clean) + '\n');
    return;
  }
  if (clean.status === 'error') {
    process.stderr.write(`scratchpool: ${clean.error.code}: ${clean.error.message}\n`);
  } else {
    const text = human ? human(clean) : `${clean.command}: ${clean.status}`;
    if (text) process.stdout.write(scrub(text) + '\n');
  }
  for (const w of clean.warnings || []) process.stderr.write(`warning: ${w}\n`);
}

export function stderrInfo(flags, msg) {
  if (!jsonMode(flags)) process.stderr.write(scrub(msg) + '\n');
}
