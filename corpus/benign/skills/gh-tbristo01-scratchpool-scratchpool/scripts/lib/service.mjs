// scratchpool background scheduler integration (SPEC section 0 + section 2 "service").
//
// Everything here is per-user and local: a macOS LaunchAgent, a Linux systemd --user timer
// (crontab line fallback), or a Windows Task Scheduler task. Nothing is hosted.
//
// Exports exactly:
//   installService({home, nodePath, scriptPath, sfPath, intervalMinutes, platform, dryRun})
//   uninstallService({home, platform, dryRun})
//   serviceStatus({home, platform, dryRun})
//
// Test seam: SCRATCHPOOL_SERVICE_DRYRUN=1 (or dryRun:true) writes the unit/plist files under
// <home>/service-dryrun/ and appends the would-be commands to <home>/service-dryrun/commands.json,
// executing nothing. SCRATCHPOOL_PLATFORM overrides process.platform.
//
// Zero dependencies. Commands are spawned with argument arrays, never a shell string.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

export const LABEL = 'dev.scratchpool.tick';
export const SYSTEMD_NAME = 'scratchpool-tick';
export const WINDOWS_TASK = 'scratchpool-tick';

const DRYRUN_DIR = 'service-dryrun';
const WINDOWS_DRYRUN_FILE = 'schtasks-scratchpool-tick.json';

// ---------------------------------------------------------------- helpers

function svcError(code, message, extra = {}) {
  const err = new Error(message);
  err.code = code;
  Object.assign(err, extra);
  return err;
}

function resolvePlatform(platform) {
  return platform || process.env.SCRATCHPOOL_PLATFORM || process.platform;
}

function resolveDryRun(dryRun) {
  // The env var always forces dry-run so a test can never reach the real scheduler.
  return dryRun === true || process.env.SCRATCHPOOL_SERVICE_DRYRUN === '1';
}

function requireHome(home) {
  if (!home || typeof home !== 'string') throw svcError('USAGE', 'service: home is required');
  return path.resolve(home);
}

function validInterval(n) {
  const v = Number(n);
  if (!Number.isInteger(v) || v < 1 || v > 1439) {
    throw svcError('USAGE', `service: intervalMinutes must be an integer between 1 and 1439 (got ${n})`);
  }
  return v;
}

function uid() {
  return typeof process.getuid === 'function' ? process.getuid() : 0;
}

function writeAtomic(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmp, content);
  fs.renameSync(tmp, file);
}

// <home>/logs is private (0700) and scheduler-written logs are created 0600 up front, because they hold tick
// JSON (usernames, org ids). The scheduler then appends to the existing file and keeps its mode.
function ensureLogs(home, files = []) {
  const dir = path.join(home, 'logs');
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  for (const f of files) {
    try {
      fs.closeSync(fs.openSync(path.join(dir, f), 'a', 0o600));
      if (process.platform !== 'win32') fs.chmodSync(path.join(dir, f), 0o600);
    } catch { /* best effort */ }
  }
}

function removeIfExists(file) {
  try {
    fs.unlinkSync(file);
    return true;
  } catch (e) {
    if (e.code === 'ENOENT') return false;
    throw e;
  }
}

function readIfExists(file) {
  try {
    return fs.readFileSync(file, 'utf8');
  } catch {
    return null;
  }
}

