import { randomUUID } from 'node:crypto';
import type { Bassfish } from '../service.js';
import { ReplyPages } from '../bounded.js';
import { presentThread, presentTicket, presentTurnStatus } from '../mcp-presenters.js';
import { describeTickets } from './resources.js';

type Metadata = Record<string, Record<string, unknown>>;
interface Checkpoint {
  token: string;
  head: string;
  metadata: Metadata;
}
export class AgentUpdates {
  private readonly checkpoints = new Map<string, Checkpoint[]>();
  private readonly inflight = new Map<string, Checkpoint>();
  private readonly pages = new ReplyPages();
  constructor(private readonly service: Bassfish) {}
  close(handle: string): void {
    this.checkpoints.delete(handle);
    this.inflight.delete(handle);
    this.pages.close(handle);
  }
  private flatten(result: Record<string, unknown>): Record<string, unknown> {
    if (Array.isArray(result.context)) {
      Object.assign(result, result.context[0]);
      delete result.context;
    }
    return result;
  }
  private complete(handle: string, result: Record<string, unknown>): Record<string, unknown> {
    const pending = this.inflight.get(handle);
    if (pending && result.cursor === pending.token) {
      this.checkpoints.set(handle, [...(this.checkpoints.get(handle) ?? []), pending].slice(-2));
      this.inflight.delete(handle);
    }
    return this.flatten(result);
  }
  async read(handle: string, cursor?: string): Promise<Record<string, unknown>> {
    if (cursor?.startsWith('page:')) {
      await this.service.control.view(state => this.service.actor(state, handle));
      const result = this.pages.read(handle, cursor.slice(5));
      if (result.nextCursor) result.nextCursor = `page:${result.nextCursor}`;
      return this.complete(handle, result);
    }
    const s = this.service;
    return s.control.readTransaction(async () => {
      const actor = await s.control.view(state => s.actor(state, handle));
      const head = await s.control.activity.head();
      const previous = this.checkpoints.get(handle)?.find(c => c.token === cursor);
      const reset = Boolean(
        cursor && (!previous || (await s.control.activity.gap(actor.projectId, previous.head))),
      );
      const baseline = reset ? undefined : previous;
      const info = (await s.info(handle)) as {
        name: string;
        pendingRequests: Record<string, unknown>[];
      };
      const pendingTurns = [];
      for (const pending of info.pendingRequests) {
        const status = presentTurnStatus(pending);
        const request = await s.control.view(state =>
          state.get('requests', String(status.requestToken)),
        );
        pendingTurns.push({ ...status, ...(request?.turnId ? { turnToken: request.turnId } : {}) });
      }
      const notifications = await s.inbox.summary(handle);
      let metadata: Metadata;
      const transient: Metadata = {
        context: { agentName: info.name, pendingTurns, notifications },
      };
      if (baseline?.head === head) metadata = { ...baseline.metadata, ...transient };
      else {
        const agents = (await s.listAgents(handle, true, false)) as {
          agents: Array<{ name: string; online: boolean }>;
        };
        const follows = await s.control.view(state =>
          state.all('follows', { projectId: actor.projectId, identityId: actor.identityId }),
        );
        const tickets = describeTickets(await s.content.listTicketMetadata(actor.projectId));
        metadata = { ...transient };
        for (const a of agents.agents)
          metadata[`agent:${a.name}`] = { name: a.name, online: a.online };
        for (const t of await s.content.listThreads(actor.projectId))
          if (t.state === 'active')
            metadata[`thread:${t.id}`] = presentThread({
              ...t,
              following: follows.some(f => f.threadId === t.id),
            });
        for (const t of tickets)
          if (t.state !== 'done') metadata[`ticket:${t.id}`] = presentTicket(t);
      }
      const rows: Array<{ section: string; value: unknown }> = [];
      for (const [key, value] of Object.entries(metadata))
        if (JSON.stringify(value) !== JSON.stringify(baseline?.metadata[key]))
          rows.push({ section: key === 'context' ? 'context' : `${key.split(':')[0]}s`, value });
      const removed = baseline ? Object.keys(baseline.metadata).filter(k => !(k in metadata)) : [];
      for (const key of removed) rows.push({ section: 'removed', value: key });
      if (!rows.length) return { changed: false };
      const token = randomUUID();
      this.inflight.set(handle, { token, head, metadata });
      const result = this.pages.capture(
        handle,
        {
          changed: true,
          mode: baseline ? 'delta' : 'bootstrap',
          ...(reset ? { reset: true } : {}),
        },
        rows,
        { cursor: token },
      );
      if (result.nextCursor) result.nextCursor = `page:${result.nextCursor}`;
      return this.complete(handle, result);
    });
  }
}
