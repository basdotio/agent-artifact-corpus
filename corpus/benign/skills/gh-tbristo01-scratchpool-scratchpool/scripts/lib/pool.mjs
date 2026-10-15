// The pool engine: tick (reconcile, recycle, surplus, refill guards, start workers), the background worker,
// the setup hook and the shared "release an entry" primitive. Everything runs on the developer's machine.
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { lifeLeftHours, isExpiredDate, nowIso, now, randHex, scrub } from './util.mjs';
import { loadState, updateState, counts, logLine, paths, tryLock, unlock, poolDefHash, hookFile, hookTrusted, orgDescription } from './store.mjs';

const CREATING_DEAD_MS = 45 * 60 * 1000;
const TICK_LOCK_STALE_MS = 50 * 60 * 1000; // longer than one synchronous create (--wait 30) + hook budget slack
const HOOK_TIMEOUT_MS = 30 * 60 * 1000;

export const noDetach = () => process.env.SCRATCHPOOL_NO_DETACH === '1';

export function pidAlive(pid) {
  if (!pid || !Number.isInteger(pid)) return false;
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}

export function findListed(list, username) {
  if (!list || !username) return null;
  return list.scratchOrgs.find((o) => o.username === username) || null;
}

export function orgIsLive(o, entry) {
  return !!o && !o.isExpired && !isExpiredDate(o.expirationDate || entry?.expiresAt);
}

// ---------------------------------------------------------------- release primitive

// Delete one state entry's org (if it has one and it is ours) and report. Does NOT touch state.
// Returns {ok:true} | {ok:false, reason}. An entry with a username is always deleted on the hub, even if a
// (possibly stale) `sf org list` does not show it; only a failed delete of an unlisted or expired org is
// treated as "already gone".
export function deleteEntryOrg(ctx, pool, entry, list) {
  if (!entry.username) return { ok: true, note: 'no org created' };
  const o = findListed(list, entry.username);
  if (o && o.devHubUsername && pool.hubUsername && o.devHubUsername !== pool.hubUsername) {
    return { ok: false, reason: `NOT_MINE: ${entry.username} belongs to another Dev Hub` };
  }
  try {
    ctx.sf.deleteScratch(entry.username);
    return { ok: true };
  } catch (e) {
    if (e.code === 'SF_MISSING') throw e;
    if (entry.status === 'expired' || entry.prevStatus === 'expired' || (o && o.isExpired)) return { ok: true, note: 'expired; local record dropped' };
    if (list && !o) return { ok: true, note: 'not in local sf org list; local record dropped' };
    return { ok: false, reason: scrub(e.message) };
  }
}

export const RELEASABLE = ['ready', 'creating', 'failed', 'expired'];

// Release entries of one pool, chosen from an earlier snapshot. Two-phase, so a concurrent claim, worker or
// tick can never lose or double-handle an entry:
//   1. under the state lock, re-read each target by alias; keep it only if its CURRENT status is in `allowed`
//      (never `claimed` unless the caller explicitly allows it), take the current username, and mark it
//      `releasing` (claims only ever pick `ready`, and workers only finish `creating` entries);
//   2. delete the org outside the lock, then drop the entry (or restore its status if the delete failed).
export function releaseEntries(ctx, name, pool, entries, list, { allowed = RELEASABLE } = {}) {
  const deleted = [];
  const skipped = [];
  const wanted = new Set(entries.map((e) => e.alias));
  const marked = updateState(name, (s) => {
    const out = [];
    for (const e of s.entries) {
      if (!wanted.has(e.alias)) continue;
      wanted.delete(e.alias);
      if (!allowed.includes(e.status)) {
        skipped.push({ alias: e.claimedAs || e.alias, reason: `now ${e.status}; left alone` });
        continue;
      }
      e.prevStatus = e.status;
      e.status = 'releasing';
      e.releasePid = process.pid;
      out.push({ ...e });
    }
    return out;
  });
  for (const a of wanted) skipped.push({ alias: a, reason: 'no longer in state' });
  for (const e of marked) {
    const label = e.claimedAs || e.alias;
    const r = deleteEntryOrg(ctx, pool, e, list);
    if (r.ok) {
      updateState(name, (s) => { s.entries = s.entries.filter((x) => x.alias !== e.alias); });
      deleted.push(label);
      logLine(name, 'released', `${label}${r.note ? ' (' + r.note + ')' : ''}`);
    } else {
      updateState(name, (s) => {
        const x = s.entries.find((y) => y.alias === e.alias);
        if (x && x.status === 'releasing') { x.status = e.prevStatus; delete x.prevStatus; delete x.releasePid; }
      });
      skipped.push({ alias: label, reason: r.reason });
      logLine(name, 'release-failed', `${label} ${r.reason}`);
    }
  }
  return { deleted, skipped };
}