function sleepMs(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

/** PATH for the scheduled job: node's dir, sf's dir, then the system basics (deduplicated). */
export function schedulerPath(nodePath, sfPath, base = ['/usr/bin', '/bin']) {
  const dirs = [];
  for (const p of [nodePath, sfPath]) if (p) dirs.push(path.dirname(p));
  dirs.push(...base);
  return [...new Set(dirs)].join(':');
}

// A runner executes (or, in dry-run, records) commands. Each command is an argv array.
function makeRunner(home, dryRun) {
  const commands = [];
  return {
    commands,
    run(argv, { allowFail = false } = {}) {
      commands.push(argv);
      if (dryRun) return { status: 0, stdout: '', stderr: '', dryRun: true };
      const r = spawnSync(argv[0], argv.slice(1), { encoding: 'utf8', windowsHide: true, timeout: 60_000 });
      const res = { status: r.error ? -1 : r.status, stdout: r.stdout || '', stderr: r.stderr || '', error: r.error };
      if (res.status !== 0 && !allowFail) {
        const msg = (res.stderr || res.stdout || (r.error && r.error.message) || '').trim();
        throw svcError('SERVICE_FAILED', `${argv.join(' ')} failed (exit ${res.status}): ${msg}`, { exitCode: res.status });
      }
      return res;
    },
    // Read-only probe used by status: runs for real unless dry-run; never recorded.
    probe(argv) {
      if (dryRun) return { status: 0, stdout: '', stderr: '' };
      const r = spawnSync(argv[0], argv.slice(1), { encoding: 'utf8', windowsHide: true, timeout: 30_000 });
      return { status: r.error ? -1 : r.status, stdout: r.stdout || '', stderr: r.stderr || '' };
    },
    flush() {
      if (!dryRun || commands.length === 0) return;
      const file = path.join(home, DRYRUN_DIR, 'commands.json');
      let prior = [];
      try {
        const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
        if (Array.isArray(parsed)) prior = parsed;
      } catch { /* first write */ }
      writeAtomic(file, JSON.stringify([...prior, ...commands], null, 2) + '\n');
    },
  };
}

// ---------------------------------------------------------------- macOS (launchd)

function xmlEscape(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function xmlUnescape(s) {
  return String(s)
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, '&');
}

export function buildPlist({ home, nodePath, scriptPath, sfPath, intervalMinutes }) {
  const log = path.join(home, 'logs', 'launchd.log');
  const args = [nodePath, scriptPath, 'tick', '--json'];
  const str = (v) => `<string>${xmlEscape(v)}</string>`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  ${str(LABEL)}
  <key>ProgramArguments</key>
  <array>
${args.map((a) => `    ${str(a)}`).join('\n')}
  </array>
  <key>StartInterval</key>
  <integer>${intervalMinutes * 60}</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>ProcessType</key>
  ${str('Background')}
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    ${str(schedulerPath(nodePath, sfPath))}
    <key>SCRATCHPOOL_HOME</key>
    ${str(home)}
  </dict>
  <key>StandardOutPath</key>
  ${str(log)}
  <key>StandardErrorPath</key>
  ${str(log)}
</dict>
</plist>
`;
}

function macPaths(home, dryRun) {
  const dir = dryRun ? path.join(home, DRYRUN_DIR) : path.join(os.homedir(), 'Library', 'LaunchAgents');
  return { plist: path.join(dir, `${LABEL}.plist`) };
}

function macInstall(opts, runner) {
  const { home, dryRun } = opts;
  const { plist } = macPaths(home, dryRun);
  ensureLogs(home, ['launchd.log']);
  writeAtomic(plist, buildPlist(opts));
  const domain = `gui/${uid()}`;
  runner.run(['launchctl', 'bootout', `${domain}/${LABEL}`], { allowFail: true });
  const bootstrap = ['launchctl', 'bootstrap', domain, plist];
  const r = runner.run(bootstrap, { allowFail: true });
  if (r.status !== 0) {
    // bootout can still be finishing (launchctl then reports "Input/output error"); retry once.
    sleepMs(750);
    runner.run(bootstrap);
  }
  return [plist];
}

function macUninstall({ home, dryRun }, runner) {
  const { plist } = macPaths(home, dryRun);
  runner.run(['launchctl', 'bootout', `gui/${uid()}/${LABEL}`], { allowFail: true });
  return removeIfExists(plist) ? [plist] : [];
}

function macStatus({ home, dryRun }, runner) {
  const { plist } = macPaths(home, dryRun);
  const text = readIfExists(plist);
  if (text == null) return { installed: false, intervalMinutes: null, detail: `no LaunchAgent at ${plist}` };
  const m = /<key>StartInterval<\/key>\s*<integer>(\d+)<\/integer>/.exec(text);
  const intervalMinutes = m ? Math.round(Number(m[1]) / 60) : null;
  if (dryRun) return { installed: true, intervalMinutes, detail: `dry-run plist at ${plist}` };
  const p = runner.probe(['launchctl', 'print', `gui/${uid()}/${LABEL}`]);
  if (p.status === 0) return { installed: true, intervalMinutes, detail: `LaunchAgent ${LABEL} loaded (${plist})` };
  return { installed: false, intervalMinutes, detail: `plist present at ${plist} but ${LABEL} is not loaded; run "scratchpool service install"` };
}

// ---------------------------------------------------------------- Linux (systemd --user, cron fallback)

// systemd unit-file quoting: double-quoted word, C-style escapes for \ and ", '%' specifiers doubled.
function systemdQuote(s, { dollar = true } = {}) {
  let v = String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/%/g, '%%');
  if (dollar) v = v.replace(/\$/g, '$$$$'); // ExecStart expands $VAR; $$ is a literal $
  return `"${v}"`;
}

function systemdUnquote(s) {
  let v = s.trim();
  if (v.startsWith('"') && v.endsWith('"')) v = v.slice(1, -1);
  return v.replace(/\$\$/g, '$').replace(/%%/g, '%').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
}

export function buildSystemdService({ home, nodePath, scriptPath, sfPath }) {
  const exec = [nodePath, scriptPath].map((a) => systemdQuote(a)).concat(['tick', '--json']).join(' ');
  return `[Unit]
Description=scratchpool tick (keeps your local scratch org pool warm)
Documentation=https://github.com/Tbristo01/scratchpool/blob/main/docs/background-service.md

[Service]
Type=oneshot
# tick starts detached background creates (_worker) and returns. The default KillMode=control-group would
# kill them when tick exits (setsid does not leave the cgroup); "process" kills only the main process.
KillMode=process
ExecStart=${exec}
Environment=${systemdQuote(`PATH=${schedulerPath(nodePath, sfPath)}`, { dollar: false })}
Environment=${systemdQuote(`SCRATCHPOOL_HOME=${home}`, { dollar: false })}
`;
}

export function buildSystemdTimer({ intervalMinutes }) {
  return `[Unit]
Description=Run scratchpool tick every ${intervalMinutes} minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=${intervalMinutes}min
Persistent=true
Unit=${SYSTEMD_NAME}.service

[Install]
WantedBy=timers.target
`;
}

// POSIX shell single-quote; '%' is special in crontab and must be escaped.
function shQuote(s) {
  return `'${String(s).replace(/'/g, `'\\''`)}'`;
}

