/**
 * Discover already-installed tunnel-client artifacts.
 *
 * The Settings page should recognize an existing install and official
 * tunnel-client profile without a full-disk scan and without taking
 * ownership of a process this plugin did not start.
 *
 * Search order for the binary: configured path → PATH → well-known
 * install directories → image path of a running tunnel-client (hint only).
 *
 * Existing official profiles (`%APPDATA%/tunnel-client/*.yaml` on Windows,
 * `~/.config/tunnel-client/*.yaml` elsewhere) may supply a tunnel id and
 * control-plane URL. Secret values are never returned: `env:` / `file:`
 * references and non-empty literals are reported only as
 * `runtimeApiKeyAvailable: true`. A running `tunnel-client` is observed for
 * status (pid / health listen_addr / proxy flags) but never adopted.
 */
import { existsSync, readdirSync, readFileSync, readlinkSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { posix as posixPath, win32 as win32Path, type PlatformPath } from 'node:path';
import { spawnSync } from 'node:child_process';

import { normalizeSocketHostname } from '../config.js';

export type DiscoverySource = 'configured' | 'path' | 'well-known' | 'running-process';

export interface DiscoveredExecutable {
  path: string;
  source: DiscoverySource;
}

export interface DiscoveredProxyHint {
  host: string;
  port: number;
  source: 'env';
}

/** Observed `tunnel-client` process this plugin did not start. Never adopted. */
export interface DiscoveredRunningProcess {
  pid: number;
  executablePath: string;
  profileName?: string;
  proxyFlag?: boolean;
}

export interface ExistingRuntimeDiscovery {
  executable?: DiscoveredExecutable;
  /** Official tunnel-client profile path that supplied the hints. */
  profilePath?: string;
  profileName?: string;
  tunnelId?: string;
  controlPlaneBaseUrl?: string;
  /** True when a referenced env/file runtime key exists, or a non-empty literal is present. Never the secret. */
  runtimeApiKeyAvailable?: boolean;
  proxy?: DiscoveredProxyHint;
  /** True when a running tunnel-client was launched with an explicit proxy flag. */
  proxyInUse?: boolean;
  /** Loopback health base derived from profile `listen_addr` (never a public bind). */
  healthBaseUrl?: string;
  /** Observed process. Hint + status only; the plugin does not take ownership. */
  runningProcess?: DiscoveredRunningProcess;
}

export interface DiscoverHooks {
  configuredExecutable?: string;
  env?: NodeJS.ProcessEnv;
  platform?: NodeJS.Platform;
  existsSync?: (path: string) => boolean;
  listRunningProcesses?: () => DiscoveredRunningProcess[];
  readFileSync?: (path: string, encoding: 'utf8') => string;
  readdirSync?: (path: string) => string[];
  listRunningExecutables?: () => string[];
  profileDirs?: string[];
  wellKnownPaths?: string[];
}

const BINARY_NAMES_WIN = ['tunnel-client.exe', 'tunnel-client'];
const BINARY_NAMES_POSIX = ['tunnel-client'];
const PROFILE_NAMES_PREFERRED = ['dsh-chatgpt-bridge.yaml', 'dsh-chatgpt-bridge.yml'];
const MAX_PROFILE_BYTES = 64 * 1024;

function envOf(hooks: DiscoverHooks): NodeJS.ProcessEnv {
  return hooks.env ?? process.env;
}

function platformOf(hooks: DiscoverHooks): NodeJS.Platform {
  return hooks.platform ?? process.platform;
}

/** Path API matching the *simulated* platform, not the host OS. */
function pathOf(platform: NodeJS.Platform): PlatformPath {
  return platform === 'win32' ? win32Path : posixPath;
}

function exists(hooks: DiscoverHooks, path: string): boolean {
  const fn = hooks.existsSync ?? existsSync;
  try {
    return fn(path);
  } catch {
    return false;
  }
}

function firstExisting(hooks: DiscoverHooks, candidates: string[]): string | undefined {
  for (const candidate of candidates) {
    if (candidate !== '' && exists(hooks, candidate)) return candidate;
  }
  return undefined;
}

/** Well-known install locations. Bounded list — never a recursive disk walk. */
export function wellKnownExecutableCandidates(env: NodeJS.ProcessEnv, platform: NodeJS.Platform): string[] {
  const names = platform === 'win32' ? BINARY_NAMES_WIN : BINARY_NAMES_POSIX;
  const path = pathOf(platform);
  const dirs: string[] = [];
  if (platform === 'win32') {
    for (const drive of ['D:', 'C:']) dirs.push(path.join(drive + '\\', 'Application', 'tunnel-client'));
    if (env.LOCALAPPDATA) {
      dirs.push(path.join(env.LOCALAPPDATA, 'tunnel-client'));
      dirs.push(path.join(env.LOCALAPPDATA, 'Programs', 'tunnel-client'));
    }
    if (env.ProgramFiles) dirs.push(path.join(env.ProgramFiles, 'tunnel-client'));
    if (env['ProgramFiles(x86)']) dirs.push(path.join(env['ProgramFiles(x86)'], 'tunnel-client'));
    const home = env.USERPROFILE;
    if (home) {
      dirs.push(path.join(home, 'Application', 'tunnel-client'));
      dirs.push(path.join(home, 'scoop', 'apps', 'tunnel-client', 'current'));
    }
  } else {
    dirs.push('/usr/local/bin', '/usr/bin', '/opt/tunnel-client');
    const home = env.HOME;
    if (home) {
      dirs.push(path.join(home, '.local', 'bin'));
      dirs.push(path.join(home, 'Application', 'tunnel-client'));
    }
  }
  const out: string[] = [];
  for (const dir of dirs) {
    for (const name of names) out.push(path.join(dir, name));
  }
  return out;
}

function pathCandidates(env: NodeJS.ProcessEnv, platform: NodeJS.Platform): string[] {
  const names = platform === 'win32' ? BINARY_NAMES_WIN : BINARY_NAMES_POSIX;
  const path = pathOf(platform);
  const sep = platform === 'win32' ? ';' : ':';
  const dirs = (env.PATH ?? '').split(sep);
  const out: string[] = [];
  for (const dir of dirs) {
    if (dir === '') continue;
    for (const name of names) out.push(path.join(dir, name));
  }
  return out;
}

export function defaultProfileDirs(env: NodeJS.ProcessEnv, platform: NodeJS.Platform): string[] {
  const path = pathOf(platform);
  if (platform === 'win32') {
    const appdata = env.APPDATA ?? (env.USERPROFILE ? path.join(env.USERPROFILE, 'AppData', 'Roaming') : undefined);
    return appdata === undefined ? [] : [path.join(appdata, 'tunnel-client')];
  }
  const home = env.HOME ?? homedir();
  return [path.join(home, '.config', 'tunnel-client')];
}

/** Pull profile name and proxy-flag presence off a command line. Never returns secret values. */
export function parseTunnelCommandLine(commandLine: string): { profileName?: string; proxyFlag: boolean } {
  const proxyFlag = /--(?:http-proxy|control-plane\.http-proxy)\b/.test(commandLine);
  const match = /--profile(?:-file)?(?:\s+|=)(?:"([^"]+)"|'([^']+)'|(\S+))/.exec(commandLine);
  const raw = match === null ? undefined : (match[1] ?? match[2] ?? match[3]);
  if (raw === undefined || raw === '') return { proxyFlag };
  const base = raw.replace(/\\/g, '/').split('/').pop() ?? raw;
  return { proxyFlag, profileName: base.replace(/\.ya?ml$/i, '') };
}

