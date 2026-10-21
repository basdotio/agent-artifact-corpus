import {
  appendFileSync,
  chmodSync,
  closeSync,
  mkdirSync,
  openSync,
  readFileSync,
  renameSync,
  writeFileSync,
} from 'node:fs';
import { join } from 'node:path';
import { diagnosticCode, diagnosticHash } from './diagnostic-events.js';
import { diagnosticLine } from './diagnostic-log.js';
import { diagnosticRotationBytes, rotateDiagnosticLog } from './diagnostic-log.js';

export function daemonDiagnostics(dataDir: string): {
  logPath: string;
  runtimeLogPath: string;
  clientLogPath: string;
  lastLifecycle?: Record<string, unknown>;
} {
  const logPath = join(dataDir, 'run', 'daemon.log');
  const paths = {
    logPath,
    runtimeLogPath: join(dataDir, 'run', 'runtime.log'),
    clientLogPath: join(dataDir, 'run', 'clients.log'),
  };
  try {
    return {
      ...paths,
      lastLifecycle: JSON.parse(readFileSync(join(dataDir, 'run', 'daemon-state.json'), 'utf8')),
    };
  } catch {
    return paths;
  }
}
/** Copy/truncate preserves the inherited O_APPEND stderr descriptor across rotation. */
export function rotateDaemonLog(dataDir: string, limit = diagnosticRotationBytes): void {
  rotateDiagnosticLog(daemonDiagnostics(dataDir).logPath, limit);
}
export function openDaemonLog(dataDir: string): number {
  mkdirSync(join(dataDir, 'run'), { recursive: true, mode: 0o700 });
  const fd = openSync(daemonDiagnostics(dataDir).logPath, 'a', 0o600);
  chmodSync(daemonDiagnostics(dataDir).logPath, 0o600);
  return fd;
}
export function recordDaemonLifecycle(
  dataDir: string,
  event: string,
  details: Record<string, unknown> = {},
): void {
  const record = {
    schemaVersion: 1,
    at: new Date().toISOString(),
    monoMs: performance.now(),
    pid: process.pid,
    event,
    ...details,
  };
  try {
    const fd = openDaemonLog(dataDir);
    closeSync(fd);
    rotateDaemonLog(dataDir);
    appendFileSync(daemonDiagnostics(dataDir).logPath, diagnosticLine(event, details));
    if (event !== 'maintenance_deferred' && event !== 'maintenance_recovered') {
      const path = join(dataDir, 'run', 'daemon-state.json');
      writeFileSync(`${path}.tmp`, JSON.stringify(record) + '\n', { mode: 0o600 });
      renameSync(`${path}.tmp`, path);
    }
  } catch {
    process.stderr.write('Bassfish could not persist daemon diagnostics.\n');
  }
}
/** Native error messages can include SQL or parameters; preserve categories and frame locations instead. */
export function daemonError(error: unknown): Record<string, unknown> {
  const code = diagnosticCode(error);
  return {
    code,
    error: `Daemon failure: ${code}.`,
    errorClass:
      error instanceof TypeError
        ? 'TypeError'
        : error instanceof RangeError
          ? 'RangeError'
          : 'Error',
    messageHash: error instanceof Error ? diagnosticHash(error.message) : undefined,
    stack:
      error instanceof Error
        ? error.stack
            ?.split('\n')
            .filter(line => /^\s+at /.test(line))
            .slice(0, 8)
            .map(line => line.slice(0, 256))
            .join('\n')
        : undefined,
  };
}
