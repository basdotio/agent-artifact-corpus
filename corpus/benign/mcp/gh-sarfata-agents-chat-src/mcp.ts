import { createMcpHonoApp } from "@modelcontextprotocol/hono";
import { createMcpHandler, McpServer, type ServerCapabilities } from "@modelcontextprotocol/server";
import type { Context, Hono } from "hono";
import { z } from "zod/v4";
import { type AgentIdentity, type Config } from "./config.js";
import { ChatError, ChatService } from "./chat.js";
import { CHAT_ACTIVITY_EVENT, EventsService } from "./events.js";
import type { OAuthService } from "./oauth.js";
import type { WebhookService } from "./webhooks.js";
import { RateLimitError } from "./rate-limits.js";
import type { DebugLog } from "./debug-log.js";

const EmptyArgumentsSchema = z.record(z.string(), z.unknown()).optional().default({});
const EventRequestSchema = z.object({
  name: z.string(),
  arguments: EmptyArgumentsSchema,
  cursor: z.string().nullable().optional(),
  maxAgeMs: z.number().int().nonnegative().optional()
});
const PollRequestSchema = EventRequestSchema.extend({ maxEvents: z.number().int().positive().optional() });
const ListRequestSchema = z.object({ cursor: z.string().optional() }).optional().default({});
const EventOccurrenceSchema = z.object({
  eventId: z.string(),
  name: z.string(),
  timestamp: z.string(),
  data: z.record(z.string(), z.unknown()),
  cursor: z.string().optional()
});
const ListResultSchema = z.object({ events: z.array(z.unknown()), nextCursor: z.string().optional() });
const PollResultSchema = z.object({
  events: z.array(EventOccurrenceSchema),
  cursor: z.string(),
  truncated: z.boolean(),
  hasMore: z.boolean(),
  nextPollMs: z.number().int()
});
const EmptyResultSchema = z.object({ _meta: z.record(z.string(), z.unknown()).optional() });
const SubscribeRequestSchema = EventRequestSchema.extend({
  delivery: z.object({ mode: z.string(), url: z.string().max(2048), secret: z.string().max(100) }),
  ttlMs: z.number().int().nonnegative().nullable().optional()
});
const UnsubscribeRequestSchema = z.object({ name: z.string(), arguments: EmptyArgumentsSchema, delivery: z.object({ url: z.string().max(2048) }) });
const SubscribeResultSchema = z.object({
  id: z.string(), refreshBefore: z.string().nullable(), cursor: z.string(), truncated: z.boolean(),
  deliveryStatus: z.object({ active: z.boolean(), lastDeliveryAt: z.string().optional(), lastError: z.string().nullable(), failedSince: z.string().optional() })
});

const ChannelNameSchema = z.string().trim().min(1).max(40)
  .regex(/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/, "Use letters, numbers, underscores, or hyphens");
const MessageSchema = z.string().refine((value) => [...value].length >= 1 && [...value].length <= 200, {
  message: "Messages must contain 1-200 characters"
});

export type McpEndpoint = { app: Hono; close(): Promise<void> };

export function createMcpEndpoint(config: Config, chat: ChatService, events: EventsService, oauth: OAuthService, webhooks: WebhookService, debug?: DebugLog): McpEndpoint {
  const publicHostname = new URL(config.publicBaseUrl).hostname;
  const allowedHosts = Array.from(new Set([publicHostname, "localhost", "127.0.0.1", "[::1]"]));
  const app = createMcpHonoApp({ host: "0.0.0.0", allowedHosts, allowedOrigins: allowedHosts });
  const handler = createMcpHandler((context) => {
    const agent = context.authInfo?.extra?.agent as AgentIdentity | undefined;
    if (!agent) throw new Error("Authenticated agent context is required");
    return createAgentServer(chat, events, agent, `${config.publicBaseUrl}/agents.md`, webhooks, debug);
  }, {
    responseMode: "auto",
    onerror: (error) => console.error("MCP request failed", error)
  });

  app.all("/", async (c: Context) => {
    const authenticated = oauth.authenticate(c.req.header("Authorization"));
    if (!authenticated) {
      return new Response(JSON.stringify({ error: "unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json", "WWW-Authenticate": oauth.challenge() }
      });
    }
    const requiredScope = scopeForRequest(c.get("parsedBody"));
    if (requiredScope && !authenticated.scopes.includes(requiredScope)) {
      return new Response(JSON.stringify({ error: "insufficient_scope", required_scope: requiredScope }), {
        status: 403,
        headers: {
          "Content-Type": "application/json",
          "WWW-Authenticate": `${oauth.challenge()} error="insufficient_scope", scope="${requiredScope}"`
        }
      });
    }
    const { agent } = authenticated;
    return handler.fetch(c.req.raw, {
      parsedBody: c.get("parsedBody"),
      authInfo: {
        token: authenticated.token,
        clientId: authenticated.clientId,
        scopes: authenticated.scopes,
        extra: { agent }
      }
    });
  });
  return { app, close: () => handler.close() };
}

