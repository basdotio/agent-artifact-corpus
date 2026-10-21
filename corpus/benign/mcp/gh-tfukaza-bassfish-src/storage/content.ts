import { BassfishError, bodyPage, requireThat } from '../domain.js';
import type {
  ContentResourceType,
  ContentStore,
  HistoryEntry,
  Message,
  MutationResult,
  ProjectHistoryEntry,
  CurrentProject,
  Snapshot,
  StorageResult,
  Thread,
  Ticket,
  TicketSnapshot,
  WriteOperation,
} from '../domain.js';
import type { TursoStore, TursoTransaction } from './turso.js';
import type {
  ContentObservation,
  ObservationGraph,
  ObservedTicket,
  ObservedThread,
} from '../observation-types.js';
import type { ObservationFilter } from './observation-content.js';
import { ticketStatuses } from '../ticket.js';

const table = (type: ContentResourceType) =>
  type === 'thread' ? 'threadContent' : 'ticketContent';
const decode = <T>(row: { dataJson: string }): T => JSON.parse(row.dataJson) as T;

/** Current resources and immutable resource revisions share the coordination transaction. */
export class TursoContent implements ContentStore {
  constructor(readonly store: TursoStore) {}

  async ensureProject(projectId: string): Promise<void> {
    await this.store.read(async tx => {
      requireThat(
        await tx.get('SELECT id FROM projects WHERE id=?', projectId),
        'NOT_FOUND',
        'Project not found.',
      );
    });
  }

  async listThreads(projectId: string): Promise<Thread[]> {
    return this.store.read(async tx =>
      (
        await tx.all<{ dataJson: string }>(
          'SELECT dataJson FROM threadContent WHERE projectId=?',
          projectId,
        )
      ).map(decode<Thread>),
    );
  }

  async listTickets(projectId: string): Promise<Ticket[]> {
    return this.store.read(async tx =>
      (
        await tx.all<{ dataJson: string }>(
          'SELECT dataJson FROM ticketContent WHERE projectId=?',
          projectId,
        )
      ).map(decode<Ticket>),
    );
  }

  async listTicketMetadata(projectId: string): Promise<Ticket[]> {
    return this.store.read(async tx =>
      (
        await tx.all<{ dataJson: string }>(
          "SELECT json_remove(dataJson,'$.body') AS dataJson FROM ticketContent WHERE projectId=?",
          projectId,
        )
      ).map(row => ({ ...decode<Ticket>(row), body: '' })),
    );
  }

  async resourceType(projectId: string, resourceId: string): Promise<ContentResourceType> {
    return this.store.read(async tx => {
      if (
        await tx.get(
          'SELECT id FROM threadContent WHERE projectId=? AND id=?',
          projectId,
          resourceId,
        )
      )
        return 'thread';
      if (
        await tx.get(
          'SELECT id FROM ticketContent WHERE projectId=? AND id=?',
          projectId,
          resourceId,
        )
      )
        return 'ticket';
      throw new BassfishError('NOT_FOUND', 'Resource not found in this project.');
    });
  }

  private async resource<T extends Thread | Ticket>(
    tx: TursoTransaction,
    projectId: string,
    type: ContentResourceType,
    resourceId: string,
    revision?: string,
  ): Promise<T> {
    const row = revision
      ? await tx.get<{ dataJson: string }>(
          'SELECT dataJson FROM revisions WHERE projectId=? AND resourceId=? AND (revision=? OR operationId=?)',
          projectId,
          resourceId,
          revision,
          revision,
        )
      : await tx.get<{ dataJson: string }>(
          `SELECT dataJson FROM ${table(type)} WHERE projectId=? AND id=?`,
          projectId,
          resourceId,
        );
    requireThat(
      row,
      revision ? 'REVISION_NOT_FOUND' : 'NOT_FOUND',
      revision ? 'Resource revision not found.' : 'Resource not found.',
    );
    return decode<T>(row);
  }

