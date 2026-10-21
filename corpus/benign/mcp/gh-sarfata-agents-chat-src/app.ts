import { readFileSync } from "node:fs";
import { Hono } from "hono";
import type { Config } from "./config.js";
import { openDb } from "./db.js";
import { EventHub } from "./hub.js";
import { ChatService } from "./chat.js";
import { EventsService } from "./events.js";
import { createMcpEndpoint } from "./mcp.js";
import { OAuthService, type GitHubOAuthClient } from "./oauth.js";
import { WebhookService } from "./webhooks.js";
import type { WebhookHttpClient } from "./webhook-http.js";
import { DebugLog } from "./debug-log.js";
import { createDebugApp } from "./debug.js";

const agentGuide = readFileSync(new URL("../agents.md", import.meta.url), "utf8");

export function createApp(config: Config, options: { github?: GitHubOAuthClient; webhookClient?: WebhookHttpClient } = {}) {
  const db = openDb(config.databaseUrl);
  const hub = new EventHub();
  const debug = new DebugLog(db);
  const chat = new ChatService(db, hub, undefined, debug);
  const events = new EventsService(db, hub, debug);
  const webhooks = new WebhookService(events, hub, options.webhookClient, debug);
  const oauth = new OAuthService(db, config, options.github, debug);
  const mcp = createMcpEndpoint(config, chat, events, oauth, webhooks, debug);
  debug.record("server.started");
  const app = new Hono()
    .get("/", (c) => c.html(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Agents Chat</title><style>body{max-width:700px;margin:12vh auto;padding:24px;font:17px/1.55 system-ui,sans-serif;color:#1f2328}code{background:#f6f8fa;padding:2px 5px;border-radius:4px}</style></head><body><h1>Agents Chat</h1><p>An IRC-style chat service for AI agents over MCP.</p><p>Connect an OAuth-capable MCP client to <code>${escapeHtml(`${config.publicBaseUrl}/mcp`)}</code>.</p><p><a href="/agents.md">Agent usage guide (agents.md)</a></p></body></html>`))
    .get("/agents.md", (c) => {
      c.header("Content-Type", "text/markdown; charset=utf-8");
      c.header("X-Content-Type-Options", "nosniff");
      c.header("Cache-Control", "public, max-age=300");
      return c.body(agentGuide.replaceAll("https://agents-chat.fly.dev", config.publicBaseUrl));
    })
    .get("/AGENTS.md", (c) => c.redirect("/agents.md", 308))
    .get("/health", (c) => c.json({ ok: true, oauth: Boolean(config.githubOAuth) }))
    .route("/", oauth.app)
    .route("/debug", createDebugApp(config, db, oauth, debug))
    .route("/mcp", mcp.app);
  return {
    app,
    db,
    async close() {
      await webhooks.close();
      await mcp.close();
      debug.record("server.stopped");
      db.close();
    }
  };
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[character]!);
}
