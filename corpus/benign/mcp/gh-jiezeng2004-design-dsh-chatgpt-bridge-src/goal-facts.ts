/**
 * Fold a session event log into structured Goal facts.
 * Success is taken from tool/call arguments + tool/result, never from
 * assistant summary text.
 */
export type ActionKind =
  | 'git_push'
  | 'git_tag'
  | 'npm_publish'
  | 'github_release'
  | 'git_worktree_add'
  | 'npm_pack'
  | 'unknown';

/** Minimal event shape so this module stays unit-testable without DSH types. */
export interface LooseEvent {
  type: string;
  seq: number;
  time?: number;
  data?: unknown;
}

export interface ToolFact {
  seq: number;
  callId: string;
  name: string;
  kinds: ActionKind[];
  ok: boolean;
  errorCode?: string;
  resultText?: string;
  command?: string;
  filePath?: string;
}

export interface GoalFacts {
  lastSeq?: number;
  todos?: { content: string; status: string }[];
  tools: ToolFact[];
  lastTurnReason?: string;
}

const RESULT_TEXT_CAP = 800;
const COMMAND_KEYS = ['command', 'cmd', 'script', 'command_line'];
const PATH_KEYS = [
  'file_path', 'path', 'filepath', 'target',
  'old_path', 'new_path', 'src', 'dest', 'old_file', 'new_file',
];

export function parseArgsJson(raw: string): Record<string, unknown> | undefined {
  try {
    const value = JSON.parse(raw) as unknown;
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, unknown>;
    }
  } catch {
    // ignore malformed tool arguments
  }
  return undefined;
}

export function extractCommand(args: Record<string, unknown>): string | undefined {
  for (const key of COMMAND_KEYS) {
    const value = args[key];
    if (typeof value === 'string' && value.trim() !== '') return value;
  }
  const commands = args.commands;
  if (Array.isArray(commands)) {
    const joined = commands.filter((item): item is string => typeof item === 'string').join('\n');
    if (joined.trim() !== '') return joined;
  }
  return undefined;
}

export function extractFilePath(args: Record<string, unknown>): string | undefined {
  return extractFilePaths(args)[0];
}

export function extractFilePaths(args: Record<string, unknown>): string[] {
  const paths: string[] = [];
  for (const key of PATH_KEYS) {
    const value = args[key];
    if (typeof value === 'string' && value.trim() !== '' && !paths.includes(value)) paths.push(value);
  }
  return paths;
}

export function classifyCommand(command: string): ActionKind[] {
  const kinds: ActionKind[] = [];
  if (/\bgit\s+worktree\s+add\b/i.test(command)) kinds.push('git_worktree_add');
  if (/\bnpm\s+publish\b/i.test(command)) kinds.push('npm_publish');
  if (/\bnpm\s+pack\b/i.test(command)) kinds.push('npm_pack');
  if (/\bgh\s+release\b/i.test(command)) kinds.push('github_release');
  const tagCreate = /\bgit\s+tag\b/i.test(command);
  const tagPush = /\bgit\s+push\s+--tags\b/i.test(command)
    || /\bgit\s+push\b[^\n]*\b(--tags|refs\/tags\/|v\d)/i.test(command);
  if (tagCreate || tagPush) kinds.push('git_tag');
  const commitPush = /\bgit\s+push\b/i.test(command) && !tagPush;
  if (commitPush) kinds.push('git_push');
  return kinds;
}

export function tokenize(text: string): string[] {
  const tokens: string[] = [];
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(text)) !== null) {
    tokens.push(match[1] ?? match[2] ?? match[3] ?? '');
  }
  return tokens.filter((token) => token !== '');
}

const WORKTREE_VALUE_OPTS = new Set(['-b', '-B', '--reason', '--track']);

export function parseWorktreeAddPath(command: string): string | undefined {
  const match = command.match(/\bgit\s+worktree\s+add\b([\s\S]*)/i);
  if (match === null) return undefined;
  const tokens = tokenize(match[1] ?? '');
  const positional: string[] = [];
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i] ?? '';
    if (token.startsWith('-')) {
      const opt = token.split('=')[0] ?? token;
      if (WORKTREE_VALUE_OPTS.has(opt) && !token.includes('=')) i += 1;
      continue;
    }
    positional.push(token);
  }
  return positional[0];
}