  async messageAt(
    projectId: string,
    resourceId: string,
    messageId: string,
    revision: string,
  ): Promise<Message> {
    return this.store.read(async tx => {
      const thread = await this.resource<Thread>(tx, projectId, 'thread', resourceId, revision);
      const row = await tx.get<{ dataJson: string }>(
        'SELECT dataJson FROM messages WHERE threadId=? AND id=?',
        resourceId,
        messageId,
      );
      requireThat(row, 'NOT_FOUND', 'Message not found in this thread.');
      const message = decode<Message>(row);
      requireThat(
        BigInt(message.sequence) <= BigInt(thread.headSequence),
        'NOT_FOUND',
        'Message is newer than the pinned revision.',
      );
      const visibility = await tx.get<{ visible: number }>(
        `SELECT visible FROM messageVisibility WHERE messageId=? AND (length(revision)<length(?) OR (length(revision)=length(?) AND revision<=?)) ORDER BY length(revision) DESC,revision DESC LIMIT 1`,
        message.id,
        revision,
        revision,
        revision,
      );
      message.retracted = visibility?.visible === 0;
      if (message.retracted) message.body = '';
      return message;
    });
  }

  async threadDelta(
    projectId: string,
    resourceId: string,
    fromRevision: string,
    revision?: string,
    before?: string,
  ): Promise<Snapshot> {
    return this.store.read(async tx => {
      const from = await this.resource<Thread>(tx, projectId, 'thread', resourceId, fromRevision);
      const thread = await this.resource<Thread>(tx, projectId, 'thread', resourceId, revision);
      requireThat(
        BigInt(from.revision) <= BigInt(thread.revision),
        'INVALID_REVISION',
        'Delta starts after its target revision.',
      );
      const rows = await tx.all<{ id: string }>(
        `SELECT id FROM messages WHERE threadId=? AND
        (length(sequence)<length(?) OR (length(sequence)=length(?) AND sequence<=?)) AND
        ((length(sequence)>length(?) OR (length(sequence)=length(?) AND sequence>?)) OR EXISTS
          (SELECT 1 FROM messageVisibility v WHERE v.messageId=messages.id AND
           (length(v.revision)>length(?) OR (length(v.revision)=length(?) AND v.revision>?)) AND
           (length(v.revision)<length(?) OR (length(v.revision)=length(?) AND v.revision<=?))))
        ${before ? 'AND (length(sequence)<length(?) OR (length(sequence)=length(?) AND sequence<?))' : ''}
        ORDER BY length(sequence) DESC,sequence DESC LIMIT 21`,
        resourceId,
        thread.headSequence,
        thread.headSequence,
        thread.headSequence,
        from.headSequence,
        from.headSequence,
        from.headSequence,
        from.revision,
        from.revision,
        from.revision,
        thread.revision,
        thread.revision,
        thread.revision,
        ...(before ? [before, before, before] : []),
      );
      const messages: Message[] = [];
      for (const row of rows.slice(0, 20).reverse())
        messages.push(await this.messageAt(projectId, resourceId, row.id, thread.revision));
      return {
        resourceType: 'thread',
        thread,
        revision: thread.revision,
        messages,
        truncated: rows.length > 20,
        nextBefore: rows.length > 20 ? messages[0]!.sequence : null,
      };
    });
  }

  async snapshot(
    projectId: string,
    resourceId: string,
    limit: number,
    before?: string,
    revision?: string,
  ): Promise<Snapshot> {
    return this.store.read(async tx => {
      const thread = await this.resource<Thread>(tx, projectId, 'thread', resourceId, revision);
      // Counters are decimal strings. Length then lexicographic ordering avoids integer overflow.
      const rows = await tx.all<{ dataJson: string }>(
        `SELECT dataJson FROM messages WHERE threadId=? AND
        (length(sequence)<length(?) OR (length(sequence)=length(?) AND sequence<=?))
        ${before ? 'AND (length(sequence)<length(?) OR (length(sequence)=length(?) AND sequence<?))' : ''}
        ORDER BY length(sequence) DESC, sequence DESC LIMIT ?`,
        resourceId,
        thread.headSequence,
        thread.headSequence,
        thread.headSequence,
        ...(before ? [before, before, before] : []),
        limit + 1,
      );
      const messages = rows
        .slice(0, limit)
        .map(decode<Message>)
        .reverse();
      for (const message of messages) {
        const visibility = await tx.get<{ visible: number }>(
          `SELECT visible FROM messageVisibility WHERE messageId=? AND
          (length(revision)<length(?) OR (length(revision)=length(?) AND revision<=?))
          ORDER BY length(revision) DESC,revision DESC LIMIT 1`,
          message.id,
          thread.revision,
          thread.revision,
          thread.revision,
        );
        message.retracted = visibility?.visible === 0;
        if (message.retracted) message.body = '';
      }
      return {
        resourceType: 'thread',
        thread,
        revision: thread.revision,
        messages,
        truncated: rows.length > limit,
        nextBefore: rows.length > limit ? messages[0]!.sequence : null,
      };
    });
  }

