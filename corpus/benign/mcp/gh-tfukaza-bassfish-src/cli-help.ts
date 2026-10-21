type HelpEntry = {
  summary: string;
  usage: string[];
  details?: string[];
  examples?: string[];
};

const globalOptions = [
  ['--json', 'Force the stable machine-readable result.'],
  ['--plain', 'Force human-readable output without terminal styling.'],
  ['-h, --help', 'Show help for a command.'],
] as const;
const repositoryOptions = [
  ['--workspace PATH', 'Use PATH instead of the current Git repository.'],
  ['--name NAME', 'Use or reclaim a stable human CLI identity.'],
] as const;

const entries: Record<string, HelpEntry> = {
  sonar: {
    summary: 'Watch conversations, file reservations, tickets and agent activity live.',
    usage: [
      'bassfish sonar [--monitor | --view monitor|threads|files|tickets|activity]',
      'bassfish sonar --workspace PATH [--ascii]',
      'bassfish sonar --once [--json | --plain]',
    ],
    details: [
      'Monitor opens by default. Sonar is read-only and waits for a stopped daemon.',
      'Use 1–5 to switch views, Tab to focus panes, Space to pause, and ? for help.',
      'Tickets offer dependency graphs, boards and lists. Threads use a channel-style reader.',
      'Activity is retained for seven days, bounded to 100,000 events per project.',
      'Piped output is one JSON snapshot; --plain and TERM=dumb produce static output.',
    ],
  },
  setup: {
    summary: 'Initialize the embedded Turso database.',
    usage: ['bassfish setup'],
  },
  doctor: {
    summary: 'Inspect the Bassfish CLI, runtime, data directory, and daemon.',
    usage: ['bassfish doctor'],
  },
  daemon: {
    summary: 'Start, inspect, or stop the shared local backend.',
    usage: [
      'bassfish daemon start [--turn-timeout DURATION]',
      'bassfish daemon status',
      'bassfish daemon stop',
      'bassfish daemon run [--turn-timeout DURATION]',
    ],
    details: ['DURATION accepts 5s through 5m using ms, s, or m.'],
  },
  config: {
    summary: 'Inspect or change daemon timing configuration.',
    usage: [
      'bassfish config show',
      'bassfish config set KEY MILLISECONDS',
      'bassfish config reset [--yes]',
    ],
  },
  data: {
    summary: 'Move preview data to a timestamped, recoverable backup.',
    usage: ['bassfish data reset [--yes]'],
    details: ['The daemon must be stopped. Interactive terminals ask before resetting.'],
  },
  turn: {
    summary: 'Inspect coordination state or revoke one abandoned claimed turn.',
    usage: ['bassfish turn list', 'bassfish turn release TURN_ID --force'],
    details: ['A committing write cannot be force-released.'],
  },
  thread: {
    summary: 'Create, inspect, search, and edit shared conversations.',
    usage: [
      'bassfish thread list [--archived|--deleted] [--limit N] [--cursor C]',
      'bassfish thread create TITLE [--description TEXT]',
      'bassfish thread get|show THREAD_ID',
      'bassfish thread search QUERY [--archived|--deleted] [--limit N]',
      'bassfish thread rename THREAD_ID TITLE',
      'bassfish thread describe THREAD_ID (--description TEXT | --clear)',
      'bassfish thread follow|unfollow THREAD_ID',
      'bassfish thread archive|activate THREAD_ID',
      'bassfish thread delete THREAD_ID [--yes]',
      'bassfish thread retract|reinstate THREAD_ID MESSAGE_ID',
      'bassfish thread history THREAD_ID',
      'bassfish thread revision|diff THREAD_ID REVISION',
    ],
  },
  ticket: {
    summary: 'Create, find, inspect, and edit owned work in the ticket DAG.',
    usage: [
      'bassfish ticket list [--owner NAME] [--state STATES] [--ready]',
      'bassfish ticket search QUERY [--owner NAME] [--state STATES] [--ready]',
      'bassfish ticket create TITLE --description TEXT --owner NAME [options]',
      'bassfish ticket show TICKET_ID',
      'bassfish ticket history TICKET_ID [--limit N] [--offset N]',
      'bassfish ticket revision TICKET_ID REVISION',
      'bassfish ticket diff TICKET_ID REVISION',
      'bassfish ticket update TICKET_ID [options]',
      'bassfish ticket edit|append|patch TICKET_ID (--file PATH|-|--editor)',
    ],
    details: ['Ticket body input uses exactly one of --file PATH, --file -, or --editor.'],
  },
  project: {
    summary: 'Inspect current content, export it, or read the project audit history.',
    usage: [
      'bassfish project inspect',
      'bassfish project export',
      'bassfish project history [--limit N] [--cursor C]',
    ],
    details: [
      'Project reads are consistent and do not require a turn. History contains immutable resource revisions.',
    ],
  },
  mcp: {
    summary: 'Run the agent-facing stdio MCP server.',
    usage: ['bassfish mcp [--workspace PATH] [--name NAME]'],
  },
};

