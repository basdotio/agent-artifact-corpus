// CLI commands (SPEC section 2). Each returns an output object built on baseOutput() from allowlisted fields
// only, or throws SpError (optionally with .extra fields merged into the error output).
import fs from 'node:fs';
import path from 'node:path';
import {
  SpError, fail, baseOutput, jsonMode, intArg, lifeLeftHours, now, nowIso, randHex, realpath, sanitizePoolName, ALIAS_RE, scrub,
} from './util.mjs';
import {
  POOL_DEFAULTS, loadConfig, updateConfig, loadState, updateState, counts, logLine, poolDefHash, hookFile, hookSha256,
  newMachineId, MACHINE_ID_RE, orgDescription,
} from './store.mjs';
import { tick, kickTick, runWorker, releaseEntries, findListed, orgIsLive, durationFitsClaimLife, RELEASABLE } from './pool.mjs';

const MIN_SF = [2, 147, 7];

// ---------------------------------------------------------------- shared

const service = () => import('./service.mjs');
const serviceOpts = (ctx) => ({ home: ctx.home, platform: ctx.platform, dryRun: process.env.SCRATCHPOOL_SERVICE_DRYRUN === '1' });

function serviceError(e) {
  if (e instanceof SpError) return e;
  const code = e.code === 'SERVICE_UNSUPPORTED' || e.code === 'USAGE' ? e.code : 'SERVICE_UNSUPPORTED';
  const msg = e.crontab ? `${e.message}. Add this line with \`crontab -e\` instead: ${e.crontab}` : e.message;
  return new SpError(code, msg, { extra: e.crontab ? { crontab: e.crontab } : {} });
}

async function installSvc(ctx, intervalMinutes) {
  const svc = await service();
  try {
    const r = svc.installService({ ...serviceOpts(ctx), nodePath: ctx.nodePath, scriptPath: ctx.scriptPath, sfPath: ctx.sf.bin, intervalMinutes });
    return { installed: r.installed, platform: r.platform, intervalMinutes };
  } catch (e) { throw serviceError(e); }
}

async function svcStatus(ctx) {
  const svc = await service();
  try {
    const s = svc.serviceStatus(serviceOpts(ctx));
    return { installed: !!s.installed, platform: s.platform, intervalMinutes: s.intervalMinutes ?? null, detail: s.detail ?? null };
  } catch (e) { return { installed: false, platform: ctx.platform, intervalMinutes: null, detail: scrub(e.message) }; }
}

// The scheduler entry points at the exact nodePath/scriptPath/sfPath recorded at install time. When one of
// them disappears (npx cache purged, plugin updated to a new versioned directory, Node or sf moved) the
// scheduled tick fails silently. Any interactive command that notices re-installs the service with the
// paths of the copy that is running now.
async function healService(ctx, out) {
  const c = ctx.config;
  const gone = (p) => !!p && !fs.existsSync(p);
  const stale = gone(c.scriptPath) || gone(c.nodePath) || (gone(c.sfPath) && !!ctx.sf.bin);
  if (!stale || !Object.keys(c.pools).length) return;
  const s = await svcStatus(ctx);
  if (!s.installed) return;
  try {
    await installSvc(ctx, c.intervalMinutes);
    ctx.config = updateConfig((x) => {
      x.nodePath = ctx.nodePath; x.scriptPath = ctx.scriptPath;
      if (ctx.sf.bin) x.sfPath = ctx.sf.bin;
    });
    out.warnings.push(`SERVICE_REPAIRED: the scheduler pointed at a path that no longer exists; re-installed it for ${ctx.scriptPath}`);
    logLine(null, 'service-repaired', ctx.scriptPath);
  } catch (e) {
    out.warnings.push(`SERVICE_STALE: the scheduler points at a missing path and could not be re-installed (${scrub(e.message)}); run \`scratchpool service install\``);
  }
}

// Orgs expire at UTC midnight of their expiration date, so durationDays must leave more than
// claimMinLifeHours of life even for an org created just before midnight, or every tick would delete and
// recreate it. durationDays null resolves to 3 (Developer Edition hub) or 7, so it is checked as 3.
function checkDuration(pool) {
  const days = pool.durationDays ?? 3;
  if (!durationFitsClaimLife(days, pool.claimMinLifeHours)) {
    const minDays = Math.floor(pool.claimMinLifeHours / 24) + 2;
    fail('USAGE', `durationDays ${pool.durationDays ?? 'default (3 on a Developer Edition hub)'} is too short for claimMinLifeHours ${pool.claimMinLifeHours}: `
      + `a new org would be recycled at once. Use durationDays >= ${minDays}, or lower claimMinLifeHours below ${(days - 1) * 24}.`);
  }
}