/** Loopback-only health base from profile `listen_addr`. Ephemeral `:0` is skipped. */
export function healthBaseFromListenAddr(addr: string): string | undefined {
  const trimmed = addr.trim();
  if (trimmed === '') return undefined;
  if (/^https?:\/\//i.test(trimmed)) {
    try {
      const url = new URL(trimmed);
      const host = normalizeSocketHostname(url.hostname).toLowerCase();
      if (host !== '127.0.0.1' && host !== 'localhost' && host !== '::1') return undefined;
      if (url.port === '0') return undefined;
      return url.origin;
    } catch {
      return undefined;
    }
  }
  const match = /^(127\.0\.0\.1|localhost|\[::1\]|::1):(\d+)$/i.exec(trimmed);
  if (match === null) return undefined;
  const port = Number(match[2]);
  if (!Number.isInteger(port) || port < 1) return undefined;
  const host = match[1] === '::1' ? '[::1]' : match[1];
  return 'http://' + host + ':' + port;
}

function parseCimProcessJson(raw: string): { ProcessId?: number; ExecutablePath?: string; CommandLine?: string }[] {
  const text = raw.trim();
  if (text === '') return [];
  try {
    const parsed: unknown = JSON.parse(text);
    if (Array.isArray(parsed)) return parsed as { ProcessId?: number; ExecutablePath?: string; CommandLine?: string }[];
    if (parsed !== null && typeof parsed === 'object') return [parsed as { ProcessId?: number; ExecutablePath?: string; CommandLine?: string }];
    return [];
  } catch {
    return [];
  }
}

