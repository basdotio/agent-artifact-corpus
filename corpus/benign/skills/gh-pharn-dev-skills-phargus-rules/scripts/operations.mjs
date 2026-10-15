import { open, stat, readFile } from 'node:fs/promises';
import { setTimeout as sleep } from 'node:timers/promises';
import { pipeline } from 'node:stream/promises';
import { fileEvents, lines, classifyLine, quality, object } from './records.mjs';
import { resolvePhargus } from './upstream.mjs';

/** @typedef {import('./types.js').Event} Event */
/** @typedef {import('./types.js').Window} Window */
/** @typedef {import('./types.js').Rule} Rule */

/** @param {string} path @param {AbortSignal} signal */
async function* tail(path, signal) {
  const handle = await open(path, 'r');
  const identity = await handle.stat();
  let position = 0;
  // One scratch buffer for the whole tail. Reuse is safe because the only consumer, lines(),
  // decodes each yielded chunk synchronously (StringDecoder copies any partial character)
  // before it asks this generator for the next read.
  const buffer = Buffer.alloc(64 * 1024);
  try {
    while (!signal.aborted) {
      const current = await stat(path);
      if (current.ino !== identity.ino || current.size < position)
        throw new Error('NDJSON input was rotated or truncated; start a new collection');
      const { bytesRead } = await handle.read(buffer, 0, buffer.length, position);
      if (bytesRead) {
        position += bytesRead;
        yield buffer.subarray(0, bytesRead);
      } else {
        try {
          await sleep(100, undefined, { signal });
        } catch (error) {
          if (!signal.aborted) throw error;
        }
      }
    }
  } finally {
    await handle.close();
  }
}

/** @param {string} path @param {AbortSignal} signal @param {import('./types.js').Quality} status @param {boolean} allowLogs */
async function* following(path, signal, status, allowLogs) {
  for await (const line of lines(tail(path, signal))) {
    const classified = classifyLine(line);
    if (classified.kind === 'empty') continue;
    if (classified.kind === 'record') yield classified.record;
    else if (allowLogs && classified.kind === 'log') status.ignoredLogs += 1;
    else {
      status.invalidRecords += 1;
      throw new Error('invalid NDJSON record while collecting');
    }
  }
}

const SINK_TYPES = ['file', 'webhook'];

/**
 * Read collector alert sink configs. Only file and webhook sinks are accepted: a stdout sink
 * would interleave alert lines with this helper's JSON result.
 * @param {string} path @returns {Promise<Record<string, unknown>[]>}
 */
export async function readSinks(path) {
  /** @type {unknown} */ const input = JSON.parse(await readFile(path, 'utf8'));
  if (!Array.isArray(input) || !input.length)
    throw new Error('--sinks must be a non-empty JSON array of sink configs');
  return input.map((entry, index) => {
    if (!object(entry) || !SINK_TYPES.includes(String(entry.type)))
      throw new Error('sink ' + index + ': type must be file or webhook');
    return entry;
  });
}

/** @param {Record<string, unknown>[]} sinks */
function describeSinks(sinks) {
  // Never echo paths or webhook URLs: a URL can carry credentials.
  return sinks.map((sink) => ({
    type: String(sink.type),
    ...(typeof sink.name === 'string' ? { name: sink.name } : {}),
  }));
}