function lastTickAll(ctx) {
  let last = null;
  for (const n of Object.keys(ctx.config.pools)) {
    const t = loadState(n).lastTickAt;
    if (t && (!last || t > last)) last = t;
  }
  return last;
}

export function selectPool(ctx, flags) {
  const pools = ctx.config.pools;
  const names = Object.keys(pools);
  if (flags.pool) {
    if (!Object.hasOwn(pools, flags.pool)) fail('NO_POOL', `no pool named "${flags.pool}"${names.length ? `; pools: ${names.join(', ')}` : '; run `scratchpool init` in your project'}`);
    return flags.pool;
  }
  if (!names.length) fail('NO_POOL', 'no pool configured; run `scratchpool init` in your Salesforce project');
  const cwd = realpath(process.cwd());
  let best = null;
  for (const n of names) {
    const d = pools[n].projectDir;
    if (cwd === d || cwd.startsWith(d.endsWith(path.sep) ? d : d + path.sep)) {
      if (!best || d.length > pools[best].projectDir.length) best = n;
    }
  }
  if (best) return best;
  if (names.length === 1) return names[0];
  fail('NO_POOL', `more than one pool and the current directory is in none of them; pass --pool <name>. Pools: ${names.join(', ')}`);
}

function withPool(out, ctx, name) {
  const pool = ctx.config.pools[name];
  out.pool = name;
  out.counts = counts(loadState(name), pool);
  return out;
}

function confirm(flags, question) {
  if (flags.yes) return;
  if (jsonMode(flags) || !process.stdin.isTTY) fail('CONFIRM_REQUIRED', `${question} Re-run with --yes to confirm.`);
  process.stderr.write(`${question} [y/N] `);
  const buf = Buffer.alloc(256);
  let n = 0;
  try { n = fs.readSync(0, buf, 0, buf.length, null); } catch { n = 0; }
  if (!/^\s*y(es)?\s*$/i.test(buf.toString('utf8', 0, n))) fail('CONFIRM_REQUIRED', 'cancelled');
}

function findProjectRoot(start) {
  let d = realpath(start);
  for (;;) {
    if (fs.existsSync(path.join(d, 'sfdx-project.json'))) return d;
    const up = path.dirname(d);
    if (up === d) return null;
    d = up;
  }
}

function cmpVersion(a, b) {
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] - b[i];
  return 0;
}

function verifyHub(ctx, hub) {
  let hubUsername;
  try { hubUsername = ctx.sf.hubUsername(hub); } catch (e) {
    if (e.code === 'SF_MISSING') throw e;
    fail('NO_DEVHUB', `"${hub}" is not an authenticated org: ${e.message}. Run \`sf org login web --set-default-dev-hub --alias ${hub}\`.`);
  }
  const list = ctx.sf.orgList();
  if (!hubUsername || !list.devHubs.some((h) => h.username === hubUsername)) {
    fail('NO_DEVHUB', `"${hub}" is not a Dev Hub in your local sf auth (sf org list → devHubs).`);
  }
  return hubUsername;
}

const SNAPSHOT_RE = /^[A-Za-z0-9_][A-Za-z0-9_.-]{0,79}$/;

function relDef(projectDir, p, cwd) {
  const abs = path.resolve(cwd, p);
  if (!fs.existsSync(abs)) fail('USAGE', `definition file not found: ${abs}`);
  const rel = path.relative(projectDir, abs);
  return rel && !rel.startsWith('..') && !path.isAbsolute(rel) ? rel.split(path.sep).join('/') : abs;
}

// ---------------------------------------------------------------- init