  async ticketSnapshot(
    projectId: string,
    resourceId: string,
    cursor?: string,
    revision?: string,
  ): Promise<TicketSnapshot> {
    return this.store.read(async tx => {
      const ticket = await this.resource<Ticket>(tx, projectId, 'ticket', resourceId, revision);
      return {
        resourceType: 'ticket',
        ticket,
        revision: ticket.revision,
        page: bodyPage(ticket.body, cursor),
      };
    });
  }

  async write(operation: WriteOperation): Promise<StorageResult> {
    return this.store.write(async tx => {
      const receipt = await tx.get<{ resultJson: string }>(
        'SELECT resultJson FROM revisions WHERE operationId=?',
        operation.id,
      );
      if (receipt) return JSON.parse(receipt.resultJson) as MutationResult;
      const resource = operation.resourceType === 'thread' ? operation.thread : operation.ticket;
      const creating =
        operation.mutation.kind === 'createThread' || operation.mutation.kind === 'createTicket';
      const previousRevision = creating ? '0' : String(BigInt(resource.revision) - 1n);
      const result: MutationResult = {
        resourceId: resource.id,
        previousRevision,
        revision: resource.revision,
        operationId: operation.id,
      };
      if (creating)
        await tx.run(
          `INSERT INTO ${table(operation.resourceType)}(id,projectId,revision,dataJson) VALUES(?,?,?,?)`,
          resource.id,
          operation.actor.projectId,
          resource.revision,
          JSON.stringify(resource),
        );
      else {
        const changed = await tx.run(
          `UPDATE ${table(operation.resourceType)} SET revision=?,dataJson=? WHERE id=? AND projectId=? AND revision=?`,
          resource.revision,
          JSON.stringify(resource),
          resource.id,
          operation.actor.projectId,
          previousRevision,
        );
        requireThat(changed === 1, 'REVISION_CHANGED', 'The persisted resource revision changed.');
      }
      if (operation.resourceType === 'thread' && operation.mutation.kind === 'appendMessage') {
        const message: Message = {
          id: operation.id,
          threadId: resource.id,
          sequence: operation.thread.headSequence,
          identityId: operation.actor.identityId,
          name: operation.actor.name,
          instanceId: operation.actor.instanceId,
          createdAt: operation.at,
          body: operation.mutation.body,
          mentions: {
            agents: operation.mutation.mentions?.agents ?? [],
            here: operation.mutation.mentions?.here ?? false,
            global: operation.mutation.mentions?.global ?? false,
          },
        };
        await tx.run(
          'INSERT INTO messages(id,threadId,sequence,dataJson) VALUES(?,?,?,?)',
          message.id,
          message.threadId,
          message.sequence,
          JSON.stringify(message),
        );
        result.messageId = message.id;
        result.sequence = message.sequence;
      }
      const history: HistoryEntry = {
        operationId: operation.id,
        kind: operation.mutation.kind,
        actorIdentityId: operation.actor.identityId,
        actorName: operation.actor.name,
        instanceId: operation.actor.instanceId,
        createdAt: operation.at,
        reason: null,
        beforeRevision: previousRevision,
        afterRevision: resource.revision,
      };
      await tx.run(
        'INSERT INTO revisions(operationId,projectId,resourceId,resourceType,revision,at,dataJson,historyJson,resultJson) VALUES(?,?,?,?,?,?,?,?,?)',
        operation.id,
        operation.actor.projectId,
        resource.id,
        operation.resourceType,
        resource.revision,
        operation.at,
        JSON.stringify(resource),
        JSON.stringify(history),
        JSON.stringify(result),
      );
      if (
        operation.resourceType === 'thread' &&
        (operation.mutation.kind === 'retractMessage' ||
          operation.mutation.kind === 'reinstateMessage')
      ) {
        requireThat(
          await tx.get(
            'SELECT id FROM messages WHERE id=? AND threadId=?',
            operation.mutation.messageId,
            resource.id,
          ),
          'NOT_FOUND',
          'Message not found in this thread.',
        );
        await tx.run(
          'INSERT INTO messageVisibility(operationId,threadId,messageId,revision,visible) VALUES(?,?,?,?,?)',
          operation.id,
          resource.id,
          operation.mutation.messageId,
          resource.revision,
          Number(operation.mutation.kind === 'reinstateMessage'),
        );
      }
      return result;
    });
  }