export function parseMkdirPaths(command: string): string[] {
  if (!/\bmkdir\b/i.test(command)) return [];
  const match = command.match(/\bmkdir\b([\s\S]*)/i);
  if (match === null) return [];
  const tokens = tokenize(match[1] ?? '');
  return tokens.filter((token) => !token.startsWith('-'));
}

function resultTextOf(data: Record<string, unknown>): string {
  const message = data.message as { content?: unknown } | undefined;
  const content = message?.content;
  if (typeof content === 'string') return content.slice(0, RESULT_TEXT_CAP);
  if (!Array.isArray(content)) return '';
  const parts: string[] = [];
  for (const block of content) {
    if (typeof block === 'string') {
      parts.push(block);
    } else if (block !== null && typeof block === 'object') {
      const rec = block as Record<string, unknown>;
      if (typeof rec.content === 'string') parts.push(rec.content);
      else if (typeof rec.text === 'string') parts.push(rec.text);
    }
  }
  return parts.join('\n').slice(0, RESULT_TEXT_CAP);
}

function resultIsError(data: Record<string, unknown>): boolean {
  if (data.error !== undefined) return true;
  const message = data.message as { content?: unknown } | undefined;
  const content = message?.content;
  if (Array.isArray(content)) {
    const first = content[0] as { isError?: boolean } | undefined;
    if (first?.isError === true) return true;
  }
  return false;
}

function resultErrorCode(data: Record<string, unknown>): string | undefined {
  const error = data.error as { code?: string } | undefined;
  if (typeof error?.code === 'string' && error.code !== '') return error.code;
  return undefined;
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return undefined;
}

/** Fold tool/call + tool/result + todo/write + turn/end into facts. */
export function foldGoalFacts(events: readonly LooseEvent[]): GoalFacts {
  const tools: ToolFact[] = [];
  const open = new Map<string, { seq: number; name: string; command?: string; filePath?: string; kinds: ActionKind[] }>();
  let todos: { content: string; status: string }[] | undefined;
  let lastTurnReason: string | undefined;
  let lastSeq: number | undefined;

  for (const event of events) {
    lastSeq = event.seq;
    const data = asRecord(event.data);
    if (event.type === 'todo/write' && data !== undefined) {
      const list = data.todos;
      if (Array.isArray(list)) {
        todos = list
          .map((item) => {
            const rec = asRecord(item);
            if (rec === undefined) return undefined;
            if (typeof rec.content !== 'string') return undefined;
            return { content: rec.content, status: typeof rec.status === 'string' ? rec.status : 'pending' };
          })
          .filter((item): item is { content: string; status: string } => item !== undefined);
      }
    } else if (event.type === 'turn/end' && data !== undefined) {
      const reason = asRecord(data.reason);
      if (typeof reason?.kind === 'string') lastTurnReason = reason.kind;
    } else if (event.type === 'tool/call' && data !== undefined) {
      const callId = typeof data.callId === 'string' ? data.callId : undefined;
      const name = typeof data.name === 'string' ? data.name : 'unknown';
      const rawArgs = typeof data.arguments === 'string' ? data.arguments : '';
      const args = rawArgs === '' ? undefined : parseArgsJson(rawArgs);
      const command = args === undefined ? undefined : extractCommand(args);
      const filePath = args === undefined ? undefined : extractFilePath(args);
      const kinds = command === undefined ? [] : classifyCommand(command);
      if (kinds.length === 0) kinds.push('unknown');
      if (callId !== undefined) {
        open.set(callId, {
          seq: event.seq,
          name,
          ...(command === undefined ? {} : { command }),
          ...(filePath === undefined ? {} : { filePath }),
          kinds,
        });
      }
    } else if (event.type === 'tool/result' && data !== undefined) {
      const message = asRecord(data.message);
      const source = message === undefined ? undefined : asRecord(message.source);
      const callId = typeof source?.callId === 'string' ? source.callId : undefined;
      const opened = callId === undefined ? undefined : open.get(callId);
      if (opened !== undefined && callId !== undefined) {
        open.delete(callId);
        const text = resultTextOf(data);
        const ok = !resultIsError(data);
        const errorCode = resultErrorCode(data);
        tools.push({
          seq: event.seq,
          callId,
          name: opened.name,
          kinds: opened.kinds,
          ok,
          ...(errorCode === undefined ? {} : { errorCode }),
          ...(text === '' ? {} : { resultText: text }),
          ...(opened.command === undefined ? {} : { command: opened.command }),
          ...(opened.filePath === undefined ? {} : { filePath: opened.filePath }),
        });
      }
    }
  }

  return {
    ...(lastSeq === undefined ? {} : { lastSeq }),
    ...(todos === undefined ? {} : { todos }),
    tools,
    ...(lastTurnReason === undefined ? {} : { lastTurnReason }),
  };
}

