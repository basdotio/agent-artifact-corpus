/**
 * Tool: unblock_agent — Unblocks a previously blocked agent.
 */
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { unblockAgent } from "../graph/packages.js";

export async function handleUnblockAgent(
  args: { agentId: string },
  incomingToken?: string,
): Promise<CallToolResult> {
  try {
    await unblockAgent(args.agentId, incomingToken);

    return {
      content: [{ type: "text", text: `Agent ${args.agentId} has been unblocked.` }],
      structuredContent: {
        success: true,
        message: `Agent unblocked successfully`,
        agentId: args.agentId,
        action: "unblock",
      },
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Failed to unblock agent: ${message}` }],
      isError: true,
    };
  }
}
