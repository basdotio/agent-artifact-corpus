/**
 * Process identity and ownership verification.
 *
 * Windows reuses PIDs, so the plugin never treats a PID alone as proof that a
 * process belongs to it. Every plugin-launched runtime carries a ProcessIdentity
 * (pid + startedAt + executablePath + per-launch runtimeInstanceId); before any
 * termination the manager re-verifies the live process against that identity.
 *
 * Verification checks three facts on the live process: the PID exists, its
 * executable path matches (normalized), and its real process start time lies
 * within a tolerance of the recorded start time. A re-used PID with a matching
 * path but a different start time is rejected (start-time-mismatch). This
 * module also provides the read-only probes used by that verification. Nothing
 * here kills processes.
 */
import { spawnSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { readFileSync, readlinkSync } from 'node:fs';
import { normalize } from 'node:path';

import type { ProcessIdentity } from './types.js';

/**
 * Tolerance when comparing the recorded start time (set at launch) against the
 * live process start time. Covers clock/precision skew between the plugin's
 * clock and the OS-reported process start time without weakening PID-reuse
 * detection (a re-used PID starts seconds/minutes later).
 */
export const START_TIME_TOLERANCE_MS = 2000;

/** Probe whether a pid currently exists (signal 0 does not deliver a signal). */
export function isProcessAlive(pid: number): boolean {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return (error as NodeJS.ErrnoException).code === 'EPERM'; // exists but not ours
  }
}

/**
 * Best-effort read of another process's executable path. Returns undefined when
 * the process does not exist or the path cannot be determined. Structured
 * spawn only; the pid is validated numeric, so no shell is ever involved.
 */
export function processExecutablePath(pid: number): string | undefined {
  if (!Number.isInteger(pid) || pid <= 0) return undefined;
  try {
    if (process.platform === 'win32') {
      const result = spawnSync(
        'powershell.exe',
        ['-NoProfile', '-NonInteractive', '-Command', `(Get-Process -Id ${pid} -ErrorAction SilentlyContinue).Path`],
        { encoding: 'utf8', windowsHide: true, timeout: 5000 },
      );
      const path = (result.stdout ?? '').trim();
      return path === '' ? undefined : path;
    }
    // POSIX: the /proc/<pid>/exe symlink is the Linux canonical answer.
    try {
      return readlinkSync(`/proc/${pid}/exe`);
    } catch {
      // macOS / BSD fallback via ps
      const result = spawnSync('ps', ['-p', String(pid), '-o', 'comm='], { encoding: 'utf8', timeout: 5000 });
      const path = (result.stdout ?? '').trim();
      return path === '' ? undefined : path;
    }
  } catch {
    return undefined;
  }
}

/**
 * Best-effort read of another process's actual start time (epoch ms).
 * Windows queries `Get-Process ... StartTime` via PowerShell (structured
 * spawn, pid validated numeric, no shell). POSIX reads the `starttime` field
 * from /proc plus the boot time. Returns undefined when the process does not
 * exist or the start time cannot be determined.
 */
export function processStartTimeMs(pid: number): number | undefined {
  if (!Number.isInteger(pid) || pid <= 0) return undefined;
  try {
    if (process.platform === 'win32') {
      const result = spawnSync(
        'powershell.exe',
        [
          '-NoProfile',
          '-NonInteractive',
          '-Command',
          `$p = Get-Process -Id ${pid} -ErrorAction SilentlyContinue; if ($null -eq $p) { '' } else { try { [DateTimeOffset]::new($p.StartTime.ToUniversalTime()).ToUnixTimeMilliseconds() } catch { '' } }`,
        ],
        { encoding: 'utf8', windowsHide: true, timeout: 5000 },
      );
      const raw = (result.stdout ?? '').trim();
      if (raw === '') return undefined;
      const ms = Number(raw);
      return Number.isFinite(ms) ? ms : undefined;
    }
    // POSIX: field 22 (starttime) is ticks since boot; add boot time (/proc/stat).
    const fromProc = posixStartTimeMs(pid);
    if (fromProc !== undefined) return fromProc;
    return psStartTimeMs(pid);
  } catch {
    return undefined;
  }
}

function psStartTimeMs(pid: number): number | undefined {
  try {
    const result = spawnSync('ps', ['-p', String(pid), '-o', 'lstart='], { encoding: 'utf8', timeout: 5000 });
    const raw = (result.stdout ?? '').trim();
    if (raw === '') return undefined;
    const ms = new Date(raw).getTime();
    return Number.isFinite(ms) ? ms : undefined;
  } catch {
    return undefined;
  }
}