export async function cmdInit(ctx, { flags }) {
  const out = baseOutput('init');
  const projectDir = findProjectRoot(process.cwd());
  if (!projectDir) fail('NOT_A_PROJECT', 'no sfdx-project.json found in this directory or any parent; run init inside your Salesforce project');
  if (!ctx.sf.bin) fail('SF_MISSING', 'the Salesforce CLI (sf) was not found; install @salesforce/cli or set SCRATCHPOOL_SF_BIN');
  if (flags.def && flags.snapshot) fail('USAGE', 'use either --def or --snapshot, not both');

  const v = ctx.sf.version();
  if (v && cmpVersion(v, MIN_SF) < 0) out.warnings.push(`SF_OLD: sf ${v.join('.')} found; scratchpool is tested with ${MIN_SF.join('.')}+ (run \`sf update\`)`);

  const hub = flags.hub || ctx.sf.defaultHub();
  if (!hub) fail('NO_DEVHUB', 'no Dev Hub given and no default target-dev-hub set; pass --hub <alias> or run `sf config set target-dev-hub=<alias> --global`');
  const hubUsername = verifyHub(ctx, hub);

  const name = flags.pool ? sanitizePoolName(flags.pool) : sanitizePoolName(path.basename(projectDir));
  const prev = ctx.config.pools[name] || {};
  const pool = { projectDir, hub, hubUsername, ...POOL_DEFAULTS, ...prev };
  pool.projectDir = projectDir;
  pool.hub = hub;
  pool.hubUsername = hubUsername;
  if (flags.size !== undefined) pool.size = intArg(flags.size, '--size', 0, 50);
  if (flags.duration !== undefined) pool.durationDays = intArg(flags.duration, '--duration', 1, 30);
  if (flags.snapshot) {
    if (!SNAPSHOT_RE.test(flags.snapshot)) fail('USAGE', `invalid snapshot name "${flags.snapshot}"`);
    pool.snapshot = flags.snapshot;
    if (pool.definitionFile && !fs.existsSync(path.resolve(projectDir, pool.definitionFile))) pool.definitionFile = null;
  }
  if (flags.def) { pool.definitionFile = relDef(projectDir, flags.def, process.cwd()); pool.snapshot = null; }
  if (!pool.snapshot) {
    pool.definitionFile ||= POOL_DEFAULTS.definitionFile;
    if (!fs.existsSync(path.resolve(projectDir, pool.definitionFile))) {
      fail('USAGE', `scratch org definition not found: ${path.resolve(projectDir, pool.definitionFile)}; pass --def <path> or --snapshot <name>`);
    }
  }
  if (flags['setup-hook']) {
    pool.setupHook = true;
    pool.setupHookSha256 = hookSha256(projectDir, ctx.platform);
    if (!hookFile(projectDir, ctx.platform)) out.warnings.push('SETUP_HOOK_MISSING: --setup-hook given but .scratchpool/setup (or setup.mjs / setup.cmd) does not exist yet; refill is skipped until you create it and run `config set setupHook true`');
  }
  checkDuration(pool);
  const interval = flags.interval !== undefined ? intArg(flags.interval, '--interval', 1, 1439) : undefined;

  ctx.config = updateConfig((c) => {
    if (!MACHINE_ID_RE.test(c.machineId || '')) c.machineId = newMachineId();
    c.nodePath = ctx.nodePath;
    c.sfPath = ctx.sf.bin;
    c.scriptPath = ctx.scriptPath;
    if (interval !== undefined) c.intervalMinutes = interval;
    c.pools[name] = pool;
  });
  logLine(name, 'init', `hub=${hub} size=${pool.size}`);
  if (process.platform !== 'win32') { try { fs.chmodSync(ctx.home, 0o700); } catch { /* best effort */ } }

  if (flags['no-service']) {
    out.service = await svcStatus(ctx);
  } else {
    try {
      out.service = await installSvc(ctx, ctx.config.intervalMinutes);
    } catch (e) {
      out.service = { installed: false, platform: ctx.platform, intervalMinutes: null };
      out.warnings.push(`${e.code}: ${e.message}`);
    }
  }

  const t = tick(ctx, [name]);
  out.pools = t.pools;
  out.warnings.push(...t.warnings);
  if (t.limits) out.limits = { activeRemaining: t.limits.activeRemaining, dailyRemaining: t.limits.dailyRemaining };
  out.config = ctx.config.pools[name];
  return withPool(out, ctx, name);
}

// ---------------------------------------------------------------- claim

function yyyymmdd(d) { return d.toISOString().slice(0, 10).replace(/-/g, ''); }

