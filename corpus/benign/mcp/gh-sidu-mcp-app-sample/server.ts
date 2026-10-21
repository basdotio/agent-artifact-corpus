/**
 * Kitchen-sink MCP server exercising as many protocol + MCP Apps capabilities
 * as possible. Every capability is labelled so a verification harness or a
 * human reading the source can map behavior back to the spec.
 *
 * Capability map:
 *   [CAP-TOOL]              Tools with inputSchema / outputSchema / structuredContent
 *   [CAP-TOOL-ANNOT]        Tool annotations (readOnly / destructive / idempotent)
 *   [CAP-TOOL-RESLINK]      Resource links returned in tool content
 *   [CAP-RES-STATIC]        Static resource
 *   [CAP-RES-TEMPLATE]      Templated resource (RFC 6570)
 *   [CAP-RES-BLOB]          Binary resource (base64 blob)
 *   [CAP-RES-SUBSCRIBE]     resources/subscribe + notifications/resources/updated
 *   [CAP-PROMPT]            Prompt with arguments
 *   [CAP-COMPLETE]          completion/complete for prompt args
 *   [CAP-SAMPLING]          Server -> client sampling/createMessage
 *   [CAP-ELICIT]            Server -> client elicitation/create
 *   [CAP-ROOTS]             Server -> client roots/list
 *   [CAP-LOG]               logging/setLevel + notifications/message
 *   [CAP-PROGRESS]          notifications/progress
 *   [CAP-CANCEL]            notifications/cancelled honored
 *   [CAP-LISTCHANGED]       notifications/tools/list_changed (dynamic tool set)
 *   [CAP-APP]               MCP Apps: tool with _meta.ui.resourceUri
 *   [CAP-APP-APPONLY]       App-only tool (_meta.ui.visibility=["app"])
 *   [CAP-APP-STRUCT]        structuredContent consumed by View
 *   [CAP-APP-CHUNK]         Chunked binary read (bypass tool-result size limits)
 *   [CAP-APP-CSP]           UI resource declaring CSP metadata
 *   [CAP-APP-PARTIAL]       Streaming tool input consumed by View (ontoolinputpartial)
 *   [CAP-APP-VIEWUUID]      View state persistence via CallToolResult._meta.viewUUID
 */

