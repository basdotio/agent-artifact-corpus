import { Worker } from 'node:worker_threads';
import { performance, PerformanceObserver } from 'node:perf_hooks';
import type { DiagnosticFields, DiagnosticSink } from './diagnostic-events.js';
import { DiagnosticLog } from './diagnostic-log.js';
import { join } from 'node:path';

// Bun emits no `gc` performance entries and returns a permanent zero from
// eventLoopUtilization(); reporting those as real numbers would hide a stalled loop.
const isBun = Boolean((process.versions as { bun?: string }).bun);
const supportedEntryTypes = (PerformanceObserver as unknown as { supportedEntryTypes?: string[] })
  .supportedEntryTypes;
const gcEntriesSupported = supportedEntryTypes ? supportedEntryTypes.includes('gc') : !isBun;
const eventLoopUtilizationSupported = !isBun;
const unavailableMetrics = [
  ...(gcEntriesSupported ? [] : ['gc']),
  ...(eventLoopUtilizationSupported ? [] : ['eventLoopUtilization']),
];

/** A worker owns runtime I/O and observes a shared heartbeat without main-loop cooperation. */
export class RuntimeDiagnostics {
  private readonly heartbeat = new BigInt64Array(new SharedArrayBuffer(8));
  private readonly worker: Worker;
  private readonly timer: NodeJS.Timeout;
  private readonly gc: PerformanceObserver | undefined;
  private gcMs = 0;
  private gcCount = 0;
  private pending = 0;
  private dropped = 0;
  private coalescedOperationUpdates = 0;
  private readonly deferredOperations = new Map<
    string,
    { event: string; fields: DiagnosticFields }
  >();
  private readonly sentOperations = new Set<string>();
  private stopped = false;
  private previousElu = performance.eventLoopUtilization();
  private lastSummary: DiagnosticFields = { status: 'starting' };
  constructor(dataDir: string, startup: DiagnosticFields) {
    Atomics.store(this.heartbeat, 0, process.hrtime.bigint() / 1000000n);
    const workerUrl = import.meta.url.endsWith('.ts')
      ? new URL('./runtime-diagnostics-worker.ts', import.meta.url)
      : new URL('./runtime-diagnostics-worker.js', import.meta.url);
    this.worker = new Worker(workerUrl, {
      workerData: { dataDir, startup, heartbeat: this.heartbeat.buffer },
    });
    this.worker.on('message', (message: { ack?: number; summary?: DiagnosticFields }) => {
      if (message.ack) this.pending = Math.max(0, this.pending - message.ack);
      if (message.summary) this.lastSummary = message.summary;
      this.flushOperations();
    });
    this.worker.on('error', () => {
      this.lastSummary = { status: 'worker_failed' };
      this.stopped = true;
      clearInterval(this.timer);
      this.gc?.disconnect();
      const fallback = new DiagnosticLog(join(dataDir, 'run', 'runtime.log'));
      fallback.emit('runtime.worker_failed', { epoch: startup.epoch });
      fallback.close();
    });
    this.worker.on('exit', code => {
      if (!this.stopped) {
        this.lastSummary = { status: 'worker_failed', exitCode: code };
        this.stopped = true;
        clearInterval(this.timer);
        this.gc?.disconnect();
        const fallback = new DiagnosticLog(join(dataDir, 'run', 'runtime.log'));
        fallback.emit('runtime.worker_failed', { epoch: startup.epoch, exitCode: code });
        fallback.close();
      }
    });
    this.worker.unref();
    if (gcEntriesSupported) {
      this.gc = new PerformanceObserver(list => {
        for (const entry of list.getEntries()) {
          this.gcMs += entry.duration;
          this.gcCount++;
        }
      });
      this.gc.observe({ entryTypes: ['gc'] });
    }
    this.timer = setInterval(() => {
      Atomics.store(this.heartbeat, 0, process.hrtime.bigint() / 1000000n);
      const elu = performance.eventLoopUtilization(this.previousElu);
      this.previousElu = performance.eventLoopUtilization();
      const memory = process.memoryUsage();
      this.emit('runtime.main', {
        sampledAt: Date.now(),
        ...(eventLoopUtilizationSupported ? { eventLoopUtilization: elu.utilization } : {}),
        heapUsedBytes: memory.heapUsed,
        heapTotalBytes: memory.heapTotal,
        externalBytes: memory.external,
        ...(gcEntriesSupported ? { gcMs: this.gcMs, gcCount: this.gcCount } : {}),
        coalescedOperationUpdates: this.coalescedOperationUpdates,
        deferredOperationStates: this.deferredOperations.size,
        ...(unavailableMetrics.length ? { unavailableMetrics } : {}),
      });
      this.gcMs = 0;
      this.gcCount = 0;
    }, 1000);
    this.timer.unref();
  }
  readonly emit: DiagnosticSink = (event, fields) => {
    if (this.stopped) return;
    if (event === 'operation.active' || event === 'operation.finished') {
      const id = String(fields.operationId);
      // Fast successful operations that finish before being sampled need no worker state.
      if (event === 'operation.finished' && !this.sentOperations.has(id)) {
        this.deferredOperations.delete(id);
        this.coalescedOperationUpdates++;
        return;
      }
      // Reserve most of the message budget for incidents and health, not transient SQL phases.
      if (this.pending >= 128 || this.deferredOperations.has(id)) {
        if (this.deferredOperations.has(id) || this.deferredOperations.size < 1024) {
          this.deferredOperations.set(id, { event, fields });
          this.coalescedOperationUpdates++;
        } else this.dropped++;
        return;
      }
    }
    this.send(event, fields);
  };
  private send(event: string, fields: DiagnosticFields): void {
    if (
      event === 'operation.active' &&
      !this.sentOperations.has(String(fields.operationId)) &&
      this.sentOperations.size >= 1024
    ) {
      this.dropped++;
      return;
    }
    if (this.pending >= 1024) {
      this.dropped++;
      return;
    }
    try {
      this.worker.postMessage({ event, fields, dropped: this.dropped });
      this.dropped = 0;
      this.pending++;
      if (event === 'operation.active') this.sentOperations.add(String(fields.operationId));
      if (event === 'operation.finished') this.sentOperations.delete(String(fields.operationId));
    } catch {
      this.dropped++;
    }
  }
  private flushOperations(): void {
    if (this.stopped) return;
    for (const [id, message] of this.deferredOperations) {
      if (this.pending >= 128) break;
      this.deferredOperations.delete(id);
      this.send(message.event, message.fields);
    }
  }
  summary(): DiagnosticFields {
    return {
      ...this.lastSummary,
      summaryAgeMs:
        typeof this.lastSummary.sampledAt === 'number'
          ? Date.now() - this.lastSummary.sampledAt
          : null,
      pendingLogMessages: this.pending,
      droppedLogMessages: this.dropped,
      coalescedOperationUpdates: this.coalescedOperationUpdates,
      deferredOperationStates: this.deferredOperations.size,
    };
  }
  async close(): Promise<void> {
    clearInterval(this.timer);
    this.gc?.disconnect();
    if (this.stopped) return;
    this.stopped = true;
    await new Promise<void>(resolve => {
      const timeout = setTimeout(() => {
        void this.worker.terminate();
        resolve();
      }, 1000);
      this.worker.once('exit', () => {
        clearTimeout(timeout);
        resolve();
      });
      this.worker.postMessage({ event: 'runtime.stop', fields: {} });
    });
  }
}

/** Optional construction must not prevent the daemon from starting. */
export function startRuntimeDiagnostics(
  dataDir: string,
  startup: DiagnosticFields,
): RuntimeDiagnostics | undefined {
  try {
    return new RuntimeDiagnostics(dataDir, startup);
  } catch {
    const fallback = new DiagnosticLog(join(dataDir, 'run', 'runtime.log'));
    fallback.emit('runtime.unavailable', {});
    fallback.close();
    return undefined;
  }
}
