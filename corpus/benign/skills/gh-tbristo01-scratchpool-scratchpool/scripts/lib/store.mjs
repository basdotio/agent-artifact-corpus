// Local files (SPEC section 3): user config, per-pool state, locks, the action log and defHash.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { homeDir, nowIso, scrub, SpError } from './util.mjs';

export const POOL_DEFAULTS = {
  size: 1, definitionFile: 'config/project-scratch-def.json', snapshot: null, durationDays: null,
  coldDurationDays: 1, setupHook: false, dailyFloor: 2, teamCapPct: 25, claimMinLifeHours: 24,
  activeReserve: 1, paused: false, setupHookSha256: null,
};

export const paths = {
  home: () => homeDir(),
  config: () => path.join(homeDir(), 'config.json'),
  stateDir: () => path.join(homeDir(), 'state'),
  state: (pool) => path.join(homeDir(), 'state', `${pool}.json`),
  tickLock: (pool) => path.join(homeDir(), 'state', `${pool}.tick.lock`),
  logDir: () => path.join(homeDir(), 'logs'),
  log: () => path.join(homeDir(), 'logs', 'scratchpool.log'),
};

// ---------------------------------------------------------------- atomic write + locks

// Every directory scratchpool creates under <home> is private to the user (0700; ignored on Windows).
export function ensureDir(dir) { fs.mkdirSync(dir, { recursive: true, mode: 0o700 }); }

export function writeAtomic(file, text) {
  ensureDir(path.dirname(file));
  const tmp = `${file}.${process.pid}.${crypto.randomBytes(4).toString('hex')}.tmp`;
  fs.writeFileSync(tmp, text, { mode: 0o600 });
  try {
    fs.renameSync(tmp, file);
  } catch (e) {
    // Windows can refuse a rename over a file another process has open; retry briefly.
    for (let i = 0; i < 20; i++) {
      sleep(50);
      try { fs.renameSync(tmp, file); return; } catch { /* retry */ }
    }
    try { fs.rmSync(tmp, { force: true }); } catch { /* ignore */ }
    throw e;
  }
}

const sab = new Int32Array(new SharedArrayBuffer(4));
export function sleep(ms) { Atomics.wait(sab, 0, 0, ms); }

const STATE_LOCK_STALE_MS = 60 * 1000;

export function tryLock(lockFile, staleMs) {
  ensureDir(path.dirname(lockFile));
  try {
    const fd = fs.openSync(lockFile, 'wx');
    fs.writeSync(fd, String(process.pid));
    fs.closeSync(fd);
    return true;
  } catch (e) {
    if (e.code !== 'EEXIST') throw e;
    try {
      const age = Date.now() - fs.statSync(lockFile).mtimeMs;
      if (age > staleMs) {
        fs.rmSync(lockFile, { force: true });
        return tryLock(lockFile, staleMs * 1000); // one retry, no recursion loop
      }
    } catch { /* vanished: let caller retry */ }
    return false;
  }
}
export function unlock(lockFile) { try { fs.rmSync(lockFile, { force: true }); } catch { /* ignore */ } }

export function withFileLock(file, fn, { timeoutMs = 30000 } = {}) {
  const lock = `${file}.lock`;
  const start = Date.now();
  while (!tryLock(lock, STATE_LOCK_STALE_MS)) {
    if (Date.now() - start > timeoutMs) throw new SpError('LOCKED', `timed out waiting for ${path.basename(lock)}`);
    sleep(25 + Math.floor(Math.random() * 50));
  }
  try { return fn(); } finally { unlock(lock); }
}

function readJson(file, fallback) {
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch (e) {
    if (e.code === 'ENOENT') return fallback;
    throw e;
  }
  try { return JSON.parse(text); } catch {
    throw new SpError('USAGE', `${file} is not valid JSON; fix or remove it`);
  }
}

// ---------------------------------------------------------------- config

export function emptyConfig() {
  return { schema: 1, intervalMinutes: 15, machineId: null, nodePath: null, sfPath: null, scriptPath: null, pools: {} };
}
export function loadConfig() {
  const c = readJson(paths.config(), null);
  if (!c) return emptyConfig();
  c.pools ||= {};
  c.intervalMinutes ??= 15;
  for (const p of Object.values(c.pools)) for (const [k, v] of Object.entries(POOL_DEFAULTS)) if (!(k in p)) p[k] = v;
  return c;
}
// Read-modify-write of the user config under its lock.
export function updateConfig(fn) {
  return withFileLock(paths.config(), () => {
    const c = loadConfig();
    const r = fn(c);
    writeAtomic(paths.config(), JSON.stringify(c, null, 2) + '\n');
    return r === undefined ? c : r;
  });
}

