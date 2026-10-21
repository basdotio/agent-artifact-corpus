import { createHash, randomBytes, randomUUID } from "node:crypto";
import { setMaxListeners } from "node:events";
import { ProtocolError, type ServerContext } from "@modelcontextprotocol/server";
import { z } from "zod/v4";

export const EVENT_NAME = "galaxy.signal";
export const POLL_LEASE_MS = 90_000;
export const RECONNECT_GRACE_MS = 10_000;
export type WebhookLease = { renewedAt: number; expiresAt: number; ttlMs: number };
export const ArgumentsSchema = z.object({
  name: z.string().trim().min(1).max(32).refine(s => !/[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/u.test(s), "Use a short, printable public name"),
  clientId: z.string().min(8).max(80).regex(/^[a-zA-Z0-9_-]+$/)
}).strict();
export const RequestSchema = z.object({
  name: z.string(),
  arguments: ArgumentsSchema,
  cursor: z.string().max(200).nullable().optional(),
  maxAgeMs: z.number().int().nonnegative().optional()
});
export type EventRequest = z.infer<typeof RequestSchema>;
export type SubscriberArguments = z.infer<typeof ArgumentsSchema>;
export type Signal = { eventId: string; name: string; timestamp: string; cursor: string; data: { kind: "ping" | "message"; subscriber: { id: string; name: string }; text?: string; anonymous: true } };
type Row = {
  id: string; name: string; ip: string; joinedAt: string; lastSignalAt: string | null; signalCount: number;
  pollUntil: number; graceUntil: number; streams: number; streamOpenedAt: number;
  webhooks: Map<string, WebhookLease>; events: Array<{ seq: number; event: Signal }>;
  generation: string; seq: number; droppedThrough: number; listeners: Set<(event: Signal) => void>;
};

export class LimitError extends Error {
  constructor(readonly retryAfterMs: number) { super("Too many signals. Give this patch of sky a moment."); }
}

/** Bounded, in-memory token buckets; no visitor IPs are exposed or persisted. */
export class Limiter {
  private rows = new Map<string, { tokens: number; at: number; expires: number }>();
  constructor(private readonly now = () => Date.now()) {}
  consume(rules: Array<{ key: string; capacity: number; period: number }>) {
    const now = this.now();
    for (const [key, row] of this.rows) if (row.expires <= now) this.rows.delete(key);
    const next = rules.map(rule => {
      const row = this.rows.get(rule.key);
      const tokens = Math.min(rule.capacity, row ? row.tokens + Math.max(0, now - row.at) * rule.capacity / rule.period : rule.capacity);
      return { ...rule, tokens, wait: tokens >= 1 ? 0 : Math.ceil((1 - tokens) * rule.period / rule.capacity) };
    });
    const wait = Math.max(...next.map(r => r.wait));
    if (wait) throw new LimitError(wait);
    if (this.rows.size + next.filter(r => !this.rows.has(r.key)).length > 4096) throw new LimitError(60_000);
    for (const r of next) this.rows.set(r.key, { tokens: r.tokens - 1, at: now, expires: now + r.period });
  }
}

export class Galaxy {
  private rows = new Map<string, Row>();
  readonly limiter: Limiter;
  private stopping = new AbortController();
  constructor(readonly now: () => number = () => Date.now()) {
    this.limiter = new Limiter(now);
    setMaxListeners(128, this.stopping.signal); // The enforced global stream ceiling.
  }

  list() {
    this.sweep();
    return [...this.rows.values()].map(r => {
      const subscriptions: Array<{ type: string; renewedAt: string; expiresAt: string | null; ttlMs: number | null }> = [];
      if (r.streams) subscriptions.push({ type: "push", renewedAt: new Date(r.streamOpenedAt).toISOString(), expiresAt: null, ttlMs: null });
      if (r.pollUntil > this.now()) subscriptions.push({ type: "poll", renewedAt: new Date(r.pollUntil - POLL_LEASE_MS).toISOString(), expiresAt: new Date(r.pollUntil).toISOString(), ttlMs: POLL_LEASE_MS });
      for (const lease of r.webhooks.values()) subscriptions.push({ type: "webhook", renewedAt: new Date(lease.renewedAt).toISOString(), expiresAt: new Date(lease.expiresAt).toISOString(), ttlMs: lease.ttlMs });
      const modes = [...new Set(subscriptions.map(s => s.type))];
      if (!r.streams && r.graceUntil > this.now()) subscriptions.push({ type: "reconnecting", renewedAt: new Date(r.graceUntil - RECONNECT_GRACE_MS).toISOString(), expiresAt: new Date(r.graceUntil).toISOString(), ttlMs: RECONNECT_GRACE_MS });
      return { id: r.id, name: r.name, joinedAt: r.joinedAt, lastSignalAt: r.lastSignalAt, signalCount: r.signalCount, modes, subscriptions };
    }).sort((a, b) => a.joinedAt.localeCompare(b.joinedAt));
  }
  sweep() {
    for (const [id, r] of this.rows) {
      for (const [key, lease] of r.webhooks) if (lease.expiresAt <= this.now()) r.webhooks.delete(key);
      if (!r.streams && !r.webhooks.size && Math.max(r.pollUntil, r.graceUntil) <= this.now()) this.rows.delete(id);
    }
  }
  private validate(input: EventRequest) {
    if (input.name !== EVENT_NAME) throw new ProtocolError(-32011, "NotFound", { kind: "event" });
    const parsed = ArgumentsSchema.safeParse(input.arguments);
    if (!parsed.success) throw new ProtocolError(-32602, "InvalidParams", { field: "arguments" });
    return parsed.data;
  }
  private ensure(args: SubscriberArguments, ip: string) {
    this.sweep();
    const id = "star_" + createHash("sha256").update(JSON.stringify(args)).digest("hex").slice(0, 24);
    let row = this.rows.get(id);
    if (!row) {
      if (this.rows.size >= 128 || [...this.rows.values()].filter(r => r.ip === ip).length >= 8) throw new ProtocolError(-32013, "ResourceExhausted", { limit: "subscribers", max: 128, perIp: 8 });
      this.limiter.consume([{ key: "join:" + ip, capacity: 8, period: 60_000 }, { key: "join:global", capacity: 32, period: 60_000 }]);
      row = { id, name: args.name, ip, joinedAt: new Date(this.now()).toISOString(), lastSignalAt: null,
        signalCount: 0, pollUntil: 0, graceUntil: 0, streams: 0, streamOpenedAt: 0, webhooks: new Map(), events: [], seq: 0, droppedThrough: 0,
        generation: randomBytes(12).toString("hex"), listeners: new Set() };
      this.rows.set(id, row);
    }
    return row;
  }
  private cursor(row: Row, seq = row.seq) { return row.generation + ":" + seq; }
  private replay(row: Row, input: EventRequest, maxEvents = 50) {
    if (input.cursor == null) return { events: [] as Signal[], cursor: this.cursor(row), truncated: false, hasMore: false, nextPollMs: 2000 };
    const match = /^([a-f0-9]{24}):(\d+)$/.exec(input.cursor);
    if (!match || !Number.isSafeInteger(Number(match[2]))) throw new ProtocolError(-32602, "InvalidParams", { field: "cursor" });
    if (match[1] !== row.generation || Number(match[2]) > row.seq) return { events: [] as Signal[], cursor: this.cursor(row), truncated: true, hasMore: false, nextPollMs: 2000 };
    const after = Number(match[2]);
    const cutoff = input.maxAgeMs === undefined ? -Infinity : this.now() - input.maxAgeMs;
    const pending = row.events.filter(e => e.seq > after);
    const filtered = pending.filter(e => Date.parse(e.event.timestamp) >= cutoff);
    const selected = filtered.slice(0, Math.min(50, maxEvents));
    const hasMore = filtered.length > selected.length;
    return {
      events: selected.map(e => e.event),
      cursor: this.cursor(row, hasMore ? selected[selected.length - 1].seq : row.seq),
      truncated: after < row.droppedThrough || filtered.length < pending.length,
      hasMore, nextPollMs: 2000
    };
  }
  poll(input: EventRequest & { maxEvents?: number }, ip: string) {
    const args = this.validate(input);
    const row = this.ensure(args, ip);
    const result = this.replay(row, input, input.maxEvents);
    row.pollUntil = this.now() + POLL_LEASE_MS;
    return result;
  }
  attachWebhook(input: EventRequest, ip: string, id: string, lease: WebhookLease, wake: () => void) {
    const row = this.ensure(this.validate(input), ip);
    if (row.webhooks.size >= 2) throw new ProtocolError(-32013, "ResourceExhausted", { limit: "webhooksPerSubscriber", max: 2 });
    const initial = this.replay(row, input);
    const cursor = initial.events.length ? this.cursor(row, Number(initial.events[0].cursor.split(":")[1]) - 1) : initial.cursor;
    row.webhooks.set(id, lease);
    row.listeners.add(wake);
    return {
      subscriberId: row.id, cursor, truncated: initial.truncated,
      // maxAgeMs bounds the initial replay, not newly arriving live events.
      read: (cursor: string) => this.replay(row, { ...input, cursor, maxAgeMs: undefined }, 1),
      detach: () => { row.webhooks.delete(id); row.listeners.delete(wake); this.sweep(); }
    };
  }
  send(id: string, body: { kind: "ping" | "message"; text?: string }, ip: string): Signal {
    this.sweep();
    const row = this.rows.get(id);
    if (!row) throw new ProtocolError(-32011, "NotFound", { kind: "subscriber" });
    if (!["ping", "message"].includes(body.kind) || (body.kind === "message" && (typeof body.text !== "string" || !body.text.trim() || [...body.text].length > 200)) || (body.kind === "ping" && body.text !== undefined)) throw new ProtocolError(-32602, "InvalidParams", { field: "message" });
    this.limiter.consume([
      { key: "send:" + ip, capacity: 20, period: 60_000 },
      { key: "target:" + id, capacity: 12, period: 60_000 },
      { key: "send:global", capacity: 300, period: 60_000 }
    ]);
    const seq = ++row.seq;
    const event: Signal = {
      eventId: "signal_" + randomUUID(), name: EVENT_NAME, timestamp: new Date(this.now()).toISOString(),
      cursor: this.cursor(row, seq), data: { kind: body.kind, subscriber: { id, name: row.name },
        ...(body.kind === "message" ? { text: body.text } : {}), anonymous: true }
    };
    row.events.push({ seq, event });
    if (row.events.length > 50) row.droppedThrough = row.events.shift()!.seq;
    row.signalCount++;
    row.lastSignalAt = event.timestamp;
    for (const listener of row.listeners) listener(event);
    return event;
  }
  async stream(input: EventRequest, ip: string, ctx: ServerContext) {
    const args = this.validate(input);
    const row = this.ensure(args, ip);
    const replay = this.replay(row, input);
    if (row.streams >= 2 || [...this.rows.values()].reduce((n, r) => n + r.streams, 0) >= 128) throw new ProtocolError(-32013, "ResourceExhausted", { limit: "streams", max: 128 });
    row.streams++;
    row.streamOpenedAt = this.now();
    let finish!: () => void;
    const ended = new Promise<void>(resolve => { finish = resolve; });
    let queue = Promise.resolve();
    let queued = 0;
    let closed = false;
    const notify = (method: string, params: object) => {
      if (closed) return;
      if (++queued > 64) { closed = true; finish(); return; }
      queue = queue.then(() => closed ? undefined : ctx.mcpReq.notify({
        method, params: { ...params, _meta: { "io.modelcontextprotocol/subscriptionId": String(ctx.mcpReq.id) } }
      })).catch(() => { closed = true; finish(); }).finally(() => { queued--; });
    };
    const onEvent = (event: Signal) => notify("notifications/events/event", event);
    row.listeners.add(onEvent);
    const stop = () => { closed = true; finish(); };
    ctx.mcpReq.signal.addEventListener("abort", stop, { once: true });
    this.stopping.signal.addEventListener("abort", stop, { once: true });
    // Never acknowledge a cursor beyond events still queued for replay.
    const activeCursor = replay.events.length
      ? this.cursor(row, Number(replay.events[0].cursor.split(":")[1]) - 1)
      : replay.cursor;
    notify("notifications/events/active", { cursor: activeCursor, truncated: replay.truncated, subscriberId: row.id });
    for (const event of replay.events) onEvent(event);
    const heartbeat = setInterval(() => notify("notifications/events/heartbeat", { cursor: this.cursor(row) }), 25_000);
    heartbeat.unref();
    if (ctx.mcpReq.signal.aborted || this.stopping.signal.aborted) stop();
    try { await ended; } finally {
      clearInterval(heartbeat); row.listeners.delete(onEvent); row.streams--;
      row.graceUntil = this.now() + RECONNECT_GRACE_MS;
      ctx.mcpReq.signal.removeEventListener("abort", stop);
      this.stopping.signal.removeEventListener("abort", stop);
    }
    return {};
  }
  close() { this.stopping.abort(); this.rows.clear(); }
}