function defaultListRunningProcesses(platform: NodeJS.Platform): DiscoveredRunningProcess[] {
  try {
    if (platform === 'win32') {
      const result = spawnSync(
        'powershell.exe',
        [
          '-NoProfile',
          '-NonInteractive',
          '-Command',
          "Get-CimInstance Win32_Process -Filter \"Name='tunnel-client.exe'\" | Select-Object ProcessId, ExecutablePath, CommandLine | ConvertTo-Json -Compress",
        ],
        { encoding: 'utf8', windowsHide: true, timeout: 5000 },
      );
      const out: DiscoveredRunningProcess[] = [];
      for (const row of parseCimProcessJson(result.stdout ?? '')) {
        const pid = Number(row.ProcessId);
        const executablePath = typeof row.ExecutablePath === 'string' ? row.ExecutablePath.trim() : '';
        if (!Number.isInteger(pid) || pid <= 0 || executablePath === '') continue;
        const flags = parseTunnelCommandLine(typeof row.CommandLine === 'string' ? row.CommandLine : '');
        out.push({
          pid,
          executablePath,
          ...(flags.profileName === undefined ? {} : { profileName: flags.profileName }),
          ...(flags.proxyFlag ? { proxyFlag: true } : {}),
        });
      }
      return out;
    }
    let proc: string[] = [];
    try {
      proc = readdirSync('/proc');
    } catch {
      proc = [];
    }
    const out: DiscoveredRunningProcess[] = [];
    if (proc.length > 0) {
      for (const entry of proc) {
        if (!/^\d+$/.test(entry)) continue;
        try {
          const comm = readFileSync(posixPath.join('/proc', entry, 'comm'), 'utf8').trim();
          if (comm !== 'tunnel-client') continue;
          const exe = readlinkSync(posixPath.join('/proc', entry, 'exe'));
          if (exe === '') continue;
          const pid = Number(entry);
          let cmdline = '';
          try {
            cmdline = readFileSync(posixPath.join('/proc', entry, 'cmdline'), 'utf8').replace(/\0/g, ' ');
          } catch {
            cmdline = '';
          }
          const flags = parseTunnelCommandLine(cmdline);
          out.push({
            pid,
            executablePath: exe,
            ...(flags.profileName === undefined ? {} : { profileName: flags.profileName }),
            ...(flags.proxyFlag ? { proxyFlag: true } : {}),
          });
        } catch {
          // not every /proc row is a readable process
        }
      }
      return out;
    }
    // macOS / BSD fallback via ps
    const result = spawnSync('ps', ['-ax', '-o', 'pid=,command='], { encoding: 'utf8', timeout: 5000 });
    const raw = (result.stdout ?? '').trim();
    for (const line of raw.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (trimmed === '' || !trimmed.includes('tunnel-client')) continue;
      const match = /^(\d+)\s+(.*)$/.exec(trimmed);
      if (match === null) continue;
      const pid = Number(match[1]);
      const cmd = match[2] ?? '';
      const exe = cmd.split(' ')[0] ?? '';
      const flags = parseTunnelCommandLine(cmd);
      out.push({
        pid,
        executablePath: exe,
        ...(flags.profileName === undefined ? {} : { profileName: flags.profileName }),
        ...(flags.proxyFlag ? { proxyFlag: true } : {}),
      });
    }
    return out;
  } catch {
    return [];
  }
}

