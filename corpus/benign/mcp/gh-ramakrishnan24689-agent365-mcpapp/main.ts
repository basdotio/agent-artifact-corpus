/**
 * Entry point — Express server with Streamable HTTP transport (stateless).
 * Extracts the bearer token from the Authorization header and passes
 * it into the MCP server for OBO → Graph calls.
 */
import "dotenv/config";
import { createMcpExpressApp } from "@modelcontextprotocol/sdk/server/express.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import cors from "cors";
import type { Request, Response } from "express";
import { createServer } from "./server.js";

let requestCounter = 0;
const toolCallCounts = new Map<string, number>();

export async function startServer(): Promise<void> {
  const port = parseInt(process.env.PORT ?? "3001", 10);
  const debug = process.env.DEBUG === "true";

  const app = createMcpExpressApp({ host: "0.0.0.0" });
  app.use(cors());

  app.all("/mcp", async (req: Request, res: Response) => {
    const reqId = ++requestCounter;

    if (debug) {
      const ts = new Date().toISOString();
      console.log(`[#${reqId} @ ${ts}] ${req.method} /mcp from ${req.ip}`);
      console.log(`  JSON-RPC method: ${req.body?.method ?? "(none)"} | rpc-id: ${req.body?.id ?? "(none)"}`);
    }

    if (req.body?.method === "tools/call") {
      const toolName = req.body?.params?.name ?? "(unknown)";
      const count = (toolCallCounts.get(toolName) ?? 0) + 1;
      toolCallCounts.set(toolName, count);
      if (debug) console.log(`[#${reqId}] tools/call -> ${toolName} (call #${count})`);
    }

    // Extract bearer token from Copilot's Authorization header
    const authHeader = req.headers.authorization;
    const incomingToken = authHeader?.startsWith("Bearer ")
      ? authHeader.slice(7)
      : undefined;

    if (debug) {
      console.log(`[#${reqId}] Auth token: ${incomingToken ? "present" : "MISSING"}`);
    }

    const server = createServer(incomingToken);
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined, // Stateless
    });

    res.on("close", () => {
      if (debug) console.log(`[#${reqId}] connection closed`);
      transport.close().catch(() => {});
      server.close().catch(() => {});
    });

    try {
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } catch (error) {
      console.error("MCP error:", error);
      if (!res.headersSent) {
        res.status(500).json({
          jsonrpc: "2.0",
          error: { code: -32603, message: "Internal server error" },
          id: null,
        });
      }
    }
  });

  const httpServer = app.listen(port, () => {
    console.log(`\nAgent365 MCP Server listening on http://localhost:${port}/mcp\n`);
    console.log("Available tools: show_agent_registry, show_agent_map, show_risky_agents, block/unblock/reassign_agent, search_users, load_agent_info");
    console.log(process.env.USE_MOCK_DATA === "false"
      ? "Mode: Live (Graph API)"
      : "Mode: Mock (set USE_MOCK_DATA=false for live)\n");
  });

  const shutdown = () => {
    console.log("\nShutting down...");
    httpServer.close(() => process.exit(0));
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

startServer().catch((e) => {
  console.error(e);
  process.exit(1);
});