// ---------------------------------------------------------------- setup hook

export function runSetupHook(ctx, pool, alias) {
  const file = hookFile(pool.projectDir, ctx.platform);
  if (!file) return { ok: false, error: 'setup hook enabled but .scratchpool/setup (or setup.mjs / setup.cmd) was not found' };
  if (!hookTrusted(pool, ctx.platform)) return { ok: false, error: 'SETUP_UNTRUSTED: the setup hook changed since it was enabled; review it, then run `config set setupHook true`' };
  let cmd = file;
  let args = [];
  const opts = { cwd: pool.projectDir, env: { ...process.env, SCRATCHPOOL_TARGET: alias }, stdio: 'ignore', timeout: HOOK_TIMEOUT_MS, windowsHide: true };
  if (file.endsWith('.mjs')) { cmd = ctx.nodePath; args = [file]; }
  // cmd /s strips the first and last quote of the command line, so wrap the quoted path in one more pair
  // (as lib/sf.mjs does); otherwise a path with spaces or & | ( is split by cmd.
  else if (/\.cmd$/i.test(file)) { cmd = process.env.ComSpec || 'cmd.exe'; args = ['/d', '/s', '/c', `""${file}""`]; opts.windowsVerbatimArguments = true; }
  const r = spawnSync(cmd, args, opts);
  if (r.error) return { ok: false, error: `setup hook failed to run: ${r.error.code || r.error.message}` };
  if (r.status !== 0) return { ok: false, error: `setup hook exited with code ${r.status ?? r.signal}` };
  return { ok: true };
}

// ---------------------------------------------------------------- worker

export function startWorker(ctx, name, pool, days, defHash) {
  const alias = updateState(name, (s) => {
    let a;
    do { a = `sp-${name}-${randHex(4)}`; } while (s.entries.some((e) => e.alias === a));
    s.entries.push({ alias: a, username: null, orgId: null, defHash, createdAt: nowIso(), expiresAt: null,
      status: 'creating', claimedAs: null, claimedAt: null, pid: noDetach() ? process.pid : null, error: null, days });
    return a;
  });
  logLine(name, 'started', alias);
  if (noDetach()) {
    runWorker(ctx, name, alias);
    return alias;
  }
  const child = spawn(ctx.nodePath, [ctx.scriptPath, '_worker', '--pool', name, '--alias', alias],
    { detached: true, stdio: 'ignore', cwd: pool.projectDir, windowsHide: true });
  child.on('error', () => {});
  const pid = child.pid;
  child.unref();
  updateState(name, (s) => { const e = s.entries.find((x) => x.alias === alias); if (e && !e.pid) e.pid = pid ?? null; });
  return alias;
}

