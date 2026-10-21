import { BassfishError, type Notification, type NotificationContent } from '../domain.js';

const workReasons = new Set([
  'direct_mention',
  'here',
  'global',
  'ticket_assigned',
  'ticket_ready',
]);

export function notificationPriority(notification: Notification): number {
  return isWorkNotification(notification) ? 0 : 1;
}

export function isWorkNotification(notification: Notification): boolean {
  return notification.reasons.some(reason => workReasons.has(reason));
}

export function presentNotification(
  notification: Notification,
  content: NotificationContent | undefined = notification.content,
): Record<string, unknown> {
  return {
    notificationId: notification.id,
    resourceType: notification.resourceType,
    resourceId: notification.resourceId,
    ...(notification.threadId
      ? {
          threadId: notification.threadId,
          messageId: notification.messageId,
          sequence: notification.sequence,
        }
      : {}),
    ...(notification.ticketId ? { ticketId: notification.ticketId } : {}),
    sender: {
      identityId: notification.senderIdentityId,
      name: notification.senderName,
    },
    createdAt: new Date(notification.createdAt).toISOString(),
    reasons: notification.reasons,
    ...(content ? { content } : {}),
  };
}

export class WakeSignals {
  private readonly waiters = new Map<string, Set<() => void>>();

  signal(identityIds: Iterable<string>): void {
    for (const identityId of new Set(identityIds)) {
      const waiters = this.waiters.get(identityId);
      if (!waiters) continue;
      this.waiters.delete(identityId);
      for (const wake of waiters) wake();
    }
  }

  wait(
    identityId: string,
    timeout: number,
    signal?: AbortSignal,
  ): { promise: Promise<void>; cancel: () => void } {
    let settled = false;
    let timer: NodeJS.Timeout | undefined;
    let resolvePromise!: () => void;
    let rejectPromise!: (error: Error) => void;
    const promise = new Promise<void>((resolve, reject) => {
      resolvePromise = resolve;
      rejectPromise = reject;
    });
    const wake = () => {
      if (settled) return;
      settled = true;
      cleanup();
      resolvePromise();
    };
    const abort = () => {
      if (settled) return;
      settled = true;
      cleanup();
      rejectPromise(new BassfishError('CANCELLED', 'Wake observation was cancelled.'));
    };
    const cleanup = () => {
      if (timer) clearTimeout(timer);
      signal?.removeEventListener('abort', abort);
      const waiters = this.waiters.get(identityId);
      waiters?.delete(wake);
      if (waiters?.size === 0) this.waiters.delete(identityId);
    };
    const waiters = this.waiters.get(identityId) ?? new Set<() => void>();
    waiters.add(wake);
    this.waiters.set(identityId, waiters);
    if (signal?.aborted) abort();
    else {
      signal?.addEventListener('abort', abort, { once: true });
      timer = setTimeout(wake, Math.max(0, timeout));
      timer.unref();
    }
    return { promise, cancel: wake };
  }
}