  async history(
    projectId: string,
    _type: ContentResourceType,
    resourceId: string,
  ): Promise<HistoryEntry[]> {
    return this.store.read(async tx =>
      (
        await tx.all<{ historyJson: string }>(
          'SELECT historyJson FROM revisions WHERE projectId=? AND resourceId=? ORDER BY length(revision) DESC,revision DESC',
          projectId,
          resourceId,
        )
      ).map(row => JSON.parse(row.historyJson) as HistoryEntry),
    );
  }

  async projectSnapshot(projectId: string): Promise<CurrentProject> {
    return this.store.read(async tx => {
      const threads = await this.listThreads(projectId),
        tickets = await this.listTickets(projectId);
      const messages = (
        await tx.all<{ dataJson: string }>(
          'SELECT m.dataJson FROM messages m JOIN threadContent t ON t.id=m.threadId WHERE t.projectId=? ORDER BY m.threadId,length(m.sequence),m.sequence',
          projectId,
        )
      ).map(decode<Message>);
      const visibility = await tx.all<{
        operationId: string;
        threadId: string;
        messageId: string;
        revision: string;
        visible: number;
        at: string;
      }>(
        'SELECT v.*,r.at FROM messageVisibility v JOIN revisions r ON r.operationId=v.operationId JOIN threadContent t ON t.id=v.threadId WHERE t.projectId=? ORDER BY length(v.revision),v.revision',
        projectId,
      );
      return {
        exportedAt: new Date().toISOString(),
        threads,
        tickets,
        messages,
        visibility: visibility.map(v => ({
          operationId: v.operationId,
          threadId: v.threadId,
          messageId: v.messageId,
          threadRevision: v.revision,
          visible: Boolean(v.visible),
          createdAt: v.at,
        })),
      };
    });
  }

  async projectHistory(projectId: string): Promise<ProjectHistoryEntry[]> {
    return this.store.read(async tx =>
      (
        await tx.all<{
          historyJson: string;
          resourceId: string;
          resourceType: ContentResourceType;
          revision: string;
        }>(
          'SELECT historyJson,resourceId,resourceType,revision FROM revisions WHERE projectId=? ORDER BY at DESC,operationId DESC',
          projectId,
        )
      ).map(
        ({ historyJson, ...resource }) =>
          ({ ...JSON.parse(historyJson), ...resource }) as ProjectHistoryEntry,
      ),
    );
  }