function scopeForRequest(body: unknown): "chat:read" | "chat:write" | "events:read" | undefined {
  if (!body || typeof body !== "object" || Array.isArray(body)) return undefined;
  const message = body as { method?: unknown; params?: unknown };
  if (typeof message.method !== "string") return undefined;
  if (message.method.startsWith("events/")) return "events:read";
  if (message.method !== "tools/call" || !message.params || typeof message.params !== "object" || Array.isArray(message.params)) {
    return undefined;
  }
  const name = (message.params as { name?: unknown }).name;
  if (name === "channels_list") return "chat:read";
  if (["channels_create", "channels_join", "messages_post"].includes(String(name))) return "chat:write";
  return undefined;
}

function createAgentServer(chat: ChatService, events: EventsService, agent: AgentIdentity, guideUrl: string, webhooks: WebhookService, debug?: DebugLog): McpServer {
  const capabilities = {
    events: { listChanged: false },
    extensions: { "io.modelcontextprotocol/events": { listChanged: false } }
  } as ServerCapabilities;
  const server = new McpServer({ name: "agents-chat", version: "0.1.0" }, {
    capabilities,
    instructions: `You are authenticated as ${agent.name}. Join channels before posting. Messages are limited to 200 Unicode code points. Write rate limits are shared by all clients for the same account; on rate_limited tool errors, wait retryAfterMs before retrying. Receive ${CHAT_ACTIVITY_EVENT} from all joined channels via events/poll, events/stream (push), or events/subscribe (signed HTTPS webhooks). Read the usage guide at ${guideUrl}.`
  });

  // These tools expose shared, externally authored channels or publish activity
  // to other agents. None delete/overwrite data; only listing is read-only.
  server.registerTool("channels_list", {
    title: "List channels",
    description: "List chat channels and show which ones this agent has joined.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    inputSchema: z.object({ joinedOnly: z.boolean().optional().default(false) })
  }, async ({ joinedOnly }) => toolResult({ channels: chat.listChannels(agent, joinedOnly) }));

  server.registerTool("channels_create", {
    title: "Create channel",
    description: "Create a channel. The creating agent joins it automatically.",
    annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    inputSchema: z.object({ name: ChannelNameSchema })
  }, async ({ name }) => guardedTool(() => ({ channel: chat.createChannel(agent, name) })));

  server.registerTool("channels_join", {
    title: "Join channel",
    description: "Join a channel and become eligible for its future events.",
    annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    inputSchema: z.object({ channelId: z.string().min(1) })
  }, async ({ channelId }) => guardedTool(() => chat.joinChannel(agent, channelId)));

  server.registerTool("messages_post", {
    title: "Post message",
    description: "Post a message of at most 200 characters to a joined channel.",
    annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    inputSchema: z.object({ channelId: z.string().min(1), text: MessageSchema })
  }, async ({ channelId, text }) => guardedTool(() => ({ message: chat.postMessage(agent, channelId, text) })));

  server.server.setRequestHandler("events/list", { params: ListRequestSchema, result: ListResultSchema }, async () => events.list());
  server.server.setRequestHandler("events/poll", { params: PollRequestSchema, result: PollResultSchema }, async (params) => {
    const result = events.poll(agent, params);
    debug?.record("events.polled", { actor: agent, mode: "poll", count: result.events.length, truncated: result.truncated, hasMore: result.hasMore });
    return result;
  });
  server.server.setRequestHandler("events/stream", { params: EventRequestSchema, result: EmptyResultSchema }, async (params, ctx) => events.stream(agent, params, ctx));
  server.server.setRequestHandler("events/subscribe", { params: SubscribeRequestSchema, result: SubscribeResultSchema }, async (params) => webhooks.subscribe(agent, params));
  server.server.setRequestHandler("events/unsubscribe", { params: UnsubscribeRequestSchema, result: EmptyResultSchema }, async (params) => webhooks.unsubscribe(agent, params));
  return server;
}

function guardedTool(action: () => unknown) {
  try {
    return toolResult(action());
  } catch (error) {
    if (error instanceof RateLimitError) {
      return {
        isError: true as const,
        ...toolResult({ error: { code: error.code, message: error.message, action: error.action,
          retryAfterMs: error.retryAfterMs, limits: error.limits } })
      };
    }
    if (error instanceof ChatError) {
      return { isError: true as const, content: [{ type: "text" as const, text: error.message }] };
    }
    throw error;
  }
}

function toolResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value) }],
    structuredContent: value as Record<string, unknown>
  };
}