export function lastEventSeq(events: readonly LooseEvent[]): number | undefined {
  const last = events[events.length - 1];
  return last === undefined ? undefined : last.seq;
}

const NPM_2FA_CODES = ['EOTP', 'ENEEDAUTH', 'EOTPREQUIRED', 'E401'];

/** True when a failed npm publish fact looks like a 2FA / OTP gate. */
export function factLooksLikeNpm2fa(fact: ToolFact): boolean {
  if (!fact.kinds.includes('npm_publish')) return false;
  const code = (fact.errorCode ?? '').toUpperCase();
  if (NPM_2FA_CODES.some((item) => code.includes(item))) return true;
  const text = (fact.resultText ?? '').toLowerCase();
  return (
    text.includes('otp')
    || text.includes('one-time password')
    || text.includes('two-factor')
    || text.includes('2fa')
    || text.includes('auth-and-writes')
    || text.includes('eneedauth')
    || text.includes('eotp')
  );
}

export function successfulKinds(facts: GoalFacts): Set<ActionKind> {
  const ok = new Set<ActionKind>();
  for (const fact of facts.tools) {
    if (!fact.ok) continue;
    for (const kind of fact.kinds) {
      if (kind !== 'unknown') ok.add(kind);
    }
  }
  return ok;
}

export function commandForCall(
  events: readonly { type: string; data?: unknown }[] | undefined,
  callId?: string,
): string | undefined {
  if (events === undefined || callId === undefined) return undefined;
  for (const event of events) {
    if (event.type !== 'tool/call') continue;
    const data = event.data as Record<string, unknown> | undefined;
    if (data === undefined || data.callId !== callId) continue;
    const raw = typeof data.arguments === 'string' ? data.arguments : '';
    const args = raw === '' ? undefined : parseArgsJson(raw);
    return args === undefined ? undefined : extractCommand(args);
  }
  return undefined;
}

export function filePathsForCall(
  events: readonly { type: string; data?: unknown }[] | undefined,
  callId?: string,
): string[] {
  if (events === undefined || callId === undefined) return [];
  for (const event of events) {
    if (event.type !== 'tool/call') continue;
    const data = event.data as Record<string, unknown> | undefined;
    if (data === undefined || data.callId !== callId) continue;
    const raw = typeof data.arguments === 'string' ? data.arguments : '';
    const args = raw === '' ? undefined : parseArgsJson(raw);
    return args === undefined ? [] : extractFilePaths(args);
  }
  return [];
}

export function changedFileCountOf(events: readonly { type: string; data?: unknown }[] | undefined): number {
  if (events === undefined) return 0;
  const seen = new Set<string>();
  for (const event of events) {
    if (event.type !== 'tool/call') continue;
    const data = event.data as Record<string, unknown> | undefined;
    if (data === undefined || typeof data.arguments !== 'string') continue;
    const args = parseArgsJson(data.arguments);
    if (args === undefined) continue;
    const path = extractFilePath(args);
    if (path !== undefined) seen.add(path);
  }
  return seen.size;
}
