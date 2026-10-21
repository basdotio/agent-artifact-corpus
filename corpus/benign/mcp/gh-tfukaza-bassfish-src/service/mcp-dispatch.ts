import { mapAsync, filterAsync } from '../async.js';
import { BassfishError, type MutationResult, type Ticket } from '../domain.js';
import type { Mutation } from '../domain.js';
import { presentThread, presentTicket, presentTurnStatus } from '../mcp-presenters.js';
import type { Bassfish } from '../service.js';
import { ticketStatuses } from '../ticket.js';
import { bytes, pageBytes } from '../bounded.js';

function fit<T>(values: T[], present: (value: T) => Record<string, unknown>): T[] {
  const selected: T[] = [];
  for (const item of values) {
    if (bytes(selected.map(present).concat(present(item))) > pageBytes - 300) {
      if (!selected.length)
        throw new BassfishError(
          'RESPONSE_TOO_LARGE',
          'Resource metadata exceeds this page budget.',
        );
      break;
    }
    selected.push(item);
  }
  return selected;
}
import {
  compare,
  decodeCursor,
  describeTicket,
  describeTickets,
  encodeCursor,
  sortThreads,
} from './resources.js';

const followKey = (projectId: string, threadId: string, identityId: string): string =>
  `${projectId}:${threadId}:${identityId}`;
