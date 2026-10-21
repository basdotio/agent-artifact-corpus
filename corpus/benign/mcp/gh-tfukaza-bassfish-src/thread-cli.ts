import { resourceHistoryCli } from './resource-history-cli.js';
import { BassfishError, requireThat } from './domain.js';
import {
  acquire,
  booleanFlag,
  boundedIntegerOption,
  mutation,
  release,
  take,
} from './cli-helpers.js';
import type { Call, CliInteraction } from './cli-helpers.js';
import { cancelledResult } from './cli-output.js';
function threadState(args: string[]): 'active' | 'archived' | 'deleted' {
  const archived = booleanFlag(args, '--archived');
  const deleted = booleanFlag(args, '--deleted');
  requireThat(
    !(archived && deleted),
    'INVALID_ARGUMENT',
    'Choose at most one of --archived or --deleted.',
  );
  return archived ? 'archived' : deleted ? 'deleted' : 'active';
}
function limit(args: string[]): number | undefined {
  return boundedIntegerOption(args, '--limit', { min: 1 });
}
export async function runThreadCli(
  action: string | undefined,
  args: string[],
  call: Call,
  interaction?: CliInteraction,
): Promise<unknown> {
  if (action === 'list') {
    const state = threadState(args);
    const input = {
      state,
      limit: limit(args),
      cursor: take(args, '--cursor'),
      creatorIdentityId: take(args, '--creator'),
      titlePrefix: take(args, '--title-prefix'),
    };
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown thread list argument.');
    return await call('listThreads', input);
  }
  if (action === 'create') {
    const description = take(args, '--description') ?? '';
    const title = args.shift();
    requireThat(title && args.length === 0, 'INVALID_ARGUMENT', 'Pass one quoted thread title.');
    return await call('createThread', { title, description });
  }
  if (action === 'search') {
    const query = args.shift();
    const state = threadState(args);
    const input = { query, state, limit: limit(args) };
    requireThat(
      query && args.length === 0,
      'INVALID_ARGUMENT',
      'Use thread search QUERY [--archived|--deleted] [--limit N].',
    );
    return await call('searchThreads', input);
  }
  const id = args.shift();
  requireThat(id, 'INVALID_ARGUMENT', 'Pass a thread ID.');
  if (action === 'get') {
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown thread get argument.');
    return await call('getThread', { threadId: id });
  }
  if (action === 'show') {
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown thread show argument.');
    const turn = await acquire(call, 'thread', id);
    try {
      return turn;
    } finally {
      await release(call, turn);
    }
  }
  if (action === 'rename') {
    const title = args.shift();
    requireThat(
      title && args.length === 0,
      'INVALID_ARGUMENT',
      'Use thread rename THREAD_ID TITLE.',
    );
    return mutation(call, 'thread', id, { kind: 'renameThread', title });
  }
  if (action === 'describe') {
    const description = take(args, '--description');
    const clear = booleanFlag(args, '--clear');
    requireThat(
      (description !== undefined) !== clear && args.length === 0,
      'INVALID_ARGUMENT',
      'Use thread describe THREAD_ID (--description TEXT | --clear).',
    );
    return mutation(call, 'thread', id, {
      kind: 'setThreadDescription',
      description: description ?? '',
    });
  }
  if (action === 'follow' || action === 'unfollow') {
    requireThat(args.length === 0, 'INVALID_ARGUMENT', `Unknown thread ${action} argument.`);
    return await call(action === 'follow' ? 'followThread' : 'unfollowThread', { threadId: id });
  }
  if (action === 'archive' || action === 'activate') {
    requireThat(args.length === 0, 'INVALID_ARGUMENT', `Unknown thread ${action} argument.`);
    return mutation(call, 'thread', id, {
      kind: action === 'archive' ? 'archiveThread' : 'activateThread',
    });
  }
  if (action === 'delete') {
    const confirmed = booleanFlag(args, '--yes');
    requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Use thread delete THREAD_ID [--yes].');
    requireThat(
      confirmed || interaction?.interactive,
      'CONFIRMATION_REQUIRED',
      'Use thread delete THREAD_ID --yes outside an interactive terminal.',
    );
    if (!confirmed) {
      const current = await call('getThread', { threadId: id });
      if (
        !(await interaction!.confirm('Delete this thread?', {
          request: { command: 'thread', action: 'get' },
          value: current,
        }))
      )
        return cancelledResult;
    }
    return mutation(call, 'thread', id, { kind: 'deleteThread' });
  }
  if (action === 'retract' || action === 'reinstate') {
    const messageId = args.shift();
    requireThat(
      messageId && args.length === 0,
      'INVALID_ARGUMENT',
      `Use thread ${action} THREAD_ID MESSAGE_ID.`,
    );
    return mutation(call, 'thread', id, {
      kind: action === 'retract' ? 'retractMessage' : 'reinstateMessage',
      messageId,
    });
  }
  if (['history', 'revision', 'diff'].includes(action ?? ''))
    return resourceHistoryCli(action!, args, id, call);
  throw new BassfishError('INVALID_ARGUMENT', 'Unknown thread command.');
}
