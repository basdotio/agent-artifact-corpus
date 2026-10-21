import { createInterface } from 'node:readline/promises';
import { styleText } from 'node:util';
import type { Readable, Writable } from 'node:stream';
import { BassfishError } from './domain.js';
type Data = Record<string, unknown>;
type Format = Parameters<typeof styleText>[0];
type CliMode = 'human' | 'json';
export type OutputRequest = {
  command: string;
  action?: string;
  started?: boolean;
  cancelled?: boolean;
  preview?: boolean;
};
export type CliOutputOptions = {
  mode: CliMode;
  color: boolean;
  interactive: boolean;
  width: number;
};
const data = (value: unknown): Data =>
  value && typeof value === 'object' && !Array.isArray(value) ? (value as Data) : {};
const array = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);
const text = (value: unknown): string => {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'yes' : 'no';
  if (Array.isArray(value)) return value.length ? value.map(text).join(', ') : 'none';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};
const titleCase = (value: string): string =>
  value
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replaceAll('_', ' ')
    .replace(/^./, first => first.toUpperCase());
const configLabels: Record<string, string> = {
  offerMs: 'Offer window',
  turnTimeoutMs: 'Content turn',
  reconnectMs: 'Reconnect grace',
  instanceMs: 'Presence timeout',
  queueMs: 'Queue lifetime',
  retentionMs: 'Result retention',
  waitMs: 'Wait interval',
  idleMs: 'Daemon idle',
};
function removeFlag(args: string[], name: string): boolean {
  let found = false;
  for (let index = args.indexOf(name); index >= 0; index = args.indexOf(name)) {
    args.splice(index, 1);
    found = true;
  }
  return found;
}
export function outputOptions(
  args: string[],
  environment: NodeJS.ProcessEnv = process.env,
  streams: {
    stdoutTTY?: boolean;
    stdinTTY?: boolean;
    columns?: number;
  } = {},
): CliOutputOptions {
  const json = removeFlag(args, '--json');
  const plain = removeFlag(args, '--plain');
  if (json && plain)
    throw new BassfishError('INVALID_ARGUMENT', 'Choose either --json or --plain, not both.');
  const stdoutTTY = streams.stdoutTTY ?? Boolean(process.stdout.isTTY);
  const stdinTTY = streams.stdinTTY ?? Boolean(process.stdin.isTTY);
  const mode: CliMode = json || (!plain && !stdoutTTY) ? 'json' : 'human';
  return {
    mode,
    color:
      mode === 'human' &&
      !plain &&
      stdoutTTY &&
      environment.NO_COLOR === undefined &&
      environment.TERM !== 'dumb',
    interactive: mode === 'human' && stdoutTTY && stdinTTY,
    width: Math.max(40, streams.columns ?? process.stdout.columns ?? 80),
  };
}
function duration(value: unknown): string {
  if (typeof value !== 'number') return text(value);
  if (value % 60000 === 0) return `${value / 60000}m (${value} ms)`;
  if (value % 1000 === 0) return `${value / 1000}s (${value} ms)`;
  return `${value} ms`;
}
function target(value: unknown): string {
  const item = data(value);
  if (item.type === 'files')
    return array(item.paths)
      .map(path => text(data(path).path))
      .join(', ');
  return text(item.threadId ?? item.ticketId ?? item.id ?? item.purpose ?? item.type);
}
export function renderHuman(
  request: OutputRequest,
  value: unknown,
  options: Pick<CliOutputOptions, 'color' | 'width'>,
): string {
  const paint = (format: Format, source: string): string =>
    options.color ? styleText(format, source, { validateStream: false }) : source;
  const heading = (source: string): string => paint('bold', source);
  const muted = (source: string): string => paint('gray', source);
  const success = (source: string): string => paint('green', source);
  const info = (source: string): string => paint('cyan', source);
  const warning = (source: string): string => paint('yellow', source);
  const badge = (state: unknown): string => {
    const source = text(state);
    if (['ready', 'active', 'done', 'claimed', 'committed', 'running'].includes(source))
      return success(source);
    if (['queued', 'offered', 'blocked', 'in_progress', 'stopping'].includes(source))
      return warning(source);
    return muted(source);
  };
  const field = (label: string, item: unknown, width = 12): string =>
    `  ${muted(label.padEnd(width))}${text(item)}`;
  const record = (item: unknown, hidden: string[] = []): string[] => {
    const object = data(item);
    return Object.entries(object)
      .filter(([key]) => !hidden.includes(key))
      .flatMap(([key, child]) => {
        if (Array.isArray(child) && child.every(row => !row || typeof row !== 'object'))
          return [field(titleCase(key), child)];
        if (child && typeof child === 'object')
          return [field(titleCase(key), JSON.stringify(child))];
        return [field(titleCase(key), child)];
      });
  };
  const stacked = (rows: unknown[], keys: string[]): string[] =>
    rows.flatMap((row, index) => {
      const item = data(row);
      return [
        `${index ? '\n' : ''}${heading(text(item.title ?? item.name ?? item.kind ?? `Item ${index + 1}`))}`,
        ...keys.filter(key => item[key] !== undefined).map(key => field(titleCase(key), item[key])),
      ];
    });
  const table = (
    rows: unknown[],
    columns: {
      key: string;
      label: string;
      width: number;
    }[],
  ): string[] => {
    if (options.width < 100)
      return stacked(
        rows,
        columns.map(column => column.key),
      );
    const line = (row: Data, header = false) =>
      columns
        .map(column => {
          const raw = header ? column.label : text(row[column.key]);
          const clipped = raw.length > column.width ? `${raw.slice(0, column.width - 1)}…` : raw;
          const padded = clipped.padEnd(column.width);
          return header ? muted(padded) : column.key === 'state' ? badge(padded) : padded;
        })
        .join('  ')
        .trimEnd();
    return [line({}, true), ...rows.map(row => line(data(row)))];
  };
  const messages = (rows: unknown[]): string[] => {
    if (!rows.length) return [muted('  No messages yet.')];
    return rows.flatMap((row, index) => {
      const item = data(row);
      const author = text(item.author ?? item.name);
      const sequence = item.sequence === undefined ? '' : ` #${text(item.sequence)}`;
      const retracted = item.retracted ? ` ${warning('[retracted]')}` : '';
      const body = text(item.body)
        .split('\n')
        .map(line => `  ${line}`);
      return [`${index ? '\n' : ''}${info(author)}${muted(sequence)}${retracted}`, ...body];
    });
  };
  const generic = (item: unknown): string[] => {
    if (Array.isArray(item)) return stacked(item, Object.keys(data(item[0])));
    if (!item || typeof item !== 'object') return [text(item)];
    const object = data(item);
    const output: string[] = [];
    for (const [key, child] of Object.entries(object)) {
      if (['previewToken', 'turnToken', 'requestToken'].includes(key)) continue;
      if (Array.isArray(child) && child.every(row => row && typeof row === 'object')) {
        output.push('', heading(titleCase(key)), ...stacked(child, Object.keys(data(child[0]))));
      } else if (child && typeof child === 'object') {
        output.push('', heading(titleCase(key)), ...record(child));
      } else output.push(field(titleCase(key), child));
    }
    return output.length && output[0] === '' ? output.slice(1) : output;
  };
  const object = data(value);
  const command = request.command;
  const action = request.action;
  let output: string[];
  if (request.cancelled) output = [`${muted('○')} ${muted('Cancelled. No changes were made.')}`];
  else if (command === 'setup') {
    output = [
      `${success('✓')} Turso is ready`,
      field('Version', object.version),
      field('Path', object.path),
    ];
  } else if (command === 'doctor') {
    const storage = data(object.storage);
    const daemon = data(object.daemon);
    output = [
      heading(`Bassfish ${text(object.version)}`),
      field('Node', `${text(object.node)} ${success('✓')}`),
      field('Platform', object.platform),
      field(
        'Turso',
        storage.state === 'ready'
          ? `${text(storage.version)} ${success('✓')}`
          : `${text(storage.state)} ${warning('!')}`,
      ),
      ...(storage.bindingIdentity ? [field('Binding', storage.bindingIdentity)] : []),
      ...(data(daemon.storage).replacementSuccesses !== undefined
        ? [field('Connection replacements', data(daemon.storage).replacementSuccesses)]
        : []),
      field('Daemon', daemon.state === 'stopped' ? muted('stopped ○') : success('running ✓')),
      field('Data', object.dataDir),
      ...(data(daemon.diagnostics).logPath
        ? [field('Daemon log', data(daemon.diagnostics).logPath)]
        : []),
      ...(data(daemon.diagnostics).runtimeLogPath
        ? [field('Runtime log', data(daemon.diagnostics).runtimeLogPath)]
        : []),
      ...(data(daemon.diagnostics).clientLogPath
        ? [field('Client log', data(daemon.diagnostics).clientLogPath)]
        : []),
      ...(data(data(daemon.diagnostics).runtime).status
        ? [field('Runtime', data(data(daemon.diagnostics).runtime).status)]
        : []),
      ...(storage.error ? [field('Problem', storage.error)] : []),
    ];
  } else if (command === 'daemon') {
    const state = text(object.state);
    if (action === 'stop')
      output = [
        object.stopping === false
          ? `${muted('○')} Daemon already stopped`
          : `${success('✓')} Daemon stopped`,
      ];
    else if (state === 'stopped') output = [`${muted('○')} Daemon stopped`];
    else
      output = [
        `${success('✓')} Daemon ${request.started === false ? 'already running' : 'running'}`,
        field('PID', object.pid),
        field('State', object.state),
        ...(data(object.config).turnTimeoutMs
          ? [field('Turn timeout', duration(data(object.config).turnTimeoutMs))]
          : []),
      ];
    if (data(object.diagnostics).logPath)
      output.push(field('Daemon log', data(object.diagnostics).logPath));
    if (data(object.diagnostics).runtimeLogPath)
      output.push(field('Runtime log', data(object.diagnostics).runtimeLogPath));
    if (data(object.diagnostics).clientLogPath)
      output.push(field('Client log', data(object.diagnostics).clientLogPath));
    const runtime = data(data(object.diagnostics).runtime);
    if (runtime.status) output.push(field('Runtime', runtime.status));
    const lifecycle = data(data(object.diagnostics).lastLifecycle);
    if (lifecycle.event)
      output.push(
        field(
          'Last lifecycle',
          `${text(lifecycle.event)} · ${text(lifecycle.at)}${lifecycle.code ? ` · ${text(lifecycle.code)}` : ''}`,
        ),
      );
  } else if (command === 'data') {
    output = object.reset
      ? [`${success('✓')} Preview data moved to backup`, field('Backup', object.backup)]
      : [`${muted('○')} No Bassfish data to reset`];
  } else if (command === 'config') {
    output = [
      `${action === 'show' ? heading('Bassfish configuration') : `${success('✓')} Configuration ${action === 'reset' ? 'reset' : 'updated'}`}`,
      ...Object.entries(object).map(([key, item]) =>
        field(configLabels[key] ?? titleCase(key), duration(item), 20),
      ),
    ];
  } else if (command === 'turn' && action === 'list') {
    const turns = array(data(object.control).turns);
    output = turns.length
      ? [
          heading(`Turns · ${turns.length}`),
          ...table(
            turns.map(row => ({
              ...data(row),
              target: target(data(row).target),
            })),
            [
              { key: 'turnId', label: 'TURN ID', width: 36 },
              { key: 'state', label: 'STATE', width: 11 },
              { key: 'owner', label: 'OWNER', width: 16 },
              { key: 'target', label: 'TARGET', width: Math.max(20, options.width - 71) },
            ],
          ),
        ]
      : [`${muted('○')} No active turns`];
  } else if (command === 'turn' && action === 'release') {
    output = [`${success('✓')} Turn released`];
  } else if (command === 'thread' && ['list', 'search'].includes(action ?? '')) {
    const rows = array(object.threads);
    output = rows.length
      ? [
          heading(`Threads · ${rows.length}`),
          ...table(rows, [
            { key: 'id', label: 'THREAD ID', width: 36 },
            { key: 'state', label: 'STATE', width: 10 },
            { key: 'revision', label: 'REV', width: 5 },
            { key: 'title', label: 'TITLE', width: Math.max(20, options.width - 57) },
          ]),
          ...(object.nextCursor
            ? [muted('More results are available; pass --cursor with the JSON cursor.')]
            : []),
        ]
      : [`${muted('○')} No threads found`];
  } else if (command === 'thread' && action === 'show') {
    const page = data(object.page);
    const thread = data(page.thread);
    output = [
      heading(text(thread.title ?? 'Thread')),
      field('Thread ID', thread.id),
      field('State', thread.state),
      field('Revision', thread.revision ?? data(object.snapshot).revision),
      ...(thread.description ? ['', text(thread.description)] : []),
      '',
      heading('Messages'),
      ...messages(array(page.messages)),
    ];
  } else if (command === 'thread' && action === 'revision') {
    const thread = data(object.thread);
    output = [
      heading(`${text(thread.title ?? 'Thread')} · revision ${text(object.revision)}`),
      field('Thread ID', thread.id),
      field('State', thread.state),
      '',
      heading('Messages'),
      ...messages(array(object.messages)),
    ];
  } else if (command === 'thread' && action === 'get') {
    output = [heading(text(object.title ?? 'Thread')), ...record(object)];
  } else if (['thread', 'ticket'].includes(command) && action === 'history') {
    const rows = array(object.entries);
    output = rows.length
      ? [
          heading(`${titleCase(command)} history · ${rows.length}`),
          ...table(rows, [
            { key: 'afterRevision', label: 'REV', width: 5 },
            { key: 'kind', label: 'CHANGE', width: 24 },
            { key: 'actorName', label: 'AUTHOR', width: 16 },
            { key: 'createdAt', label: 'TIME', width: 25 },
          ]),
        ]
      : [`${muted('○')} No history`];
  } else if (command === 'thread') {
    const labels: Record<string, string> = {
      create: 'Thread created',
      rename: 'Thread renamed',
      describe: 'Thread description updated',
      follow: 'Thread followed',
      unfollow: 'Thread unfollowed',
      archive: 'Thread archived',
      activate: 'Thread activated',
      delete: 'Thread deleted',
      retract: 'Message retracted',
      reinstate: 'Message reinstated',
      diff: 'Thread revision diff',
    };
    output = [
      action === 'diff'
        ? heading(labels.diff!)
        : `${success('✓')} ${labels[action ?? ''] ?? 'Thread updated'}`,
      ...generic(object),
    ];
  } else if (command === 'ticket' && ['list', 'search'].includes(action ?? '')) {
    const rows = array(object.resources ?? object.tickets);
    output = rows.length
      ? [
          heading(`Tickets · ${rows.length}`),
          ...table(rows, [
            { key: 'ticketId', label: 'TICKET ID', width: 36 },
            { key: 'state', label: 'STATE', width: 12 },
            { key: 'owner', label: 'OWNER', width: 16 },
            { key: 'title', label: 'TITLE', width: Math.max(20, options.width - 61) },
          ]),
          ...(object.nextCursor
            ? [muted('More results are available; pass --cursor with the JSON cursor.')]
            : []),
        ]
      : [`${muted('○')} No tickets found`];
  } else if (command === 'ticket' && ['show', 'revision'].includes(action ?? '')) {
    const ticket = data(object.ticket);
    output = [
      heading(text(ticket.title ?? 'Ticket')),
      field('Ticket ID', ticket.ticketId ?? ticket.id),
      field('State', badge(ticket.state)),
      field('Owner', ticket.owner ?? ticket.ownerName),
      field('Revision', ticket.revision),
      field('Depends on', ticket.dependsOn),
      ...(ticket.description ? ['', text(ticket.description)] : []),
      '',
      heading('Body'),
      ...text(object.body)
        .split('\n')
        .map(line => `  ${line}`),
    ];
  } else if (command === 'ticket') {
    const labels: Record<string, string> = {
      create: 'Ticket created',
      update: 'Ticket updated',
      edit: 'Ticket body replaced',
      append: 'Ticket body appended',
      patch: 'Ticket body patched',
    };
    output = [`${success('✓')} ${labels[action ?? ''] ?? 'Ticket updated'}`, ...generic(object)];
  } else if (command === 'project' && action === 'inspect') {
    output = [
      heading('Project content'),
      field('Exported at', object.exportedAt),
      field('Messages', object.messageCount),
      field('Threads', array(object.threads).length),
      field('Tickets', array(object.tickets).length),
      ...(array(object.threads).length
        ? ['', heading('Threads'), ...stacked(array(object.threads), ['id', 'state', 'revision'])]
        : []),
      ...(array(object.tickets).length
        ? [
            '',
            heading('Tickets'),
            ...stacked(array(object.tickets), ['id', 'state', 'ownerName', 'revision']),
          ]
        : []),
    ];
  } else if (command === 'project' && action === 'history') {
    const rows = array(object.entries);
    output = rows.length
      ? [
          heading(`Project history · ${rows.length}`),
          ...stacked(rows, ['resourceId', 'revision', 'kind', 'actorName', 'createdAt']),
        ]
      : [`${muted('○')} No project history`];
  } else if (command === 'project' && action === 'export') {
    output = [`${success('✓')} Project exported`, ...record(object)];
  } else if (command === 'project') {
    output = [`${success('✓')} Project content`, ...generic(object)];
  } else output = generic(value);
  return `${output.filter((line, index, rows) => !(line === '' && rows[index - 1] === '')).join('\n')}\n`;
}
function errorHint(code: string, command?: string): string | undefined {
  if (code === 'INVALID_ARGUMENT')
    return `Run bassfish${command ? ` ${command}` : ''} --help for usage.`;
  if (code === 'TURN_BUSY') return 'Inspect current ownership with bassfish turn list.';
  if (code === 'CONFIRMATION_REQUIRED')
    return 'Run this in an interactive terminal, or pass --yes after reviewing the command.';
  if (code === 'DAEMON_RUNNING') return 'Run bassfish daemon stop, then retry.';
  if (code === 'STORAGE_UNAVAILABLE') return 'Run bassfish setup.';
  if (code === 'ENOENT' || code === 'ECONNREFUSED') return 'Start it with bassfish daemon start.';
  if (code === 'EPERM' || code === 'EACCES')
    return 'Check ownership and permissions for the reported path.';
  if (code === 'REVISION_CHANGED') return 'Reread the current resource before trying again.';
  return undefined;
}
export class CliOutput {
  constructor(
    readonly options: CliOutputOptions,
    private readonly stdout: Writable = process.stdout,
    private readonly stderr: Writable = process.stderr,
    private readonly stdin: Readable = process.stdin,
  ) {}
  result(request: OutputRequest, value: unknown): void {
    if (this.options.mode === 'json') {
      this.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
      return;
    }
    this.stdout.write(renderHuman(request, value, this.options));
  }
  help(value: string): void {
    this.stdout.write(value);
  }
  error(error: unknown, command?: string): void {
    const code =
      error instanceof BassfishError
        ? error.code
        : ((error as NodeJS.ErrnoException).code ?? 'STARTUP_ERROR');
    const message = error instanceof Error ? error.message : 'Bassfish failed.';
    if (this.options.mode === 'json') {
      this.stderr.write(`${code}: ${message}\n`);
      return;
    }
    const paint = (format: Format, source: string): string =>
      this.options.color ? styleText(format, source, { validateStream: false }) : source;
    const lines = [
      `${paint('red', '✗')} ${paint('bold', message)}`,
      `  ${paint('gray', `Code: ${code}`)}`,
    ];
    const hint = errorHint(code, command);
    if (hint) lines.push(`  ${paint('cyan', hint)}`);
    this.stderr.write(`${lines.join('\n')}\n`);
  }
  async confirm(
    prompt: string,
    preview?: {
      request: OutputRequest;
      value: unknown;
    },
  ): Promise<boolean> {
    if (!this.options.interactive) return false;
    if (preview)
      this.stdout.write(
        renderHuman({ ...preview.request, preview: true }, preview.value, this.options),
      );
    const paint = (format: Format, source: string): string =>
      this.options.color ? styleText(format, source, { validateStream: false }) : source;
    const terminal = createInterface({ input: this.stdin, output: this.stdout, terminal: true });
    try {
      const answer = await terminal.question(
        `${paint('yellow', '?')} ${prompt} ${paint('gray', '[y/N]')} `,
      );
      return /^(?:y|yes)$/i.test(answer.trim());
    } catch {
      return false;
    } finally {
      terminal.close();
    }
  }
  async activity<T>(label: string, operation: () => Promise<T>): Promise<T> {
    if (this.options.mode !== 'human' || !this.options.interactive || !this.options.color)
      return await operation();
    const frames = ['◐', '◓', '◑', '◒'];
    let frame = 0;
    let shown = false;
    const draw = () => {
      shown = true;
      this.stderr.write(`\r\u001b[2K${frames[frame++ % frames.length]} ${label}`);
    };
    const delay = setTimeout(() => {
      draw();
      interval = setInterval(draw, 90);
    }, 180);
    let interval: NodeJS.Timeout | undefined;
    delay.unref();
    try {
      return await operation();
    } finally {
      clearTimeout(delay);
      if (interval) clearInterval(interval);
      if (shown) this.stderr.write('\r\u001b[2K');
    }
  }
}
export const cancelledResult = Object.freeze({ cancelled: true });
