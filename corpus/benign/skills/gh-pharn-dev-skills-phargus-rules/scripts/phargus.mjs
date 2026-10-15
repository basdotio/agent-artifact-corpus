import { parseArgs } from 'node:util';
import { doctor } from './upstream.mjs';
import { capture } from './capture.mjs';
import { summarizeFile, compareSummaries } from './summary.mjs';
import { collect, heap, replayRules } from './operations.mjs';

const commands = ['doctor', 'collect', 'capture', 'summarize', 'compare', 'heap', 'rules'];
/** @param {string[]} args */
export async function main(args) {
  const { values, positionals } = parseArgs({
    args,
    allowPositionals: true,
    options: {
      project: { type: 'string' },
      'phargus-package': { type: 'string' },
      file: { type: 'string' },
      url: { type: 'string' },
      out: { type: 'string' },
      manifest: { type: 'string' },
      conditions: { type: 'string' },
      before: { type: 'string' },
      after: { type: 'string' },
      'before-manifest': { type: 'string' },
      'after-manifest': { type: 'string' },
      'duration-ms': { type: 'string' },
      'max-events': { type: 'string' },
      'interval-ms': { type: 'string' },
      'window-ms': { type: 'string' },
      capacity: { type: 'string' },
      host: { type: 'string' },
      port: { type: 'string' },
      'token-env': { type: 'string' },
      mode: { type: 'string' },
      rules: { type: 'string' },
      sinks: { type: 'string' },
      'allowed-host': { type: 'string', multiple: true },
      follow: { type: 'boolean' },
      'allow-logs': { type: 'boolean' },
      help: { type: 'boolean' },
    },
  });
  const command = positionals[0];
  if (values.help || command === 'help' || !command)
    return {
      schemaVersion: 1,
      command: 'help',
      commands,
      usage: 'node <skill-dir>/scripts/phargus.mjs <command> [options]',
      required: {
        doctor: '--project',
        collect: '--project --file',
        capture: '--file|--url --out',
        summarize: '--file',
        compare: '--before --after',
        heap: '--project --file|--before+--after',
        rules: '--project --file --rules --mode alerts|sandbox',
      },
    };
  if (positionals.length !== 1 || !commands.includes(command))
    throw new Error('unknown command: ' + command);
  /** @param {keyof typeof values} key */
  const required = (key) => {
    const value = values[key];
    if (typeof value !== 'string' || !value) throw new Error('--' + key + ' is required');
    return value;
  };
  /** @param {keyof typeof values} key @param {number | undefined} fallback @param {number} [min] */
  const number = (key, fallback, min = 1) => {
    const value = values[key];
    if (value === undefined) return fallback;
    if (
      typeof value !== 'string' ||
      !/^\d+$/.test(value) ||
      !Number.isSafeInteger(Number(value)) ||
      Number(value) < min
    )
      throw new Error('--' + key + ' must be an integer >= ' + min);
    return Number(value);
  };
  let token;
  if (values['token-env']) {
    token = process.env[values['token-env']];
    if (!token) throw new Error('the token environment variable is empty');
  }
  const packageName = values['phargus-package'];
  const options = {
    // Undefined: live capture and rules replay stop at 10,000 events; other file reads do not.
    maxEvents: number('max-events', undefined),
    allowLogs: values['allow-logs'],
    // Undefined lets capture/summarize use declared conditions.intervalMs, then 1000.
    intervalMs: number('interval-ms', undefined),
  };
  const controller = new AbortController();
  const stop = () => controller.abort();
  process.once('SIGINT', stop);
  process.once('SIGTERM', stop);
  try {
    switch (command) {
      case 'doctor':
        return await doctor(required('project'), packageName);
      case 'collect':
        return await collect({
          project: required('project'),
          packageName,
          file: required('file'),
          follow: values.follow,
          allowLogs: values['allow-logs'],
          host: values.host,
          port: number('port', 7070, 0),
          windowMs: number('window-ms', 1000),
          capacity: number('capacity', 300),
          durationMs: number('duration-ms', undefined),
          token,
          alerts: values.rules,
          sinks: values.sinks,
          allowedHosts: values['allowed-host'],
          signal: controller.signal,
        });
      case 'capture':
        return await capture({
          ...options,
          file: values.file,
          url: values.url,
          out: required('out'),
          conditions: values.conditions,
          durationMs: number('duration-ms', 30_000),
          token,
          signal: controller.signal,
        });
      case 'summarize':
        return await summarizeFile(required('file'), { ...options, manifest: values.manifest });
      case 'compare':
        return compareSummaries(
          await summarizeFile(required('before'), {
            ...options,
            manifest: values['before-manifest'],
          }),
          await summarizeFile(required('after'), {
            ...options,
            manifest: values['after-manifest'],
          }),
        );
      case 'heap':
        return await heap({
          project: required('project'),
          packageName,
          file: values.file,
          before: values.before,
          after: values.after,
        });
      case 'rules':
        return await replayRules({
          project: required('project'),
          packageName,
          file: required('file'),
          rules: required('rules'),
          mode: values.mode ?? 'alerts',
          windowMs: number('window-ms', 1000),
          maxEvents: options.maxEvents,
        });
    }
  } finally {
    process.removeListener('SIGINT', stop);
    process.removeListener('SIGTERM', stop);
  }
}

// This file is the executable entry point; module helpers are imported separately in tests.
main(process.argv.slice(2))
  .then((result) => {
    process.stdout.write(JSON.stringify(result, null, 2) + '\n');
    if (result && 'ok' in result && result.ok === false) process.exitCode = 1;
  })
  .catch((error) => {
    process.stderr.write(
      JSON.stringify({
        schemaVersion: 1,
        error: { message: error instanceof Error ? error.message : String(error) },
      }) + '\n',
    );
    process.exitCode = 1;
  });
