import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileEvents, quality, qualityTracker, object, samplingInterval } from './records.mjs';

/** @typedef {import('./types.js').Summary} Summary */
/** @typedef {import('./types.js').Event} Event */
/** @typedef {import('./types.js').Hotspot} Hotspot */
/** @typedef {import('./types.js').Route} Route */
/** @typedef {import('./types.js').IntervalSource} IntervalSource */

/** @param {number[]} values @param {number} p */
export function percentile(values, p) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.max(0, Math.ceil(p * sorted.length) - 1)];
}

/** @param {number} before @param {number} after */
export function percentage(before, after) {
  return before === 0 ? null : ((after - before) / before) * 100;
}

/** @param {number[]} values */
function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : Math.round((sorted[middle - 1] + sorted[middle]) / 2);
}

const ROUTE_LIMIT = 20;

/** @param {{method: string, path: string, durationNs: number, statusCode: number}[]} spans */
function routeBreakdown(spans) {
  /** @type {Map<string, {method: string, path: string, durations: number[], errors: number}>} */
  const groups = new Map();
  for (const span of spans) {
    const key = JSON.stringify([span.method, span.path]);
    let group = groups.get(key);
    if (!group)
      groups.set(key, (group = { method: span.method, path: span.path, durations: [], errors: 0 }));
    group.durations.push(span.durationNs);
    if (span.statusCode >= 500) group.errors += 1;
  }
  /** @type {Route[]} */ const routes = [...groups.values()].map((group) => ({
    method: group.method,
    path: group.path,
    count: group.durations.length,
    // Groups are never empty, so percentiles are numbers.
    p50Ns: /** @type {number} */ (percentile(group.durations, 0.5)),
    p99Ns: /** @type {number} */ (percentile(group.durations, 0.99)),
    maxNs: group.durations.reduce((max, value) => Math.max(max, value), 0),
    serverErrors: group.errors,
  }));
  /** @param {string} a @param {string} b */
  const order = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  routes.sort(
    (a, b) =>
      b.count - a.count || b.p99Ns - a.p99Ns || order(a.method, b.method) || order(a.path, b.path),
  );
  return { routes: routes.slice(0, ROUTE_LIMIT), distinctRoutes: groups.size };
}

/**
 * @param {AsyncIterable<Event>} events @param {string} source
 * @param {import('./types.js').Quality} status @param {number} [intervalMs]
 * @param {IntervalSource} [intervalSource] @returns {Promise<Summary>}
 */