// ---------------------------------------------------------------- state

export function loadState(pool) {
  const s = readJson(paths.state(pool), null) || { schema: 1, entries: [] };
  s.entries ||= [];
  return s;
}
// Read-modify-write of a pool's state under its lock; fn mutates `state` and may return a value.
export function updateState(pool, fn) {
  const file = paths.state(pool);
  return withFileLock(file, () => {
    const s = loadState(pool);
    const r = fn(s);
    writeAtomic(file, JSON.stringify(s, null, 2) + '\n');
    return r;
  });
}

export function counts(state, pool) {
  const c = { ready: 0, creating: 0, claimed: 0, size: pool?.size ?? 0, paused: !!pool?.paused };
  for (const e of state.entries) if (e.status in c && e.status !== 'size' && e.status !== 'paused') c[e.status]++;
  return c;
}

// ---------------------------------------------------------------- log (rotate at 1 MB, keep 1 backup)

const LOG_MAX = 1024 * 1024;
export function logLine(pool, action, detail = '') {
  try {
    const file = paths.log();
    ensureDir(path.dirname(file));
    try {
      if (fs.statSync(file).size >= LOG_MAX) fs.renameSync(file, file + '.1');
    } catch { /* no log yet */ }
    const d = typeof detail === 'string' ? detail : JSON.stringify(detail);
    fs.appendFileSync(file, scrub(`${nowIso()} ${pool || '-'} ${action}${d ? ' ' + d : ''}`).replace(/\r?\n/g, ' ') + '\n', { mode: 0o600 });
  } catch { /* logging must never break a command */ }
}

// A random id for this machine's scratchpool install, written into each org's ScratchOrgInfo Description
// so orphan cleanup never touches orgs created by the same Dev Hub user on another machine.
export const MACHINE_ID_RE = /^[0-9a-f]{8}$/;
export function newMachineId() { return crypto.randomBytes(4).toString('hex'); }
export function orgDescription(pool, defHash, machineId) {
  return `scratchpool:v1:${pool.hubUsername}:${defHash}${machineId ? ':' + machineId : ''}`;
}

// ---------------------------------------------------------------- recipe / defHash

export function hookFile(projectDir, platform = process.platform) {
  const dir = path.join(projectDir, '.scratchpool');
  const order = platform === 'win32' ? ['setup.cmd', 'setup.mjs', 'setup'] : ['setup', 'setup.mjs'];
  for (const n of order) {
    const p = path.join(dir, n);
    try { if (fs.statSync(p).isFile()) return p; } catch { /* next */ }
  }
  return null;
}

// The setup hook runs unattended as the user, so it is pinned: enabling it records the file's sha256,
// and a hook whose contents changed since (a `git pull`, a branch switch, an edit) is not run until the
// user re-enables it with `config set setupHook true` or `init --setup-hook`.
export function hookSha256(projectDir, platform = process.platform) {
  const f = hookFile(projectDir, platform);
  if (!f) return null;
  try { return crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex'); } catch { return null; }
}

export function hookTrusted(pool, platform = process.platform) {
  if (!pool.setupHook) return true;
  const sha = hookSha256(pool.projectDir, platform);
  return !!sha && sha === pool.setupHookSha256;
}

export function computeDefHash({ def, namespace, hubUsername, hook }) {
  const json = JSON.stringify({ def: def ?? null, namespace: namespace ?? '', hubUsername: hubUsername ?? '', hook: hook ?? null });
  return crypto.createHash('sha256').update(json).digest('hex').slice(0, 12);
}

export function poolDefHash(pool) {
  let def;
  if (pool.snapshot) def = `snapshot:${pool.snapshot}`;
  else {
    try { def = fs.readFileSync(path.resolve(pool.projectDir, pool.definitionFile), 'utf8'); } catch { def = `missing:${pool.definitionFile}`; }
  }
  let namespace = '';
  try { namespace = JSON.parse(fs.readFileSync(path.join(pool.projectDir, 'sfdx-project.json'), 'utf8')).namespace || ''; } catch { /* none */ }
  let hook = null;
  if (pool.setupHook) {
    const f = hookFile(pool.projectDir);
    hook = f ? fs.readFileSync(f, 'utf8') : 'missing';
  }
  return computeDefHash({ def, namespace, hubUsername: pool.hubUsername, hook });
}
