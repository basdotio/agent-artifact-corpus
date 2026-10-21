import { nanoid } from "nanoid";
import type { AgentIdentity } from "./config.js";
import type { Db } from "./db.js";
import type { EventHub } from "./hub.js";
import { ChatRateLimiter } from "./rate-limits.js";
import type { DebugLog } from "./debug-log.js";

export type ChatEventKind = "channel.created" | "member.joined" | "message.posted";

export class ChatError extends Error {
  constructor(readonly code: "not_found" | "conflict" | "forbidden" | "invalid", message: string) {
    super(message);
  }
}

type ChannelRow = {
  id: string;
  name: string;
  created_at: string;
  member_count: number;
  joined: number;
};

export class ChatService {
  constructor(private readonly db: Db, private readonly hub: EventHub,
    private readonly rateLimits = new ChatRateLimiter(db), private readonly debug?: DebugLog) {}

  listChannels(agent: AgentIdentity, joinedOnly = false) {
    const rows = this.db.prepare(`
      select c.id, c.name, c.created_at,
        count(m.agent_id) as member_count,
        max(case when mine.agent_id is not null then 1 else 0 end) as joined
      from channels c
      left join memberships m on m.channel_id = c.id
      left join memberships mine on mine.channel_id = c.id and mine.agent_id = ?
      ${joinedOnly ? "where mine.agent_id is not null" : ""}
      group by c.id
      order by c.name collate nocase
    `).all(agent.id) as ChannelRow[];
    return rows.map((row) => ({
      id: row.id,
      name: row.name,
      memberCount: Number(row.member_count),
      joined: Boolean(row.joined),
      createdAt: row.created_at
    }));
  }

  createChannel(agent: AgentIdentity, name: string) {
    const normalizedName = name.toLowerCase();
    const channelId = `channel_${nanoid(16)}`;
    const now = new Date().toISOString();
    let published!: { rowId: number; recipients: string[] };
    try {
      this.db.transaction(() => {
        this.rateLimits.consume(agent.id, "channels_create");
        this.db.prepare(`insert into channels(id, name, created_by, created_at) values (?, ?, ?, ?)`)
          .run(channelId, normalizedName, agent.id, now);
        this.db.prepare(`insert into memberships(channel_id, agent_id, agent_name, joined_at) values (?, ?, ?, ?)`)
          .run(channelId, agent.id, agent.name, now);
        published = this.recordEvent(channelId, "channel.created", {
          channel: { id: channelId, name: normalizedName },
          actor: agent
        }, now);
      }).immediate();
    } catch (error) {
      if (isUniqueConstraint(error)) throw new ChatError("conflict", `Channel ${normalizedName} already exists`);
      throw error;
    }
    this.debug?.chatEvent(published.rowId);
    this.hub.publish(published.recipients, published.rowId);
    return { id: channelId, name: normalizedName, joined: true, createdAt: now };
  }

  joinChannel(agent: AgentIdentity, channelId: string) {
    const channel = this.channel(channelId);
    const existing = this.db.prepare(`select 1 from memberships where channel_id = ? and agent_id = ?`)
      .get(channelId, agent.id);
    if (existing) return { channel, joined: true, alreadyJoined: true };

    const now = new Date().toISOString();
    let published!: { rowId: number; recipients: string[] };
    this.db.transaction(() => {
      this.rateLimits.consume(agent.id, "channels_join");
      this.db.prepare(`insert into memberships(channel_id, agent_id, agent_name, joined_at) values (?, ?, ?, ?)`)
        .run(channelId, agent.id, agent.name, now);
      published = this.recordEvent(channelId, "member.joined", {
        channel,
        member: agent
      }, now);
    }).immediate();
    this.debug?.chatEvent(published.rowId);
    this.hub.publish(published.recipients, published.rowId);
    return { channel, joined: true, alreadyJoined: false };
  }

  postMessage(agent: AgentIdentity, channelId: string, text: string) {
    const channel = this.channel(channelId);
    const membership = this.db.prepare(`select 1 from memberships where channel_id = ? and agent_id = ?`)
      .get(channelId, agent.id);
    if (!membership) throw new ChatError("forbidden", "Join the channel before posting");
    if (text.length < 1 || [...text].length > 200) {
      throw new ChatError("invalid", "Messages must contain 1-200 characters");
    }

    const now = new Date().toISOString();
    let messageId!: number;
    let published!: { rowId: number; recipients: string[] };
    this.db.transaction(() => {
      this.rateLimits.consume(agent.id, "messages_post");
      const result = this.db.prepare(`
        insert into messages(channel_id, agent_id, agent_name, text, created_at)
        values (?, ?, ?, ?, ?)
      `).run(channelId, agent.id, agent.name, text, now);
      messageId = Number(result.lastInsertRowid);
      published = this.recordEvent(channelId, "message.posted", {
        channel,
        message: { id: messageId, text },
        sender: agent
      }, now);
    }).immediate();
    this.debug?.chatEvent(published.rowId);
    this.hub.publish(published.recipients, published.rowId);
    return { id: messageId, channel, text, sender: agent, createdAt: now };
  }

  private channel(channelId: string): { id: string; name: string } {
    const row = this.db.prepare(`select id, name from channels where id = ?`).get(channelId) as
      | { id: string; name: string }
      | undefined;
    if (!row) throw new ChatError("not_found", "Channel not found");
    return row;
  }

  private recordEvent(channelId: string, kind: ChatEventKind, data: unknown, occurredAt: string) {
    const eventId = `event_${nanoid(20)}`;
    const result = this.db.prepare(`
      insert into chat_events(event_id, channel_id, kind, data_json, occurred_at)
      values (?, ?, ?, ?, ?)
    `).run(eventId, channelId, kind, JSON.stringify(data), occurredAt);
    const rowId = Number(result.lastInsertRowid);
    const recipients = (this.db.prepare(`select agent_id from memberships where channel_id = ?`)
      .all(channelId) as Array<{ agent_id: string }>).map((row) => row.agent_id);
    const insertRecipient = this.db.prepare(`insert into event_recipients(event_row_id, agent_id) values (?, ?)`);
    for (const recipient of recipients) insertRecipient.run(rowId, recipient);
    return { rowId, recipients };
  }
}

function isUniqueConstraint(error: unknown): boolean {
  return error instanceof Error && error.message.includes("UNIQUE constraint failed");
}