export async function summarizeEvents(events, source, status, intervalMs, intervalSource) {
  const origin = intervalSource ?? (intervalMs === undefined ? 'default' : 'flag');
  intervalMs ??= 1000;
  const counts = { samples: 0, windows: 0, spans: 0, alerts: 0 };
  /** @type {Record<string, number>} */ const raw = {};
  /** @type {Record<string, number>} */ const aggregate = {};
  /** @type {{startMs: number, endMs: number, durationNs: number, statusCode: number, method: string, path: string}[]} */ const spans =
    [];
  /** @type {number[]} */ const spacing = [];
  /** @type {number | undefined} */ let previousTimestamp;
  /** @type {Map<string, Hotspot>} */ const sites = new Map();
  /** @type {Record<string, number> | null} */ let firstRaw = null;
  /** @type {Record<string, number> | null} */ let lastRaw = null;
  /** @type {Record<string, number> | null} */ let firstWindow = null;
  /** @type {Record<string, number> | null} */ let lastWindow = null;
  let start = Infinity;
  let end = -Infinity;
  let spanStart = Infinity;
  let spanEnd = -Infinity;
  let windowSamples = 0;
  const tracker = qualityTracker(status, intervalMs);
  /** @param {Record<string, number>} into @param {string} key @param {number} value @param {'sum' | 'max'} [mode] */
  const fold = (into, key, value, mode = 'max') => {
    into[key] =
      mode === 'max'
        ? Math.max(into[key] ?? 0, value)
        : Math.min(Number.MAX_SAFE_INTEGER, (into[key] ?? 0) + value);
  };
  for await (const record of events) {
    tracker.add(record);
    if (record.event === 'sample' || record.event === 'window') {
      const isRaw = record.event === 'sample';
      if ((isRaw && counts.windows) || (!isRaw && counts.samples))
        throw new Error('summary cannot combine raw samples with already aggregated windows');
      const data = record.data;
      const metrics = isRaw ? raw : aggregate;
      counts[isRaw ? 'samples' : 'windows'] += 1;
      if (record.event === 'sample') {
        if (previousTimestamp !== undefined && record.data.timestamp > previousTimestamp)
          spacing.push(record.data.timestamp - previousTimestamp);
        previousTimestamp = record.data.timestamp;
        start = Math.min(start, record.data.timestamp);
        end = Math.max(end, record.data.timestamp + intervalMs);
        lastRaw = { ...record.data.memory };
        firstRaw ??= lastRaw;
        for (const site of record.data.backpressure.hotspots ?? []) {
          const previous = sites.get(site.site);
          sites.set(site.site, {
            site: site.site,
            events: (previous?.events ?? 0) + site.events,
            totalStall: (previous?.totalStall ?? 0) + site.totalStall,
            maxStall: Math.max(previous?.maxStall ?? 0, site.maxStall),
          });
        }
        fold(metrics, 'heapUsedMaxBytes', record.data.memory.heapUsed);
        fold(metrics, 'rssMaxBytes', record.data.memory.rss);
        fold(metrics, 'externalMaxBytes', record.data.memory.external);
        fold(metrics, 'arrayBuffersMaxBytes', record.data.memory.arrayBuffers);
        fold(metrics, 'lagMeanSumNs', data.eventLoop.mean, 'sum');
        fold(metrics, 'lagMeanWeight', 1, 'sum');
      } else {
        start = Math.min(start, record.data.start);
        end = Math.max(end, record.data.end);
        lastWindow = { heapUsed: record.data.memory.heapUsedLast, rss: record.data.memory.rssLast };
        firstWindow ??= lastWindow;
        fold(metrics, 'heapUsedMaxBytes', record.data.memory.heapUsedMax);
        fold(metrics, 'rssMaxBytes', record.data.memory.rssMax);
        fold(metrics, 'lagMeanSumNs', record.data.eventLoop.mean * record.data.count, 'sum');
        fold(metrics, 'lagMeanWeight', record.data.count, 'sum');
        fold(metrics, 'lateSamples', record.data.late, 'sum');
        windowSamples = Math.min(Number.MAX_SAFE_INTEGER, windowSamples + record.data.count);
      }
      fold(metrics, 'eventLoopMaxNs', data.eventLoop.max);
      fold(metrics, 'maxSampleP99Ns', data.eventLoop.p99);
      fold(metrics, 'gcCount', data.gc.count, 'sum');
      fold(metrics, 'gcTotalPauseNs', data.gc.totalPause, 'sum');
      fold(metrics, 'gcMaxPauseNs', data.gc.maxPause);
      fold(metrics, 'backpressureEvents', data.backpressure.events, 'sum');
      fold(metrics, 'backpressureTotalStallNs', data.backpressure.totalStall, 'sum');
      fold(metrics, 'backpressureMaxStallNs', data.backpressure.maxStall);
    } else if (record.event === 'span') {
      counts.spans += 1;
      const startMs = record.data.startTimeMs;
      const endMs = startMs + record.data.durationNs / 1_000_000;
      spans.push({
        startMs,
        endMs,
        durationNs: record.data.durationNs,
        statusCode: record.data.statusCode,
        method: record.data.method,
        path: record.data.path,
      });
      spanStart = Math.min(spanStart, startMs);
      spanEnd = Math.max(spanEnd, endMs);
    } else counts.alerts += 1;
  }
  const metrics = counts.samples ? raw : aggregate;
  const mean =
    (metrics.lagMeanWeight ?? 0) > 0
      ? Math.floor(metrics.lagMeanSumNs / metrics.lagMeanWeight)
      : null;
  delete metrics.lagMeanSumNs;
  delete metrics.lagMeanWeight;
  const durationMs = Number.isFinite(start) ? Math.max(0, end - start) : 0;
  // Dashboard spans and windows have independent retention. Align requests only after
  // all records have established the runtime interval, regardless of arrival order.
  const selectedSpans = spans.filter(
    (span) => span.startMs >= start && span.startMs < end && span.endMs <= end,
  );
  const durations = selectedSpans.map((span) => span.durationNs);
  const errors = selectedSpans.filter((span) => span.statusCode >= 500).length;
  const { routes, distinctRoutes } = routeBreakdown(selectedSpans);
  return {
    schemaVersion: 1,
    command: 'summarize',
    source,
    period: {
      startMs: Number.isFinite(start) ? start : null,
      endMs: Number.isFinite(end) ? end : null,
      durationMs,
    },
    counts,
    coverage: {
      format: counts.samples ? 'samples' : counts.windows ? 'windows' : null,
      samplingIntervalMs: counts.samples ? intervalMs : null,
      samplingIntervalSource: counts.samples ? origin : null,
      observedIntervalMs: counts.samples ? median(spacing) : null,
      sampleCount: counts.samples || windowSamples,
    },
    requests: {
      period: {
        startMs: Number.isFinite(spanStart) ? spanStart : null,
        endMs: Number.isFinite(spanEnd) ? spanEnd : null,
        durationMs: Number.isFinite(spanStart) ? Math.max(0, spanEnd - spanStart) : 0,
      },
      inPeriod: selectedSpans.length,
      outsidePeriod: counts.spans - selectedSpans.length,
      selection: 'fully-contained-in-runtime-period',
      routes,
      distinctRoutes,
    },
    quality: status,
    metrics: {
      ...metrics,
      eventLoopMeanNs: mean,
      externalMaxBytes: metrics.externalMaxBytes ?? null,
      arrayBuffersMaxBytes: metrics.arrayBuffersMaxBytes ?? null,
      observedRequestP50Ns: percentile(durations, 0.5),
      observedRequestP99Ns: percentile(durations, 0.99),
      observedRequestRatePerSecond:
        durationMs > 0 ? (selectedSpans.length * 1000) / durationMs : null,
      observedServerErrors: selectedSpans.length ? errors : null,
    },
    memory: {
      first: counts.samples ? firstRaw : firstWindow,
      last: counts.samples ? lastRaw : lastWindow,
    },
    hotspots: [...sites.values()].sort((a, b) => b.totalStall - a.totalStall).slice(0, 20),
    conditions: null,
  };
}

