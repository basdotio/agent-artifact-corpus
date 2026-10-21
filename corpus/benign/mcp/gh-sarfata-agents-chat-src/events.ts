import { ProtocolError, type RequestId, type ServerContext } from "@modelcontextprotocol/server";
import type { AgentIdentity } from "./config.js";
import type { Db } from "./db.js";
import type { EventHub } from "./hub.js";
import { nanoid } from "nanoid";
import type { DebugLog } from "./debug-log.js";

export const CHAT_ACTIVITY_EVENT = "agents-chat.activity";
const DEFAULT_POLL_MS = 2_000;

export type EventRequest = {
  name: string;
  arguments?: Record<string, unknown>;
  cursor?: string | null;
  maxAgeMs?: number;
};

export type PollEventRequest = EventRequest & { maxEvents?: number };

type EventRow = {
  id: number;
  event_id: string;
  kind: "channel.created" | "member.joined" | "message.posted";
  data_json: string;
  occurred_at: string;
};

export class EventsService {
  constructor(private readonly db: Db, private readonly hub: EventHub, private readonly debug?: DebugLog) {}

  list() {
    return {
      events: [{
        name: CHAT_ACTIVITY_EVENT,
        description: "Channel creation, joins, and messages for channels the authenticated agent had joined when the activity occurred.",
        delivery: ["poll", "push", "webhook"] as const,
        inputSchema: { type: "object", properties: {}, additionalProperties: false },
        payloadSchema: {
          type: "object",
          properties: {
            kind: { enum: ["channel.created", "member.joined", "message.posted"] },
            channel: {
              type: "object",
              properties: { id: { type: "string" }, name: { type: "string" } },
              required: ["id", "name"],
              additionalProperties: false
            }
          },
          required: ["kind", "channel"]
        }
      }]
    };
  }

  webhookStart(agent: AgentIdentity, input: EventRequest) {
    this.assertRequest(input);
    const head = this.head();
    if (input.cursor == null) return { cursor: formatCursor(head), truncated: false };
    const requested = parseCursor(input.cursor);
    let start = Math.min(requested, head);
    let truncated = requested > head;
    if (input.maxAgeMs !== undefined) {
      const cutoff = new Date(Math.max(0, Date.now() - input.maxAgeMs)).toISOString();
      const skipped = this.db.prepare(`select max(e.id) as id from chat_events e
        join event_recipients r on r.event_row_id = e.id
        where r.agent_id = ? and e.id > ? and e.occurred_at < ?`).get(agent.id, start, cutoff) as { id: number | null };
      if (skipped.id !== null) { start = skipped.id; truncated = true; }
    }
    return { cursor: formatCursor(start), truncated };
  }

  poll(agent: AgentIdentity, input: PollEventRequest) {
    this.assertRequest(input);
    const requestedLimit = input.maxEvents ?? 50;
    if (!Number.isInteger(requestedLimit) || requestedLimit < 1) {
      throw new ProtocolError(-32602, "InvalidParams", { field: "maxEvents" });
    }
    const limit = Math.min(requestedLimit, 100);
    const head = this.head();
    if (input.cursor === undefined || input.cursor === null) {
      return { events: [], cursor: formatCursor(head), truncated: false, hasMore: false, nextPollMs: DEFAULT_POLL_MS };
    }
    const start = parseCursor(input.cursor);
    if (start > head) {
      return { events: [], cursor: formatCursor(head), truncated: true, hasMore: false, nextPollMs: DEFAULT_POLL_MS };
    }
    const cutoff = input.maxAgeMs === undefined ? null : new Date(Date.now() - input.maxAgeMs).toISOString();
    const truncated = cutoff !== null && this.hasBefore(agent.id, start, cutoff);
    const rows = this.rowsAfter(agent.id, start, cutoff, limit + 1);
    const selected = rows.slice(0, limit);
    const hasMore = rows.length > limit;
    const position = hasMore && selected.length > 0 ? selected[selected.length - 1].id : head;
    return {
      events: selected.map((row) => this.occurrence(row, false)),
      cursor: formatCursor(position),
      truncated,
      hasMore,
      nextPollMs: DEFAULT_POLL_MS
    };
  }

