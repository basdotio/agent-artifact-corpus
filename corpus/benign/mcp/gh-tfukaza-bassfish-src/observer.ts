import { mapAsync } from './async.js';
import { z } from 'zod';
import { activeStates, BassfishError, reservedStates } from './domain.js';
import type { ControlState, FileTurnRequest, TurnRequest } from './domain.js';
import { fileSetsOverlap } from './files.js';
import { TursoControl } from './storage/coordination.js';
import type { TursoContent } from './storage/content.js';
import type { ObservationFilter } from './storage/observation-content.js';
import type {
  ObservationSnapshot,
  ObservedAgent,
  ObservedTicketDetail,
  ObservedTurn,
} from './observation-types.js';
const cursor = z.string().regex(/^\d{1,30}$/);
const revision = cursor.optional();
const filterSchema = z
  .object({
    threadOffset: z.number().int().min(0).max(1000000).optional(),
    ticketOffset: z.number().int().min(0).max(1000000).optional(),
    agentOffset: z.number().int().min(0).max(1000000).optional(),
    turnOffset: z.number().int().min(0).max(1000000).optional(),
    query: z.string().max(200).optional(),
    threadState: z.enum(['active', 'archived', 'deleted', 'all']).optional(),
    ticketState: z.enum(['todo', 'in_progress', 'blocked', 'done', 'all']).optional(),
    owner: z.string().max(64).optional(),
  })
  .strict();
export const observerOpenSchema = z
  .object({ workspace: z.string().min(1).max(4096), protocolVersion: z.literal(2) })
  .strict();
export const observationReadSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('snapshot'), filter: filterSchema.optional() }).strict(),
  z.object({ kind: z.literal('content'), filter: filterSchema.optional() }).strict(),
  z
    .object({
      kind: z.literal('thread'),
      id: z.string().min(1).max(200),
      revision,
      before: cursor.optional(),
    })
    .strict(),
  z
    .object({
      kind: z.literal('ticket'),
      id: z.string().min(1).max(200),
      revision,
      cursor: z.string().max(4096).optional(),
    })
    .strict(),
  z
    .object({
      kind: z.literal('graph'),
      id: z.string().min(1).max(200),
      focused: z.boolean().optional(),
    })
    .strict(),
  z
    .object({
      kind: z.literal('activity'),
      before: cursor.optional(),
      actor: z.string().max(64).optional(),
      resourceId: z.string().max(200).optional(),
      eventKind: z.string().max(100).optional(),
    })
    .strict(),
  z
    .object({
      kind: z.literal('files'),
      id: z.string().min(1).max(200),
      pathOffset: z.number().int().min(0).max(1000000).optional(),
      blockerOffset: z.number().int().min(0).max(1000000).optional(),
    })
    .strict(),
  z
    .object({
      kind: z.literal('event'),
      id: z.string().min(1).max(200),
      pathOffset: z.number().int().min(0).max(1000000).optional(),
    })
    .strict(),
]);
export type ObservationRead = z.infer<typeof observationReadSchema>;
export const observationWaitSchema = z
  .object({ cursor, timeoutMs: z.number().int().min(0).max(20000).default(20000) })
  .strict();
export type ObservationReader = Pick<
  TursoContent,
  'observeContent' | 'observeGraph' | 'snapshot' | 'ticketSnapshot'