/** @param {string} file @param {{maxEvents?: number, allowLogs?: boolean, intervalMs?: number, manifest?: string}} [options] */
export async function summarizeFile(file, options = {}) {
  /** @type {Record<string, unknown> | undefined} */ let manifest;
  if (options.manifest) {
    /** @type {unknown} */ const input = JSON.parse(await readFile(options.manifest, 'utf8'));
    if (!object(input) || input.schemaVersion !== 1 || !object(input.quality))
      throw new Error('unsupported capture manifest');
    manifest = input;
  }
  const interval = samplingInterval(options.intervalMs, manifest?.conditions, manifest?.intervalMs);
  const status = quality();
  const result = await summarizeEvents(
    fileEvents(file, status, options),
    resolve(file),
    status,
    interval.intervalMs,
    interval.source,
  );
  if (manifest && object(manifest.quality)) {
    const previous = manifest.quality;
    result.quality.invalidRecords += Number(previous.invalidRecords ?? 0);
    result.quality.ignoredLogs += Number(previous.ignoredLogs ?? 0);
    result.quality.truncated ||= previous.truncated === true;
    if (object(manifest.source) && manifest.source.kind === 'sse')
      result.quality.loss.known = false;
    if (manifest.termination !== 'duration' && manifest.termination !== 'eof')
      result.quality.truncated = true;
    result.conditions = object(manifest.conditions) ? manifest.conditions : null;
  }
  return result;
}

/** @param {Summary} summary */
export function evidenceProblems(summary) {
  const reasons = [];
  const q = summary.quality;
  if (!summary.counts.samples && !summary.counts.windows) reasons.push('no runtime metrics');
  if (summary.period.durationMs <= 0) reasons.push('no measurement interval');
  if (q.invalidRecords) reasons.push('invalid records');
  if (q.truncated) reasons.push('capture was truncated');
  if (q.gaps) reasons.push('measurement gaps');
  if (!q.loss.known) reasons.push('record loss is unknown');
  if (q.loss.resets) reasons.push('loss counters reset');
  if (q.loss.delta.samples || q.loss.delta.spans) reasons.push('records were dropped');
  if (summary.requests.outsidePeriod) reasons.push('request evidence outside runtime interval');
  const { format, samplingIntervalMs, observedIntervalMs } = summary.coverage;
  if (
    format === 'samples' &&
    samplingIntervalMs !== null &&
    observedIntervalMs !== null &&
    !matchesCoverage(observedIntervalMs, samplingIntervalMs)
  )
    reasons.push('sampling interval differs from observed sample spacing');
  return reasons;
}