export async function cmdClaim(ctx, { flags, positional }) {
  const out = baseOutput('claim');
  const name = selectPool(ctx, flags);
  const pool = ctx.config.pools[name];
  out.pool = name;
  const alias = positional[0] || `sp-${yyyymmdd(now())}-${randHex(4)}`;
  if (positional.length > 1) fail('USAGE', 'claim takes at most one alias');
  if (!ALIAS_RE.test(alias)) fail('USAGE', `invalid alias "${alias}" (letters, digits, . _ - ; max 80)`);

  await healService(ctx, out);
  const list = ctx.sf.orgList();
  // Never repoint an alias that names a Dev Hub, sandbox or production org (including the pool's own hub).
  const taken = list.otherAliases.find((o) => o.alias === alias);
  if (alias === pool.hub || taken) {
    fail('USAGE', `alias "${alias}" already names ${alias === pool.hub ? "this pool's Dev Hub" : `a non-scratch org (${taken.username})`}; pick another alias`);
  }
  const fill = (o, e) => {
    out.alias = alias;
    out.username = o?.username ?? e?.username ?? null;
    out.orgId = o?.orgId ?? e?.orgId ?? null;
    out.instanceUrl = o?.instanceUrl ?? null;
    out.expiresAt = (o?.expirationDate || e?.expiresAt || null)?.slice(0, 10) ?? null;
    out.lifeLeftHours = lifeLeftHours(out.expiresAt);
  };

  // 1. Idempotent
  const existing = list.scratchOrgs.find((o) => o.alias === alias && orgIsLive(o));
  if (existing) {
    fill(existing, null);
    out.status = 'ready';
    out.source = 'existing';
    return finishClaim(ctx, flags, out, name, false);
  }

  // 2. Warm path: no limits call, no create.
  const defHash = poolDefHash(pool);
  const picked = updateState(name, (s) => {
    const cands = s.entries
      .filter((e) => e.status === 'ready' && (flags.any || e.defHash === defHash)
        && (lifeLeftHours(e.expiresAt) ?? 0) >= pool.claimMinLifeHours
        && orgIsLive(findListed(list, e.username), e))
      .sort((a, b) => String(a.createdAt).localeCompare(String(b.createdAt)));
    const e = cands[0];
    if (!e) return null;
    e.status = 'claimed';
    e.claimedAs = alias;
    e.claimedAt = nowIso();
    return { ...e };
  });
  if (picked) {
    try {
      ctx.sf.aliasSet(alias, picked.username);
      if (picked.alias !== alias) ctx.sf.aliasUnset(picked.alias);
      ctx.sf.setTargetOrg(alias, pool.projectDir);
    } catch (e) {
      updateState(name, (s) => {
        const x = s.entries.find((y) => y.alias === picked.alias);
        if (x) { x.status = 'ready'; x.claimedAs = null; x.claimedAt = null; }
      });
      throw e;
    }
    logLine(name, 'claimed', `${picked.alias} as ${alias}`);
    fill(findListed(list, picked.username), picked);
    out.status = 'ready';
    out.source = 'pool';
    out.setupRan = picked.setupRan ?? !!pool.setupHook;
    return finishClaim(ctx, flags, out, name, true);
  }

  // 3. Cold path
  const limits = ctx.sf.limits(pool.hub);
  out.limits = { activeRemaining: limits.activeRemaining, dailyRemaining: limits.dailyRemaining };
  if ((limits.activeRemaining ?? 0) < 1 || (limits.dailyRemaining ?? 0) < 1) {
    throw new SpError('LIMIT', `Dev Hub scratch org limit reached (active remaining ${limits.activeRemaining}, daily remaining ${limits.dailyRemaining})`,
      { extra: { limits: out.limits, pool: name, counts: counts(loadState(name), pool) } });
  }
  const interactive = process.stdout.isTTY && process.stdin.isTTY && !jsonMode(flags);
  if (!(interactive || flags.cold)) {
    kickTickIfIdle(ctx, name, pool);
    throw new SpError('POOL_EMPTY', `no ready org in pool "${name}"; it refills in the background. Retry shortly, or pass --cold to create one now (blocking, several minutes).`,
      { retryable: true, extra: { limits: out.limits, refillEtaMin: 5, pool: name, counts: counts(loadState(name), pool) } });
  }
  // A cold create spends a daily allocation and an active slot, so an agent or script must
  // carry the user's explicit yes; an interactive terminal is the user asking directly.
  if (!interactive && !flags.yes) {
    fail('CONFIRM_REQUIRED', `pool "${name}" is empty; a cold create uses one daily scratch org and one active slot for ${pool.coldDurationDays} day(s). Re-run with --cold --yes to confirm.`);
  }
  if (interactive && !flags.json) process.stderr.write(`Pool "${name}" is empty; creating a fresh scratch org (this takes a few minutes)...\n`);
  const created = ctx.sf.createScratch({
    defFile: pool.snapshot ? null : path.resolve(pool.projectDir, pool.definitionFile), snapshot: pool.snapshot || null,
    hub: pool.hub, days: pool.coldDurationDays, alias, description: orgDescription(pool, defHash, ctx.config.machineId), cwd: pool.projectDir,
  });
  updateState(name, (s) => {
    s.entries.push({ alias, username: created.username, orgId: created.orgId, defHash, createdAt: nowIso(), expiresAt: created.expiresAt,
      status: 'claimed', claimedAs: alias, claimedAt: nowIso(), pid: null, error: null, settledAt: Date.now() });
  });
  logLine(name, 'claimed-fresh', alias);
  // The setup hook runs only during background refill, never at claim time (docs/security.md).
  out.setupRan = false;
  if (pool.setupHook) out.warnings.push(`SETUP_SKIPPED: the setup hook runs only in background refill; "${alias}" was created without it`);
  ctx.sf.setTargetOrg(alias, pool.projectDir);
  fill(null, { username: created.username, orgId: created.orgId, expiresAt: created.expiresAt });
  out.status = 'ready';
  out.source = 'fresh';
  return finishClaim(ctx, flags, out, name, true);
}

