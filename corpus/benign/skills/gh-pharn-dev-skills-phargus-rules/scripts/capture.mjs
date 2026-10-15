import { mkdir, open, readFile, unlink } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import {
  lines,
  parseRecord,
  fileEvents,
  quality,
  qualityTracker,
  object,
  samplingInterval,
} from './records.mjs';

/** @typedef {import('./types.js').Event} Event */
/** @typedef {import('./types.js').CaptureManifest} CaptureManifest */

// Live capture is bounded by the network and memory; file reads have no default event limit.
export const LIVE_MAX_EVENTS = 10_000;

/** @param {Event} record */
export function eventEnd(record) {
  switch (record.event) {
    case 'sample':
      return record.data.timestamp;
    case 'window':
      return record.data.end;
    case 'span':
      return record.data.startTimeMs + record.data.durationNs / 1_000_000;
    case 'alert':
      return record.data.windowEnd;
  }
}

/** @param {string} source */
export function safeUrl(source) {
  const url = new URL(source);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password)
    throw new Error('use an HTTP(S) URL without embedded credentials');
  url.search = '';
  url.hash = '';
  return url.href;
}

/** @param {string} source @param {CaptureManifest} manifest @param {{durationMs: number, maxEvents: number, token?: string, signal?: AbortSignal}} options */
export async function* sseEvents(source, manifest, options) {
  safeUrl(source);
  const controller = new AbortController();
  const stop = () => controller.abort(new Error('capture interrupted'));
  options.signal?.addEventListener('abort', stop, { once: true });
  let expired = false;
  const timer = setTimeout(() => {
    expired = true;
    controller.abort();
  }, options.durationMs);
  let received = 0;
  let bytes = 0;
  try {
    const response = await fetch(source, {
      signal: controller.signal,
      redirect: 'error',
      headers: {
        accept: 'text/event-stream',
        ...(options.token ? { authorization: 'Bearer ' + options.token } : {}),
      },
    });
    if (!response.ok) throw new Error('SSE endpoint returned HTTP ' + response.status);
    if (
      !response.headers.get('content-type')?.toLowerCase().startsWith('text/event-stream') ||
      !response.body
    )
      throw new Error('endpoint is not an SSE stream');
    const connectedAt = Date.now();
    let event = '';
    /** @type {string[]} */ let data = [];
    async function* chunks() {
      for await (const chunk of /** @type {AsyncIterable<Uint8Array>} */ (response.body)) {
        bytes += chunk.byteLength;
        if (bytes > 64 * 1024 * 1024) throw new Error('SSE capture exceeds 64 MiB');
        yield Buffer.from(chunk);
      }
    }
    for await (const line of lines(chunks())) {
      if (line === '') {
        if (!data.length) {
          event = '';
          continue;
        }
        /** @type {unknown} */ let payload;
        try {
          payload = JSON.parse(data.join('\n'));
        } catch {
          payload = null;
        }
        // An SSE message without an event field has type "message": classify the payload itself.
        const record = parseRecord(event ? { event, data: payload } : payload);
        event = '';
        data = [];
        if (!record || record.event === 'sample') {
          manifest.quality.invalidRecords += 1;
          continue;
        }
        received += 1;
        if (eventEnd(record) <= connectedAt) manifest.historyEvents += 1;
        else manifest.observedEvents += 1;
        yield record;
        if (received >= options.maxEvents) {
          manifest.quality.truncated = true;
          manifest.termination = 'limit';
          return;
        }
      } else if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
      // Comments, ids, retry fields and heartbeats contain no metric payload.
    }
    if (data.length) manifest.quality.invalidRecords += 1;
    manifest.termination = 'disconnected';
    manifest.quality.truncated = true;
  } catch (error) {
    if (expired) manifest.termination = 'duration';
    else if (options.signal?.aborted) {
      manifest.termination = 'interrupted';
      manifest.quality.truncated = true;
    } else {
      manifest.termination = 'error';
      manifest.quality.truncated = true;
      throw error;
    }
  } finally {
    clearTimeout(timer);
    controller.abort();
    options.signal?.removeEventListener('abort', stop);
  }
}

/** @param {{file?: string, url?: string, out: string, durationMs?: number, maxEvents?: number, intervalMs?: number, token?: string, conditions?: string, allowLogs?: boolean, signal?: AbortSignal}} options */
export async function capture(options) {
  if (options.token && /[^\x21-\x7e]/.test(options.token))
    throw new Error('bearer token must contain visible ASCII characters without whitespace');
  if (Boolean(options.file) === Boolean(options.url))
    throw new Error('capture requires exactly one of --file or --url');
  const location = options.url
    ? safeUrl(options.url)
    : resolve(/** @type {string} */ (options.file));
  const out = resolve(options.out);
  await mkdir(out, { recursive: true });
  /** @type {Record<string, unknown> | undefined} */ let conditions;
  if (options.conditions) {
    /** @type {unknown} */ const input = JSON.parse(await readFile(options.conditions, 'utf8'));
    if (!object(input)) throw new Error('conditions must be a JSON object');
    conditions = input;
  }
  const { intervalMs } = samplingInterval(options.intervalMs, conditions);
  const eventsPath = join(out, 'events.ndjson');
  const manifestPath = join(out, 'manifest.json');
  // Reserve both artifacts; never replace a previous measurement.
  const manifestHandle = await open(manifestPath, 'wx', 0o600);
  let output;
  try {
    output = await open(eventsPath, 'wx', 0o600);
  } catch (error) {
    await manifestHandle.close();
    // Remove only the empty manifest reserved above so a retry is not blocked by it.
    await unlink(manifestPath);
    throw error;
  }
  /** @type {CaptureManifest} */ const manifest = {
    schemaVersion: 1,
    source: {
      kind: options.url ? 'sse' : 'file',
      location,
    },
    startedAt: new Date().toISOString(),
    endedAt: '',
    events: 0,
    historyEvents: 0,
    observedEvents: 0,
    termination: 'eof',
    quality: quality(),
    ...(conditions ? { conditions } : {}),
    intervalMs,
  };
  const tracker = qualityTracker(manifest.quality, intervalMs);
  let failure;
  try {
    const records = options.url
      ? sseEvents(options.url, manifest, {
          durationMs: options.durationMs ?? 30_000,
          maxEvents: options.maxEvents ?? LIVE_MAX_EVENTS,
          token: options.token,
          signal: options.signal,
        })
      : fileEvents(/** @type {string} */ (options.file), manifest.quality, options);
    for await (const record of records) {
      tracker.add(record);
      manifest.events += 1;
      if (!options.url) manifest.historyEvents += 1;
      await output.write(JSON.stringify(record) + '\n');
    }
    if (!manifest.events) throw new Error('capture contains no valid Phargus events');
    if (manifest.quality.truncated && manifest.termination === 'eof')
      manifest.termination = 'limit';
    if (manifest.termination === 'disconnected')
      throw new Error('SSE connection ended before the observation duration');
  } catch (error) {
    failure = error;
    if (manifest.termination === 'eof') manifest.termination = 'error';
  } finally {
    manifest.endedAt = new Date().toISOString();
    await output.close();
    await manifestHandle.writeFile(
      JSON.stringify(
        {
          ...manifest,
          historyClassification:
            'event-time-before-connection; estimate, SSE has no history marker',
        },
        null,
        2,
      ) + '\n',
    );
    await manifestHandle.close();
  }
  if (failure) throw failure;
  return { schemaVersion: 1, command: 'capture', eventsPath, manifestPath, manifest };
}