function defaultListRunningExecutables(platform: NodeJS.Platform): string[] {
  return defaultListRunningProcesses(platform)
    .map((row) => row.executablePath)
    .filter((path) => path !== '');
}

function resolveRunningProcesses(hooks: DiscoverHooks, platform: NodeJS.Platform): DiscoveredRunningProcess[] {
  if (hooks.listRunningProcesses !== undefined) {
    try {
      return hooks.listRunningProcesses();
    } catch {
      return [];
    }
  }
  if (hooks.listRunningExecutables !== undefined) {
    try {
      return hooks
        .listRunningExecutables()
        .filter((path) => path !== '')
        .map((executablePath) => ({ pid: 0, executablePath }));
    } catch {
      return [];
    }
  }
  return defaultListRunningProcesses(platform);
}

/** Resolve the tunnel-client binary. Configured path wins when it exists. */
export function discoverExecutable(hooks: DiscoverHooks = {}): DiscoveredExecutable | undefined {
  const env = envOf(hooks);
  const platform = platformOf(hooks);
  const configured = hooks.configuredExecutable;
  if (configured !== undefined && configured !== '') {
    return exists(hooks, configured) ? { path: configured, source: 'configured' } : undefined;
  }
  const fromPath = firstExisting(hooks, pathCandidates(env, platform));
  if (fromPath !== undefined) return { path: fromPath, source: 'path' };
  const wellKnown = hooks.wellKnownPaths ?? wellKnownExecutableCandidates(env, platform);
  const fromWellKnown = firstExisting(hooks, wellKnown);
  if (fromWellKnown !== undefined) return { path: fromWellKnown, source: 'well-known' };
  const listRunning = hooks.listRunningExecutables ?? (() => defaultListRunningExecutables(platform));
  let running: string[] = [];
  try {
    running = listRunning();
  } catch {
    running = [];
  }
  const fromRunning = firstExisting(hooks, running);
  if (fromRunning !== undefined) return { path: fromRunning, source: 'running-process' };
  return undefined;
}

export function resolveTunnelClientExecutable(configured?: string): string | undefined {
  return discoverExecutable({ configuredExecutable: configured })?.path;
}

function stripInlineComment(value: string): string {
  let inSingle = false;
  let inDouble = false;
  for (let i = 0; i < value.length; i++) {
    const ch = value[i];
    if (ch === "'" && !inDouble) inSingle = !inSingle;
    else if (ch === '"' && !inSingle) inDouble = !inDouble;
    else if (ch === '#' && !inSingle && !inDouble) return value.slice(0, i).trim();
  }
  return value.trim();
}