// When the pool is empty but should not be, nudge a refill (no-op if a tick is already running).
function kickTickIfIdle(ctx, name, pool) {
  if (pool.size > 0 && !pool.paused && process.env.SCRATCHPOOL_NO_DETACH !== '1') kickTick(ctx, name);
}

function finishClaim(ctx, flags, out, name, replenish) {
  if (replenish) kickTick(ctx, name);
  if (process.stdout.isTTY && !jsonMode(flags) && !flags['no-open'] && out.alias) ctx.sf.open(out.alias);
  return withPool(out, ctx, name);
}

// ---------------------------------------------------------------- release

export async function cmdRelease(ctx, { flags, positional }) {
  const out = baseOutput('release');
  const name = selectPool(ctx, flags);
  const pool = ctx.config.pools[name];
  out.pool = name;
  const modes = [positional.length > 0, !!flags['pool-orgs'], !!flags.surplus, !!flags.stale, !!flags.orphans].filter(Boolean).length;
  if (modes === 0) fail('USAGE', 'release needs <alias...>, --pool-orgs, --surplus, --stale or --orphans');
  if (modes > 1) fail('USAGE', 'use only one of <alias...>, --pool-orgs, --surplus, --stale, --orphans');
  for (const a of positional) if (!ALIAS_RE.test(a) && !a.includes('@')) fail('USAGE', `invalid alias "${a}"`);

  const list = ctx.sf.orgList();
  const st = loadState(name);
  let targets = [];
  let orphans = [];
  let allowed = RELEASABLE;
  out.deleted = [];
  out.skipped = [];

  if (positional.length) {
    for (const a of positional) {
      const e = st.entries.find((x) => (x.claimedAs === a || x.alias === a) && (x.status === 'claimed' || x.status === 'ready'));
      if (!e) {
        const o = list.scratchOrgs.find((x) => x.alias === a || x.username === a);
        if (o && o.devHubUsername === pool.hubUsername) fail('NOT_MANAGED', `"${a}" is a scratch org of your Dev Hub but not managed by pool "${name}"; delete it yourself with \`sf org delete scratch -o ${a}\``);
        if (o) fail('NOT_MINE', `"${a}" is a scratch org of a different Dev Hub; scratchpool will not touch it`);
        fail('NOT_SCRATCH', `"${a}" is not a scratch org in your local sf org list`);
      }
      const o = findListed(list, e.username);
      if (!o) fail('NOT_SCRATCH', `"${a}" is not in your local sf org list scratchOrgs (already deleted or expired?)`);
      if (o.devHubUsername !== pool.hubUsername) fail('NOT_MINE', `"${a}" was not created by this pool's Dev Hub (${pool.hub})`);
      if (!targets.includes(e)) targets.push(e);
    }
    allowed = ['claimed', 'ready'];
  } else if (flags['pool-orgs']) {
    targets = st.entries.filter((e) => RELEASABLE.includes(e.status));
  } else if (flags.surplus) {
    allowed = ['ready'];
    const ready = st.entries.filter((e) => e.status === 'ready');
    const creating = st.entries.filter((e) => e.status === 'creating').length;
    const excess = Math.min(ready.length, ready.length + creating - pool.size);
    if (excess > 0) targets = [...ready].sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt))).slice(0, excess);
  } else if (flags.stale) {
    // A claimed entry is only ever a target once it is past expiresAt (the org is already gone).
    allowed = ['ready', 'failed', 'expired', 'claimed'];
    const defHash = poolDefHash(pool);
    targets = st.entries.filter((e) => e.status === 'failed' || e.status === 'expired'
      || (e.status === 'ready' && e.defHash !== defHash)
      || ((e.status === 'ready' || e.status === 'claimed') && e.expiresAt && (lifeLeftHours(e.expiresAt) ?? 1) <= 0));
  } else {
    orphans = findOrphans(ctx, name, pool, list, out);
  }

  const labels = [...targets.map((e) => e.claimedAs || e.alias), ...orphans.map((o) => o.label)];
  if (!labels.length) return withPool(out, ctx, name);
  if (orphans.length) {
    confirm(flags, `Delete ${labels.length} ORPHANED scratch org(s) of Dev Hub ${pool.hubUsername}: ${labels.join(', ')}? `
      + 'They were created by scratchpool on this machine but are not in its state (for example after a crash or a lost state file); '
      + 'if you claimed one of them and still use it, answer no.');
  } else {
    confirm(flags, `Delete ${labels.length} scratch org(s) from pool "${name}": ${labels.join(', ')}?`);
  }

  const r = releaseEntries(ctx, name, pool, targets, list, { allowed });
  out.deleted.push(...r.deleted);
  out.skipped.push(...r.skipped);
  for (const o of orphans) {
    try {
      ctx.sf.deleteScratch(o.username);
      out.deleted.push(o.label);
      logLine(name, 'released-orphan', o.label);
    } catch (e) {
      if (e.code === 'SF_MISSING') throw e;
      out.skipped.push({ alias: o.label, reason: scrub(e.message) });
    }
  }
  // Releasing named orgs frees Dev Hub slots: let the pool refill now instead of at the next scheduled tick.
  // (Mode releases such as --pool-orgs mean "empty the pool", so they never trigger a refill.)
  if (positional.length && out.deleted.length) kickTickIfIdle(ctx, name, pool);
  return withPool(out, ctx, name);
}