  async stream(agent: AgentIdentity, input: EventRequest, ctx: ServerContext): Promise<{ _meta: Record<string, never> }> {
    this.assertRequest(input);
    const requested = input.cursor === undefined || input.cursor === null ? null : parseCursor(input.cursor);
    const initialHead = this.head();
    const start = requested === null ? initialHead : Math.min(requested, initialHead);
    const cutoff = input.maxAgeMs === undefined || requested === null ? null : new Date(Date.now() - input.maxAgeMs).toISOString();
    const truncated = requested !== null && (requested > initialHead || (cutoff !== null && this.hasBefore(agent.id, start, cutoff)));
    const buffered: number[] = [];
    let ready = false;
    let lastSent = start;
    let stopped = false;
    let end!: () => void;
    const ended = new Promise<void>((resolve) => { end = resolve; });
    let queue = Promise.resolve();
    const subscriptionId = `push_${nanoid(20)}`;
    const details = { actor: agent, mode: "push" as const, subscriptionId };
    let reason: "cancelled" | "transport_error" = "cancelled";
    let active = false;

    const notify = (method: string, params: Record<string, unknown>) => {
      queue = queue.then(async () => {
        if (stopped) return;
        await ctx.mcpReq.notify({ method, params });
        if (method === "notifications/events/active") {
          active = true;
          this.debug?.record("subscription.created", { ...details, truncated });
        } else if (method === "notifications/events/event") {
          this.debug?.record("delivery.sent", { ...details, eventId: String(params.eventId) });
        }
      }).catch(() => {
        reason = "transport_error";
        stopped = true;
        this.debug?.record("delivery.failed", { ...details, reason });
        end();
      });
      return queue;
    };
    const sendRow = (row: EventRow) => {
      if (row.id <= lastSent) return;
      lastSent = row.id;
      void notify("notifications/events/event", withSubscriptionId(this.occurrence(row), ctx.mcpReq.id));
    };
    const off = this.hub.onEvent(agent.id, (rowId) => {
      if (!ready) return void buffered.push(rowId);
      const row = this.row(agent.id, rowId);
      if (row) sendRow(row);
    });
    const abort = () => { stopped = true; end(); };
    ctx.mcpReq.signal.addEventListener("abort", abort, { once: true });
    if (ctx.mcpReq.signal.aborted) abort();

    let heartbeat: ReturnType<typeof setInterval> | undefined;
    try {
      await notify("notifications/events/active", withSubscriptionId({ cursor: formatCursor(start), truncated }, ctx.mcpReq.id));
      if (!stopped && requested !== null) {
        for (const row of this.rowsAfter(agent.id, start, cutoff, 1_000)) sendRow(row);
      }
      ready = true;
      for (const rowId of buffered.sort((a, b) => a - b)) {
        if (stopped) break;
        const row = this.row(agent.id, rowId);
        if (row) sendRow(row);
      }
      heartbeat = setInterval(() => {
        void notify("notifications/events/heartbeat", withSubscriptionId({ cursor: formatCursor(this.head()) }, ctx.mcpReq.id));
      }, 25_000);
      heartbeat.unref?.();
      await ended;
    } finally {
      stopped = true;
      clearInterval(heartbeat);
      off();
      ctx.mcpReq.signal.removeEventListener("abort", abort);
      await queue;
      if (active) this.debug?.record("subscription.closed", { ...details, reason });
    }
    return { _meta: {} };
  }

  private assertRequest(input: EventRequest) {
    if (input.name !== CHAT_ACTIVITY_EVENT) throw new ProtocolError(-32011, "NotFound", { kind: "event" });
    if (input.arguments && Object.keys(input.arguments).length > 0) {
      throw new ProtocolError(-32602, "InvalidParams", { field: "arguments" });
    }
    if (input.maxAgeMs !== undefined && (!Number.isInteger(input.maxAgeMs) || input.maxAgeMs < 0)) {
      throw new ProtocolError(-32602, "InvalidParams", { field: "maxAgeMs" });
    }
  }

  private head(): number {
    return Number((this.db.prepare(`select coalesce(max(id), 0) as value from chat_events`).get() as { value: number }).value);
  }

  private rowsAfter(agentId: string, start: number, cutoff: string | null, limit: number): EventRow[] {
    return this.db.prepare(`
      select e.id, e.event_id, e.kind, e.data_json, e.occurred_at
      from chat_events e
      join event_recipients r on r.event_row_id = e.id
      where r.agent_id = ? and e.id > ? and (? is null or e.occurred_at >= ?)
      order by e.id
      limit ?
    `).all(agentId, start, cutoff, cutoff, limit) as EventRow[];
  }

  private hasBefore(agentId: string, start: number, cutoff: string): boolean {
    return Boolean(this.db.prepare(`
      select 1 from chat_events e join event_recipients r on r.event_row_id = e.id
      where r.agent_id = ? and e.id > ? and e.occurred_at < ? limit 1
    `).get(agentId, start, cutoff));
  }

  private row(agentId: string, rowId: number): EventRow | undefined {
    return this.db.prepare(`
      select e.id, e.event_id, e.kind, e.data_json, e.occurred_at
      from chat_events e join event_recipients r on r.event_row_id = e.id
      where r.agent_id = ? and e.id = ?
    `).get(agentId, rowId) as EventRow | undefined;
  }

  private occurrence(row: EventRow, includeCursor = true) {
    const data = JSON.parse(row.data_json) as Record<string, unknown>;
    return {
      eventId: row.event_id,
      name: CHAT_ACTIVITY_EVENT,
      timestamp: row.occurred_at,
      data: { kind: row.kind, ...data },
      ...(includeCursor ? { cursor: formatCursor(row.id) } : {})
    };
  }
}

export function formatCursor(position: number): string {
  return `chat-event:${position}`;
}

function parseCursor(cursor: string): number {
  const match = /^chat-event:(\d+)$/.exec(cursor);
  const value = match ? Number(match[1]) : NaN;
  if (!Number.isSafeInteger(value) || value < 0) throw new ProtocolError(-32602, "InvalidParams", { field: "cursor" });
  return value;
}

function withSubscriptionId(params: Record<string, unknown>, requestId: RequestId) {
  return {
    ...params,
    _meta: { "io.modelcontextprotocol/subscriptionId": String(requestId) }
  };
}