/** @param {{project: string, packageName?: string, file: string, follow?: boolean, allowLogs?: boolean, host?: string, port?: number, windowMs?: number, capacity?: number, durationMs?: number, token?: string, alerts?: string, sinks?: string, allowedHosts?: string[], signal?: AbortSignal}} options */
export async function collect(options) {
  // Read and validate inputs before arming the duration timer and abort listener, so a bad
  // --alerts or --sinks file fails fast instead of leaving a pending timer behind.
  /** @type {Rule[] | undefined} */ const alerts = options.alerts
    ? JSON.parse(await readFile(options.alerts, 'utf8'))
    : undefined;
  const sinks = options.sinks ? await readSinks(options.sinks) : undefined;
  const upstream = await resolvePhargus(options.project, options.packageName);
  const collectorApi = /** @type {unknown} */ (upstream.load('collector', ['createCollector']));
  const dashboardApi = /** @type {unknown} */ (
    upstream.load('dashboard', ['createDashboardServer'])
  );
  const { createCollector } = /** @type {import('./types.js').CollectorModule} */ (collectorApi);
  const { createDashboardServer } = /** @type {import('./types.js').DashboardModule} */ (
    dashboardApi
  );
  let sinkErrors = 0;
  const collector = createCollector({
    windowMs: options.windowMs ?? 1000,
    capacity: options.capacity ?? 300,
    alerts,
    ...(sinks
      ? {
          sinks,
          /** @param {Error} error */
          onSinkError: (error) => {
            sinkErrors += 1;
            process.stderr.write(
              JSON.stringify({ event: 'sink-error', message: error.message }) + '\n',
            );
          },
        }
      : {}),
  });
  // Arm the timer and abort listener only right before the region whose finally clears them;
  // createCollector can still throw (for example on invalid alert rules).
  const controller = new AbortController();
  const stop = () => controller.abort();
  options.signal?.addEventListener('abort', stop, { once: true });
  if (options.signal?.aborted) stop();
  const timer = options.durationMs ? setTimeout(stop, options.durationMs) : undefined;
  let dashboard;
  const status = quality();
  try {
    dashboard = await createDashboardServer({
      collector,
      host: options.host ?? '127.0.0.1',
      port: options.port ?? 7070,
      token: options.token,
      ...(options.allowedHosts?.length ? { allowedHosts: options.allowedHosts } : {}),
    });
    process.stderr.write(
      JSON.stringify({ event: 'ready', url: dashboard.url, pid: process.pid }) + '\n',
    );
    const input = options.follow
      ? following(options.file, controller.signal, status, options.allowLogs ?? false)
      : fileEvents(options.file, status, {
          maxEvents: Number.MAX_SAFE_INTEGER,
          allowLogs: options.allowLogs,
        });
    async function* samples() {
      for await (const record of input) {
        if (controller.signal.aborted) break;
        if (record.event === 'sample') yield record.data;
        else if (record.event === 'span')
          yield { ...record.data, type: /** @type {const} */ ('span') };
        else
          throw new Error(
            'collect accepts raw samples and spans; use capture for persisted windows',
          );
      }
    }
    await collector.consume(samples());
    if (status.invalidRecords) throw new Error('invalid input records: ' + status.invalidRecords);
    if (!controller.signal.aborted)
      await new Promise((resolve) =>
        controller.signal.addEventListener('abort', resolve, { once: true }),
      );
    return {
      schemaVersion: 1,
      command: 'collect',
      url: dashboard.url,
      windows: collector.windows.snapshot().length,
      spans: collector.spans.snapshot().length,
      alerts: collector.alerts.snapshot().length,
      sinks: sinks ? describeSinks(sinks) : [],
      sinkErrors,
      allowedHosts: options.allowedHosts ?? [],
      quality: status,
    };
  } finally {
    stop();
    if (timer) clearTimeout(timer);
    options.signal?.removeEventListener('abort', stop);
    await dashboard?.close();
    await collector.close();
  }
}

/**
 * Unlike summarize, replay buffers every record and may run sandboxed code per window, so it
 * keeps a 10,000-event default; --max-events raises it.
 * @param {string} file @param {import('./types.js').CollectorModule} api @param {number} windowMs @param {number} [maxEvents] @returns {Promise<Window[]>}
 */