function lines(rows: readonly (readonly [string, string])[]): string[] {
  const width = Math.max(...rows.map(([left]) => left.length));
  return rows.map(([left, right]) => `  ${left.padEnd(width)}  ${right}`);
}

export function commandHelp(topic?: string): string {
  if (topic) {
    const root = topic.split(/\s+/)[0]!;
    const entry = entries[root];
    if (!entry) return `Unknown help topic: ${topic}\nRun bassfish --help to list commands.\n`;
    const output = [
      `Bassfish ${root}`,
      '',
      entry.summary,
      '',
      'Usage:',
      ...entry.usage.map(value => `  ${value}`),
    ];
    if (entry.details?.length) output.push('', ...entry.details);
    if (entry.examples?.length)
      output.push('', 'Examples:', ...entry.examples.map(value => `  ${value}`));
    output.push('', 'Global options:', ...lines(globalOptions), '');
    if (['thread', 'ticket', 'project', 'mcp'].includes(root))
      output.push('Repository options:', ...lines(repositoryOptions), '');
    return output.join('\n');
  }
  return [
    'Bassfish: A local coordination layer for coding agents',
    '',
    'Usage:',
    '  bassfish <command> [options]',
    '',
    'Runtime:',
    ...lines([
      ['bassfish setup', 'Initialize embedded Turso.'],
      ['bassfish doctor', 'Show runtime and daemon diagnostics.'],
      ['bassfish daemon', 'Start, inspect, or stop the shared backend.'],
      ['bassfish config', 'Inspect or change daemon timing configuration.'],
      ['bassfish data', 'Reset preview data into a timestamped backup.'],
    ]),
    '',
    'Coordination:',
    ...lines([
      ['bassfish sonar', 'Open the live project monitor and visual browser.'],
      ['bassfish turn', 'Inspect or force-release coordination turns.'],
      ['bassfish thread', 'Manage shared conversations and history.'],
      ['bassfish ticket', 'Manage owned work and dependencies.'],
      ['bassfish project', 'Inspect, export, and read project history.'],
    ]),
    '',
    'Agent integration:',
    ...lines([['bassfish mcp', 'Run the stdio MCP server used by agent hosts.']]),
    '',
    'Global options:',
    ...lines(globalOptions),
    '',
    'Repository options:',
    ...lines(repositoryOptions),
    '',
    'Run bassfish help <command> for command-specific usage.',
    'Agents should use the MCP server rather than the human CLI.',
    '',
  ].join('\n');
}

export function hasHelp(args: string[]): boolean {
  return args.includes('--help') || args.includes('-h');
}

export function hasCommandHelp(topic: string): boolean {
  return Object.hasOwn(entries, topic.split(/\s+/)[0]!);
}