function unquote(value: string): string {
  const trimmed = stripInlineComment(value);
  if (trimmed.length >= 2) {
    const start = trimmed[0];
    const end = trimmed[trimmed.length - 1];
    if ((start === '"' && end === '"') || (start === "'" && end === "'")) {
      return trimmed
        .slice(1, -1)
        .replace(/\\n/g, '\n')
        .replace(/\\"/g, '"')
        .replace(/\\'/g, "'")
        .replace(/\\\\/g, '\\');
    }
  }
  return trimmed;
}

function yamlScalar(lines: string[], key: string): string | undefined {
  const re = new RegExp(`^\\s*${key}:\\s*(.*)$`);
  for (const line of lines) {
    const match = re.exec(line);
    if (match === null) continue;
    const value = unquote(match[1] ?? '');
    if (value !== '') return value;
  }
  return undefined;
}

function profileNameFromPath(profilePath: string): string {
  const base = profilePath.replace(/\\/g, '/').split('/').pop() ?? '';
  return base.replace(/\.ya?ml$/i, '');
}

function readProfileHints(
  hooks: DiscoverHooks,
  profilePath: string,
): Pick<ExistingRuntimeDiscovery, 'tunnelId' | 'controlPlaneBaseUrl' | 'runtimeApiKeyAvailable' | 'profileName' | 'healthBaseUrl'> {
  const read = hooks.readFileSync ?? ((p: string) => readFileSync(p, 'utf8'));
  let text = '';
  try {
    if (hooks.existsSync === undefined) {
      try {
        if (statSync(profilePath).size > MAX_PROFILE_BYTES) return {};
      } catch {
        return {};
      }
    }
    text = read(profilePath, 'utf8');
  } catch {
    return {};
  }
  if (text.length > MAX_PROFILE_BYTES) text = text.slice(0, MAX_PROFILE_BYTES);
  const lines = text.split(/\r?\n/);
  const tunnelId = yamlScalar(lines, 'tunnel_id');
  const controlPlaneBaseUrl = yamlScalar(lines, 'base_url');
  const apiKeyRef = yamlScalar(lines, 'api_key');
  const listenAddr = yamlScalar(lines, 'listen_addr');
  const healthBaseUrl = listenAddr === undefined ? undefined : healthBaseFromListenAddr(listenAddr);
  let runtimeApiKeyAvailable: boolean | undefined;
  if (apiKeyRef !== undefined) {
    if (apiKeyRef.startsWith('env:')) {
      const name = apiKeyRef.slice(4);
      runtimeApiKeyAvailable = name !== '' && (envOf(hooks)[name] ?? '') !== '';
    } else if (apiKeyRef.startsWith('file:')) {
      const filePath = apiKeyRef.slice(5);
      runtimeApiKeyAvailable = filePath !== '' && exists(hooks, filePath);
    } else if (apiKeyRef !== '' && apiKeyRef !== '~' && apiKeyRef !== 'null') {
      // Literal is present in the official profile. Report presence only —
      // never copy, return, or log the value.
      runtimeApiKeyAvailable = true;
    }
  }
  return {
    ...(tunnelId === undefined ? {} : { tunnelId }),
    ...(controlPlaneBaseUrl === undefined ? {} : { controlPlaneBaseUrl }),
    ...(runtimeApiKeyAvailable === undefined ? {} : { runtimeApiKeyAvailable }),
    ...(healthBaseUrl === undefined ? {} : { healthBaseUrl }),
    profileName: profileNameFromPath(profilePath),
  };
}

function listProfileFiles(hooks: DiscoverHooks, dir: string, platform: NodeJS.Platform): string[] {
  const readDir = hooks.readdirSync ?? ((p: string) => readdirSync(p));
  const path = pathOf(platform);
  let names: string[] = [];
  try {
    names = readDir(dir);
  } catch {
    return [];
  }
  const yaml = names.filter((name) => /\.ya?ml$/i.test(name));
  yaml.sort((a, b) => {
    const ap = PROFILE_NAMES_PREFERRED.includes(a.toLowerCase()) ? 0 : 1;
    const bp = PROFILE_NAMES_PREFERRED.includes(b.toLowerCase()) ? 0 : 1;
    if (ap !== bp) return ap - bp;
    return a.localeCompare(b);
  });
  // Prefer the exact official name even if case differs.
  const preferred = yaml.find((name) => PROFILE_NAMES_PREFERRED.includes(name.toLowerCase()));
  const ordered = preferred === undefined ? yaml : [preferred, ...yaml.filter((name) => name !== preferred)];
  return ordered.map((name) => path.join(dir, name));
}

function parseProxyEnv(value: string | undefined): DiscoveredProxyHint | undefined {
  if (value === undefined || value === '') return undefined;
  try {
    const url = new URL(value);
    const host = normalizeSocketHostname(url.hostname);
    const port = url.port !== '' ? Number(url.port) : url.protocol === 'https:' ? 443 : 80;
    if (host === '' || !Number.isInteger(port) || port < 1 || port > 65535) return undefined;
    return { host, port, source: 'env' };
  } catch {
    return undefined;
  }
}

/** Collect non-secret hints from an already-configured tunnel-client install. */
export function discoverExistingRuntime(hooks: DiscoverHooks = {}): ExistingRuntimeDiscovery {
  const env = envOf(hooks);
  const platform = platformOf(hooks);
  const out: ExistingRuntimeDiscovery = {};
  const executable = discoverExecutable(hooks);
  if (executable !== undefined) out.executable = executable;

  const dirs = hooks.profileDirs ?? defaultProfileDirs(env, platform);
  let chosen: (Pick<ExistingRuntimeDiscovery, 'tunnelId' | 'controlPlaneBaseUrl' | 'runtimeApiKeyAvailable' | 'profileName' | 'healthBaseUrl'> & { profilePath: string }) | undefined;
  for (const dir of dirs) {
    for (const file of listProfileFiles(hooks, dir, platform)) {
      const hints = readProfileHints(hooks, file);
      if (hints.tunnelId === undefined && hints.controlPlaneBaseUrl === undefined && hints.runtimeApiKeyAvailable === undefined) {
        continue;
      }
      chosen = { profilePath: file, ...hints };
      if (PROFILE_NAMES_PREFERRED.includes((file.replace(/\\/g, '/').split('/').pop() ?? '').toLowerCase())) break;
      if (hints.tunnelId !== undefined) break;
    }
    if (chosen?.tunnelId !== undefined) break;
  }
  if (chosen !== undefined) {
    out.profilePath = chosen.profilePath;
    if (chosen.profileName !== undefined) out.profileName = chosen.profileName;
    if (chosen.tunnelId !== undefined) out.tunnelId = chosen.tunnelId;
    if (chosen.controlPlaneBaseUrl !== undefined) out.controlPlaneBaseUrl = chosen.controlPlaneBaseUrl;
    if (chosen.runtimeApiKeyAvailable !== undefined) out.runtimeApiKeyAvailable = chosen.runtimeApiKeyAvailable;
    if (chosen.healthBaseUrl !== undefined) out.healthBaseUrl = chosen.healthBaseUrl;
  }

  const processes = resolveRunningProcesses(hooks, platform).filter((row) => row.executablePath !== '');
  const observed = processes.find((row) => Number.isInteger(row.pid) && row.pid > 0);
  if (observed !== undefined) {
    out.runningProcess = {
      pid: observed.pid,
      executablePath: observed.executablePath,
      ...(observed.profileName === undefined ? {} : { profileName: observed.profileName }),
      ...(observed.proxyFlag === true ? { proxyFlag: true } : {}),
    };
  }
  if (processes.some((row) => row.proxyFlag === true)) out.proxyInUse = true;

  const proxy =
    parseProxyEnv(env.HTTPS_PROXY) ??
    parseProxyEnv(env.HTTP_PROXY) ??
    parseProxyEnv(env.https_proxy) ??
    parseProxyEnv(env.http_proxy);
  if (proxy !== undefined) out.proxy = proxy;
  return out;
}