function posixStartTimeMs(pid: number): number | undefined {
  try {
    const stat = readFileSync(`/proc/${pid}/stat`, 'utf8');
    // `comm` may contain ')'; the fields after the last ')' start at state (field 3).
    const afterComm = stat.slice(stat.lastIndexOf(')') + 2);
    const fields = afterComm.split(' ');
    // fields[0] is state (field 3); starttime is field 22 -> index 22 - 3 = 19.
    const startTicks = Number(fields[19]);
    if (!Number.isFinite(startTicks)) return undefined;
    const bootTimeLine = readFileSync('/proc/stat', 'utf8').split('\n').find((line) => line.startsWith('btime '));
    if (bootTimeLine === undefined) return undefined;
    const bootTime = Number(bootTimeLine.slice(6).trim());
    if (!Number.isFinite(bootTime)) return undefined;
    // CLK_TCK is 100 on Linux; 1000 would shift by a factor of ten, so use 100.
    return (bootTime + startTicks / 100) * 1000;
  } catch {
    return undefined;
  }
}

/**
 * Platform-aware executable path comparison: Windows filesystems are
 * case-insensitive, POSIX are case-sensitive. Paths are normalized so
 * separator/`.`/`..` differences do not cause false mismatches. realpath is
 * deliberately avoided — the target process may exit between probes.
 */
function sameExecutablePath(expected: string, actual: string): boolean {
  const left = normalize(expected);
  const right = normalize(actual);
  return process.platform === 'win32' ? left.toLowerCase() === right.toLowerCase() : left === right;
}

/** Create a fresh identity for a process the plugin just launched. */
export function createProcessIdentity(options: {
  pid: number;
  executablePath: string;
  /** Optional recorded start time (ISO); defaults to the current time. */
  startedAt?: string;
  profileName?: string;
  tunnelId?: string;
}): ProcessIdentity {
  return {
    pid: options.pid,
    startedAt: options.startedAt ?? new Date().toISOString(),
    executablePath: options.executablePath,
    runtimeInstanceId: randomUUID(),
    ...(options.profileName === undefined ? {} : { profileName: options.profileName }),
    ...(options.tunnelId === undefined ? {} : { tunnelId: options.tunnelId }),
  };
}

/** Injectable probes so verification can be tested without real processes. */
export interface ProcessIdentityProbes {
  isAlive?: (pid: number) => boolean;
  executablePath?: (pid: number) => string | undefined;
  startTimeMs?: (pid: number) => number | undefined;
}

export interface IdentityVerification {
  ok: boolean;
  code:
    | 'verified'
    | 'not-alive'
    | 'executable-mismatch'
    | 'start-time-mismatch'
    | 'unknown-executable'
    | 'unknown-start-time';
}

/**
 * Verify a live process still matches the identity the plugin recorded at
 * launch. A mismatch — path, start time, or an unreadable probe — is treated
 * as "not ours": callers must refuse to terminate in that case
 * (stale-process-identity). An unknown start time also fails closed: the
 * plugin cannot confirm the process is the one it launched.
 */
export function verifyProcessIdentity(identity: ProcessIdentity, probes: ProcessIdentityProbes = {}): IdentityVerification {
  const isAlive = probes.isAlive ?? isProcessAlive;
  const executablePath = probes.executablePath ?? processExecutablePath;
  const startTimeMs = probes.startTimeMs ?? processStartTimeMs;

  if (!isAlive(identity.pid)) return { ok: false, code: 'not-alive' };
  const current = executablePath(identity.pid);
  if (current === undefined) return { ok: false, code: 'unknown-executable' };
  if (!sameExecutablePath(identity.executablePath, current)) return { ok: false, code: 'executable-mismatch' };

  const observedStart = startTimeMs(identity.pid);
  if (observedStart === undefined) return { ok: false, code: 'unknown-start-time' };
  const recordedStart = new Date(identity.startedAt).getTime();
  if (!Number.isFinite(recordedStart)) return { ok: false, code: 'unknown-start-time' };
  if (Math.abs(observedStart - recordedStart) > START_TIME_TOLERANCE_MS) {
    return { ok: false, code: 'start-time-mismatch' };
  }
  return { ok: true, code: 'verified' };
}
