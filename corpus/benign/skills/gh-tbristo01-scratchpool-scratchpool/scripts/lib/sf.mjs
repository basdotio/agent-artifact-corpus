// The ONLY place scratchpool talks to Salesforce: spawning the developer's own `sf` CLI with --json and an
// argument array (never a shell string). Every call is one of the allowlisted commands in SPEC section 4.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { SpError, scrub, clipUntrusted } from './util.mjs';

const isWin = () => process.platform === 'win32';

function onPath(names) {
  const dirs = String(process.env.PATH || '').split(path.delimiter).filter(Boolean);
  for (const d of dirs) {
    for (const n of names) {
      const p = path.join(d, n);
      try { if (fs.statSync(p).isFile()) return p; } catch { /* keep looking */ }
    }
  }
  return null;
}

// SCRATCHPOOL_SF_BIN > configured sfPath (if it still exists) > PATH lookup.
export function resolveSf(configSfPath) {
  const env = process.env.SCRATCHPOOL_SF_BIN;
  if (env) return fs.existsSync(env) ? path.resolve(env) : null;
  if (configSfPath && fs.existsSync(configSfPath)) return configSfPath;
  return onPath(isWin() ? ['sf.cmd', 'sf.exe', 'sf'] : ['sf']);
}

// Windows: Node refuses to spawn .cmd/.bat without a shell (CVE-2024-27980). Go through cmd.exe, escaping
// the way cross-spawn does; still built from an array, never interpolated from free text (aliases are
// validated against ALIAS_RE before they get here).
// cmd metacharacters, including space and comma, which split tokens when not inside cmd's quote mode.
const CMD_META = /([()\][%!^"`<>&|;, *?])/g;
// The command token: caret-escape metacharacters (spaces too) without quoting, so a path such as
// C:\Program Files\sf\bin\sf.cmd stays one token. (A caret-escaped quote does not enter quote mode.)
export function winEscapeCommand(cmd) {
  return String(cmd).replace(CMD_META, '^$1');
}
// An argument: MSVCRT-quote it (backslashes before a quote doubled), then caret-escape every metacharacter.
export function winQuote(a) {
  let s = String(a);
  s = s.replace(/(\\*)"/g, '$1$1\\"').replace(/(\\*)$/, '$1$1');
  return `"${s}"`.replace(CMD_META, '^$1');
}
// argv for cmd.exe running a .cmd/.bat: /s strips the outer quote pair we add around the whole line.
export function winCmdArgv(bin, args) {
  return ['/d', '/s', '/c', `"${[winEscapeCommand(bin), ...args.map(winQuote)].join(' ')}"`];
}

export class Sf {
  constructor(bin, opts = {}) {
    this.bin = bin;
    this.log = opts.log || (() => {});
  }

  raw(args, { cwd, timeoutMs = 45 * 60 * 1000 } = {}) {
    if (!this.bin) throw new SpError('SF_MISSING', 'the Salesforce CLI (sf) was not found; install @salesforce/cli or set SCRATCHPOOL_SF_BIN');
    let cmd = this.bin;
    let argv = args;
    const opts = { cwd, encoding: 'utf8', timeout: timeoutMs, maxBuffer: 64 * 1024 * 1024,
      env: { ...process.env, SF_JSON_TO_STDOUT: 'true', SF_DISABLE_TELEMETRY: 'true', SF_AUTOUPDATE_DISABLE: 'true' },
      stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true };
    if (isWin() && /\.(cmd|bat)$/i.test(this.bin)) {
      cmd = process.env.ComSpec || 'cmd.exe';
      argv = winCmdArgv(this.bin, args);
      opts.windowsVerbatimArguments = true;
    }
    const r = spawnSync(cmd, argv, opts);
    if (r.error) {
      if (r.error.code === 'ENOENT') throw new SpError('SF_MISSING', 'the Salesforce CLI (sf) was not found; install @salesforce/cli or set SCRATCHPOOL_SF_BIN');
      throw new SpError('SF_ERROR', scrub(`sf ${args.slice(0, 3).join(' ')} failed: ${r.error.message}`), { sfExit: 1 });
    }
    return { status: r.status ?? 1, stdout: r.stdout || '', stderr: r.stderr || '' };
  }

  // Run an sf command that supports --json; returns `result` or throws SpError(LIMIT|SF_ERROR) with a scrubbed message.
  json(args, opts) {
    const r = this.raw([...args, '--json'], opts);
    let parsed = null;
    try { parsed = JSON.parse(r.stdout); } catch {
      const i = r.stdout.indexOf('{');
      if (i >= 0) { try { parsed = JSON.parse(r.stdout.slice(i)); } catch { /* not json */ } }
    }
    const what = `sf ${args.filter((a) => !a.startsWith('-')).slice(0, 3).join(' ')}`;
    if (r.status === 0 && parsed && (parsed.status === 0 || parsed.status === undefined)) return parsed.result;
    const name = clipUntrusted(parsed?.name || '', 80);
    const message = clipUntrusted(parsed?.message || r.stderr.split('\n').find(Boolean) || `${what} exited ${r.status}`);
    const code = /limit|allocation/i.test(name) || /limit|allocation/i.test(message) ? 'LIMIT' : 'SF_ERROR';
    const exit = r.status || parsed?.exitCode || parsed?.status || 1;
    throw new SpError(code, `${what}: ${name ? name + ': ' : ''}${message}`, { sfExit: exit, sfName: name });
  }

  version() {
    const r = this.raw(['--version']);
    const m = /@salesforce\/cli\/(\d+)\.(\d+)\.(\d+)/.exec(r.stdout);
    return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
  }

  defaultHub() {
    const res = this.json(['config', 'get', 'target-dev-hub']);
    const v = Array.isArray(res) ? res[0]?.value : null;
    return v || null;
  }

  hubUsername(hub) {
    return this.json(['org', 'display', '-o', hub])?.username || null;
  }

  orgList() {
    const r = this.json(['org', 'list']) || {};
    const pick = (o) => ({
      alias: o.alias ?? null, username: o.username ?? null, orgId: o.orgId ?? null,
      expirationDate: o.expirationDate ?? null, devHubUsername: o.devHubUsername ?? null,
      isExpired: o.isExpired === true || o.status === 'Expired', instanceUrl: o.instanceUrl ?? null,
    });
    const brief = (o) => ({ alias: o.alias ?? null, username: o.username ?? null });
    return {
      devHubs: (r.devHubs || []).map(brief),
      scratchOrgs: (r.scratchOrgs || []).map(pick),
      // Aliases of every non-scratch org (Dev Hubs, production, sandboxes): claim must never repoint them.
      otherAliases: [...(r.devHubs || []), ...(r.nonScratchOrgs || []), ...(r.sandboxes || []), ...(r.other || [])]
        .map(brief).filter((o) => o.alias),
    };
  }

  limits(hub) {
    const res = this.json(['org', 'list', 'limits', '-o', hub]) || [];
    const get = (n) => res.find((x) => x.name === n) || {};
    const a = get('ActiveScratchOrgs');
    const d = get('DailyScratchOrgs');
    return { activeMax: a.max ?? null, activeRemaining: a.remaining ?? null, dailyMax: d.max ?? null, dailyRemaining: d.remaining ?? null };
  }

  // Ignores authFields entirely: only username, orgId and the expiration date are read.
  createScratch({ defFile, snapshot, hub, days, alias, description, cwd }) {
    const args = ['org', 'create', 'scratch'];
    if (snapshot) args.push('--snapshot', snapshot); else args.push('-f', defFile);
    args.push('-v', hub, '-y', String(days), '-a', alias, '--description', description, '--wait', '30');
    const r = this.json(args, { cwd }) || {};
    const exp = r.scratchOrgInfo?.ExpirationDate || null;
    return { username: r.username || null, orgId: r.orgId || null, expiresAt: exp ? String(exp).slice(0, 10) : null };
  }

  aliasSet(alias, username) { return this.json(['alias', 'set', `${alias}=${username}`]); }
  aliasUnset(alias) { return this.json(['alias', 'unset', alias]); }
  setTargetOrg(alias, cwd) { return this.json(['config', 'set', `target-org=${alias}`], { cwd }); }
  deleteScratch(username) { return this.json(['org', 'delete', 'scratch', '-o', username, '--no-prompt']); }

  hubRecords(hub) {
    // Description is a long text area: SOQL cannot filter on it (INVALID_FIELD, seen live on a real
    // Dev Hub), so fetch the hub's Active records (bounded by its active allocation) and match the tag here.
    const q = "SELECT Id, SignupUsername, Description, ExpirationDate, Status, CreatedDate FROM ScratchOrgInfo WHERE Status = 'Active'";
    const r = this.json(['data', 'query', '-o', hub, '-q', q]) || {};
    return (r.records || []).filter((x) => typeof x.Description === 'string' && x.Description.startsWith('scratchpool:v1:')).map((x) => ({ SignupUsername: x.SignupUsername, Description: x.Description, ExpirationDate: x.ExpirationDate, Status: x.Status, CreatedDate: x.CreatedDate ?? null }));
  }

  open(alias) {
    // TTY only, output discarded (it may contain a frontdoor URL).
    try {
      const viaCmd = isWin() && /\.(cmd|bat)$/i.test(this.bin);
      spawnSync(viaCmd ? (process.env.ComSpec || 'cmd.exe') : this.bin,
        viaCmd ? winCmdArgv(this.bin, ['org', 'open', '-o', alias]) : ['org', 'open', '-o', alias],
        { stdio: 'ignore', windowsVerbatimArguments: viaCmd, timeout: 120000, windowsHide: true });
    } catch { /* best effort */ }
  }
}