export function buildCrontabLine({ home, nodePath, scriptPath, sfPath, intervalMinutes }) {
  let schedule;
  if (intervalMinutes < 60) schedule = `*/${intervalMinutes} * * * *`;
  else if (intervalMinutes % 60 === 0 && intervalMinutes / 60 < 24) schedule = `0 */${intervalMinutes / 60} * * *`;
  else schedule = `0 * * * *`;
  const log = path.join(home, 'logs', 'cron.log');
  const cmd = [
    `PATH=${shQuote(schedulerPath(nodePath, sfPath))}`,
    `SCRATCHPOOL_HOME=${shQuote(home)}`,
    shQuote(nodePath),
    shQuote(scriptPath),
    'tick --json',
    `>> ${shQuote(log)} 2>&1`,
  ].join(' ');
  return `${schedule} ${cmd.replace(/%/g, '\\%')}`;
}

function linuxPaths(home, dryRun) {
  const dir = dryRun
    ? path.join(home, DRYRUN_DIR)
    : path.join(process.env.XDG_CONFIG_HOME || path.join(os.homedir(), '.config'), 'systemd', 'user');
  return {
    service: path.join(dir, `${SYSTEMD_NAME}.service`),
    timer: path.join(dir, `${SYSTEMD_NAME}.timer`),
  };
}

function systemdUserAvailable(opts, runner) {
  if (typeof opts.systemdAvailable === 'boolean') return opts.systemdAvailable; // test seam
  if (opts.dryRun) return true;
  return runner.probe(['systemctl', '--user', 'show-environment']).status === 0;
}

function linuxInstall(opts, runner) {
  const { home, dryRun } = opts;
  if (!systemdUserAvailable(opts, runner)) {
    const line = buildCrontabLine(opts);
    ensureLogs(home, ['cron.log']);
    throw svcError(
      'SERVICE_UNSUPPORTED',
      'systemctl --user is not available on this machine. Add this line with "crontab -e" to run scratchpool tick on a schedule:\n' + line,
      { crontab: line },
    );
  }
  const p = linuxPaths(home, dryRun);
  ensureLogs(home);
  writeAtomic(p.service, buildSystemdService(opts));
  writeAtomic(p.timer, buildSystemdTimer(opts));
  runner.run(['systemctl', '--user', 'daemon-reload']);
  runner.run(['systemctl', '--user', 'enable', '--now', `${SYSTEMD_NAME}.timer`]);
  // enable --now does not restart an already-active timer, so pick up a changed interval.
  runner.run(['systemctl', '--user', 'restart', `${SYSTEMD_NAME}.timer`]);
  return [p.service, p.timer];
}

function linuxUninstall(opts, runner) {
  const { home, dryRun } = opts;
  const p = linuxPaths(home, dryRun);
  const available = systemdUserAvailable(opts, runner);
  if (available) runner.run(['systemctl', '--user', 'disable', '--now', `${SYSTEMD_NAME}.timer`], { allowFail: true });
  const removed = [p.timer, p.service].filter((f) => removeIfExists(f));
  if (available) runner.run(['systemctl', '--user', 'daemon-reload'], { allowFail: true });
  return removed;
}

