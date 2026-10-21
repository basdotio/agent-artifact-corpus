import { randomUUID } from 'node:crypto';
import { BassfishError, requireThat } from '../domain.js';
import type { Notification, NotificationBatchRecord, Actor } from '../domain.js';
import type { Bassfish } from '../service.js';
import { bytes, pageBytes, prefix } from '../bounded.js';
import { emptyBatch, formatDeliveryContext } from '../notification-delivery.js';
import type { DeliveryBatch, DeliveredNotification } from '../notification-delivery.js';
import { isWorkNotification, notificationPriority } from './notifications.js';
import { KeyedMutex } from '../runtime.js';

export class Inbox {
  private readonly captures = new KeyedMutex();
  constructor(private readonly service: Bassfish) {}
  async capture(
    handle: string,
    scope: 'all' | 'actionable' = 'all',
    sessionId?: string,
  ): Promise<DeliveryBatch> {
    const s = this.service;
    const actorKey = await s.control.view(state => s.actor(state, handle));
    return this.captures.run(`${actorKey.projectId}:${actorKey.identityId}`, () =>
      s.control.update(async state => {
        const actor = await s.actor(state, handle);
        const batches = await state.all('notificationBatches', {
          projectId: actor.projectId,
          identityId: actor.identityId,
        });
        if (
          sessionId &&
          batches.some(
            b =>
              b.sessionId === sessionId &&
              ['reserved', 'submitting', 'accepted', 'uncertain'].includes(b.status),
          )
        )
          return emptyBatch();
        const presented = new Set(
          batches
            .filter(b => b.status !== 'released')
            .flatMap(b => b.entries.map(e => `${e.id}:${e.eventId}`)),
        );
        const available = (
          await state.all('notifications', {
            projectId: actor.projectId,
            identityId: actor.identityId,
          })
        )
          .filter(
            n =>
              !presented.has(`${n.id}:${n.eventId}`) && (scope === 'all' || isWorkNotification(n)),
          )
          .sort(
            (a, b) =>
              notificationPriority(a) - notificationPriority(b) ||
              a.createdAt - b.createdAt ||
              a.id.localeCompare(b.id),
          );
        if (!available.length) return emptyBatch();
        const id = randomUUID();
        const payload: DeliveryBatch = {
          kind: isWorkNotification(available[0]!) ? 'actionable' : 'activity',
          count: 0,
          batchToken: id,
          moreAvailable: true,
          notifications: [],
        };
        const entries: Notification[] = [];
        const fits = () =>
          bytes(payload) <= pageBytes &&
          Buffer.byteLength(formatDeliveryContext(payload)) <= pageBytes;
        for (const notification of available.slice(0, 20)) {
          const item: DeliveredNotification = {
            index: entries.length,
            resourceType: notification.resourceType,
            resourceId: notification.resourceId,
            sender: notification.senderName,
            reasons: notification.reasons,
            ...(notification.content ? { content: { ...notification.content } } : {}),
          };
          payload.notifications.push(item);
          payload.count++;
          if (!fits()) {
            if (entries.length) {
              payload.notifications.pop();
              payload.count--;
              break;
            }
            item.truncated = true;
            if (item.content?.kind === 'thread_message') {
              while (!fits() && item.content.body.length)
                item.content.body = prefix(
                  item.content.body,
                  Math.max(0, Buffer.byteLength(item.content.body) - 256),
                );
            }
            requireThat(
              fits(),
              'RESPONSE_TOO_LARGE',
              'Notification metadata exceeds its delivery budget.',
            );
          }
          entries.push(notification);
        }
        payload.moreAvailable = entries.length < available.length;
        await state.set('notificationBatches', id, {
          id,
          projectId: actor.projectId,
          identityId: actor.identityId,
          ...(sessionId ? { sessionId } : {}),
          status: sessionId ? 'reserved' : 'presented',
          entries,
          acknowledged: [],
          payload,
          createdAt: s.clock.now(),
        });
        return payload;
      }),
    );
  }
  private own(actor: Actor, batch: NotificationBatchRecord | undefined): NotificationBatchRecord {
    requireThat(
      batch && batch.projectId === actor.projectId && batch.identityId === actor.identityId,
      'BATCH_NOT_FOUND',
      'Notification batch not found for this agent.',
    );
    return batch;
  }
  async read(handle: string, args: Record<string, unknown>): Promise<unknown> {
    if (!args.batchToken) return this.capture(handle);
    return this.service.control.view(async state => {
      const batch = this.own(
        await this.service.actor(state, handle),
        await state.get('notificationBatches', String(args.batchToken)),
      );
      if (args.item === undefined) return batch.payload;
      const entry = batch.entries[Number(args.item)];
      requireThat(entry, 'INVALID_ARGUMENT', 'Batch entry index is invalid.');
      if (entry.content?.kind !== 'thread_message')
        return { batchToken: batch.id, item: args.item, content: entry.content };
      const offset = Number(args.cursor ?? 0);
      requireThat(
        Number.isSafeInteger(offset) && offset >= 0 && offset <= entry.content.body.length,
        'INVALID_CURSOR',
        'Content cursor is invalid.',
      );
      let text = prefix(entry.content.body.slice(offset), pageBytes - 500);
      while (bytes({ text }) > pageBytes - 500) text = prefix(text, Buffer.byteLength(text) - 128);
      return {
        batchToken: batch.id,
        item: args.item,
        text,
        nextCursor:
          offset + text.length < entry.content.body.length ? String(offset + text.length) : null,
      };
    });
  }
  async acknowledge(handle: string, token: string, items?: number[]): Promise<unknown> {
    return this.service.control.update(async state => {
      const actor = await this.service.actor(state, handle);
      const batch = this.own(actor, await state.get('notificationBatches', token));
      const indices = [...new Set(items ?? batch.entries.map((_, i) => i))];
      for (const i of indices)
        requireThat(batch.entries[i], 'INVALID_ARGUMENT', 'Batch entry index is invalid.');
      let acknowledged = 0;
      for (const i of indices) {
        if (batch.acknowledged.includes(i)) continue;
        const entry = batch.entries[i]!;
        const current = await state.get('notifications', entry.id);
        if (current?.eventId === entry.eventId) await state.remove('notifications', entry.id);
        batch.acknowledged.push(i);
        acknowledged++;
      }
      if (batch.acknowledged.length === batch.entries.length && batch.status !== 'handled') {
        batch.status = 'handled';
        batch.finishedAt = this.service.clock.now();
      }
      return {
        acknowledged,
        remaining: (
          await state.all('notifications', {
            projectId: actor.projectId,
            identityId: actor.identityId,
          })
        ).length,
      };
    });
  }
  async transition(
    handle: string,
    token: string,
    status: NotificationBatchRecord['status'],
    issue?: string,
  ): Promise<void> {
    await this.service.control.update(async state => {
      const batch = this.own(
        await this.service.actor(state, handle),
        await state.get('notificationBatches', token),
      );
      const allowed: Record<string, string[]> = {
        reserved: ['submitting', 'released', 'uncertain'],
        submitting: ['accepted', 'uncertain', 'released'],
        accepted: ['presented'],
        uncertain: ['presented'],
      };
      if (batch.status === status || batch.status === 'handled') return;
      if (!allowed[batch.status]?.includes(status))
        throw new BassfishError('INVALID_DELIVERY_STATE', 'Delivery state cannot move backwards.');
      batch.status = status;
      if (status === 'released') batch.finishedAt = this.service.clock.now();
      if (issue) batch.issue = issue.slice(0, 200);
    });
  }
  async summary(handle: string): Promise<Record<string, unknown>> {
    return this.service.control.view(async state => {
      const a = await this.service.actor(state, handle);
      const batches = await state.all('notificationBatches', {
        projectId: a.projectId,
        identityId: a.identityId,
      });
      const presented = new Set(
        batches
          .filter(b => b.status !== 'released')
          .flatMap(b => b.entries.map(e => `${e.id}:${e.eventId}`)),
      );
      const unread = await state.all('notifications', {
        projectId: a.projectId,
        identityId: a.identityId,
      });
      return {
        moreUnhandled: batches.filter(b => !['handled', 'released'].includes(b.status)).length > 20,
        unread: unread.length,
        new: unread.filter(n => !presented.has(`${n.id}:${n.eventId}`)).length,
        unhandled: batches
          .filter(b => !['handled', 'released'].includes(b.status))
          .slice(0, 20)
          .map(b => ({
            batchToken: b.id,
            status: b.status,
            ...(b.issue ? { issue: b.issue } : {}),
          })),
      };
    });
  }
  async hasActionable(handle: string): Promise<boolean> {
    return this.service.control.view(async state => {
      const a = await this.service.actor(state, handle);
      const batches = await state.all('notificationBatches', {
        projectId: a.projectId,
        identityId: a.identityId,
      });
      if (batches.some(b => ['reserved', 'submitting', 'accepted', 'uncertain'].includes(b.status)))
        return false;
      const seen = new Set(
        batches
          .filter(b => b.status !== 'released')
          .flatMap(b => b.entries.map(n => `${n.id}:${n.eventId}`)),
      );
      return (
        await state.all('notifications', { projectId: a.projectId, identityId: a.identityId })
      ).some(n => isWorkNotification(n) && !seen.has(`${n.id}:${n.eventId}`));
    });
  }
  async presented(handle: string, sessionId: string): Promise<void> {
    await this.service.control.update(async state => {
      const a = await this.service.actor(state, handle);
      for (const batch of await state.all('notificationBatches', {
        projectId: a.projectId,
        identityId: a.identityId,
        sessionId,
      }))
        if (batch.status === 'accepted' || batch.status === 'uncertain') batch.status = 'presented';
    });
  }
}