export function runWorker(ctx, name, alias) {
  const pool = ctx.config.pools[name];
  if (!pool) return { ok: false, reason: 'no such pool' };
  const entry = loadState(name).entries.find((e) => e.alias === alias && e.status === 'creating');
  if (!entry) return { ok: false, reason: 'no creating entry' };
  updateState(name, (s) => { const e = s.entries.find((x) => x.alias === alias); if (e) e.pid = process.pid; });
  // Only ever advance an entry that is still `creating`: a release may have taken it over meanwhile.
  const mine = (s) => s.entries.find((x) => x.alias === alias && x.status === 'creating');

  const markFailed = (msg) => {
    updateState(name, (s) => { const e = mine(s); if (e) { e.status = 'failed'; e.error = scrub(msg); e.pid = null; } });
    logLine(name, 'failed', `${alias} ${msg}`);
  };

  let created;
  try {
    created = ctx.sf.createScratch({
      defFile: pool.snapshot ? null : path.resolve(pool.projectDir, pool.definitionFile),
      snapshot: pool.snapshot || null, hub: pool.hub, days: entry.days ?? pool.durationDays ?? 7, alias,
      description: orgDescription(pool, entry.defHash, ctx.config.machineId), cwd: pool.projectDir,
    });
  } catch (e) {
    markFailed(e.message);
    return { ok: false, reason: e.code };
  }
  const still = updateState(name, (s) => {
    const e = mine(s);
    if (!e) return false;
    e.username = created.username; e.orgId = created.orgId; e.expiresAt = created.expiresAt;
    return true;
  });
  if (!still) {
    // Released while we were creating: do not leave an orphan holding an active slot.
    try { if (created.username) ctx.sf.deleteScratch(created.username); } catch { /* --stale will find it */ }
    logLine(name, 'orphan-cleanup', alias);
    return { ok: false, reason: 'released during create' };
  }
  let setupRan = false;
  if (pool.setupHook) {
    const h = runSetupHook(ctx, pool, alias);
    if (!h.ok) { markFailed(h.error); return { ok: false, reason: 'SETUP_FAILED' }; }
    setupRan = true;
  }
  const done = updateState(name, (s) => {
    const e = mine(s);
    if (!e) return false;
    // settledAt is wall-clock (not SCRATCHPOOL_NOW): reconcile compares it with when `sf org list` was fetched.
    e.status = 'ready'; e.pid = null; e.error = null; e.setupRan = setupRan; e.settledAt = Date.now(); delete e.days;
    return true;
  });
  if (!done) {
    // Released during the setup hook; the releaser deletes the org (it had the username by then).
    logLine(name, 'released-during-setup', alias);
    return { ok: false, reason: 'released during setup' };
  }
  logLine(name, 'ready', `${alias} expires ${created.expiresAt}`);
  return { ok: true };
}

// ---------------------------------------------------------------- tick

// Expiry is a UTC date, so an org created just before UTC midnight with `days` of duration has only
// (days - 1) * 24 h left. It must still have more than claimMinLifeHours, or recycle deletes it on the next
// tick and refill creates another: a create/delete loop that burns the daily allocation.
export function durationFitsClaimLife(days, claimMinLifeHours) {
  return (days - 1) * 24 > claimMinLifeHours;
}

function reconcile(s, list) {
  const t = now().getTime();
  const kept = [];
  for (const e of s.entries) {
    if (e.status === 'creating') {
      const age = t - Date.parse(e.createdAt || 0);
      if (!pidAlive(e.pid) && age > CREATING_DEAD_MS) { e.status = 'failed'; e.error = 'background create did not finish (worker exited)'; e.pid = null; }
    } else if (e.status === 'releasing') {
      // The releasing process died mid-delete: hand the entry back to recycle (it retries the delete).
      if (!pidAlive(e.releasePid)) { e.status = 'failed'; e.error = 'release did not finish'; delete e.prevStatus; delete e.releasePid; }
    } else if (list && (e.status === 'ready' || e.status === 'claimed')) {
      // Settled (ready, or claimed fresh) after the org list was fetched: the list cannot know it yet.
      if (e.settledAt && list.fetchedAt && e.settledAt > list.fetchedAt) { kept.push(e); continue; }
      const live = orgIsLive(findListed(list, e.username), e) && !isExpiredDate(e.expiresAt);
      if (!live) {
        if (e.status === 'claimed') continue; // gone: drop it
        e.status = 'expired';
      }
    }
    kept.push(e);
  }
  s.entries = kept;
}