function linuxStatus(opts, runner) {
  const { home, dryRun } = opts;
  const p = linuxPaths(home, dryRun);
  const timer = readIfExists(p.timer);
  if (timer == null || readIfExists(p.service) == null) {
    return { installed: false, intervalMinutes: null, detail: `no systemd user timer at ${p.timer}` };
  }
  const m = /^OnUnitActiveSec=(\d+)min\s*$/m.exec(timer);
  const intervalMinutes = m ? Number(m[1]) : null;
  if (dryRun) return { installed: true, intervalMinutes, detail: `dry-run units at ${path.dirname(p.timer)}` };
  if (!systemdUserAvailable(opts, runner)) {
    return { installed: false, intervalMinutes, detail: 'unit files present but systemctl --user is not available' };
  }
  const enabled = runner.probe(['systemctl', '--user', 'is-enabled', `${SYSTEMD_NAME}.timer`]).status === 0;
  const active = runner.probe(['systemctl', '--user', 'is-active', `${SYSTEMD_NAME}.timer`]).status === 0;
  return {
    installed: enabled,
    intervalMinutes,
    detail: `${SYSTEMD_NAME}.timer ${enabled ? 'enabled' : 'not enabled'}, ${active ? 'active' : 'inactive'} (${p.timer})`,
  };
}

// ---------------------------------------------------------------- Windows (Task Scheduler)

export const WINDOWS_WRAPPER = 'scratchpool-tick.cmd';
const winWrapperPath = (home) => path.join(home, WINDOWS_WRAPPER);

/** The /TR value: the double-quoted absolute path of the wrapper under <home> (Windows paths cannot contain "). */
export function buildWindowsTaskRun({ home }) {
  return `"${winWrapperPath(home)}"`;
}

/**
 * The wrapper the task runs. Like the plist and systemd unit, it pins SCRATCHPOOL_HOME (so a home chosen with
 * SCRATCHPOOL_HOME or XDG_CONFIG_HOME at install time is the one the task ticks) and PATH, and it sends the
 * tick output to <home>\logs\task.log. In a batch file a literal % must be written %%.
 */
export function buildWindowsWrapper({ home, nodePath, scriptPath, sfPath }) {
  const pct = (v) => String(v).replace(/%/g, '%%');
  const dirs = [...new Set([nodePath, sfPath].filter(Boolean).map((p) => path.win32.dirname(p)))];
  return [
    '@echo off',
    'rem Written by "scratchpool service install"; removed by "scratchpool service uninstall".',
    `set "SCRATCHPOOL_HOME=${pct(home)}"`,
    `set "PATH=${dirs.map(pct).join(';')};%PATH%"`,
    `"${pct(nodePath)}" "${pct(scriptPath)}" tick --json >> "${pct(path.join(home, 'logs', 'task.log'))}" 2>&1`,
    '',
  ].join('\r\n');
}

function winInstall(opts, runner) {
  const { home, dryRun, intervalMinutes } = opts;
  const tr = buildWindowsTaskRun(opts);
  if (tr.length > 261) {
    throw svcError('SERVICE_UNSUPPORTED', `schtasks /TR is limited to 261 characters (got ${tr.length}); install scratchpool at a shorter path`);
  }
  const argv = ['schtasks', '/Create', '/F', '/SC', 'MINUTE', '/MO', String(intervalMinutes), '/TN', WINDOWS_TASK, '/TR', tr];
  const wrapper = winWrapperPath(home);
  writeAtomic(wrapper, buildWindowsWrapper(opts));
  const files = [wrapper];
  if (dryRun) {
    const f = path.join(home, DRYRUN_DIR, WINDOWS_DRYRUN_FILE);
    writeAtomic(f, JSON.stringify({ taskName: WINDOWS_TASK, intervalMinutes, tr, argv }, null, 2) + '\n');
    files.push(f);
  }
  ensureLogs(home);
  runner.run(argv);
  return files;
}

function winUninstall({ home, dryRun }, runner) {
  runner.run(['schtasks', '/Delete', '/F', '/TN', WINDOWS_TASK], { allowFail: true });
  const removed = removeIfExists(winWrapperPath(home)) ? [winWrapperPath(home)] : [];
  if (!dryRun) return removed;
  const f = path.join(home, DRYRUN_DIR, WINDOWS_DRYRUN_FILE);
  return removeIfExists(f) ? [...removed, f] : removed;
}

