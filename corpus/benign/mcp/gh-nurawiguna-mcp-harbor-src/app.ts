#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createMcpExpressApp } from "@modelcontextprotocol/sdk/server/express.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  McpError,
  ErrorCode,
  CallToolRequest,
  isInitializeRequest,
} from "@modelcontextprotocol/sdk/types.js";
import { HarborService } from "./services/harbor.service.js";
import { TOOL_DEFINITIONS } from "./definitions/tool.definitions.js";
import { config } from "dotenv";
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import express from "express";
import { timingSafeEqual, randomUUID } from "node:crypto";

// Load environment variables
config();

// Parse command line arguments
const argv = yargs(hideBin(process.argv))
  .env("HARBOR")
  .options({
    url: {
      type: "string",
      description: "Harbor API URL (the remote Harbor server mcp-harbor connects to)",
      demandOption: true,
    },
    username: {
      type: "string",
      description: "Harbor username",
      demandOption: true,
      default: "admin",
    },
    password: {
      type: "string",
      description: "Harbor password",
      demandOption: true,
    },
    insecureTls: {
      type: "boolean",
      description:
        "Disable TLS certificate verification when connecting to the Harbor URL over HTTPS. Only enable this for trusted internal networks using a self-signed certificate; has no effect if --url is http://.",
      default: false,
    },
    debug: {
      type: "boolean",
      description: "Enable debug mode",
      default: false,
    },
    sse: {
      type: "boolean",
      description: "Enable SSE transport",
      default: false,
    },
    port: {
      type: "number",
      description: "Port for the local SSE server to listen on",
      default: 3000,
    },
    sseHost: {
      type: "string",
      description:
        "Host/interface the local SSE server binds to (this machine, not the Harbor server). Keep 127.0.0.1 unless a trusted firewall/reverse proxy restricts who can reach this port.",
      default: "127.0.0.1",
    },
    sseAuthToken: {
      type: "string",
      description:
        "Bearer token required to authenticate SSE connections to this MCP server (required in practice whenever --sse-host is not 127.0.0.1)",
    },
  })
  .help()
  .parseSync(); // Use parseSync instead of argv

if (argv.insecureTls) {
  console.warn(
    "[MCP Server] WARNING: TLS certificate verification is disabled (--insecure-tls). " +
      "Only use this for trusted internal networks with self-signed certificates."
  );
  // hapic/undici honor this Node-wide flag; there is no per-client TLS
  // override exposed by the Harbor client, so this is opt-in and scoped
  // to when the operator explicitly requests it.
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
}

// Initialize HarborService with command line arguments
const harborService = new HarborService(argv.url, {
  username: argv.username,
  password: argv.password,
});

const createServer: () => Promise<Server> = async (): Promise<Server> => {
  interface ToolDefinition {
    description: string;
    inputSchema: Record<string, unknown>;
  }

  interface Tool {
    name: string;
    description: string;
    inputSchema: Record<string, unknown>;
  }

  // Initialize the MCP server
  const server: Server = new Server(
    {
      name: "mcp-harbor",
      version: "1.0.0",
    },
    {
      capabilities: {
        tools: TOOL_DEFINITIONS as Record<string, ToolDefinition>,
      },
    }
  );

  server.onerror = (error: Error): void => {
    console.error("[MCP Error]", error);
    console.error("[MCP Error Stack]", error.stack);

    if (error.cause) {
      console.error("[MCP Error Cause]", error.cause);
    }
  };

  server.setRequestHandler(
    ListToolsRequestSchema,
    async (): Promise<{
      tools: Tool[];
    }> => ({
      tools: Object.entries(TOOL_DEFINITIONS).map(([name, def]) => ({
        name,
        description: def.description,
        inputSchema: def.inputSchema,
      })),
    })
  );

  server.setRequestHandler(
    CallToolRequestSchema,
    async (request: CallToolRequest) => {
      try {
        const args: Record<string, unknown> = request.params.arguments || {};
        return await harborService.handleToolRequest(request.params.name, args);
      } catch (error: unknown) {
        if (error instanceof McpError) throw error;
        throw new McpError(
          ErrorCode.InternalError,
          error instanceof Error ? error.message : "Unknown error occurred"
        );
      }
    }
  );

  return server;
};