const mutation = (value: unknown): Mutation => value as Mutation;
export async function dispatchMcp(
  service: Bassfish,
  handle: string,
  name: string,
  args: Record<string, unknown>,
  signal?: AbortSignal,
  taskCapable = false,
): Promise<unknown> {
  switch (name) {
    case 'bindHostSession':
    case 'deliverHostNotifications':
      throw new BassfishError(
        'HOST_SESSION_UNAVAILABLE',
        'Host session binding is available only through a managed MCP adapter.',
      );
    case 'getUpdates':
      return service.updates.read(handle, args.cursor as string | undefined);
    case 'setAgentName': {
      const session = (await service.requestName(handle, args.name as string)) as {
        name: string;
      };
      return { agentName: session.name };
    }
    case 'notifications':
      return args.action === 'acknowledge'
        ? service.inbox.acknowledge(
            handle,
            String(args.batchToken),
            args.items as number[] | undefined,
          )
        : service.inbox.read(handle, args);
    case 'waitForWork':
      throw new BassfishError(
        'TASKS_REQUIRED',
        'waitForWork is available only through a Tasks-capable MCP connection.',
      );
    case 'findResources': {
      const actor = await service.control.view(async state => {
        const value = await service.actor(state, handle);
        await service.ready(state, value.projectId);
        return value;
      });
      const cursor = decodeCursor(args.cursor);
      if (args.resourceType === 'thread') {
        let threads = sortThreads(await service.content.listThreads(actor.projectId)).filter(
          thread => thread.state === (args.state ?? 'active'),
        );
        if (args.threadId) {
          const thread = threads.find(value => value.id === args.threadId);
          if (!thread) throw new BassfishError('NOT_FOUND', 'Thread not found in this project.');
          return {
            resource: presentThread({
              ...thread,
              following: await service.control.view(async state =>
                Boolean(
                  await state.get(
                    'follows',
                    followKey(actor.projectId, thread.id, actor.identityId),
                  ),
                ),
              ),
            }),
          };
        }
        if (args.query) {
          const query = String(args.query).toLowerCase();
          threads = threads.filter(thread =>
            [thread.title, thread.description].some(value => value.toLowerCase().includes(query)),
          );
        }
        if (args.following !== undefined) {
          threads = await filterAsync(
            threads,
            async thread =>
              Boolean(
                await service.control.view(
                  async state =>
                    await state.get(
                      'follows',
                      followKey(actor.projectId, thread.id, actor.identityId),
                    ),
                ),
              ) === args.following,
          );
        }
        if (cursor) {
          threads = threads.filter(
            thread =>
              thread.createdAt > cursor[0] ||
              (thread.createdAt === cursor[0] && thread.id > cursor[1]),
          );
        }
        const limit = args.limit as number;
        const page = fit(threads.slice(0, limit), presentThread);
        const last = page.at(-1);
        return {
          resources: await mapAsync(page, async thread =>
            presentThread({
              ...thread,
              following: await service.control.view(async state =>
                Boolean(
                  await state.get(
                    'follows',
                    followKey(actor.projectId, thread.id, actor.identityId),
                  ),
                ),
              ),
            }),
          ),
          nextCursor:
            threads.length > page.length && last ? encodeCursor([last.createdAt, last.id]) : null,
        };
      }
      if (args.resourceType === 'ticket') {
        const allTickets = await service.content.listTicketMetadata(actor.projectId);
        let tickets = allTickets;
        if (args.ticketId) {
          const ticket = tickets.find(value => value.id === args.ticketId);
          if (!ticket) throw new BassfishError('NOT_FOUND', 'Ticket not found in this project.');
          return { resource: presentTicket(describeTicket(ticket, allTickets)) };
        }
        const states = (args.states as Ticket['state'][] | undefined) ?? [
          'todo',
          'in_progress',
          'blocked',
        ];
        tickets = tickets.filter(ticket => states.includes(ticket.state));
        if (args.query) {
          const query = String(args.query).toLowerCase();
          tickets = tickets.filter(ticket =>
            [ticket.title, ticket.description].some(value => value.toLowerCase().includes(query)),
          );
        }
        if (args.owner) {
          const owner = await service.ticketOwner(actor.projectId, args.owner as string);
          tickets = tickets.filter(ticket => ticket.owner === owner.id);
        }
        if (args.ready !== undefined) {
          const statuses = ticketStatuses(allTickets);
          tickets = tickets.filter(ticket => statuses.get(ticket.id)!.ready === args.ready);
        }
        tickets.sort((a, b) => compare(a.createdAt, b.createdAt) || compare(a.id, b.id));
        if (cursor) {
          tickets = tickets.filter(
            ticket =>
              ticket.createdAt > cursor[0] ||
              (ticket.createdAt === cursor[0] && ticket.id > cursor[1]),
          );
        }
        const limit = args.limit as number;
        const metadata = new Map(describeTickets(allTickets).map(ticket => [ticket.id, ticket]));
        const page = fit(tickets.slice(0, limit), t => presentTicket(metadata.get(t.id)));
        const last = page.at(-1);
        return {
          resources: page.map(ticket => presentTicket(metadata.get(ticket.id))),
          nextCursor:
            tickets.length > page.length && last ? encodeCursor([last.createdAt, last.id]) : null,
        };
      }
      throw new BassfishError(
        'RESOURCE_TYPE_MISMATCH',
        'Discovery requires a thread or ticket target.',
      );
    }
    case 'createResource': {
      if (args.resourceType === 'thread') {
        const result = (await service.createThread(
          handle,
          args.title as string,
          args.description as string,
        )) as MutationResult & {
          threadId: string;
        };
        return { threadId: result.threadId, revision: result.revision };
      }
      if (args.resourceType === 'ticket') {
        const result = (await service.createTicket(handle, {
          title: args.title as string,
          description: args.description as string,
          owner: args.owner as string,
          state: (args.state as Ticket['state'] | undefined) ?? 'todo',
          body: (args.body as string | undefined) ?? '',
          dependsOn: (args.dependsOn as string[] | undefined) ?? [],
        })) as MutationResult & {
          ticketId: string;
        };
        return { ticketId: result.ticketId, revision: result.revision };
      }
      throw new BassfishError(
        'RESOURCE_TYPE_MISMATCH',
        'Creation requires a thread or ticket target.',
      );
    }
    case 'acquireTurn':
      return service.acquireMcpTurn(handle, args, signal, taskCapable);
    case 'cancelTurn':
      return presentTurnStatus(
        await service.cancelTurnRequest(handle, args.requestToken as string),
      );
    case 'readResource':
      return service.reads.read(handle, args);
    case 'commitTurn': {
      const credential = await service.mcpTurnCredential(handle, args.turnToken as string);
      const result = await service.commitTurn(
        handle,
        credential.id,
        credential.fencingToken,
        credential.baseRevision,
        mutation(args.mutation),
      );
      return credential.resourceType === 'thread'
        ? {
            threadId: credential.resourceId,
            revision: result.revision,
            ...(result.messageId ? { messageId: result.messageId, sequence: result.sequence } : {}),
          }
        : { ticketId: credential.resourceId, revision: result.revision };
    }
    case 'releaseTurn': {
      const file = await service.control.view(async state =>
        (await state.all('requests')).find(
          request => request.turnId === args.turnToken && request.resourceType === 'files',
        ),
      );
      if (file) return await service.releaseFiles(handle, args.turnToken as string);
      const credential = await service.mcpTurnCredential(handle, args.turnToken as string);
      await service.releaseTurn(handle, credential.id, credential.fencingToken);
      return { released: true };
    }
  }
  throw new BassfishError('UNKNOWN_TOOL', 'Unknown Bassfish MCP operation.');
}
