import { RE2 } from 're2-wasm';
import { ReplyPages, prefix, bytes, pageBytes } from '../bounded.js';
import { requireThat } from '../domain.js';
import type { Message } from '../domain.js';
import type { Bassfish } from '../service.js';
import { outline } from '../markdown.js';
import { presentMessage, presentThread, presentTicket } from '../mcp-presenters.js';
import { describeTicket } from './resources.js';

export class ResourceReads {
  private readonly pages = new ReplyPages();
  constructor(private readonly service: Bassfish) {}
  close(handle: string): void {
    this.pages.close(handle);
  }
  async read(handle: string, input: Record<string, unknown>): Promise<Record<string, unknown>> {
    let args = input;
    if (args.cursor && !String(args.cursor).startsWith('resource:')) {
      await this.service.control.view(state => this.service.actor(state, handle));
      const result = this.pages.read(handle, String(args.cursor));
      if (args.turnToken) {
        const turn = await this.service.mcpTurnCredential(handle, String(args.turnToken));
        const resource = result.resource as { threadId?: string; ticketId?: string };
        requireThat(
          result.revision === turn.baseRevision &&
            (resource.threadId ?? resource.ticketId) === turn.resourceId,
          'REVISION_MISMATCH',
          'Cursor does not belong to this claimed snapshot.',
        );
      }
      return result;
    }
    if (args.cursor) {
      try {
        args = {
          ...JSON.parse(Buffer.from(String(args.cursor).slice(9), 'base64url').toString()),
          turnToken: args.turnToken,
        };
      } catch {
        requireThat(false, 'INVALID_CURSOR', 'Resource cursor is invalid.');
      }
    }
    const s = this.service;
    // Expiry may write coordination state; validate before entering the pinned reader.
    const credential = args.turnToken
      ? await s.mcpTurnCredential(handle, String(args.turnToken))
      : undefined;
    const result = await s.control.readTransaction(async () => {
      const actor = await s.control.view(state => s.actor(state, handle));
      let id = String(args.resourceId ?? '');
      let revision = args.revision as string | undefined;
      if (credential) {
        const turn = credential;
        requireThat(
          !id || id === turn.resourceId,
          'RESOURCE_TYPE_MISMATCH',
          'Turn belongs to another resource.',
        );
        requireThat(
          !revision || revision === turn.baseRevision,
          'REVISION_MISMATCH',
          'Read the claimed revision.',
        );
        id = turn.resourceId;
        revision = turn.baseRevision;
      }
      const type = await s.content.resourceType(actor.projectId, id);
      const rows: Array<{ section: string; value: unknown }> = [];
      let next: string | null = null;
      const parts = (text: string, section: string, extra: Record<string, unknown> = {}) => {
        if (!text.length)
          rows.push({ section, value: { ...extra, text: '', offset: 0, last: true } });
        let offset = 0;
        while (offset < text.length) {
          const budget = pageBytes - 700 - bytes(resource);
          requireThat(
            bytes(extra) + 64 < budget,
            'RESPONSE_TOO_LARGE',
            'Message metadata exceeds this page budget.',
          );
          let part = prefix(text.slice(offset), Math.min(3500, budget));
          while (bytes({ ...extra, text: part, offset, last: false }) > budget) {
            part = prefix(part, Math.max(1, Buffer.byteLength(part) - 128));
            requireThat(part.length, 'RESPONSE_TOO_LARGE', 'Content cannot fit this page.');
          }
          rows.push({
            section,
            value: { ...extra, text: part, offset, last: offset + part.length === text.length },
          });
          offset += part.length;
        }
      };
      const message = (m: Message) => {
        const { body, ...meta } = presentMessage(m);
        parts(String(body), 'messages', meta);
      };
      let resource: Record<string, unknown>;
      if (type === 'thread') {
        const snapshot =
          args.view === 'delta' && args.fromRevision
            ? await s.content.threadDelta(
                actor.projectId,
                id,
                String(args.fromRevision),
                revision,
                args.before as string | undefined,
              )
            : await s.content.snapshot(
                actor.projectId,
                id,
                20,
                args.before as string | undefined,
                revision,
              );
        revision = snapshot.revision;
        resource = presentThread(snapshot.thread);
        if (args.view === 'message') {
          const found = await s.content.messageAt(
            actor.projectId,
            id,
            String(args.messageId),
            revision,
          );
          message(found);
        } else {
          requireThat(
            args.view === 'page' || args.view === 'delta',
            'RESOURCE_TYPE_MISMATCH',
            'Thread reads support page, delta, or message.',
          );
          for (const m of snapshot.messages) message(m);
          if (snapshot.nextBefore)
            next =
              'resource:' +
              Buffer.from(
                JSON.stringify({
                  resourceId: id,
                  revision,
                  view: args.view,
                  ...(args.fromRevision ? { fromRevision: args.fromRevision } : {}),
                  before: snapshot.nextBefore,
                }),
              ).toString('base64url');
        }
      } else {
        const snapshot = await s.content.ticketSnapshot(actor.projectId, id, undefined, revision);
        revision = snapshot.ticket.revision;
        resource = presentTicket(
          describeTicket(snapshot.ticket, await s.content.listTicketMetadata(actor.projectId)),
        );
        const body = snapshot.ticket.body;
        if (args.view === 'outline')
          for (const item of outline(body))
            rows.push({
              section: 'headings',
              value: {
                ...item,
                heading: prefix(item.heading, 200),
                path: item.path.map(p => prefix(p, 100)),
              },
            });
        else if (args.view === 'find') {
          const query = String(args.query);
          const matcher = args.mode === 'regex' ? new RE2(query, 'u') : undefined;
          for (const [i, line] of body.split('\n').entries())
            if (matcher ? matcher.test(line) : line.includes(query)) {
              rows.push({ section: 'matches', value: { line: i + 1, text: prefix(line, 500) } });
              if (rows.length >= Number(args.limit ?? 20)) break;
            }
        } else {
          requireThat(
            args.view === 'page' || args.view === 'delta',
            'RESOURCE_TYPE_MISMATCH',
            'Ticket reads support page, delta, outline, or find.',
          );
          let changed = true;
          if (args.view === 'delta' && args.fromRevision) {
            const before = await s.content.ticketSnapshot(
              actor.projectId,
              id,
              undefined,
              String(args.fromRevision),
            );
            changed = body !== before.ticket.body;
          }
          if (changed) parts(body, 'body');
          else rows.push({ section: 'body', value: { changed: false } });
        }
      }
      return this.pages.capture(
        handle,
        { resource, revision, ...(args.fromRevision ? { fromRevision: args.fromRevision } : {}) },
        rows,
        { nextCursor: next },
      );
    });
    if (credential) await s.mcpTurnCredential(handle, String(args.turnToken));
    return result;
  }
}