function winStatus({ home, dryRun }, runner) {
  if (dryRun) {
    const f = path.join(home, DRYRUN_DIR, WINDOWS_DRYRUN_FILE);
    const text = readIfExists(f);
    if (text == null) return { installed: false, intervalMinutes: null, detail: `no dry-run task at ${f}` };
    let data = {};
    try { data = JSON.parse(text); } catch { /* corrupt */ }
    return { installed: true, intervalMinutes: Number(data.intervalMinutes) || null, detail: `dry-run task ${WINDOWS_TASK} (${f})` };
  }
  // /XML output is locale-independent, unlike /FO LIST.
  const p = runner.probe(['schtasks', '/Query', '/TN', WINDOWS_TASK, '/XML']);
  if (p.status !== 0) return { installed: false, intervalMinutes: null, detail: `scheduled task ${WINDOWS_TASK} not found` };
  const m = /<Interval>PT(?:(\d+)H)?(?:(\d+)M)?<\/Interval>/.exec(p.stdout);
  const intervalMinutes = m ? Number(m[1] || 0) * 60 + Number(m[2] || 0) || null : null;
  const settings = /<Settings>([\s\S]*?)<\/Settings>/.exec(p.stdout);
  const disabled = !!settings && /<Enabled>false<\/Enabled>/.test(settings[1]);
  return { installed: true, intervalMinutes, detail: `scheduled task ${WINDOWS_TASK}${disabled ? ' (disabled)' : ''}` };
}

// ---------------------------------------------------------------- public API

const IMPL = {
  darwin: { install: macInstall, uninstall: macUninstall, status: macStatus },
  linux: { install: linuxInstall, uninstall: linuxUninstall, status: linuxStatus },
  win32: { install: winInstall, uninstall: winUninstall, status: winStatus },
};

function implFor(platform) {
  const impl = IMPL[platform];
  if (!impl) throw svcError('SERVICE_UNSUPPORTED', `no background scheduler support for platform "${platform}"`);
  return impl;
}

export function installService(options = {}) {
  const platform = resolvePlatform(options.platform);
  const dryRun = resolveDryRun(options.dryRun);
  const home = requireHome(options.home);
  if (!options.nodePath || !options.scriptPath) throw svcError('USAGE', 'service: nodePath and scriptPath are required');
  // Every path below is written into a plist, a systemd unit, a crontab line or a batch file. A control
  // character (a newline in SCRATCHPOOL_HOME, say) could start a new directive there, so refuse it.
  for (const [k, v] of Object.entries({ home, nodePath: options.nodePath, scriptPath: options.scriptPath, sfPath: options.sfPath })) {
    // eslint-disable-next-line no-control-regex
    if (v != null && /[\u0000-\u001f\u007f]/.test(String(v))) throw svcError('USAGE', `service: ${k} contains a control character`);
  }
  const opts = {
    ...options,
    home,
    platform,
    dryRun,
    nodePath: options.nodePath,
    scriptPath: options.scriptPath,
    sfPath: options.sfPath || null,
    intervalMinutes: validInterval(options.intervalMinutes ?? 15),
  };
  const impl = implFor(platform);
  const runner = makeRunner(home, dryRun);
  try {
    const files = impl.install(opts, runner);
    return { installed: true, platform, files, commands: runner.commands };
  } finally {
    runner.flush();
  }
}

export function uninstallService(options = {}) {
  const platform = resolvePlatform(options.platform);
  const dryRun = resolveDryRun(options.dryRun);
  const home = requireHome(options.home);
  const impl = implFor(platform);
  const runner = makeRunner(home, dryRun);
  try {
    const files = impl.uninstall({ ...options, home, platform, dryRun }, runner);
    return { installed: false, platform, files, commands: runner.commands };
  } finally {
    runner.flush();
  }
}

export function serviceStatus(options = {}) {
  const platform = resolvePlatform(options.platform);
  const dryRun = resolveDryRun(options.dryRun);
  const home = requireHome(options.home);
  const impl = IMPL[platform];
  if (!impl) return { installed: false, platform, intervalMinutes: null, detail: `unsupported platform "${platform}"` };
  const runner = makeRunner(home, dryRun);
  const s = impl.status({ ...options, home, platform, dryRun }, runner);
  return { installed: s.installed, platform, intervalMinutes: s.intervalMinutes, detail: s.detail };
}

// Exposed for tests only.
export const _internal = { xmlEscape, xmlUnescape, systemdQuote, systemdUnquote, shQuote };