  async observeContent(projectId: string, filter: ObservationFilter): Promise<ContentObservation> {
    return this.store.read(async tx => {
      let threads = await this.listThreads(projectId),
        tickets = await this.observedTickets(projectId);

      if (filter.threadState && filter.threadState !== 'all')
        threads = threads.filter(t => t.state === filter.threadState);
      if (filter.ticketState && filter.ticketState !== 'all')
        tickets = tickets.filter(t => t.state === filter.ticketState);
      if (filter.owner)
        tickets = tickets.filter(t => t.ownerName.toLowerCase() === filter.owner!.toLowerCase());
      if (filter.query) {
        const query = filter.query.toLowerCase();
        threads = threads.filter(t => `${t.title}\n${t.description}`.toLowerCase().includes(query));
        tickets = tickets.filter(t => `${t.title}\n${t.description}`.toLowerCase().includes(query));
      }
      const updated = new Map(
        (
          await tx.all<{ resourceId: string; at: string }>(
            'SELECT resourceId,MAX(at) AS at FROM revisions WHERE projectId=? GROUP BY resourceId',
            projectId,
          )
        ).map(row => [row.resourceId, row.at]),
      );
      threads.sort(
        (a, b) =>
          (updated.get(b.id) ?? b.createdAt).localeCompare(updated.get(a.id) ?? a.createdAt) ||
          a.id.localeCompare(b.id),
      );
      tickets.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt) || a.id.localeCompare(b.id));
      const threadOffset = filter.threadOffset ?? 0,
        ticketOffset = filter.ticketOffset ?? 0;
      const bytePage = <T>(values: T[]): T[] => {
        const result: T[] = [];
        let bytes = 0;
        for (const value of values) {
          bytes += Buffer.byteLength(JSON.stringify(value));
          if (result.length && bytes > 350_000) break;
          result.push(value);
        }
        return result;
      };
      const threadPage = bytePage(
        await Promise.all(
          threads
            .slice(threadOffset, threadOffset + 100)
            .map(async (thread): Promise<ObservedThread> => {
              const snapshot = await this.snapshot(projectId, thread.id, 1);
              const latest = snapshot.messages[0];
              const authors = await tx.all<{ name: string }>(
                "SELECT DISTINCT json_extract(dataJson,'$.name') AS name FROM messages WHERE threadId=? ORDER BY name LIMIT 64",
                thread.id,
              );
              return {
                ...thread,
                updatedAt: updated.get(thread.id) ?? thread.createdAt,
                latestAuthor: latest?.name ?? null,
                preview: latest?.retracted ? '[retracted]' : (latest?.body.slice(0, 180) ?? ''),
                participants: authors.map(a => a.name),
              };
            }),
        ),
      );
      const ticketPage = bytePage(tickets.slice(ticketOffset, ticketOffset + 100));
      return {
        totals: {
          threads: threads.length,
          tickets: tickets.length,
          states: Object.fromEntries(
            ['todo', 'in_progress', 'blocked', 'done'].map(state => [
              state,
              tickets.filter(t => t.state === state).length,
            ]),
          ),
        },
        threads: threadPage,
        tickets: ticketPage,
        nextThreadOffset:
          threadOffset + threadPage.length < threads.length
            ? threadOffset + threadPage.length
            : null,
        nextTicketOffset:
          ticketOffset + ticketPage.length < tickets.length
            ? ticketOffset + ticketPage.length
            : null,
      };
    });
  }

  private async observedTickets(projectId: string): Promise<ObservedTicket[]> {
    const tickets = await this.listTickets(projectId),
      statuses = ticketStatuses(tickets);
    return tickets.map(({ body: _body, ...ticket }) => ({
      ...ticket,
      ...statuses.get(ticket.id)!,
    }));
  }

  async observeGraph(
    projectId: string,
    ticketId: string,
    focused = false,
  ): Promise<ObservationGraph> {
    return this.store.read(async () => {
      const all = await this.observedTickets(projectId);
      const byId = new Map(all.map(ticket => [ticket.id, ticket]));
      requireThat(byId.has(ticketId), 'NOT_FOUND', 'Ticket not found.');
      const selected = new Set<string>();
      const frontier: Array<{ id: string; depth: number }> = [{ id: ticketId, depth: 0 }];
      const omitted = new Set<string>();
      while (frontier.length) {
        const { id, depth } = frontier.shift()!;
        if (selected.has(id)) continue;
        const ticket = byId.get(id);
        if (!ticket) continue;
        if (selected.size >= 200 || (focused && depth > 2)) {
          omitted.add(id);
          continue;
        }
        selected.add(id);
        for (const adjacent of [...ticket.dependsOn, ...ticket.blocks])
          if (!selected.has(adjacent)) frontier.push({ id: adjacent, depth: depth + 1 });
      }
      return {
        tickets: [...selected].map(id => byId.get(id)!),
        hidden: [...omitted].filter(id => !selected.has(id)).length,
      };
    });
  }

  async close(): Promise<void> {}
}