const ORPHAN_MIN_AGE_MS = 60 * 60 * 1000; // longer than a create (--wait 30) plus auth: never race a worker

// Orphans: Active hub ScratchOrgInfo records that THIS machine created for this hub user (Description
// `scratchpool:v1:<hubUsername>:<defHash>:<machineId>`), that no local pool state knows, that are older than
// a create can take, and that are not under a user alias locally (a sign it was claimed and is in use).
function findOrphans(ctx, name, pool, list, out) {
  const machineId = ctx.config.machineId;
  if (!MACHINE_ID_RE.test(machineId || '')) {
    out.warnings.push('NO_MACHINE_ID: this install has no machine id yet (run `scratchpool init`); no orphans can be attributed to it');
    return [];
  }
  const known = new Set();
  for (const n of Object.keys(ctx.config.pools)) for (const e of loadState(n).entries) if (e.username) known.add(e.username);
  const prefix = `scratchpool:v1:${pool.hubUsername}:`;
  const workerAlias = new RegExp(`^sp-(?:${Object.keys(ctx.config.pools).map((n) => n.replace(/[^a-z0-9-]/g, '')).join('|')})-[0-9a-f]{4}$`);
  const t = now().getTime();
  const res = [];
  for (const r of ctx.sf.hubRecords(pool.hub)) {
    const desc = String(r.Description || '');
    if (r.Status !== 'Active' || !desc.startsWith(prefix) || !desc.endsWith(`:${machineId}`) || !r.SignupUsername || known.has(r.SignupUsername)) continue;
    const o = findListed(list, r.SignupUsername);
    const label = o?.alias || r.SignupUsername;
    const created = Date.parse(r.CreatedDate || '');
    if (Number.isNaN(created) || t - created < ORPHAN_MIN_AGE_MS) {
      out.skipped.push({ alias: label, reason: 'created less than an hour ago (a create may still be running)' });
    } else if (o?.alias && !workerAlias.test(o.alias)) {
      out.skipped.push({ alias: label, reason: `has your local alias "${o.alias}" (probably claimed); delete it yourself if you are done with it` });
    } else {
      res.push({ label, username: r.SignupUsername });
    }
  }
  return res;
}

// ---------------------------------------------------------------- status

export async function cmdStatus(ctx, { flags }) {
  const out = baseOutput('status');
  const name = selectPool(ctx, flags);
  await healService(ctx, out);
  const pool = ctx.config.pools[name];
  const st = loadState(name);
  const defHash = poolDefHash(pool);
  out.entries = st.entries.map((e) => ({
    alias: e.alias, status: e.status, lifeLeftHours: lifeLeftHours(e.expiresAt), stale: e.defHash !== defHash, claimedAs: e.claimedAs ?? null,
  }));
  out.team = { poolOrgs: st.lastTeam?.poolOrgs ?? null, activeMax: st.lastTeam?.activeMax ?? st.lastLimits?.activeMax ?? null, capPct: pool.teamCapPct };
  if (st.lastLimits) out.limits = { activeRemaining: st.lastLimits.activeRemaining ?? null, dailyRemaining: st.lastLimits.dailyRemaining ?? null };
  const s = await svcStatus(ctx);
  out.service = { installed: s.installed, intervalMinutes: s.intervalMinutes ?? (s.installed ? ctx.config.intervalMinutes : null), lastTick: st.lastTickAt || lastTickAll(ctx) };
  return withPool(out, ctx, name);
}