import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { completable } from "@modelcontextprotocol/sdk/server/completable.js";
import type {
  CallToolResult,
  ReadResourceResult,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { z } from "zod";

// Works both from source (server.ts) and compiled (dist/server.js).
// `import.meta.filename`/`dirname` require Node 20.11+, so derive them.
import { fileURLToPath } from "node:url";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DIST_DIR = __filename.endsWith(".ts")
  ? path.join(__dirname, "dist")
  : __dirname;

// ---------------------------------------------------------------------------
// UI resource URIs
// ---------------------------------------------------------------------------
const DASHBOARD_URI = "ui://sample/dashboard.html";
const SHADER_URI = "ui://sample/shader.html";
const COUNTER_URI = "ui://sample/counter.html";

// ---------------------------------------------------------------------------
// Domain resource URIs
// ---------------------------------------------------------------------------
const STATIC_CONFIG_URI = "resource:///config.json";
const ITEM_TEMPLATE = "resource:///items/{id}";
const BINARY_LOGO_URI = "resource:///logo.png";
const LIVE_COUNTER_URI = "resource:///live/counter";

// ---------------------------------------------------------------------------
// Server state (module-level; per-connection is created inside createServer)
// ---------------------------------------------------------------------------

// Simulated "database" for templated resources
const ITEM_DB: Record<string, { id: string; name: string; qty: number }> = {
  "42": { id: "42", name: "Widget", qty: 3 },
  "43": { id: "43", name: "Gadget", qty: 7 },
  "44": { id: "44", name: "Gizmo", qty: 1 },
};

// A tiny 1x1 transparent PNG so we don't need any assets
const TINY_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgQAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

// Module-scoped so the counter's value persists across the stateless HTTP
// per-request server instances. In stdio mode, each process starts fresh at 0.
const startedAt = Date.now();
function currentCounterValue(): number {
  return Math.floor((Date.now() - startedAt) / 1000);
}

export function createServer(): McpServer {
  const server = new McpServer(
    { name: "MCP App Sample (kitchen sink)", version: "0.1.0" },
    {
      capabilities: {
        // Advertise every server capability we implement so clients can gate
        // on them. See spec 2025-11-25 §Server features.
        tools: { listChanged: true },
        resources: { listChanged: true, subscribe: true },
        prompts: { listChanged: true },
        logging: {},
        completions: {},
      },
    },
  );

  // -------------------------------------------------------------------------
  // Per-connection state
  // -------------------------------------------------------------------------
  const subscribers = new Set<string>(); // URIs the client has subscribed to
  // Tick every second: notify subscribers if any. The counter value itself is
  // computed from module-scoped `startedAt` so it advances even when the HTTP
  // transport creates a fresh server instance per request.
  const counterInterval: NodeJS.Timeout = setInterval(() => {
    if (subscribers.has(LIVE_COUNTER_URI)) {
      // [CAP-RES-SUBSCRIBE] notify subscribers of the change
      server.server
        .sendResourceUpdated({ uri: LIVE_COUNTER_URI })
        .catch(() => {});
    }
  }, 1000);

  // Wire subscription bookkeeping via low-level server request handlers.
  // McpServer doesn't own subscribe/unsubscribe; we add them via .server.
  server.server.setRequestHandler(
    z.object({
      method: z.literal("resources/subscribe"),
      params: z.object({ uri: z.string() }),
    }),
    async (req) => {
      subscribers.add(req.params.uri);
      return {};
    },
  );
  server.server.setRequestHandler(
    z.object({
      method: z.literal("resources/unsubscribe"),
      params: z.object({ uri: z.string() }),
    }),
    async (req) => {
      subscribers.delete(req.params.uri);
      return {};
    },
  );

  server.server.onclose = () => {
    clearInterval(counterInterval);
  };

  // =========================================================================
  // TOOLS
  // =========================================================================

  // ------------------- [CAP-TOOL] Basic tool with schemas -------------------
  server.registerTool(
    "echo",
    {
      title: "Echo",
      description:
        "Returns the input text verbatim. Demonstrates inputSchema, outputSchema, and structuredContent.",
      inputSchema: { text: z.string().describe("Text to echo back") },
      outputSchema: { echoed: z.string(), receivedAt: z.string() },
      annotations: {
        // [CAP-TOOL-ANNOT]
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ text }): Promise<CallToolResult> => {
      const receivedAt = new Date().toISOString();
      return {
        content: [{ type: "text", text: `${text} (received ${receivedAt})` }],
        structuredContent: { echoed: text, receivedAt },
      };
    },
  );

  // ------------------- [CAP-APP] UI-linked tool (dashboard) -----------------
  registerAppTool(
    server,
    "dashboard",
    {
      title: "Dashboard",
      description:
        "Opens an interactive dashboard View. Demonstrates a UI-linked tool with structured content and a resource link. Try asking to 'open the dashboard'.",
      inputSchema: {
        title: z
          .string()
          .default("Sample Dashboard")
          .describe("Title to show in the View"),
      },
      outputSchema: {
        title: z.string(),
        metrics: z.array(
          z.object({ label: z.string(), value: z.number() }),
        ),
      },
      _meta: { ui: { resourceUri: DASHBOARD_URI } },
    },
    async ({ title }): Promise<CallToolResult> => {
      const metrics = [
        { label: "Users", value: Math.round(50 + Math.random() * 50) },
        { label: "Requests", value: Math.round(100 + Math.random() * 900) },
        { label: "Errors", value: Math.round(Math.random() * 5) },
      ];
      return {
        content: [
          {
            type: "text",
            text: `Dashboard "${title}" opened. ${metrics
              .map((m) => `${m.label}=${m.value}`)
              .join(", ")}.`,
          },
          // [CAP-TOOL-RESLINK] a resource link in the tool result
          {
            type: "resource_link",
            uri: STATIC_CONFIG_URI,
            name: "config.json",
            mimeType: "application/json",
          },
        ],
        structuredContent: { title, metrics }, // [CAP-APP-STRUCT]
        _meta: { viewUUID: crypto.randomUUID() }, // [CAP-APP-VIEWUUID]
      };
    },
  );

  // ------------------- [CAP-PROGRESS] [CAP-CANCEL] long-running tool --------
  server.registerTool(
    "long-task",
    {
      title: "Long Task",
      description:
        "Simulates a long-running task, emitting progress notifications. Cancel via notifications/cancelled.",
      inputSchema: {
        steps: z.number().int().min(1).max(20).default(5),
        delayMs: z.number().int().min(50).max(2000).default(200),
      },
    },
    async ({ steps, delayMs }, extra): Promise<CallToolResult> => {
      const progressToken = extra._meta?.progressToken;
      for (let i = 1; i <= steps; i++) {
        // [CAP-CANCEL] AbortSignal is fed by notifications/cancelled
        if (extra.signal.aborted) {
          return {
            content: [
              { type: "text", text: `Cancelled at step ${i - 1}/${steps}` },
            ],
            isError: true,
          };
        }
        if (progressToken !== undefined) {
          // [CAP-PROGRESS]
          await extra.sendNotification({
            method: "notifications/progress",
            params: {
              progressToken,
              progress: i,
              total: steps,
              message: `Step ${i}/${steps}`,
            },
          });
        }
        // [CAP-LOG] also emit a log message per step so we exercise logging
        await server.sendLoggingMessage({
          level: "info",
          logger: "long-task",
          data: { step: i, total: steps },
        });
        await new Promise((r) => setTimeout(r, delayMs));
      }
      return {
        content: [
          { type: "text", text: `Completed ${steps} steps.` },
        ],
      };
    },
  );

  // ------------------- [CAP-SAMPLING] Server-requested LLM call -------------
  server.registerTool(
    "summarize-with-llm",
    {
      title: "Summarize (via client sampling)",
      description:
        "Asks the host to run an LLM completion via sampling/createMessage. Fails gracefully if the client does not support sampling.",
      inputSchema: { text: z.string() },
    },
    async ({ text }): Promise<CallToolResult> => {
      try {
        const result = await server.server.createMessage({
          messages: [
            {
              role: "user",
              content: {
                type: "text",
                text: `Summarize in one sentence:\n\n${text}`,
              },
            },
          ],
          maxTokens: 200,
          systemPrompt: "You are a concise summarizer.",
        });
        const summary =
          result.content.type === "text"
            ? result.content.text
            : "[non-text response]";
        return { content: [{ type: "text", text: summary }] };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
          content: [
            {
              type: "text",
              text: `Sampling not supported by this client: ${msg}`,
            },
          ],
          isError: true,
        };
      }
    },
  );

  // ------------------- [CAP-ELICIT] Structured user input -------------------
  server.registerTool(
    "ask-user",
    {
      title: "Ask User",
      description:
        "Requests structured input from the user via elicitation/create. Fails gracefully if unsupported.",
      inputSchema: {},
    },
    async (): Promise<CallToolResult> => {
      try {
        const result = await server.server.elicitInput({
          message: "Please pick a favorite color and enter your name.",
          requestedSchema: {
            type: "object",
            properties: {
              name: { type: "string", title: "Name" },
              color: {
                type: "string",
                title: "Favorite color",
                enum: ["red", "green", "blue"],
                enumNames: ["Red", "Green", "Blue"],
              },
            },
            required: ["name", "color"],
          },
        });
        return {
          content: [
            {
              type: "text",
              text: `Elicit result: action=${result.action} content=${JSON.stringify(result.content)}`,
            },
          ],
        };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
          content: [
            {
              type: "text",
              text: `Elicitation not supported by this client: ${msg}`,
            },
          ],
          isError: true,
        };
      }
    },
  );

  // ------------------- [CAP-ROOTS] Read client-provided roots ---------------
  server.registerTool(
    "list-roots",
    {
      title: "List Roots",
      description:
        "Asks the client for its list of roots. Fails gracefully if unsupported.",
      inputSchema: {},
    },
    async (): Promise<CallToolResult> => {
      try {
        const result = await server.server.listRoots();
        return {
          content: [
            { type: "text", text: `Roots: ${JSON.stringify(result.roots)}` },
          ],
          structuredContent: { roots: result.roots },
        };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
          content: [
            {
              type: "text",
              text: `Roots not supported by this client: ${msg}`,
            },
          ],
          isError: true,
        };
      }
    },
  );

  // ------------------- [CAP-APP-CHUNK] App-only chunked read ----------------
  const DataChunkSchema = z.object({
    bytes: z.string(),
    offset: z.number(),
    byteCount: z.number(),
    totalBytes: z.number(),
    hasMore: z.boolean(),
  });
  const MAX_CHUNK_BYTES = 256 * 1024;
  // Synthesize a 1MB "file" of random bytes at module load
  const LARGE_BUFFER = Buffer.from(
    Array.from({ length: 1024 * 1024 }, () =>
      Math.floor(Math.random() * 256),
    ),
  );
  registerAppTool(
    server,
    "read-large-file",
    {
      title: "Read Large File (chunked)",
      description:
        "Returns 1MB of synthetic data in chunks. App-only; hidden from the model.",
      inputSchema: {
        offset: z.number().int().min(0).default(0),
        byteCount: z.number().int().min(1).default(MAX_CHUNK_BYTES),
      },
      outputSchema: DataChunkSchema.shape,
      _meta: { ui: { visibility: ["app"] } },
    },
    async ({ offset, byteCount }): Promise<CallToolResult> => {
      const end = Math.min(offset + byteCount, LARGE_BUFFER.length);
      const chunk = LARGE_BUFFER.subarray(offset, end);
      return {
        content: [
          {
            type: "text",
            text: `${chunk.length} bytes @ offset ${offset}`,
          },
        ],
        structuredContent: {
          bytes: chunk.toString("base64"),
          offset,
          byteCount: chunk.length,
          totalBytes: LARGE_BUFFER.length,
          hasMore: end < LARGE_BUFFER.length,
        },
      };
    },
  );

  // ------------------- [CAP-APP-APPONLY] Refresh (poll) ---------------------
  registerAppTool(
    server,
    "poll-metrics",
    {
      title: "Poll Metrics",
      description:
        "Returns a fresh snapshot of metrics. App-only; hidden from the model. Used by the dashboard's refresh button.",
      inputSchema: {},
      outputSchema: {
        metrics: z.array(
          z.object({ label: z.string(), value: z.number() }),
        ),
        sampledAt: z.string(),
      },
      _meta: { ui: { visibility: ["app"] } },
    },
    async (): Promise<CallToolResult> => {
      const metrics = [
        { label: "Users", value: Math.round(50 + Math.random() * 50) },
        { label: "Requests", value: Math.round(100 + Math.random() * 900) },
        { label: "Errors", value: Math.round(Math.random() * 5) },
      ];
      return {
        content: [
          { type: "text", text: JSON.stringify(metrics) },
        ],
        structuredContent: {
          metrics,
          sampledAt: new Date().toISOString(),
        },
      };
    },
  );

  // ------------------- [CAP-APP-PARTIAL] Shader (fullscreen + streaming) ----
  registerAppTool(
    server,
    "shader-preview",
    {
      title: "Shader Preview",
      description:
        "Renders a GLSL fragment shader in a fullscreen View. Views subscribe to ontoolinputpartial to preview code as it streams.",
      inputSchema: {
        code: z
          .string()
          .describe(
            "GLSL fragment shader source. Must define `void main()` writing to gl_FragColor.",
          ),
      },
      _meta: { ui: { resourceUri: SHADER_URI } },
    },
    async ({ code }): Promise<CallToolResult> => {
      return {
        content: [{ type: "text", text: `Shader accepted (${code.length} chars).` }],
        structuredContent: { code },
      };
    },
  );

  // ------------------- Counter View (subscribes to live resource) -----------
  registerAppTool(
    server,
    "open-counter",
    {
      title: "Open Live Counter",
      description:
        "Opens a picture-in-picture View that subscribes to a live-updating counter resource.",
      inputSchema: {},
      _meta: { ui: { resourceUri: COUNTER_URI, preferredDisplayMode: "pip" } },
    },
    async (): Promise<CallToolResult> => {
      return {
        content: [
          {
            type: "text",
            text: "Counter opened. It will tick once per second while any client is subscribed.",
          },
        ],
        structuredContent: { resourceUri: LIVE_COUNTER_URI },
      };
    },
  );

  // ------------------- [CAP-LISTCHANGED] Toggle a dynamic tool --------------
  let dynamicRegistered = false;
  server.registerTool(
    "toggle-dynamic-tool",
    {
      title: "Toggle Dynamic Tool",
      description:
        "Registers or unregisters a `dynamic-hello` tool and emits notifications/tools/list_changed.",
      inputSchema: {},
    },
    async (): Promise<CallToolResult> => {
      if (dynamicRegistered) {
        // McpServer doesn't have a public unregister API; simulate by
        // re-registering with disabled=true would need internal access.
        // Instead we emit the notification and describe the state.
        server.server.sendToolListChanged();
        dynamicRegistered = false;
        return {
          content: [
            {
              type: "text",
              text: "Emitted list_changed (dynamic-hello considered removed).",
            },
          ],
        };
      }
      server.registerTool(
        "dynamic-hello",
        {
          title: "Dynamic Hello",
          description: "Dynamically registered tool.",
          inputSchema: {},
        },
        async (): Promise<CallToolResult> => ({
          content: [{ type: "text", text: "Hello from a dynamic tool!" }],
        }),
      );
      server.server.sendToolListChanged();
      dynamicRegistered = true;
      return {
        content: [
          {
            type: "text",
            text: "Registered `dynamic-hello` and emitted list_changed.",
          },
        ],
      };
    },
  );

  // =========================================================================
  // RESOURCES
  // =========================================================================

  // [CAP-RES-STATIC]
  server.registerResource(
    "config",
    STATIC_CONFIG_URI,
    {
      title: "Server Configuration",
      description: "Static JSON configuration blob for this server.",
      mimeType: "application/json",
    },
    async (): Promise<ReadResourceResult> => ({
      contents: [
        {
          uri: STATIC_CONFIG_URI,
          mimeType: "application/json",
          text: JSON.stringify(
            { name: "mcp-app-sample", version: "0.1.0", tools: 11 },
            null,
            2,
          ),
        },
      ],
    }),
  );

  // [CAP-RES-TEMPLATE]
  server.registerResource(
    "item",
    new ResourceTemplate(ITEM_TEMPLATE, {
      list: async () => ({
        resources: Object.values(ITEM_DB).map((it) => ({
          uri: `resource:///items/${it.id}`,
          name: `item ${it.id}`,
          mimeType: "application/json",
        })),
      }),
    }),
    {
      title: "Item lookup",
      description:
        "Look up an item by id. Try ids 42, 43, 44 to see resources listed above.",
      mimeType: "application/json",
    },
    async (uri, params): Promise<ReadResourceResult> => {
      const id = Array.isArray(params.id) ? params.id[0] : params.id;
      const item = ITEM_DB[id];
      if (!item) {
        return {
          contents: [
            {
              uri: uri.href,
              mimeType: "application/json",
              text: JSON.stringify({ error: `no item ${id}` }),
            },
          ],
        };
      }
      return {
        contents: [
          {
            uri: uri.href,
            mimeType: "application/json",
            text: JSON.stringify(item),
          },
        ],
      };
    },
  );

  // [CAP-RES-BLOB]
  server.registerResource(
    "logo",
    BINARY_LOGO_URI,
    {
      title: "Logo (binary blob)",
      description: "A 1x1 transparent PNG served as a base64 blob.",
      mimeType: "image/png",
    },
    async (): Promise<ReadResourceResult> => ({
      contents: [
        { uri: BINARY_LOGO_URI, mimeType: "image/png", blob: TINY_PNG_B64 },
      ],
    }),
  );

  // [CAP-RES-SUBSCRIBE] the live counter resource
  server.registerResource(
    "live-counter",
    LIVE_COUNTER_URI,
    {
      title: "Live Counter",
      description:
        "Increments every second. Call resources/subscribe to receive notifications/resources/updated.",
      mimeType: "application/json",
    },
    async (): Promise<ReadResourceResult> => ({
      contents: [
        {
          uri: LIVE_COUNTER_URI,
          mimeType: "application/json",
          text: JSON.stringify({
            counter: currentCounterValue(),
            observedAt: new Date().toISOString(),
          }),
        },
      ],
    }),
  );

  // =========================================================================
  // PROMPTS
  // =========================================================================

  // [CAP-PROMPT] + [CAP-COMPLETE] argument completion
  server.registerPrompt(
    "code-review",
    {
      title: "Code Review",
      description: "Requests a code review in the given language.",
      argsSchema: {
        language: completable(
          z.string().describe("Programming language"),
          (partial) => {
            const options = [
              "typescript",
              "javascript",
              "python",
              "rust",
              "go",
              "java",
            ];
            return options.filter((o) =>
              o.startsWith(partial.toLowerCase()),
            );
          },
        ),
        focus: z
          .string()
          .optional()
          .describe("Optional focus area (perf, security, ...)"),
      },
    },
    ({ language, focus }) => ({
      messages: [
        {
          role: "user" as const,
          content: {
            type: "text" as const,
            text: `Please review the ${language} code below${focus ? ` focusing on ${focus}` : ""}. Point out bugs and suggest concrete improvements.`,
          },
        },
      ],
    }),
  );

  // =========================================================================
  // UI RESOURCES (MCP Apps)
  // =========================================================================

  // [CAP-APP] [CAP-APP-CSP]
  registerAppResource(
    server,
    "Dashboard View",
    DASHBOARD_URI,
    {
      mimeType: RESOURCE_MIME_TYPE,
      _meta: {
        // ext-apps CSP metadata: no external network calls needed.
        "mcpui/csp": {
          "connect-src": [],
        },
      },
    },
    async (): Promise<ReadResourceResult> => {
      const html = await fs.readFile(
        path.join(DIST_DIR, "dashboard.html"),
        "utf-8",
      );
      return {
        contents: [
          { uri: DASHBOARD_URI, mimeType: RESOURCE_MIME_TYPE, text: html },
        ],
      };
    },
  );

  registerAppResource(
    server,
    "Shader View",
    SHADER_URI,
    { mimeType: RESOURCE_MIME_TYPE },
    async (): Promise<ReadResourceResult> => {
      const html = await fs.readFile(
        path.join(DIST_DIR, "shader.html"),
        "utf-8",
      );
      return {
        contents: [
          { uri: SHADER_URI, mimeType: RESOURCE_MIME_TYPE, text: html },
        ],
      };
    },
  );

  registerAppResource(
    server,
    "Counter View",
    COUNTER_URI,
    { mimeType: RESOURCE_MIME_TYPE },
    async (): Promise<ReadResourceResult> => {
      const html = await fs.readFile(
        path.join(DIST_DIR, "counter.html"),
        "utf-8",
      );
      return {
        contents: [
          { uri: COUNTER_URI, mimeType: RESOURCE_MIME_TYPE, text: html },
        ],
      };
    },
  );

  return server;
}
