import { z } from "zod/v4";
import type { Db } from "./db.js";

export const DEBUG_RETENTION = 10_000;
const kindSchema = z.enum([
  "server.started", "server.stopped", "agent.registered", "agent.authenticated",
  "channel.created", "member.joined", "message.posted", "events.polled",
  "subscription.created", "subscription.renewed", "subscription.expired", "subscription.closed",
  "webhook.verified", "webhook.verification_failed", "delivery.attempted", "delivery.sent",
  "delivery.failed", "delivery.retry_scheduled", "delivery.abandoned"
]);
const identity = z.object({ id: z.string().max(128), name: z.string().max(128) });
// An explicit allowlist: never serialize requests, credentials, callback URLs,
// headers, arbitrary errors, or webhook response bodies into the debug log.
const detailsSchema = z.object({
  actor: identity.optional(), channel: identity.optional(),
  message: z.object({ id: z.number(), text: z.string().max(800) }).optional(),
  eventId: z.string().max(128).optional(), subscriptionId: z.string().max(128).optional(),
  mode: z.enum(["poll", "push", "webhook"]).optional(),
  expiresAt: z.string().datetime().optional(),
  reason: z.enum(["cancelled", "transport_error", "server_stopped", "unsubscribed", "expired",
    "timeout", "connection_refused", "tls_error", "http_4xx", "http_5xx", "unsafe_address", "challenge_failed",
    "verification_rejected", "retry_exhausted"]).optional(),
  count: z.number().int().nonnegative().optional(), attempt: z.number().int().positive().optional(),
  retryAfterMs: z.number().int().nonnegative().optional(),
  truncated: z.boolean().optional(), hasMore: z.boolean().optional()
});
export type DebugKind = z.infer<typeof kindSchema>;
export type DebugDetails = z.infer<typeof detailsSchema>;
type Row = { id: number; kind: DebugKind; occurred_at: string; details_json: string };

export class DebugLog {
  private failures = 0;
  constructor(private readonly db: Db, private readonly retention = DEBUG_RETENTION) {
    if (!Number.isSafeInteger(retention) || retention < 1) throw new Error("Invalid debug retention");
    db.exec(`create table if not exists debug_events (
      id integer primary key autoincrement,
      kind text not null, occurred_at text not null, details_json text not null
    )`);
  }

  record(kind: DebugKind, details: DebugDetails = {}) {
    try {
      const safeKind = kindSchema.parse(kind);
      const safeDetails = detailsSchema.parse(details);
      this.db.transaction(() => {
        const result = this.db.prepare(`insert into debug_events(kind, occurred_at, details_json) values (?, ?, ?)`)
          .run(safeKind, new Date().toISOString(), JSON.stringify(safeDetails));
        this.db.prepare(`delete from debug_events where id <= ?`).run(Number(result.lastInsertRowid) - this.retention);
      })();
    } catch {
      // Diagnostics must not break chat writes, OAuth, or event delivery.
      this.failures++;
      if (this.failures === 1) console.error("Debug activity recording failed; chat remains available");
    }
  }

  chatEvent(rowId: number) {
    try {
      const row = this.db.prepare(`select kind, event_id, data_json from chat_events where id = ?`).get(rowId) as
        { kind: "channel.created" | "member.joined" | "message.posted"; event_id: string; data_json: string };
      const data = JSON.parse(row.data_json);
      this.record(row.kind, { eventId: row.event_id, actor: data.actor ?? data.member ?? data.sender,
        channel: data.channel, ...(row.kind === "message.posted" ? { message: data.message } : {}) });
    } catch {
      this.failures++;
    }
  }

  read(after?: number, limit = 200) {
    if ((after !== undefined && (!Number.isSafeInteger(after) || after < 0)) ||
      !Number.isSafeInteger(limit) || limit < 1 || limit > 500) throw new Error("Invalid debug cursor or limit");
    const bounds = this.db.prepare(`select min(id) as oldest, coalesce(max(id), 0) as head, count(*) as count from debug_events`).get() as
      { oldest: number | null; head: number; count: number };
    const reset = after !== undefined && (after > bounds.head || (bounds.oldest !== null && after < bounds.oldest - 1));
    const rows = (after === undefined || reset
      ? (this.db.prepare(`select * from debug_events order by id desc limit ?`).all(limit) as Row[]).reverse()
      : this.db.prepare(`select * from debug_events where id > ? order by id limit ?`).all(after, limit) as Row[]);
    const cursor = rows.at(-1)?.id ?? bounds.head;
    return {
      events: rows.map((row) => ({ id: row.id, kind: row.kind, timestamp: row.occurred_at, details: JSON.parse(row.details_json) })),
      cursor, hasMore: cursor < bounds.head, reset, retained: bounds.count, retention: this.retention,
      recordingFailures: this.failures,
      since: (this.db.prepare(`select occurred_at from debug_events order by id limit 1`).get() as { occurred_at: string } | undefined)?.occurred_at ?? null,
      serverTime: new Date().toISOString()
    };
  }
}