// Check if SSE transport is enabled
if (argv.sse) {
  console.info("[MCP Server] Using SSE transport");
  // createMcpExpressApp() also wires up express.json() body parsing and,
  // for localhost hosts, DNS-rebinding protection (Host header validation).
  const app = createMcpExpressApp({ host: argv.sseHost });

  const sseTransports = new Map<string, SSEServerTransport>();
  const streamableTransports = new Map<string, StreamableHTTPServerTransport>();

  const isAuthorized = (req: express.Request): boolean => {
    if (!argv.sseAuthToken) return true;

    const header = req.headers.authorization || "";
    const expected = `Bearer ${argv.sseAuthToken}`;
    const provided = Buffer.from(header);
    const expectedBuf = Buffer.from(expected);

    return (
      provided.length === expectedBuf.length &&
      timingSafeEqual(provided, expectedBuf)
    );
  };

  const requireAuth: express.RequestHandler = (req, res, next) => {
    if (!isAuthorized(req)) {
      res.status(401).send("Unauthorized");
      return;
    }
    next();
  };

  // Deprecated HTTP+SSE transport (MCP protocol version 2024-11-05). Kept for
  // clients that haven't moved to Streamable HTTP yet.
  app.get("/sse", requireAuth, async (req, res) => {
    console.log("[MCP Server] SSE connection established");

    try {
      // Each MCP Server/Protocol instance can only ever be bound to a single
      // transport at a time, so every connection needs its own instance -
      // sharing one across concurrent SSE clients throws "Already connected
      // to a transport" on the second connection.
      const server = await createServer();
      const transport = new SSEServerTransport("/messages", res);
      sseTransports.set(transport.sessionId, transport);
      transport.onclose = (): void => {
        sseTransports.delete(transport.sessionId);
      };

      await server.connect(transport);
    } catch (error) {
      console.error("[MCP Server] Failed to establish SSE connection", error);
      if (!res.headersSent) {
        res.status(500).end();
      }
    }
  });

  app.post("/messages", requireAuth, (req, res) => {
    const sessionId = req.query.sessionId as string | undefined;
    const transport = sessionId ? sseTransports.get(sessionId) : undefined;

    if (!transport) {
      res.status(400).send("No SSE connection established for this session");
      return;
    }
    // req.body is already parsed by createMcpExpressApp()'s express.json(),
    // so hand it to the transport instead of letting it re-read the stream.
    transport.handlePostMessage(req, res, req.body);
  });

  // Streamable HTTP transport (current MCP spec) - handles GET/POST/DELETE
  // on a single endpoint. Most current-generation MCP clients expect this.
  app.all("/mcp", requireAuth, async (req, res) => {
    try {
      const sessionId = req.headers["mcp-session-id"] as string | undefined;
      let transport = sessionId ? streamableTransports.get(sessionId) : undefined;

      if (!transport) {
        if (sessionId) {
          res.status(404).json({
            jsonrpc: "2.0",
            error: { code: -32001, message: "Session not found" },
            id: null,
          });
          return;
        }

        if (req.method !== "POST" || !isInitializeRequest(req.body)) {
          res.status(400).json({
            jsonrpc: "2.0",
            error: {
              code: -32000,
              message: "Bad Request: No valid session ID provided",
            },
            id: null,
          });
          return;
        }

        const newTransport = new StreamableHTTPServerTransport({
          sessionIdGenerator: (): string => randomUUID(),
          onsessioninitialized: (id: string): void => {
            streamableTransports.set(id, newTransport);
          },
        });
        newTransport.onclose = (): void => {
          if (newTransport.sessionId) {
            streamableTransports.delete(newTransport.sessionId);
          }
        };

        const server = await createServer();
        await server.connect(newTransport);
        transport = newTransport;
      }

      await transport.handleRequest(req, res, req.body);
    } catch (error) {
      console.error("[MCP Server] Failed to handle /mcp request", error);
      if (!res.headersSent) {
        res.status(500).json({
          jsonrpc: "2.0",
          error: { code: -32603, message: "Internal server error" },
          id: null,
        });
      }
    }
  });

  app.listen(argv.port, argv.sseHost, () => {
    console.info(
      `[MCP Server] SSE server running on ${argv.sseHost}:${argv.port}`
    );
  });
} else {
  const server = await createServer();
  await server.connect(new StdioServerTransport());
}
