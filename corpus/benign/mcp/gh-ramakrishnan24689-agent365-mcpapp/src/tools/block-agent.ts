/**
 * Tool: block_agent — Blocks an agent by ID (called from widget via callServerTool).
 */
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { blockAgent } from "../graph/packages.js";

export async function handleBlockAgent(
  args: { agentId: string; reason?: string },
  incomingToken?: string,
): Promise<CallToolResult> {
  try {
    await blockAgent(args.agentId, args.reason ?? "Blocked by admin", incomingToken);

    return {
      content: [{ type: "text", text: `Agent ${args.agentId} has been blocked.` }],
      structuredContent: {
        success: true,
        message: `Agent blocked successfully`,
        agentId: args.agentId,
        action: "block",
      },
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Failed to block agent: ${message}` }],
      isError: true,
    };
  }
}