// Relative tolerance accepts minor scheduling jitter without allowing a whole missing
// interval in a short recording. It applies to durations, sample coverage and spacing.
const COVERAGE_TOLERANCE = 0.05;

/** @param {number} observed @param {number} expected */
function matchesCoverage(observed, expected) {
  return Math.abs(observed - expected) <= Math.max(observed, expected) * COVERAGE_TOLERANCE;
}

/** @param {Summary} summary */
function coverageProblems(summary) {
  /** @type {string[]} */ const reasons = [];
  const conditions = summary.conditions;
  if (!conditions) return reasons;
  const expectedDuration = conditions.durationMs;
  const expectedInterval = conditions.intervalMs;
  if (
    typeof expectedDuration !== 'number' ||
    !Number.isSafeInteger(expectedDuration) ||
    expectedDuration <= 0
  )
    reasons.push('invalid condition: durationMs');
  else {
    if (!matchesCoverage(summary.period.durationMs, expectedDuration))
      reasons.push('recorded duration differs from declared durationMs');
    if (
      summary.coverage.format === 'samples' &&
      summary.coverage.samplingIntervalMs !== null &&
      !matchesCoverage(
        summary.coverage.sampleCount * summary.coverage.samplingIntervalMs,
        expectedDuration,
      )
    )
      reasons.push('recorded sample coverage differs from declared durationMs');
  }
  if (
    typeof expectedInterval !== 'number' ||
    !Number.isSafeInteger(expectedInterval) ||
    expectedInterval <= 0
  )
    reasons.push('invalid condition: intervalMs');
  else if (
    summary.coverage.format === 'samples' &&
    expectedInterval !== summary.coverage.samplingIntervalMs
  )
    reasons.push('recorded sampling interval differs from declared intervalMs');
  return reasons;
}

/** @param {Summary} before @param {Summary} after */
export function compareSummaries(before, after) {
  const reasons = [
    ...evidenceProblems(before).map((r) => 'before: ' + r),
    ...evidenceProblems(after).map((r) => 'after: ' + r),
    ...coverageProblems(before).map((r) => 'before: ' + r),
    ...coverageProblems(after).map((r) => 'after: ' + r),
  ];
  if (!matchesCoverage(before.period.durationMs, after.period.durationMs))
    reasons.push('different recorded measurement durations');
  if (
    before.coverage.format === 'samples' &&
    after.coverage.format === 'samples' &&
    !matchesCoverage(before.coverage.sampleCount, after.coverage.sampleCount)
  )
    reasons.push('different recorded sample coverage');
  const keys = [
    'workload',
    'concurrency',
    'requests',
    'warmupMs',
    'durationMs',
    'nodeVersion',
    'machine',
    'intervalMs',
    'windowMs',
  ];
  if (!before.conditions || !after.conditions) reasons.push('measurement conditions are missing');
  else {
    for (const key of keys) {
      if (before.conditions[key] === undefined || after.conditions[key] === undefined)
        reasons.push('missing condition: ' + key);
      else if (JSON.stringify(before.conditions[key]) !== JSON.stringify(after.conditions[key]))
        reasons.push('different condition: ' + key);
    }
  }
  /** @type {Record<string, {before: number | null, after: number | null, delta: number | null, percent: number | null}>} */ const deltas =
    {};
  for (const key of new Set([...Object.keys(before.metrics), ...Object.keys(after.metrics)])) {
    const a = before.metrics[key] ?? null;
    const b = after.metrics[key] ?? null;
    deltas[key] = {
      before: a,
      after: b,
      delta: a === null || b === null ? null : b - a,
      percent: a === null || b === null ? null : percentage(a, b),
    };
  }
  return {
    schemaVersion: 1,
    command: 'compare',
    comparable: reasons.length === 0,
    verdict: reasons.length ? 'inconclusive' : 'requires-goal-assessment',
    reasons,
    deltas,
    before,
    after,
  };
}