export async function readWindows(file, api, windowMs, maxEvents = 10_000) {
  /** @type {Window[]} */ const windows = [];
  /** @type {import('./types.js').Sample[]} */ const samples = [];
  const status = quality();
  for await (const record of fileEvents(file, status, { maxEvents })) {
    if (record.event === 'window') windows.push(record.data);
    else if (record.event === 'sample') samples.push(record.data);
  }
  if (status.invalidRecords || status.truncated)
    throw new Error('rule replay requires valid, untruncated input');
  if (windows.length && samples.length)
    throw new Error('rule replay cannot combine raw samples with already aggregated windows');
  if (samples.length) {
    await pipeline(samples, api.createWindowAggregator({ windowMs }), async (output) => {
      for await (const window of output) windows.push(/** @type {Window} */ (window));
    });
  }
  if (!windows.length) throw new Error('no windows available for rule replay');
  return windows;
}

/** @param {{project: string, packageName?: string, file: string, mode: string, rules: string, windowMs?: number, maxEvents?: number}} options */
export async function replayRules(options) {
  if (options.mode !== 'alerts' && options.mode !== 'sandbox')
    throw new Error('--mode must be alerts or sandbox');
  const upstream = await resolvePhargus(options.project, options.packageName);
  const api = /** @type {import('./types.js').CollectorModule} */ (
    /** @type {unknown} */ (
      upstream.load('collector', ['createWindowAggregator', 'createAlertEvaluator'])
    )
  );
  const windows = await readWindows(options.file, api, options.windowMs ?? 1000, options.maxEvents);
  if (options.mode === 'alerts') {
    /** @type {Rule[]} */ const rules = JSON.parse(await readFile(options.rules, 'utf8'));
    /** @type {import('./types.js').Alert[]} */ const alerts = [];
    await pipeline(windows, api.createAlertEvaluator(rules), async (output) => {
      for await (const alert of output)
        alerts.push(/** @type {import('./types.js').Alert} */ (alert));
    });
    return {
      schemaVersion: 1,
      command: 'rules',
      mode: 'alerts',
      ok: true,
      windows: windows.length,
      alerts,
    };
  }
  const plugins = /** @type {import('./types.js').PluginModule} */ (
    /** @type {unknown} */ (
      upstream.load('plugin-runner', ['createPluginRunner', 'loadRulesDirectory', 'runRules'])
    )
  );
  const loaded = await plugins.loadRulesDirectory(options.rules);
  if (!loaded.ok) throw new Error(loaded.error.code + ': ' + loaded.error.message);
  if (loaded.failures.length) throw new Error('some rule files could not be loaded');
  if (!loaded.rules.length) throw new Error('no .js rules found');
  const runner = plugins.createPluginRunner();
  try {
    const results = await plugins.runRules(runner, loaded.rules, windows);
    return {
      schemaVersion: 1,
      command: 'rules',
      mode: 'sandbox',
      ok: Object.values(results).every((result) => result.ok),
      windows: windows.length,
      results,
    };
  } finally {
    await runner.close();
  }
}

/** @param {{project: string, packageName?: string, file?: string, before?: string, after?: string}} options */
export async function heap(options) {
  const upstream = await resolvePhargus(options.project, options.packageName);
  const api = /** @type {import('./types.js').AnalyzerModule} */ (
    /** @type {unknown} */ (
      upstream.load('analyzer', ['summarizeHeapSnapshot', 'diffHeapSnapshots'])
    )
  );
  if (options.file && !options.before && !options.after)
    return {
      schemaVersion: 1,
      command: 'heap',
      mode: 'summary',
      result: await api.summarizeHeapSnapshot(options.file),
      limitations: ['self size and object-name counts, not retained size or retaining paths'],
    };
  if (options.before && options.after && !options.file)
    return {
      schemaVersion: 1,
      command: 'heap',
      mode: 'diff',
      result: await api.diffHeapSnapshots(options.before, options.after),
      limitations: ['a size/count increase does not prove a leak'],
    };
  throw new Error('heap requires --file or both --before and --after');
}