>;
async function observeTurn(
  state: ControlState,
  request: TurnRequest,
  pathOffset = 0,
  blockerOffset = 0,
): Promise<ObservedTurn> {
  const blockers =
    request.resourceType === 'files' && request.state === 'QUEUED'
      ? (await state.all('requests')).filter(
          (other): other is FileTurnRequest =>
            other.resourceType === 'files' &&
            other.id !== request.id &&
            activeStates.includes(other.state) &&
            fileSetsOverlap(other.paths, request.paths) &&
            (reservedStates.includes(other.state) ||
              (other.state === 'QUEUED' && BigInt(other.sequence) < BigInt(request.sequence))),
        )
      : [];
  return {
    id: request.id,
    projectId: request.projectId,
    resourceType: request.resourceType,
    ...(request.resourceType === 'files'
      ? {
          paths: request.paths.slice(pathOffset, pathOffset + 8),
          pathCount: request.paths.length,
          nextPathOffset: pathOffset + 8 < request.paths.length ? pathOffset + 8 : null,
        }
      : { resourceId: request.resourceId, expiresAt: request.expiresAt }),
    state: request.state,
    owner: (await state.get('identities', request.identityId))?.name ?? 'Unknown',
    identityId: request.identityId,
    workspace: (await state.get('instances', request.instanceId))?.workspace ?? '',
    createdAt: request.createdAt,
    claimedAt: request.claimedAt,
    blockerCount: blockers.length,
    nextBlockerOffset: blockerOffset + 8 < blockers.length ? blockerOffset + 8 : null,
    blockers: await mapAsync(blockers.slice(blockerOffset, blockerOffset + 8), async other => {
      const overlaps = other.paths.filter(
        path => request.resourceType === 'files' && fileSetsOverlap([path], request.paths),
      );
      return {
        id: other.id,
        owner: (await state.get('identities', other.identityId))?.name ?? 'Unknown',
        project: (await state.get('projects', other.projectId))?.commonDir ?? '',
        paths: overlaps.slice(0, 1),
        overlapCount: overlaps.length,
        reason: other.state === 'QUEUED' ? ('earlier_request' as const) : ('held' as const),
      };
    }),
  };
}
async function boundedPage<T>(
  items: T[],
  offset: number,
  map: (item: T) => unknown,
  budget: number,
): Promise<{ rows: unknown[]; next: number | null }> {
  const rows: unknown[] = [];
  let bytes = 0;
  for (const item of items.slice(offset, offset + 100)) {
    const row = await map(item),
      size = Buffer.byteLength(JSON.stringify(row));
    if (rows.length && bytes + size > budget) break;
    rows.push(row);
    bytes += size;
  }
  return { rows, next: offset + rows.length < items.length ? offset + rows.length : null };
}
export class ProjectObserver {
  constructor(
    private readonly control: TursoControl,
    private readonly content: ObservationReader,
    readonly epoch: string,
  ) {}
  private async project(commonDir: string) {
    return await this.control.view(async s =>
      (await s.all('projects')).find(p => p.commonDir === commonDir),
    );
  }
  async snapshot(commonDir: string, filter: ObservationFilter = {}): Promise<ObservationSnapshot> {
    return this.control.readTransaction(async () => {
      // Cursor precedes capture: any changes during SQL reads are replayed on the next wait.
      const cursor = await this.control.activity.head();
      const state = await this.control.view(s => s);
      const project = (await state.all('projects')).find(p => p.commonDir === commonDir) ?? null;
      const at = Date.now();
      if (!project)
        return {
          protocolVersion: 2,
          epoch: this.epoch,
          cursor,
          at,
          project,
          status: 'empty',
          agents: [],
          turns: [],
          content: null,
          activity: null,
        };
      const agents: ObservedAgent[] = await mapAsync(
        (await state.all('identities')).filter(i => i.projectId === project.id),
        async identity => {
          const instances = (await state.all('instances'))
            .filter(i => i.identityId === identity.id)
            .sort((a, b) => Number(b.active) - Number(a.active) || b.lastSeen - a.lastSeen);
          const latest = instances[0];
          return {
            id: identity.id,
            name: identity.name,
            online: Boolean(latest?.active),
            lastSeen: latest?.lastSeen ?? null,
            host: latest?.host ?? null,
            workspace: latest?.workspace ?? null,
          };
        },
      );
      agents.sort((a, b) => Number(b.online) - Number(a.online) || a.id.localeCompare(b.id));
      const requests = (await state.all('requests'))
        .filter(r => r.projectId === project.id && activeStates.includes(r.state))
        .sort((a, b) => a.id.localeCompare(b.id));
      const agentPage = await boundedPage(agents, filter.agentOffset ?? 0, a => a, 100000);
      const turnPage = await boundedPage(
        requests,
        filter.turnOffset ?? 0,
        async r => await observeTurn(state, r),
        350000,
      );
      const result: ObservationSnapshot = {
        protocolVersion: 2,
        epoch: this.epoch,
        cursor,
        at,
        project,
        status: 'ready',
        agents: agentPage.rows as ObservedAgent[],
        turns: turnPage.rows as ObservedTurn[],
        coordinationTotals: {
          agents: agents.length,
          online: agents.filter(a => a.online).length,
          turns: requests.length,
          files: requests.filter(r => r.resourceType === 'files').length,
        },
        nextAgentOffset: agentPage.next,
        nextTurnOffset: turnPage.next,
        content: null,
        activity: await this.control.activity.page({ projectId: project.id }),
      };
      try {
        result.content = await this.content.observeContent(project.id, {
          threadState: 'active',
          ...filter,
        });
      } catch (error) {
        result.status = 'content_unavailable';
        result.contentError =
          error instanceof BassfishError ? error.code : 'Content storage unavailable';
      }
      return result;
    });
  }
  async read(commonDir: string, request: ObservationRead): Promise<unknown> {
    return this.control.readTransaction(async () => {
      if (request.kind === 'snapshot') return this.snapshot(commonDir, request.filter);
      const project = await this.project(commonDir);
      if (!project)
        throw new BassfishError(
          'NOT_FOUND',
          'No Bassfish activity has been recorded in this project.',
        );
      switch (request.kind) {
        case 'files':
          return await this.control.view(async state => {
            const turn = await state.get('requests', request.id);
            if (!turn || turn.projectId !== project.id || turn.resourceType !== 'files')
              throw new BassfishError(
                'NOT_FOUND',
                'Reservation no longer available. Open its retained activity event.',
              );
            return await observeTurn(state, turn, request.pathOffset, request.blockerOffset);
          });
        case 'event': {
          const event = await this.control.activity.event(
            project.id,
            request.id,
            request.pathOffset,
          );
          if (!event)
            throw new BassfishError('NOT_FOUND', 'Activity event is outside the retained history.');
          return event;
        }
        case 'content':
          return this.content.observeContent(project.id, request.filter ?? {});
        case 'thread': {
          const snapshot = await this.content.snapshot(
            project.id,
            request.id,
            50,
            request.before,
            request.revision,
          );
          let bytes = 0,
            start = snapshot.messages.length;
          for (let i = snapshot.messages.length - 1; i >= 0; i--) {
            const size = Buffer.byteLength(JSON.stringify(snapshot.messages[i]));
            if (start < snapshot.messages.length && bytes + size > 500000) break;
            bytes += size;
            start = i;
          }
          if (start > 0) {
            snapshot.messages = snapshot.messages.slice(start);
            snapshot.truncated = true;
            snapshot.nextBefore = snapshot.messages[0]!.sequence;
          }
          return snapshot;
        }
        case 'ticket': {
          const snapshot = await this.content.ticketSnapshot(
            project.id,
            request.id,
            request.cursor,
            request.revision,
          );
          const { body: _body, ...ticket } = snapshot.ticket;
          return { ...snapshot, ticket } satisfies ObservedTicketDetail;
        }
        case 'graph': {
          const graph = await this.content.observeGraph(project.id, request.id, request.focused);
          if (!request.focused && graph.tickets.length >= 200 && graph.hidden)
            return this.content.observeGraph(project.id, request.id, true);
          return graph;
        }
        case 'activity':
          return await this.control.activity.page({
            projectId: project.id,
            before: request.before,
            actor: request.actor,
            resourceId: request.resourceId,
            kind: request.eventKind,
          });
      }
    });
  }
  async wait(commonDir: string, after: string, timeoutMs: number, signal?: AbortSignal) {
    if ((await this.control.activity.head()) === after && timeoutMs > 0) {
      await new Promise<void>((resolve, reject) => {
        let timer: NodeJS.Timeout;
        const cleanup = () => {
          clearTimeout(timer);
          unsubscribe();
          signal?.removeEventListener('abort', abort);
        };
        const done = () => {
          cleanup();
          resolve();
        };
        const fail = (error: unknown) => {
          cleanup();
          reject(error);
        };
        const abort = () => fail(new BassfishError('CANCELLED', 'Observation cancelled.'));
        const unsubscribe = this.control.subscribe(done);
        timer = setTimeout(done, timeoutMs);
        if (signal?.aborted) abort();
        else {
          signal?.addEventListener('abort', abort, { once: true });
          void this.control.activity.head().then(head => {
            if (head !== after) done();
          }, fail);
        }
      });
    }
    const project = await this.project(commonDir);
    return {
      cursor: await this.control.activity.head(),
      epoch: this.epoch,
      at: Date.now(),
      gap: project ? await this.control.activity.gap(project.id, after) : false,
    };
  }
}