// ---------------------------------------------------------------- config

const BOOL = (v, k) => {
  if (/^(true|yes|on|1)$/i.test(v)) return true;
  if (/^(false|no|off|0)$/i.test(v)) return false;
  return fail('USAGE', `${k} must be true or false`);
};
const NULLISH = (v) => /^(null|none|)$/i.test(String(v));

const POOL_KEYS = {
  size: (v) => intArg(v, 'size', 0, 50),
  durationDays: (v) => (NULLISH(v) ? null : intArg(v, 'durationDays', 1, 30)),
  coldDurationDays: (v) => intArg(v, 'coldDurationDays', 1, 30),
  setupHook: (v, k) => BOOL(v, k),
  dailyFloor: (v) => intArg(v, 'dailyFloor', 0, 10000),
  teamCapPct: (v) => intArg(v, 'teamCapPct', 1, 100),
  claimMinLifeHours: (v) => intArg(v, 'claimMinLifeHours', 0, 720),
  activeReserve: (v) => intArg(v, 'activeReserve', 0, 10000),
  snapshot: (v) => {
    if (NULLISH(v)) return null;
    if (!SNAPSHOT_RE.test(v)) fail('USAGE', `invalid snapshot name "${v}"`);
    return v;
  },
  definitionFile: (v, k, pool) => relDef(pool.projectDir, v, pool.projectDir),
  hub: null, // handled specially (verified against sf)
};

export async function cmdConfig(ctx, { flags, positional }) {
  const out = baseOutput('config');
  const [sub, key, value, ...rest] = positional;
  if (!['show', 'get', 'set'].includes(sub || 'show')) fail('USAGE', 'config show | get <key> | set <key> <value>');
  const isGlobal = key === 'intervalMinutes';
  if ((sub === 'get' || sub === 'set') && !key) fail('USAGE', `config ${sub} needs a key`);
  if (key && !isGlobal && !(key in POOL_KEYS)) fail('USAGE', `unknown key "${key}"; keys: ${[...Object.keys(POOL_KEYS), 'intervalMinutes'].join(', ')}`);
  if (sub === 'set' && (value === undefined || rest.length)) fail('USAGE', 'config set <key> <value>');

  if (isGlobal) {
    if (sub === 'set') {
      const n = intArg(value, 'intervalMinutes', 1, 1439);
      ctx.config = updateConfig((c) => { c.intervalMinutes = n; });
      const s = await svcStatus(ctx);
      if (s.installed) out.service = await installSvc(ctx, n);
    }
    out.value = ctx.config.intervalMinutes;
    out.intervalMinutes = ctx.config.intervalMinutes;
    try { const name = selectPool(ctx, flags); out.config = ctx.config.pools[name]; withPool(out, ctx, name); } catch { /* global key works without a pool */ }
    return out;
  }

  const name = selectPool(ctx, flags);
  const pool = ctx.config.pools[name];
  if (sub === 'set') {
    let patch;
    if (key === 'hub') {
      const hubUsername = verifyHub(ctx, value);
      patch = { hub: value, hubUsername };
    } else {
      patch = { [key]: POOL_KEYS[key](value, key, pool) };
    }
    if (key === 'setupHook') {
      // Enabling (or re-enabling) pins the hook's current contents; see hookTrusted in store.mjs.
      patch.setupHookSha256 = patch.setupHook ? hookSha256(pool.projectDir, ctx.platform) : null;
      if (patch.setupHook && !patch.setupHookSha256) {
        out.warnings.push('SETUP_HOOK_MISSING: .scratchpool/setup (or setup.mjs / setup.cmd) does not exist yet; refill is skipped until you create it and run this again');
      }
    }
    if (key === 'durationDays' || key === 'claimMinLifeHours') checkDuration({ ...pool, ...patch });
    ctx.config = updateConfig((c) => { Object.assign(c.pools[name], patch); });
    logLine(name, 'config-set', `${key}=${JSON.stringify(patch[key])}`);
  }
  out.config = ctx.config.pools[name];
  if (sub === 'get') out.value = out.config[key];
  out.intervalMinutes = ctx.config.intervalMinutes;
  return withPool(out, ctx, name);
}

// ---------------------------------------------------------------- pause / resume

