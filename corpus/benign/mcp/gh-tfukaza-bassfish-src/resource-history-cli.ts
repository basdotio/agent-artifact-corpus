import { requireThat } from './domain.js';
import { boundedIntegerOption } from './cli-helpers.js';
import type { Call } from './cli-helpers.js';

export async function resourceHistoryCli(
  action: string,
  args: string[],
  resourceId: string,
  call: Call,
): Promise<unknown> {
  if (action === 'history') {
    const limit = boundedIntegerOption(args, '--limit', { min: 1, max: 100 }) ?? 100;
    const offset = boundedIntegerOption(args, '--offset', { min: 0 }) ?? 0;
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown history argument.');
    return call('listHistory', { resourceId, limit, offset });
  }
  const revision = args.shift();
  requireThat(
    revision && args.length === 0,
    'INVALID_ARGUMENT',
    `Pass a resource ID and revision for ${action}.`,
  );
  if (action === 'diff') return call('diffRevision', { resourceId, revision });
  const messages: unknown[] = [];
  let resource: unknown;
  let type = '';
  let body = '';
  let cursor: string | undefined;
  do {
    const page = await call<{
      page: {
        type: string;
        thread?: unknown;
        ticket?: unknown;
        messages?: unknown[];
        text?: string;
      };
      nextCursor: string | null;
    }>('readRevision', { resourceId, revision, ...(cursor ? { cursor } : {}) });
    type = page.page.type;
    resource ??= page.page.thread ?? page.page.ticket;
    if (page.page.messages) messages.unshift(...page.page.messages);
    body += page.page.text ?? '';
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return type === 'thread'
    ? { thread: resource, revision, messages }
    : { ticket: resource, revision, body };
}
