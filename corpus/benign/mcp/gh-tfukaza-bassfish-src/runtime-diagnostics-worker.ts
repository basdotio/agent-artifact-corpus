import { parentPort, workerData } from 'node:worker_threads';
import { cpus, freemem, totalmem, loadavg, uptime } from 'node:os';
import { performance } from 'node:perf_hooks';
import { join } from 'node:path';
import { DiagnosticLog } from './diagnostic-log.js';
import type { DiagnosticFields } from './diagnostic-events.js';
import { RuntimeSampler } from './runtime-sampler.js';

const port = parentPort!;
const data = workerData as {
  dataDir: string;
  startup: DiagnosticFields;
  heartbeat: SharedArrayBuffer;
};
const heartbeat = new BigInt64Array(data.heartbeat);
const log = new DiagnosticLog(join(data.dataDir, 'run', 'runtime.log'));
const operations = new Map<string, DiagnosticFields>();
const sampler = new RuntimeSampler();
let main: DiagnosticFields = {};
const sessions = new Map<string, DiagnosticFields>();
let gcTotalMs = 0,
  gcTotalCount = 0,
  maxEventLoopUtilization = 0;
let lastSummary = 0;
let lastHost = 0;
let host: DiagnosticFields = {};
let previousCpu = process.cpuUsage();
let previousHostCpu = cpuTotals();
let previousHostMono = performance.now();
let operationDrops = 0;
function cpuTotals() {
  let idle = 0,
    total = 0;
  for (const cpu of cpus()) {
    idle += cpu.times.idle;
    total += Object.values(cpu.times).reduce((a, b) => a + b, 0);
  }
  return { idle, total };
}
log.emit('runtime.started', data.startup);
port.on('message', (message: { event: string; fields: DiagnosticFields; dropped?: number }) => {
  port.postMessage({ ack: 1 });
  if (message.dropped) {
    log.emit('logging.dropped', { count: message.dropped });
    operationDrops += message.dropped;
    operations.clear();
    sessions.clear();
  }
  const { event, fields } = message;
  if (event === 'runtime.stop') {
    clearInterval(timer);
    log.close();
    port.close();
    return;
  }
  if (event === 'runtime.main') {
    main = fields;
    gcTotalMs += Number(fields.gcMs ?? 0);
    gcTotalCount += Number(fields.gcCount ?? 0);
    maxEventLoopUtilization = Math.max(
      maxEventLoopUtilization,
      Number(fields.eventLoopUtilization ?? 0),
    );
    return;
  }
  if (event === 'session.heartbeat') {
    const id = String(fields.instanceId);
    if (sessions.has(id) || sessions.size < 1024) sessions.set(id, fields);
    return;
  }
  if (event === 'session.disconnected') sessions.delete(String(fields.instanceId));
  if (event === 'operation.active') {
    const id = String(fields.operationId);
    if (operations.has(id) || operations.size < 1024) operations.set(id, fields);
    else operationDrops++;
    return;
  }
  if (event === 'operation.finished') {
    operations.delete(String(fields.operationId));
    return;
  }
  log.emit(event, { epoch: data.startup.epoch, ...fields });
});
const timer = setInterval(() => {
  const mono = performance.now(),
    wall = Date.now();
  const gapMs = Number(process.hrtime.bigint() / 1000000n - Atomics.load(heartbeat, 0));
  const incidents = sampler.sample(wall, mono, gapMs);
  if (mono - lastHost >= 5000 || !lastHost) {
    const cpu = process.cpuUsage();
    const totals = cpuTotals();
    const elapsedMs = mono - previousHostMono;
    host = {
      sampledAt: wall,
      rssBytes: process.memoryUsage.rss(),
      cpuCoresUsed:
        elapsedMs > 0
          ? (cpu.user - previousCpu.user + cpu.system - previousCpu.system) / (elapsedMs * 1000)
          : 0,
      hostCpuUtilization:
        totals.total > previousHostCpu.total
          ? 1 - (totals.idle - previousHostCpu.idle) / (totals.total - previousHostCpu.total)
          : null,
      loadAverage: loadavg(),
      freeMemoryBytes: freemem(),
      totalMemoryBytes: totalmem(),
      systemUptimeSeconds: uptime(),
      cpuCount: cpus().length,
    };
    previousCpu = cpu;
    previousHostCpu = totals;
    previousHostMono = mono;
    lastHost = mono;
    const indicators = [
      typeof host.hostCpuUtilization === 'number' && host.hostCpuUtilization >= 0.9
        ? 'high_host_cpu'
        : undefined,
      Number(host.freeMemoryBytes) < Number(host.totalMemoryBytes) * 0.05
        ? 'low_free_memory'
        : undefined,
      loadavg()[0]! > cpus().length * 1.5 ? 'high_load' : undefined,
    ].filter(Boolean);
    if (indicators.length)
      log.emit('runtime.host_pressure', {
        epoch: data.startup.epoch,
        indicators,
        host,
        cause: 'unknown',
      });
  }
  const oldest = [...operations.values()].sort(
    (a, b) => Number(a.startedMonoMs) - Number(b.startedMonoMs),
  );
  const summary = {
    epoch: data.startup.epoch,
    sampledAt: wall,
    mainHeartbeatAgeMs: gapMs,
    gcTotalMs,
    gcTotalCount,
    maxEventLoopUtilization,
    trackedSessionCount: sessions.size,
    status: gapMs > 2000 ? 'main_loop_stalled' : 'responsive',
    main,
    mainSampleAgeMs: typeof main.sampledAt === 'number' ? wall - main.sampledAt : null,
    host,
    hostSampleAgeMs: typeof host.sampledAt === 'number' ? wall - host.sampledAt : null,
    activeOperationCount: operations.size,
    droppedOperationStates: operationDrops,
    oldestOperations: oldest.slice(0, 3).map(op => ({
      operationId: op.operationId,
      ipcRequestId: op.ipcRequestId,
      method: op.method,
      tool: op.tool,
      kind: op.kind,
      phase: op.phase,
      statementKind: op.statementKind,
      statementOrdinal: op.statementOrdinal,
      poolQueued: op.poolQueued,
      poolActive: op.poolActive,
      attempt: op.attempt,
      ageMs: mono - Number(op.startedMonoMs),
      phaseAgeMs: mono - Number(op.phaseStartedMonoMs),
    })),
  };
  port.postMessage({ summary });
  if (
    mono - lastSummary >= 30000 ||
    !lastSummary ||
    incidents.some(incident => incident.event !== 'runtime.stall_ongoing')
  ) {
    log.emit('runtime.summary', summary);
    lastSummary = mono;
    maxEventLoopUtilization = 0;
  }
  for (const incident of incidents) log.emit(incident.event, { ...summary, ...incident.fields });
  // Healthy main loop plus an over-budget operation yields evidence even if it never finishes.
  const slow = oldest.find(
    op => mono - Number(op.startedMonoMs) > Number(op.expectedMs ?? 0) + 1000,
  );
  if (slow)
    log.emit('operation.pending', {
      epoch: data.startup.epoch,
      ...slow,
      ageMs: mono - Number(slow.startedMonoMs),
      phaseAgeMs: mono - Number(slow.phaseStartedMonoMs),
      mainHeartbeatAgeMs: gapMs,
    });
}, 1000);