function poolSummary(name, pool, extra = {}) {
  const c = counts(loadState(name), pool);
  return { name, paused: !!pool.paused, ready: c.ready, creating: c.creating, claimed: c.claimed, size: pool.size,
    started: 0, released: [], skipped: null, ...extra };
}

export function tickPool(ctx, name, getList) {
  const pool = ctx.config.pools[name];
  const lock = paths.tickLock(name);
  if (!tryLock(lock, TICK_LOCK_STALE_MS)) {
    logLine(name, 'tick-skipped', 'locked');
    return poolSummary(name, pool, { skipped: 'locked' });
  }
  const released = [];
  let started = 0;
  let skipped = null;
  let limits = null;
  let team = null;
  const warnings = [];
  try {
    // 1. Reconcile
    const needsList = loadState(name).entries.some((e) => e.status === 'ready' || e.status === 'claimed');
    const list = needsList ? getList() : null;
    updateState(name, (s) => reconcile(s, list));

    if (pool.paused) {
      skipped = 'paused';
    } else {
      // 2. Recycle
      const st = loadState(name);
      const recycle = st.entries.filter((e) => e.status === 'failed' || e.status === 'expired'
        || (e.status === 'ready' && (lifeLeftHours(e.expiresAt) ?? 0) < pool.claimMinLifeHours));
      const r1 = releaseEntries(ctx, name, pool, recycle, list);
      released.push(...r1.deleted);

      // 3. Surplus
      const st2 = loadState(name);
      const ready = st2.entries.filter((e) => e.status === 'ready');
      const creating = st2.entries.filter((e) => e.status === 'creating').length;
      const excess = ready.length + creating - pool.size;
      if (excess > 0) {
        const youngest = [...ready].sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt))).slice(0, excess);
        const r2 = releaseEntries(ctx, name, pool, youngest, list);
        released.push(...r2.deleted);
      }

      // 4. Refill guards
      const c = counts(loadState(name), pool);
      const need = pool.size - (c.ready + c.creating);
      const minDays = pool.durationDays;
      if (need > 0 && minDays != null && !durationFitsClaimLife(minDays, pool.claimMinLifeHours)) {
        // A hand-edited config whose orgs would be recycled as soon as they are created: never burn allocation.
        skipped = 'DURATION_TOO_SHORT';
        warnings.push(`${name}: durationDays ${minDays} leaves less than claimMinLifeHours ${pool.claimMinLifeHours} h of life; refill skipped (raise durationDays or lower claimMinLifeHours)`);
        logLine(name, 'refill-skipped', `DURATION_TOO_SHORT days=${minDays} claimMinLifeHours=${pool.claimMinLifeHours}`);
      } else if (need > 0 && !hookTrusted(pool, ctx.platform)) {
        // Never create an org (and burn allocation) for a hook that would not be allowed to run.
        skipped = 'SETUP_UNTRUSTED';
        warnings.push(`${name}: the setup hook is missing or changed since it was enabled; refill skipped until you review it and run \`config set setupHook true\``);
        logLine(name, 'refill-skipped', 'SETUP_UNTRUSTED');
      } else if (need > 0) {
        limits = ctx.sf.limits(pool.hub);
        if ((limits.dailyRemaining ?? 0) < pool.dailyFloor) skipped = 'DAILY_FLOOR';
        else {
          let startable = Math.min(need, (limits.activeRemaining ?? 0) - pool.activeReserve, limits.dailyRemaining ?? 0);
          if (startable <= 0) skipped = 'ACTIVE_RESERVE';
          else {
            const records = ctx.sf.hubRecords(pool.hub);
            // The cap limits idle *pool* orgs. Orgs this machine has handed out (claimed) are in use by their
            // owner, so they must not block the owner's next refill (seen live: a 3-org DE hub has a cap of 1).
            // 'releasing' too: a release in flight still shows its org as Active on the hub for a moment (seen
            // live when a claim's background tick overlapped a release of the same org).
            const claimedHere = new Set(Object.keys(ctx.config.pools || {}).flatMap((n) =>
              loadState(n).entries.filter((e) => e.status === 'claimed' || e.status === 'releasing').map((e) => e.username)));
            const tagged = records.filter((r) => String(r.Description || '').startsWith('scratchpool:v1:') &&
              !claimedHere.has(r.SignupUsername)).length;
            const cap = (limits.activeMax ?? 0) * pool.teamCapPct / 100;
            team = { poolOrgs: tagged, activeMax: limits.activeMax, capPct: pool.teamCapPct };
            if (tagged >= cap) skipped = 'TEAM_CAP';
            else {
              startable = Math.min(startable, Math.ceil(cap - tagged));
              // 5. Start workers
              const days = pool.durationDays ?? ((limits.dailyMax ?? 99) <= 6 ? 3 : 7);
              if (!durationFitsClaimLife(days, pool.claimMinLifeHours)) throw Object.assign(new Error(`durationDays ${days} too short for claimMinLifeHours ${pool.claimMinLifeHours}`), { code: 'DURATION_TOO_SHORT' });
              const defHash = poolDefHash(pool);
              for (let i = 0; i < startable; i++) { startWorker(ctx, name, pool, days, defHash); started++; }
            }
          }
        }
        if (skipped) logLine(name, 'refill-skipped', `${skipped} need=${need} active=${limits.activeRemaining} daily=${limits.dailyRemaining}`);
      }
    }
  } catch (e) {
    if (e.code === 'SF_MISSING') throw e;
    skipped = e.code || 'ERROR';
    if (e.code === 'DURATION_TOO_SHORT') e.message += ' (raise durationDays or lower claimMinLifeHours)';
    warnings.push(`${name}: ${scrub(e.message)}`);
    logLine(name, 'tick-error', `${e.code} ${e.message}`);
  } finally {
    try {
      updateState(name, (s) => {
        s.lastTickAt = nowIso();
        if (limits) s.lastLimits = { activeRemaining: limits.activeRemaining, dailyRemaining: limits.dailyRemaining, activeMax: limits.activeMax, dailyMax: limits.dailyMax, at: nowIso() };
        if (team) s.lastTeam = team;
      });
    } catch { /* best effort */ }
    unlock(lock);
  }
  logLine(name, 'tick', `started=${started} released=${released.length} skipped=${skipped}`);
  return { summary: poolSummary(name, pool, { started, released, skipped }), limits, warnings };
}

export function tick(ctx, names) {
  let cached = null;
  const getList = () => {
    if (!cached) {
      const fetchedAt = Date.now(); // wall clock, taken BEFORE the call (see reconcile)
      cached = ctx.sf.orgList();
      cached.fetchedAt = fetchedAt;
    }
    return cached;
  };
  const pools = [];
  const warnings = [];
  let limits = null;
  for (const n of names) {
    const r = tickPool(ctx, n, getList);
    if (r.summary) { pools.push(r.summary); warnings.push(...r.warnings); limits = r.limits || limits; } else pools.push(r);
  }
  return { pools, warnings, limits };
}

// Fire-and-forget replenishment after a claim.
export function kickTick(ctx, name) {
  if (noDetach()) { try { tick(ctx, [name]); } catch { /* best effort */ } return; }
  try {
    const child = spawn(ctx.nodePath, [ctx.scriptPath, 'tick', '--pool', name, '--json'],
      { detached: true, stdio: 'ignore', cwd: ctx.config.pools[name]?.projectDir || process.cwd(), windowsHide: true });
    child.on('error', () => {});
    child.unref();
  } catch { /* timer will catch up */ }
}

