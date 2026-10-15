import { createReadStream } from 'node:fs';
import { StringDecoder } from 'node:string_decoder';

/** @typedef {import('./types.js').Event} Event */
/** @typedef {import('./types.js').Quality} Quality */

/** @param {unknown} value @returns {value is Record<string, unknown>} */
export function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/** @param {unknown} value @param {string} key @returns {unknown} */
export function at(value, key) {
  for (const part of key.split('.')) {
    if (!object(value)) return undefined;
    value = value[part];
  }
  return value;
}

/** @param {unknown} value @returns {value is number} */
export function integer(value) {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

/** @param {unknown} value @param {string[]} paths */
function integers(value, paths) {
  return paths.every((key) => integer(at(value, key)));
}

const shared = [
  'eventLoop.max',
  'eventLoop.p99',
  'eventLoop.mean',
  'gc.count',
  'gc.totalPause',
  'gc.maxPause',
  'backpressure.events',
  'backpressure.totalStall',
  'backpressure.maxStall',
];

/** Validate wire data, retaining extra upstream fields. @param {unknown} raw @returns {Event | null} */
export function parseRecord(raw) {
  if (!object(raw)) return null;
  const envelope = typeof raw.event === 'string' && object(raw.data);
  const data = envelope ? raw.data : raw;
  if (!object(data)) return null;
  let kind = envelope
    ? raw.event
    : data.type === 'span'
      ? 'span'
      : Object.hasOwn(data, 'timestamp')
        ? 'sample'
        : Object.hasOwn(data, 'start')
          ? 'window'
          : Object.hasOwn(data, 'ruleId')
            ? 'alert'
            : '';
  if (kind === 'sample') {
    if (
      !integers(data, [
        'timestamp',
        ...shared,
        'eventLoop.min',
        'eventLoop.p50',
        'memory.heapUsed',
        'memory.heapTotal',
        'memory.rss',
        'memory.external',
        'memory.arrayBuffers',
      ])
    )
      return null;
    if (data.dropped !== undefined && !integers(data.dropped, ['samples', 'spans'])) return null;
    const hotspots = at(data, 'backpressure.hotspots');
    if (
      hotspots !== undefined &&
      (!Array.isArray(hotspots) ||
        !hotspots.every(
          (h) =>
            typeof at(h, 'site') === 'string' && integers(h, ['events', 'totalStall', 'maxStall']),
        ))
    )
      return null;
  } else if (kind === 'window') {
    if (
      !integers(data, [
        'start',
        'end',
        'count',
        'late',
        ...shared,
        'memory.heapUsedLast',
        'memory.heapUsedMax',
        'memory.rssLast',
        'memory.rssMax',
      ]) ||
      Number(data.end) <= Number(data.start)
    )
      return null;
  } else if (kind === 'span') {
    if (
      !integers(data, ['startTimeMs', 'durationNs', 'statusCode']) ||
      !['traceId', 'spanId', 'name', 'method', 'path'].every((key) => typeof data[key] === 'string')
    )
      return null;
  } else if (kind === 'alert') {
    if (
      !integers(data, ['threshold', 'observed', 'windowStart', 'windowEnd']) ||
      typeof data.ruleId !== 'string' ||
      typeof data.metric !== 'string' ||
      !['>', '>='].includes(String(data.comparison)) ||
      !['firing', 'resolved'].includes(String(data.state))
    )
      return null;
  } else {
    return null;
  }
  // The discriminated payload has been structurally validated above.
  return /** @type {Event} */ ({ event: kind, data });
}

/** @returns {Quality} */
export function quality() {
  return {
    invalidRecords: 0,
    ignoredLogs: 0,
    truncated: false,
    gaps: 0,
    loss: { known: false, initial: null, delta: { samples: 0, spans: 0 }, resets: 0 },
  };
}

/** @param {AsyncIterable<Buffer | string>} input */
export async function* lines(input) {
  const decoder = new StringDecoder('utf8');
  let pending = '';
  for await (const chunk of input) {
    pending += typeof chunk === 'string' ? chunk : decoder.write(chunk);
    let end;
    while ((end = pending.indexOf('\n')) !== -1) {
      const line = pending.slice(0, end).replace(/\r$/, '');
      if (Buffer.byteLength(line) > 1024 * 1024) throw new Error('input line exceeds 1 MiB');
      yield line;
      pending = pending.slice(end + 1);
    }
    if (Buffer.byteLength(pending) > 1024 * 1024) throw new Error('input line exceeds 1 MiB');
  }
  pending += decoder.end();
  if (pending.trim()) yield pending.replace(/\r$/, '');
}

const phargusKeys = ['timestamp', 'event', 'type', 'eventLoop', 'ruleId', 'start'];

/** @param {string} line @returns {{kind: 'record', record: Event} | {kind: 'empty' | 'log' | 'invalid'}} */
export function classifyLine(line) {
  if (!line.trim()) return { kind: 'empty' };
  /** @type {unknown} */ let raw;
  try {
    raw = JSON.parse(line);
  } catch {
    // Preserve malformed Phargus JSON as corrupt data even when unrelated text logs are allowed.
    const looksLikePhargus =
      line.trimStart().startsWith('{') &&
      /"(?:timestamp|event|type|eventLoop|ruleId|start)"\s*:/.test(line);
    return { kind: looksLikePhargus ? 'invalid' : 'log' };
  }
  const record = parseRecord(raw);
  if (record) return { kind: 'record', record };
  const looksLikePhargus = object(raw) && phargusKeys.some((key) => Object.hasOwn(raw, key));
  return { kind: looksLikePhargus ? 'invalid' : 'log' };
}

/**
 * Streams a whole file unless maxEvents is given: a file is already bounded and summarizing
 * it is fast, so a default cap would only truncate evidence. Live SSE keeps its own limit.
 * @param {string} path @param {Quality} status @param {{maxEvents?: number, allowLogs?: boolean}} [options]
 */
export async function* fileEvents(path, status, options = {}) {
  const stream = createReadStream(path, { highWaterMark: 64 * 1024 });
  let count = 0;
  try {
    for await (const line of lines(stream)) {
      const classified = classifyLine(line);
      if (classified.kind === 'empty') continue;
      if (classified.kind !== 'record') {
        if (options.allowLogs && classified.kind === 'log') status.ignoredLogs += 1;
        else status.invalidRecords += 1;
        continue;
      }
      if (count >= (options.maxEvents ?? Infinity)) {
        status.truncated = true;
        break;
      }
      count += 1;
      yield classified.record;
    }
  } finally {
    stream.destroy();
  }
}

/** @param {unknown} value @returns {value is number} */
function positiveInteger(value) {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
}

/**
 * Raw sample interval: explicit flag, then the interval a capture recorded in its manifest,
 * then declared conditions.intervalMs, then 1000.
 * @param {number | undefined} explicit @param {unknown} conditions @param {unknown} [recorded]
 * @returns {{intervalMs: number, source: import('./types.js').IntervalSource}}
 */
export function samplingInterval(explicit, conditions, recorded) {
  if (explicit !== undefined) return { intervalMs: explicit, source: 'flag' };
  if (positiveInteger(recorded)) return { intervalMs: recorded, source: 'manifest' };
  const declared = at(conditions, 'intervalMs');
  if (positiveInteger(declared)) return { intervalMs: declared, source: 'conditions' };
  return { intervalMs: 1000, source: 'default' };
}

/** @param {Quality} status @param {number} intervalMs */
export function qualityTracker(status, intervalMs) {
  /** @type {{samples: number, spans: number} | undefined} */ let previousLoss;
  /** @type {number | undefined} */ let previousSample;
  /** @type {number | undefined} */ let previousWindowEnd;
  let samples = 0;
  let withLoss = 0;
  return {
    /** @param {Event} record */
    add(record) {
      if (record.event === 'sample') {
        samples += 1;
        const { timestamp, dropped } = record.data;
        if (
          previousSample !== undefined &&
          (timestamp <= previousSample || timestamp - previousSample > intervalMs * 1.5)
        )
          status.gaps += 1;
        previousSample = timestamp;
        if (dropped) {
          withLoss += 1;
          status.loss.initial ??= { ...dropped };
          if (previousLoss) {
            // After a counter reset the producer restarted from 0, so its current counters are
            // all records dropped since the restart.
            const reset =
              dropped.samples < previousLoss.samples || dropped.spans < previousLoss.spans;
            if (reset) status.loss.resets += 1;
            const base = reset ? { samples: 0, spans: 0 } : previousLoss;
            status.loss.delta.samples = Math.min(
              Number.MAX_SAFE_INTEGER,
              status.loss.delta.samples + dropped.samples - base.samples,
            );
            status.loss.delta.spans = Math.min(
              Number.MAX_SAFE_INTEGER,
              status.loss.delta.spans + dropped.spans - base.spans,
            );
          }
          previousLoss = dropped;
        }
      } else if (record.event === 'window') {
        if (previousWindowEnd !== undefined && record.data.start !== previousWindowEnd)
          status.gaps += 1;
        previousWindowEnd = record.data.end;
      }
      status.loss.known = samples > 0 && withLoss === samples;
    },
  };
}