export async function cmdPause(ctx, { flags }, paused) {
  const out = baseOutput(paused ? 'pause' : 'resume');
  const name = selectPool(ctx, flags);
  ctx.config = updateConfig((c) => { c.pools[name].paused = paused; });
  logLine(name, paused ? 'paused' : 'resumed');
  out.config = ctx.config.pools[name];
  return withPool(out, ctx, name);
}

// ---------------------------------------------------------------- tick

export async function cmdTick(ctx, { flags }) {
  const out = baseOutput('tick');
  let names = Object.keys(ctx.config.pools);
  if (flags.pool) {
    if (!Object.hasOwn(ctx.config.pools, flags.pool)) fail('NO_POOL', `no pool named "${flags.pool}"; pools: ${names.join(', ') || '(none)'}`);
    names = [flags.pool];
  }
  await healService(ctx, out);
  const t = tick(ctx, names);
  out.pools = t.pools;
  out.warnings.push(...t.warnings);
  if (t.limits) out.limits = { activeRemaining: t.limits.activeRemaining, dailyRemaining: t.limits.dailyRemaining };
  if (names.length === 1) withPool(out, ctx, names[0]);
  return out;
}

// ---------------------------------------------------------------- service

export async function cmdService(ctx, { flags, positional }) {
  const out = baseOutput('service');
  const sub = positional[0] || 'status';
  if (!['install', 'uninstall', 'status'].includes(sub)) fail('USAGE', 'service install | uninstall | status');
  if (sub === 'install') {
    const n = flags.interval !== undefined ? intArg(flags.interval, '--interval', 1, 1439) : ctx.config.intervalMinutes;
    out.service = await installSvc(ctx, n);
    ctx.config = updateConfig((c) => {
      if (!MACHINE_ID_RE.test(c.machineId || '')) c.machineId = newMachineId();
      c.intervalMinutes = n;
      c.nodePath = ctx.nodePath;
      c.scriptPath = ctx.scriptPath;
      if (ctx.sf.bin) c.sfPath = ctx.sf.bin;
    });
  } else if (sub === 'uninstall') {
    const svc = await service();
    try {
      const r = svc.uninstallService(serviceOpts(ctx));
      out.service = { installed: false, platform: r.platform, intervalMinutes: null };
    } catch (e) { throw serviceError(e); }
  } else {
    const s = await svcStatus(ctx);
    out.service = { installed: s.installed, platform: s.platform, intervalMinutes: s.intervalMinutes, lastTick: lastTickAll(ctx), detail: s.detail };
  }
  logLine(null, `service-${sub}`, out.service.installed ? 'installed' : 'not installed');
  return out;
}

// ---------------------------------------------------------------- uninstall

export async function cmdUninstall(ctx, { flags }) {
  const out = baseOutput('uninstall');
  const names = Object.keys(ctx.config.pools);
  if (flags['release-pool-orgs']) {
    const n = names.reduce((a, p) => a + loadState(p).entries.filter((e) => e.status !== 'claimed').length, 0);
    confirm(flags, `Remove the scratchpool service and delete ${n} unclaimed pool org(s)? Claimed orgs are kept.`);
  }
  const svc = await service();
  try {
    const r = svc.uninstallService(serviceOpts(ctx));
    out.service = { installed: false, platform: r.platform, intervalMinutes: null };
  } catch (e) { throw serviceError(e); }
  out.deleted = [];
  out.skipped = [];
  if (flags['release-pool-orgs'] && names.length) {
    const list = ctx.sf.orgList();
    for (const name of names) {
      const pool = ctx.config.pools[name];
      const targets = loadState(name).entries.filter((e) => ['ready', 'creating', 'failed', 'expired'].includes(e.status));
      const r = releaseEntries(ctx, name, pool, targets, list);
      out.deleted.push(...r.deleted);
      out.skipped.push(...r.skipped);
    }
  }
  logLine(null, 'uninstall', `released=${out.deleted.length}`);
  return out;
}

// ---------------------------------------------------------------- _worker

export async function cmdWorker(ctx, { flags }) {
  const out = baseOutput('_worker');
  if (!flags.pool || !flags.alias) fail('USAGE', '_worker --pool <name> --alias <alias>');
  if (!Object.hasOwn(ctx.config.pools, flags.pool)) fail('NO_POOL', `no pool named "${flags.pool}"`);
  const r = runWorker(ctx, flags.pool, flags.alias);
  out.alias = flags.alias;
  if (!r.ok) out.warnings.push(`worker: ${r.reason}`);
  return withPool(out, ctx, flags.pool);
}

export { loadConfig };
