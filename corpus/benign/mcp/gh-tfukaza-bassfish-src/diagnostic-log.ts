import {
  appendFileSync,
  chmodSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  statSync,
  truncateSync,
} from 'node:fs';
import { dirname, join } from 'node:path';
import { performance } from 'node:perf_hooks';
import { bestEffortLock } from './lock.js';
import { packageVersion } from './config.js';
import type { DiagnosticFields, DiagnosticSink } from './diagnostic-events.js';

export const diagnosticRotationBytes = 8 * 1024 * 1024;
export function rotateDiagnosticLog(path: string, limit = diagnosticRotationBytes): void {
  if (!existsSync(path) || statSync(path).size < limit) return;
  for (let index = 2; index >= 0; index--) {
    const source = index === 0 ? path : `${path}.${index}`;
    if (existsSync(source)) {
      copyFileSync(source, `${path}.${index + 1}`);
      chmodSync(`${path}.${index + 1}`, 0o600);
    }
  }
  // Preserve the inherited O_APPEND descriptor used for background stderr.
  truncateSync(path, 0);
}
export function diagnosticLine(event: string, fields: DiagnosticFields): string {
  const base = {
    ...fields,
    schemaVersion: 1,
    at: new Date().toISOString(),
    monoMs: performance.now(),
    pid: process.pid,
    event,
  };
  const line = JSON.stringify(base) + '\n';
  if (Buffer.byteLength(line) <= 4096) return line;
  return (
    JSON.stringify({
      schemaVersion: 1,
      at: base.at,
      monoMs: base.monoMs,
      pid: base.pid,
      event: event.slice(0, 100),
      truncated: true,
      operationId: fields.operationId,
      ipcRequestId: fields.ipcRequestId,
      code: fields.code,
    }) + '\n'
  );
}
/** One writer per stream; shared client writers take a separate, zero-wait kernel lock. */
export class DiagnosticLog {
  private readonly queue: string[] = [];
  private dropped = 0;
  private timer?: NodeJS.Timeout;
  private readonly summaryTimer: NodeJS.Timeout;
  private readonly rates = new Map<string, { at: number; count: number; maxDurationMs: number }>();
  constructor(
    private readonly path: string,
    private readonly shared = false,
  ) {
    this.summaryTimer = setInterval(() => {
      const now = performance.now();
      for (const [key, value] of this.rates)
        if (value.count && now - value.at >= 60000) {
          const fields = { key, count: value.count, maxDurationMs: value.maxDurationMs };
          value.count = 0;
          this.enqueue('logging.suppressed', fields);
        }
    }, 60000);
    this.summaryTimer.unref();
  }
  readonly emit: DiagnosticSink = (event, fields) => {
    if (event === 'operation.active' || event === 'operation.finished') return;
    const key = `${event}:${String(fields.tool ?? fields.method ?? fields.kind ?? '')}:${String(fields.instanceId ?? '')}:${String(fields.code ?? '')}`;
    const now = performance.now();
    const previous = this.rates.get(key);
    if (
      previous &&
      now - previous.at < 60000 &&
      ![
        'runtime.summary',
        'runtime.stall_recovered',
        'runtime.stall_started',
        'session.connected',
        'client.connected',
        'logging.dropped',
      ].includes(event)
    ) {
      previous.count++;
      previous.maxDurationMs = Math.max(
        previous.maxDurationMs,
        Number(fields.durationMs ?? fields.gapMs ?? fields.samplerGapMs ?? fields.ageMs ?? 0),
      );
      return;
    }
    if (this.rates.size >= 256 && !previous) this.rates.delete(this.rates.keys().next().value!);
    this.rates.set(key, {
      at: now,
      count: 0,
      maxDurationMs: Number(
        fields.durationMs ?? fields.gapMs ?? fields.samplerGapMs ?? fields.ageMs ?? 0,
      ),
    });
    this.enqueue(event, {
      ...fields,
      ...(previous?.count
        ? { suppressedCount: previous.count, maxDurationMs: previous.maxDurationMs }
        : {}),
    });
  };
  private enqueue(event: string, fields: DiagnosticFields): void {
    try {
      if (this.queue.length >= 1024) {
        this.dropped++;
        return;
      }
      this.queue.push(diagnosticLine(event, fields));
      this.flush();
    } catch {
      this.dropped++;
    }
  }
  flush(): void {
    let unlock: (() => void) | undefined;
    try {
      mkdirSync(dirname(this.path), { recursive: true, mode: 0o700 });
      if (this.shared) unlock = bestEffortLock(join(dirname(this.path), 'diagnostic-clients.lock'));
      rotateDiagnosticLog(this.path);
      if (this.dropped) {
        appendFileSync(this.path, diagnosticLine('logging.dropped', { count: this.dropped }), {
          mode: 0o600,
        });
        this.dropped = 0;
      }
      // Rotate between records, so a backlog cannot exceed the per-file budget.
      while (this.queue.length) {
        rotateDiagnosticLog(this.path);
        appendFileSync(this.path, this.queue[0]!, { mode: 0o600 });
        this.queue.shift();
      }
      chmodSync(this.path, 0o600);
      if (this.timer) clearTimeout(this.timer);
      this.timer = undefined;
    } catch {
      if (!this.timer) {
        this.timer = setTimeout(() => {
          this.timer = undefined;
          this.flush();
        }, 100);
        this.timer.unref();
      }
    } finally {
      try {
        unlock?.();
      } catch {
        /* logging is never authoritative */
      }
    }
  }
  close(): void {
    clearInterval(this.summaryTimer);
    for (const [key, value] of this.rates)
      if (value.count)
        this.enqueue('logging.suppressed', {
          key,
          count: value.count,
          maxDurationMs: value.maxDurationMs,
        });
    this.rates.clear();
    this.flush();
    if (this.timer) clearTimeout(this.timer);
  }
}
const clients = new Map<string, DiagnosticLog>();
export function clientDiagnosticSink(dataDir: string): DiagnosticSink {
  let log = clients.get(dataDir);
  if (!log) {
    log = new DiagnosticLog(join(dataDir, 'run', 'clients.log'), true);
    clients.set(dataDir, log);
  }
  return (event, fields) => log.emit(event, { bassfishVersion: packageVersion, ...fields });
}
