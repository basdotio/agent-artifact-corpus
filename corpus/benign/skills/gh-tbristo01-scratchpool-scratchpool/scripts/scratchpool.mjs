#!/usr/bin/env node
// scratchpool — a warm pool of ready Salesforce scratch orgs, managed entirely on your own machine.
// Zero dependencies (Node >= 20 built-ins). Talks to Salesforce only through your own `sf` CLI.
// Contract: docs/SPEC.md.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SpError, VERSION, baseOutput, emit, exitCodeFor, parseArgs, homeDir, platform, scrub } from './lib/util.mjs';
import { loadConfig } from './lib/store.mjs';
import { Sf, resolveSf } from './lib/sf.mjs';
import {
  cmdInit, cmdClaim, cmdRelease, cmdStatus, cmdConfig, cmdPause, cmdTick, cmdService, cmdUninstall, cmdWorker,
} from './lib/commands.mjs';

const SCRIPT_PATH = fileURLToPath(import.meta.url);

const HELP = `scratchpool ${VERSION} — a warm pool of Salesforce scratch orgs, managed locally by your OS scheduler

Usage:
  scratchpool init      [--hub <alias>] [--size <n>] [--def <path> | --snapshot <name>] [--duration <days>]
                        [--interval <minutes>] [--setup-hook] [--pool <name>] [--no-service] [--json]
  scratchpool claim     [alias] [--pool <name>] [--json] [--no-open] [--cold [--yes]] [--any]
  scratchpool release   <alias...> | --pool-orgs | --surplus | --stale | --orphans   [--pool <name>] [--yes] [--json]
  scratchpool status    [--pool <name>] [--json]           (alias: list)
  scratchpool config    show | get <key> | set <key> <value>   [--pool <name>] [--json]
  scratchpool pause     [--pool <name>] [--json]
  scratchpool resume    [--pool <name>] [--json]
  scratchpool tick      [--pool <name>] [--json]           (what the scheduler runs; also "fill now")
  scratchpool service   install | uninstall | status  [--interval <minutes>] [--json]
  scratchpool uninstall [--release-pool-orgs] [--yes] [--json]
  scratchpool --version | --help

Config keys: size, hub, definitionFile, snapshot, durationDays, coldDurationDays, setupHook, dailyFloor,
             teamCapPct, claimMinLifeHours, activeReserve, intervalMinutes (global)
Files: ${'$'}SCRATCHPOOL_HOME (default ~/.config/scratchpool): config.json, state/<pool>.json, logs/scratchpool.log`;

const COMMANDS = {
  init: cmdInit,
  claim: cmdClaim,
  release: cmdRelease,
  return: cmdRelease,
  status: cmdStatus,
  list: cmdStatus,
  config: cmdConfig,
  pause: (ctx, a) => cmdPause(ctx, a, true),
  resume: (ctx, a) => cmdPause(ctx, a, false),
  tick: cmdTick,
  service: cmdService,
  uninstall: cmdUninstall,
  _worker: cmdWorker,
};

