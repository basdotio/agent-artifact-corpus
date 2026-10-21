import { resourceHistoryCli } from './resource-history-cli.js';
import { spawn } from 'node:child_process';
import { chmod, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { BassfishError, requireThat } from './domain.js';
import { booleanFlag, boundedIntegerOption, take } from './cli-helpers.js';
import type { Call } from './cli-helpers.js';
async function stdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString('utf8');
}
async function source(args: string[], dataDir: string, initial = ''): Promise<string> {
  const file = take(args, '--file');
  const useEditor = booleanFlag(args, '--editor');
  requireThat(
    (file === undefined ? 0 : 1) + (useEditor ? 1 : 0) === 1,
    'INVALID_ARGUMENT',
    'Choose exactly one of --file PATH, --file -, or --editor.',
  );
  if (!useEditor) return file === '-' ? stdin() : await readFile(file!, 'utf8');
  const editor = process.env.VISUAL ?? process.env.EDITOR;
  requireThat(editor, 'EDITOR_UNAVAILABLE', 'Set VISUAL or EDITOR to an executable path.');
  const directory = await mkdtemp(join(dataDir, 'ticket-editor-'));
  const path = join(directory, 'ticket.md');
  try {
    await chmod(directory, 0o700);
    await writeFile(path, initial, { mode: 0o600 });
    const code = await new Promise<number | null>((resolve, reject) => {
      const child = spawn(editor, [path], { stdio: 'inherit' });
      child.once('error', reject);
      child.once('exit', resolve);
    });
    requireThat(code === 0, 'EDITOR_FAILED', 'The editor exited without saving successfully.');
    return await readFile(path, 'utf8');
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}
async function acquire(
  call: Call,
  id: string,
): Promise<{
  turnToken: string;
  resource: Record<string, unknown>;
  text: string;
  nextCursor: string | null;
}> {
  const result = await call<Record<string, unknown>>('acquireTurn', {
    target: { type: 'ticket', ticketId: id },
    timeoutMs: 0,
  });
  if (result.state !== 'claimed') {
    if (typeof result.requestToken === 'string')
      await call('cancelTurn', { requestToken: result.requestToken });
    throw new BassfishError(
      'TURN_BUSY',
      'Ticket is busy. This request was cancelled, not retried.',
    );
  }
  return result as never;
}
async function fullBody(
  call: Call,
  target: { turnToken?: string; resourceId?: string },
  first?: { body?: Array<{ text: string }>; nextCursor: string | null },
): Promise<string> {
  let page =
    first ??
    (await call<{ body?: Array<{ text: string }>; nextCursor: string | null }>(
      'readResource',
      target,
    ));
  let text = (page.body ?? []).map(p => p.text).join('');
  while (page.nextCursor) {
    page = await call('readResource', { ...target, cursor: page.nextCursor });
    text += (page.body ?? []).map(p => p.text).join('');
  }
  return text;
}
async function mutate(call: Call, id: string, mutation: Record<string, unknown>): Promise<unknown> {
  const turn = await acquire(call, id);
  let consumed = false;
  try {
    await fullBody(call, { turnToken: turn.turnToken });
    const value = await call('commitTurn', { turnToken: turn.turnToken, mutation });
    consumed = true;
    return value;
  } finally {
    if (!consumed) await call('releaseTurn', { turnToken: turn.turnToken }).catch(() => {});
  }
}
export async function runTicketCli(
  action: string | undefined,
  args: string[],
  call: Call,
  dataDir: string,
  historyCall: Call = call,
): Promise<{
  value?: unknown;
  raw?: string;
}> {
  await mkdir(dataDir, { recursive: true, mode: 0o700 });
  if (action === 'list' || action === 'search') {
    const query = action === 'search' ? args.shift() : undefined;
    const owner = take(args, '--owner');
    const state = take(args, '--state');
    const ready = booleanFlag(args, '--ready') ? true : undefined;
    const limit = boundedIntegerOption(args, '--limit', { min: 1, max: 50 }) ?? 20;
    const cursor = take(args, '--cursor');
    requireThat(action !== 'search' || query, 'INVALID_ARGUMENT', 'Use ticket search QUERY.');
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown ticket list/search argument.');
    return {
      value: await call('findResources', {
        resourceType: 'ticket',
        ...(query ? { query } : {}),
        ...(owner ? { owner } : {}),
        ...(state ? { states: state.split(',') } : {}),
        ...(ready !== undefined ? { ready } : {}),
        limit,
        ...(cursor ? { cursor } : {}),
      }),
    };
  }
  if (action === 'create') {
    const title = args.shift();
    const description = take(args, '--description');
    const owner = take(args, '--owner');
    const state = take(args, '--state') ?? 'todo';
    const dependsOn = (take(args, '--depends-on') ?? '').split(',').filter(Boolean);
    const body = args.some(value => value === '--file' || value === '--editor')
      ? await source(args, dataDir)
      : '';
    requireThat(
      title && description !== undefined && owner,
      'INVALID_ARGUMENT',
      'Use ticket create TITLE --description TEXT --owner NAME [--state STATE] [--depends-on IDS] [--file PATH|--editor].',
    );
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown ticket create argument.');
    return {
      value: await call('createResource', {
        resourceType: 'ticket',
        title,
        description,
        owner,
        state,
        dependsOn,
        body,
      }),
    };
  }
  const id = args.shift();
  requireThat(id, 'INVALID_ARGUMENT', 'Pass a ticket ID.');
  if (['history', 'revision', 'diff'].includes(action ?? ''))
    return { value: await resourceHistoryCli(action!, args, id, historyCall) };
  if (action === 'show') {
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown ticket show argument.');
    const page = await call<{
      resource: Record<string, unknown>;
      revision: string;
      body?: Array<{ text: string }>;
      nextCursor: string | null;
    }>('readResource', { resourceId: id });
    const metadata = await historyCall<{ page: { ticket: Record<string, unknown> } }>(
      'readRevision',
      {
        resourceId: id,
        revision: page.revision,
      },
    );
    return {
      value: {
        ticket: { ...page.resource, ...metadata.page.ticket },
        body: await fullBody(call, { resourceId: id }, page),
      },
    };
  }
  if (action === 'update') {
    const title = take(args, '--title');
    const description = take(args, '--description');
    const owner = take(args, '--owner');
    const state = take(args, '--state');
    const dependencies = take(args, '--depends-on');
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown ticket update argument.');
    const mutation = {
      kind: 'updateTicket',
      ...(title ? { title } : {}),
      ...(description !== undefined ? { description } : {}),
      ...(owner ? { owner } : {}),
      ...(state ? { state } : {}),
      ...(dependencies !== undefined ? { dependsOn: dependencies.split(',').filter(Boolean) } : {}),
    };
    requireThat(
      Object.keys(mutation).length > 1,
      'INVALID_ARGUMENT',
      'Provide ticket metadata to change.',
    );
    return { value: await mutate(call, id, mutation) };
  }
  if (['edit', 'append', 'patch'].includes(action ?? '')) {
    if (action === 'edit' && args.includes('--editor')) {
      const first = await acquire(call, id);
      const original = await fullBody(call, { turnToken: first.turnToken });
      await call('releaseTurn', { turnToken: first.turnToken });
      const body = await source(args, dataDir, original);
      requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown ticket edit argument.');
      return { value: await mutate(call, id, { kind: 'replaceTicketBody', body }) };
    }
    const body = await source(args, dataDir);
    requireThat(args.length === 0, 'INVALID_ARGUMENT', `Unknown ticket ${action} argument.`);
    return {
      value: await mutate(call, id, {
        kind:
          action === 'edit'
            ? 'replaceTicketBody'
            : action === 'append'
              ? 'appendTicketBody'
              : 'patchTicketBody',
        [action === 'patch' ? 'patch' : 'body']: body,
      }),
    };
  }
  throw new BassfishError('INVALID_ARGUMENT', 'Unknown ticket command.');
}
