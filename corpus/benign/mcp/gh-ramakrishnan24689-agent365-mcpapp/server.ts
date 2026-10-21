/**
 * MCP Server — Agent365
 *
 * Registers all tools and their corresponding UI resources.
 * Each primary tool has a widget; action tools are callable from widgets.
 */
import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult, ReadResourceResult } from "@modelcontextprotocol/sdk/types.js";
import fs from "node:fs/promises";
import path from "node:path";
import { z } from "zod";

import { handleShowRegistry } from "./src/tools/show-registry.js";
import { handleShowAgentMap } from "./src/tools/show-agent-map.js";
import { handleShowRisky } from "./src/tools/show-risky.js";
import { handleBlockAgent } from "./src/tools/block-agent.js";
import { handleUnblockAgent } from "./src/tools/unblock-agent.js";
import { handleReassignAgent } from "./src/tools/reassign-agent.js";
import { handleGetAgentDetail } from "./src/tools/get-agent-detail.js";
import { searchUsers } from "./src/graph/users.js";

const DIST_DIR = import.meta.filename.endsWith(".ts")
  ? path.join(import.meta.dirname, "dist", "ui")
  : path.join(import.meta.dirname, "ui");

/**
 * Helper: register a tool + its UI resource.
 */
function registerToolWithUI(
  server: McpServer,
  name: string,
  title: string,
  description: string,
  resourceFileName: string,
  inputSchema: Record<string, z.ZodTypeAny>,
  handler: (args: Record<string, unknown>) => Promise<CallToolResult>,
  options?: { readOnlyHint?: boolean },
) {
  const resourceUri = `ui://${name}/${resourceFileName}`;

  registerAppTool(
    server,
    name,
    {
      title,
      description,
      inputSchema,
      annotations: { readOnlyHint: options?.readOnlyHint ?? true },
      _meta: { ui: { resourceUri } },
    },
    handler as any, // MCP SDK handler generics don't align with our typed inputSchema — safe cast
  );

  registerAppResource(
    server,
    resourceUri,
    resourceUri,
    { mimeType: RESOURCE_MIME_TYPE, description: title },
    async (): Promise<ReadResourceResult> => {
      const html = await fs.readFile(
        path.join(DIST_DIR, resourceFileName),
        "utf-8",
      );
      return {
        contents: [{ uri: resourceUri, mimeType: RESOURCE_MIME_TYPE, text: html }],
      };
    },
  );
}

/**
 * Creates a new MCP server instance.
 * @param incomingToken - Bearer token from Copilot (undefined in mock mode)
 */
export function createServer(incomingToken?: string): McpServer {
  const server = new McpServer({
    name: "Agent365 — MCP App Server",
    version: "1.0.0",
  });

  // ─── Primary Tools (with widgets) ────────────────────────────────────

  registerToolWithUI(
    server,
    "show_agent_registry",
    "Agent Registry",
    "Show the full Agent 365 registry with all agents, their status, platform, risk level, and ownership. Provides an interactive inventory with filters, search, and detail drawer for managing agents.",
    "agent-registry.html",
    {},
    async () => handleShowRegistry(incomingToken),
  );

  registerToolWithUI(
    server,
    "show_agent_map",
    "Agent Map",
    "Visualize all agents as an interactive circle-packing bubble map, grouped by publisher type. Shows the distribution and scale of agents across Microsoft, Copilot Studio, Third Party, Agents Toolkit, and others.",
    "agent-map.html",
    {},
    async () => handleShowAgentMap(incomingToken),
  );

  registerToolWithUI(
    server,
    "show_risky_agents",
    "Risky Agents",
    "Show agents with active risk signals from identity protection. Displays severity levels, risk state, and details about detected threats. Allows quick blocking of compromised agents.",
    "risky-agents.html",
    {},
    async () => handleShowRisky(incomingToken),
  );

  // ─── Action Tools (callable from widgets via callServerTool) ─────────
  // Registered as standard MCP tools (no widget resource needed).
  // The samples use server.tool() for non-widget tools.

  server.tool(
    "block_agent",
    "Block a specific agent by ID. This prevents the agent from being used by anyone in the organization.",
    {
      agentId: z.string().describe("The ID of the agent to block"),
      reason: z.string().optional().describe("Reason for blocking the agent"),
    },
    async ({ agentId, reason }) => handleBlockAgent({ agentId, reason: reason ?? "" }, incomingToken) as any,
  );

  server.tool(
    "unblock_agent",
    "Unblock a previously blocked agent, restoring it to active status.",
    {
      agentId: z.string().describe("The ID of the agent to unblock"),
    },
    async ({ agentId }) => handleUnblockAgent({ agentId }, incomingToken) as any,
  );

  server.tool(
    "reassign_agent",
    "Reassign ownership of an agent to a different user in the organization.",
    {
      agentId: z.string().describe("The ID of the agent to reassign"),
      newOwnerId: z.string().describe("The user ID of the new owner"),
    },
    async ({ agentId, newOwnerId }) => handleReassignAgent({ agentId, newOwnerId }, incomingToken) as any,
  );

  server.tool(
    "load_agent_info",
    "Fetch detailed information for a single agent including instructions, knowledge sources, and actions.",
    {
      agentId: z.string().describe("The package ID of the agent"),
    },
    async ({ agentId }) => handleGetAgentDetail({ agentId }, incomingToken) as any,
  );

  server.tool(
    "search_users",
    "Search for users in the organization by name or email. Use to find a new owner for an agent.",
    {
      query: z.string().describe("Search query — user name or email prefix"),
    },
    async ({ query }) => {
      try {
        const users = await searchUsers(query, incomingToken);
        return {
          content: [{ type: "text", text: JSON.stringify(users) }],
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return { content: [{ type: "text", text: `Failed to search users: ${message}` }], isError: true };
      }
    },
  );

  return server;
}
