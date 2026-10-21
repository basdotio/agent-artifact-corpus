import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { chooseNextTool, RESPOND } from "./router.js";
import { jevStatus } from "./jev.js";
import { appendDecision } from "./log.js";
import { recordEvent } from "./history.js";

export function createMcpServer(client: string): McpServer {
  if (!["cursor", "antigravity"].includes(client)) throw new Error("MCP client must be cursor or antigravity.");
  const server = new McpServer({ name: "jev-classifier", version: "0.1.0" }, {
    instructions: "Jev recommends the next tool from a catalog you supply. Call jev_choose_next_tool with the user's request and completed actions when you want routing advice. Recommendations are advisory: Jev does not execute tools or intercept your model requests.",
  });
  server.registerTool("jev_status", {
    description: "Check the Jev classifier configuration. No inference request is sent.",
    inputSchema: {}, annotations: { readOnlyHint: true, openWorldHint: false },
  }, async () => ({ content: [{ type: "text", text: JSON.stringify({ client, integration: "mcp-advisory", ...jevStatus() }) }] }));
  server.registerTool("jev_choose_next_tool", {
    description: "Ask Jev to recommend a next tool. Supply available tool names/descriptions and completed actions; exclude this tool itself. Advice only, never executes a tool. Sends the supplied context to the configured Jev provider.",
    inputSchema: {
      user_request: z.string().min(1).max(32000),
      tools: z.array(z.object({ name: z.string().min(1).max(256), description: z.string().max(4000).optional() })).min(1).max(254),
      actions_taken: z.array(z.object({ tool: z.string().max(256), input: z.unknown().optional(), result: z.string().max(8000) })).max(200).default([]),
      assistant_said: z.array(z.string().max(4000)).max(100).default([]),
    }, annotations: { readOnlyHint: true, openWorldHint: true },
  }, async ({ user_request, tools, actions_taken, assistant_said }) => {
    if (new Set(tools.map(t => t.name)).size !== tools.length || tools.some(t => [RESPOND, "jev_choose_next_tool", "jev_status"].includes(t.name))) {
      return { isError: true, content: [{ type: "text", text: "Tool names must be unique; omit respond_to_user and Jev's own tools." }] };
    }
    try {
      const decision = await chooseNextTool({ user_request, assistant_said,
        actions_taken: actions_taken.map((a, i) => ({ ...a, input: a.input, step: i + 1 })) }, tools);
      appendDecision({ ts: new Date().toISOString(), agent: client, model: "mcp-advisory", session: "mcp",
        mode: "shadow", chosen: decision.tool, confidence: decision.confidence, done: decision.done, gated: decision.gated,
        truncated: decision.truncated, top3: decision.top.slice(0, 3).map(t => ({ ...t })), jevMs: decision.latencyMs,
        upstreamMs: 0, toolsCount: tools.length, applied: false, shadowReason: "MCP recommendation; execution remains with the agent" });
      recordEvent(client, `MCP recommendation: ${decision.tool} / confidence ${Math.round(decision.confidence * 100)}%`);
      const { state, ...result } = decision;
      return { content: [{ type: "text", text: JSON.stringify({ ...result, applied: false, integration: "mcp-advisory" }) }] };
    } catch (error) {
      recordEvent(client, `MCP classification failed: ${(error as Error).message}`, true);
      return { isError: true, content: [{ type: "text", text: (error as Error).message }] };
    }
  });
  return server;
}

export async function serveMcp(client: string): Promise<void> {
  await createMcpServer(client).connect(new StdioServerTransport());
}
