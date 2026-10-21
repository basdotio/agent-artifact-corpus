import type { Db } from "./db.js";

export type ChatAction = "messages_post" | "channels_create" | "channels_join";
type Limit = { capacity: number; periodMs: number };

// Full buckets refill continuously over periodMs. All buckets for an action
// must admit it. These are account budgets, never per-token/session budgets.
export const CHAT_RATE_LIMITS: Record<ChatAction, readonly Limit[]> = {
  messages_post: [{ capacity: 60, periodMs: 60_000 }, { capacity: 1000, periodMs: 3_600_000 }],
  channels_create: [{ capacity: 5, periodMs: 3_600_000 }, { capacity: 20, periodMs: 86_400_000 }],
  channels_join: [{ capacity: 30, periodMs: 60_000 }]
};

export class RateLimitError extends Error {
  readonly code = "rate_limited";
  constructor(readonly action: ChatAction, readonly retryAfterMs: number, readonly limits: readonly Limit[]) {
    super(`Account rate limit reached for ${action}. Wait at least ${retryAfterMs} ms before retrying; all clients for this account share the limit.`);
  }
}

/** Persistent token buckets represented by their theoretical arrival time
 * (GCRA). One row per account/policy, not per request. GitHub identities use
 * users.id, uniquely bound to the stable numeric GitHub account ID. Immediate
 * transactions serialize SQLite writers. Nested calls participate in the chat
 * mutation's transaction, so rolled-back writes do not spend quota. */
export class ChatRateLimiter {
  constructor(private readonly db: Db, private readonly now: () => number = Date.now) {}

  consume(principalId: string, action: ChatAction) {
    this.db.transaction(() => {
      const now = this.now();
      const buckets = CHAT_RATE_LIMITS[action].map((limit) => {
        const bucket = `${action}:${limit.capacity}:${limit.periodMs}`;
        const row = this.db.prepare(`select arrival_ms from chat_rate_limits where principal_id = ? and bucket = ?`)
          .get(principalId, bucket) as { arrival_ms: number } | undefined;
        const interval = limit.periodMs / limit.capacity;
        const arrival = row?.arrival_ms ?? now;
        return {
          bucket, limit,
          nextArrival: Math.max(arrival, now) + interval,
          retryAfterMs: Math.max(0, Math.ceil(arrival - (limit.capacity - 1) * interval - now))
        };
      });
      const blocked = buckets.filter((bucket) => bucket.retryAfterMs > 0);
      if (blocked.length) {
        throw new RateLimitError(action, Math.max(...blocked.map((bucket) => bucket.retryAfterMs)), blocked.map((bucket) => bucket.limit));
      }
      const write = this.db.prepare(`
        insert into chat_rate_limits(principal_id, bucket, arrival_ms) values (?, ?, ?)
        on conflict(principal_id, bucket) do update set arrival_ms = excluded.arrival_ms
      `);
      for (const bucket of buckets) write.run(principalId, bucket.bucket, bucket.nextArrival);
    }).immediate();
  }
}