function human(o) {
  switch (o.command) {
    case 'claim':
      return `${o.alias} (${o.source}) ${o.username} — expires ${o.expiresAt}, ${o.lifeLeftHours}h left. Default org set.` +
        (process.stdout.isTTY ? '' : `\nOpen it with: sf org open -o ${o.alias}`);
    case 'status': {
      const c = o.counts;
      const lines = [`pool ${o.pool}: ${c.ready} ready, ${c.creating} creating, ${c.claimed} claimed, size ${c.size}${c.paused ? ' (paused)' : ''}`];
      for (const e of o.entries) lines.push(`  ${e.alias.padEnd(24)} ${e.status.padEnd(9)} ${e.lifeLeftHours ?? '-'}h${e.stale ? ' stale' : ''}${e.claimedAs ? ' as ' + e.claimedAs : ''}`);
      lines.push(`service: ${o.service.installed ? `installed, every ${o.service.intervalMinutes} min` : 'not installed'}; last tick ${o.service.lastTick || 'never'}`);
      return lines.join('\n');
    }
    case 'release':
    case 'uninstall':
      return [`deleted: ${o.deleted.join(', ') || '(none)'}`, ...o.skipped.map((s) => `skipped ${s.alias}: ${s.reason}`),
        ...(o.service ? [`service: ${o.service.installed ? 'installed' : 'removed'}`] : [])].join('\n');
    case 'tick':
    case 'init': {
      const lines = (o.pools || []).map((p) => `pool ${p.name}: ${p.ready} ready, ${p.creating} creating, ${p.claimed} claimed / size ${p.size}; started ${p.started}` +
        `${p.released.length ? `, released ${p.released.join(', ')}` : ''}${p.skipped ? ` (skipped: ${p.skipped})` : ''}`);
      if (o.command === 'init') lines.unshift(`pool ${o.pool} configured (hub ${o.config.hub}, size ${o.config.size}); service ${o.service?.installed ? 'installed' : 'not installed'}`);
      return lines.join('\n') || 'no pools';
    }
    case 'config':
      return o.value !== undefined ? JSON.stringify(o.value) : JSON.stringify(o.config, null, 2);
    case 'service':
      return `service ${o.service.installed ? `installed (${o.service.platform}, every ${o.service.intervalMinutes} min)` : 'not installed'}`;
    case 'pause': case 'resume':
      return `pool ${o.pool} ${o.command}d`;
    case 'version': return o.version;
    case 'help': return o.help;
    default: return `${o.command}: ${o.status}`;
  }
}

async function main(argv) {
  let flags = {};
  let command = 'unknown';
  let ctx = null;
  try {
    if (process.env.SF_TEMP_SHOW_SECRETS) {
      command = argv.find((a) => !a.startsWith('-')) || 'unknown';
      throw new SpError('SECRETS_ENV', 'SF_TEMP_SHOW_SECRETS is set; scratchpool refuses to run while sf may print secrets. Unset it and retry.');
    }
    const parsed = parseArgs(argv);
    flags = parsed.flags;
    const [cmd, ...positional] = parsed.positional;
    // --help / --version always win, even after a command: `init --help` must never run init.
    if (flags.version || flags.help) {
      command = flags.version ? 'version' : 'help';
      const out = baseOutput(command);
      if (flags.version) out.version = VERSION; else out.help = HELP;
      emit(out, flags, human);
      return 0;
    }
    if (!cmd) { command = 'help'; throw new SpError('USAGE', 'no command given; run scratchpool --help'); }
    command = cmd === 'return' ? 'release' : cmd === 'list' ? 'status' : cmd;
    const fn = COMMANDS[cmd];
    if (!fn) throw new SpError('USAGE', `unknown command "${cmd}"; run scratchpool --help`);
    const config = loadConfig();
    ctx = {
      config, flags, home: homeDir(), platform: platform(),
      nodePath: process.execPath, scriptPath: SCRIPT_PATH,
      sf: new Sf(resolveSf(config.sfPath)),
    };
    const out = await fn(ctx, { flags, positional });
    emit(out, flags, human);
    return 0;
  } catch (err) {
    const e = err instanceof SpError ? err : new SpError(err?.code && typeof err.code === 'string' && /^[A-Z_]+$/.test(err.code) ? err.code : 'ERROR', err?.message || String(err));
    const out = baseOutput(command);
    out.status = 'error';
    out.error = { code: e.code, message: scrub(e.message), retryable: !!e.retryable };
    if (e.extra) Object.assign(out, e.extra);
    if (flags.pool && !out.pool) out.pool = flags.pool;
    emit(out, flags, human);
    return exitCodeFor(e);
  }
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === SCRIPT_PATH;
let realMain = isMain;
if (!isMain && process.argv[1]) {
  try { realMain = (await import('node:fs')).realpathSync(process.argv[1]) === SCRIPT_PATH; } catch { realMain = false; }
}
if (realMain) {
  process.exitCode = await main(process.argv.slice(2));
}

export { main };
