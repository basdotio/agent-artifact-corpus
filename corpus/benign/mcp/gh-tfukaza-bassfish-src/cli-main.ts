import { daemonDiagnostics } from './daemon-diagnostics.js';
import { archiveData } from './data-reset.js';
import { access } from 'node:fs/promises';
import { resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { BassfishError, requireThat } from './domain.js';
import {
  dataDirectory,
  defaultRuntimeConfig,
  loadRuntimeConfig,
  packageVersion,
  parseTurnTimeout,
  runtimeConfigSchema,
  saveRuntimeConfig,
} from './config.js';
import { connectDaemon, ensureDaemon, runDaemon } from './daemon.js';
import { runMcp } from './mcp.js';
import { runThreadCli } from './thread-cli.js';
import { setupTurso } from './setup.js';
import { requireSupportedPlatform, tursoVersion } from './storage/platform.js';
import { runNotificationWatcher } from './notifications-cli.js';
import { presentProjectCli, runProjectCli } from './project-cli.js';
import { runTicketCli } from './ticket-cli.js';
import { booleanFlag, take } from './cli-helpers.js';
import type { CliInteraction } from './cli-helpers.js';
import { commandHelp, hasCommandHelp, hasHelp } from './cli-help.js';
import { cancelledResult, CliOutput, outputOptions } from './cli-output.js';

type Health = Record<string, unknown>;

function stoppedConnection(error: unknown): boolean {
  return ['ENOENT', 'ECONNREFUSED'].includes((error as NodeJS.ErrnoException).code ?? '');
}

async function daemonHealth(data: string): Promise<Health | undefined> {
  let client;
  try {
    client = await connectDaemon(data);
    return await client.call<Health>('getHealth');
  } catch (error) {
    if (stoppedConnection(error)) return undefined;
    throw error;
  } finally {
    client?.close();
  }
}

async function waitForDaemonStop(data: string): Promise<void> {
  const deadline = performance.now() + 10_000;
  while (performance.now() < deadline) {
    try {
      if (!(await daemonHealth(data))) return;
    } catch (error) {
      // An accepted stop can close a read-only health probe before replying.
      // Probe for socket disappearance; never replay the stop operation.
      if (
        !['OUTCOME_UNKNOWN', 'CONNECTION_CLOSED', 'DAEMON_STOPPING'].includes(
          (error as { code?: string }).code ?? '',
        )
      )
        throw error;
    }
    await delay(25);
  }
  throw new BassfishError('DAEMON_STOP_FAILED', 'The daemon did not stop within 10 seconds.');
}

function helpTopic(command: string, args: string[]): string {
  const action = args.find(value => !value.startsWith('-'));
  return action ? `${command} ${action}` : command;
}

let output: CliOutput | undefined;
let activeCommand: string | undefined;

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const options = outputOptions(args);
  output = new CliOutput(options);
  const command = args.shift();
  activeCommand = command;

  if (!command || command === '--help' || command === '-h') {
    output.help(commandHelp());
    return;
  }
  if (command === 'help') {
    const topic = args.join(' ');
    requireThat(
      !topic || hasCommandHelp(topic),
      'INVALID_ARGUMENT',
      `Unknown help topic: ${topic}`,
    );
    output.help(commandHelp(topic || undefined));
    return;
  }
  if (hasHelp(args)) {
    const topic = helpTopic(command, args);
    requireThat(hasCommandHelp(topic), 'INVALID_ARGUMENT', `Unknown command: ${command}`);
    output.help(commandHelp(topic));
    return;
  }
  if (command === '--version' || command === 'version') {
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Version takes no arguments.');
    process.stdout.write(`${packageVersion}\n`);
    return;
  }

  const data = dataDirectory();
  if (command === 'sonar') {
    const { runSonar } = await import('./sonar/cli.js');
    await runSonar(args, data, options, process.argv.includes('--plain'));
    return;
  }
  if (command === 'setup') {
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Setup takes no arguments.');
    const result = await output.activity('Checking embedded Turso…', () => setupTurso(data));
    output.result({ command }, result);
    return;
  }
  if (command === 'notifications' && args.shift() === 'watch') {
    await runNotificationWatcher(args, data);
    return;
  }
  if (command === 'daemon' && args[0] === 'run') {
    args.shift();
    const rawTimeout = take(args, '--turn-timeout');
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Use daemon run [--turn-timeout DURATION].');
    await runDaemon(
      data,
      rawTimeout === undefined ? {} : { turnTimeoutMs: parseTurnTimeout(rawTimeout) },
    );
    return;
  }
  if (command === 'config') {
    const action = args.shift();
    if (action === 'show' && args.length === 0) {
      output.result({ command, action }, await loadRuntimeConfig(data));
      return;
    }
    if (action === 'reset') {
      const confirmed = booleanFlag(args, '--yes');
      requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Use config reset [--yes].');
      requireThat(
        confirmed || output.options.interactive,
        'CONFIRMATION_REQUIRED',
        'Use config reset --yes outside an interactive terminal.',
      );
      if (!confirmed && !(await output.confirm('Reset daemon timing configuration to defaults?'))) {
        output.result({ command, action, cancelled: true }, cancelledResult);
        return;
      }
      await saveRuntimeConfig(data, defaultRuntimeConfig);
      output.result({ command, action }, defaultRuntimeConfig);
      return;
    }
    if (action === 'set' && args.length === 2) {
      const [key, raw] = args;
      requireThat(
        Object.hasOwn(defaultRuntimeConfig, key!),
        'INVALID_ARGUMENT',
        'Unknown configuration key.',
      );
      requireThat(
        /^[0-9]+$/.test(raw!),
        'INVALID_ARGUMENT',
        'Configuration values are integer milliseconds.',
      );
      const next = runtimeConfigSchema.parse({
        ...(await loadRuntimeConfig(data)),
        [key!]: Number(raw),
      });
      await saveRuntimeConfig(data, next);
      output.result({ command, action }, next);
      return;
    }
    throw new BassfishError(
      'INVALID_ARGUMENT',
      'Use config show, config reset [--yes], or config set KEY MILLISECONDS.',
    );
  }
  if (command === 'data') {
    const action = args.shift();
    const confirmed = booleanFlag(args, '--yes');
    requireThat(
      action === 'reset' && args.length === 0,
      'INVALID_ARGUMENT',
      'Use data reset [--yes].',
    );
    requireThat(
      !(await daemonHealth(data)),
      'DAEMON_RUNNING',
      'Stop the Bassfish daemon before resetting preview data.',
    );
    try {
      await access(data);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
      output.result({ command, action }, { reset: false, reason: 'no_data' });
      return;
    }
    requireThat(
      confirmed || output.options.interactive,
      'CONFIRMATION_REQUIRED',
      'Use data reset --yes outside an interactive terminal.',
    );
    if (
      !confirmed &&
      !(await output.confirm('Move all Bassfish preview data to a timestamped backup?'))
    ) {
      output.result({ command, action, cancelled: true }, cancelledResult);
      return;
    }
    const backup = await archiveData(data);
    output.result({ command, action }, { reset: true, backup });
    return;
  }

  const rawDaemonTimeout = command === 'daemon' ? take(args, '--turn-timeout') : undefined;
  const daemonOverrides =
    rawDaemonTimeout === undefined ? {} : { turnTimeoutMs: parseTurnTimeout(rawDaemonTimeout) };
  const workspace = resolve(take(args, '--workspace') ?? process.cwd());
  const name = take(args, '--name');
  if (command === 'mcp') {
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown MCP argument.');
    await runMcp(workspace, data, name);
    return;
  }

  const action = args.shift();
  const valid =
    (command === 'daemon' && ['start', 'status', 'stop'].includes(action ?? '')) ||
    command === 'doctor' ||
    (command === 'turn' && ['list', 'release'].includes(action ?? '')) ||
    (command === 'thread' &&
      [
        'list',
        'create',
        'get',
        'show',
        'search',
        'rename',
        'describe',
        'follow',
        'unfollow',
        'archive',
        'activate',
        'delete',
        'retract',
        'reinstate',
        'history',
        'revision',
        'diff',
      ].includes(action ?? '')) ||
    (command === 'ticket' &&
      [
        'list',
        'search',
        'create',
        'show',
        'update',
        'edit',
        'append',
        'patch',
        'history',
        'revision',
        'diff',
      ].includes(action ?? '')) ||
    (command === 'project' && ['inspect', 'export', 'history'].includes(action ?? ''));
  requireThat(
    valid,
    'INVALID_ARGUMENT',
    `Unknown command: ${[command, action].filter(Boolean).join(' ')}`,
  );

  if (command === 'daemon') {
    requireThat(
      args.length === 0,
      'INVALID_ARGUMENT',
      'Daemon status and stop take no options; start accepts --turn-timeout DURATION.',
    );
    requireThat(
      action === 'start' || rawDaemonTimeout === undefined,
      'INVALID_ARGUMENT',
      'Only daemon start and daemon run accept --turn-timeout.',
    );
    const before = await daemonHealth(data);
    if (action === 'status') {
      output.result(
        { command, action },
        before ?? { state: 'stopped', diagnostics: daemonDiagnostics(data) },
      );
      return;
    }
    if (action === 'stop') {
      if (!before) {
        output.result({ command, action }, { stopping: false, state: 'stopped' });
        return;
      }
      let client;
      try {
        client = await connectDaemon(data);
        const result = await client.call('stopDaemon');
        client.close();
        await output.activity('Stopping daemon…', () => waitForDaemonStop(data));
        output.result({ command, action }, result);
      } catch (error) {
        if (!stoppedConnection(error)) throw error;
        output.result({ command, action }, { stopping: false, state: 'stopped' });
      } finally {
        client?.close();
      }
      return;
    }
    await output.activity('Starting daemon…', () => ensureDaemon(data, daemonOverrides));
    const health = await daemonHealth(data);
    requireThat(health, 'DAEMON_START_FAILED', 'The daemon did not report healthy after startup.');
    output.result({ command, action, started: !before }, health);
    return;
  }
  if (command === 'doctor') {
    requireThat(
      action === undefined && args.length === 0,
      'INVALID_ARGUMENT',
      'Doctor takes no arguments.',
    );
    let storage: Record<string, unknown>;
    try {
      requireSupportedPlatform();
      const { nativeIdentity } = await import('./storage/native.js');
      storage = {
        engine: 'turso',
        state: 'ready',
        version: tursoVersion,
        bindingIdentity: nativeIdentity(),
      };
    } catch (error) {
      storage = {
        state: 'unavailable',
        error: error instanceof Error ? error.message : String(error),
      };
    }
    const result = {
      version: packageVersion,
      node: process.versions.node,
      platform: `${process.platform}-${process.arch}`,
      dataDir: data,
      storage,
      daemon: (await daemonHealth(data)) ?? {
        state: 'stopped',
        diagnostics: daemonDiagnostics(data),
      },
    };
    output.result({ command }, result);
    if (storage.state !== 'ready') process.exitCode = 1;
    return;
  }

  if (command !== 'turn') await ensureDaemon(data);
  const client = await connectDaemon(data);
  let opened = false;
  let heartbeat: NodeJS.Timeout | undefined;
  try {
    let result: unknown;
    if (command === 'turn' && action === 'list') result = await client.call('getHealth');
    else if (command === 'turn') {
      requireThat(
        args.length === 2 && args[1] === '--force',
        'INVALID_ARGUMENT',
        'Use turn release TURN_ID --force.',
      );
      result = await client.call('forceRelease', { turnId: args[0], force: true });
    } else {
      await client.call('openSession', { workspace, name });
      opened = true;
      heartbeat = setInterval(() => {
        void client.call('heartbeatSession').catch(() => {});
      }, 5_000);
      heartbeat.unref();
      const call = <T = unknown>(operation: string, input: unknown = {}) =>
        client.call<T>('callTool', { name: operation, args: input });
      const mcpCall = <T = unknown>(operation: string, input: unknown = {}) =>
        client.call<T>('callMcpTool', { name: operation, args: input });
      const interaction: CliInteraction = {
        interactive: output.options.interactive,
        confirm: (prompt, preview) => output!.confirm(prompt, preview),
      };
      const run = async () => {
        if (command === 'thread') {
          const thread = await runThreadCli(action, args, call, interaction);
          return thread === cancelledResult ? thread : presentProjectCli(thread);
        }
        if (command === 'ticket') {
          const ticket = await runTicketCli(action, args, mcpCall, data, call);
          if (ticket.raw !== undefined) return { raw: ticket.raw };
          return presentProjectCli(ticket.value);
        }
        if (command === 'project') {
          const project = await runProjectCli(action, args, call, interaction);
          return project === cancelledResult ? project : presentProjectCli(project);
        }
        return undefined;
      };
      const activity =
        command === 'project' && action === 'export'
          ? 'Exporting project…'
          : command === 'project' && action === 'restore' && args.includes('--yes')
            ? 'Restoring project…'
            : undefined;
      result = activity ? await output.activity(activity, run) : await run();
      if (typeof result === 'object' && result && 'raw' in result) {
        process.stdout.write(String((result as { raw: unknown }).raw));
        return;
      }
    }
    output.result({ command, action, cancelled: result === cancelledResult }, result);
  } finally {
    if (heartbeat) clearInterval(heartbeat);
    try {
      if (opened && !client.socket.destroyed) await client.call('closeSession');
    } finally {
      client.close();
    }
  }
}

void main().catch(error => {
  const fallback =
    output ??
    new CliOutput({
      mode: process.stdout.isTTY ? 'human' : 'json',
      color: false,
      interactive: false,
      width: process.stdout.columns ?? 80,
    });
  fallback.error(error, activeCommand);
  process.exitCode = 1;
});
