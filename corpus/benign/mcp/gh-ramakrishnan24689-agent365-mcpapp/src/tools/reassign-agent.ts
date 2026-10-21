/**
 * Tool: reassign_agent — Reassigns agent ownership to a different user.
 */
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { reassignAgent } from "../graph/packages.js";

export async function handleReassignAgent(
  args: { agentId: string; newOwnerId: string },
  incomingToken?: string,
): Promise<CallToolResult> {
  try {
    await reassignAgent(args.agentId, args.newOwnerId, incomingToken);

    return {
      content: [{ type: "text", text: `Agent ${args.agentId} has been reassigned to user ${args.newOwnerId}.` }],
      structuredContent: {
        success: true,
        message: `Agent reassigned successfully`,
        agentId: args.agentId,
        action: "reassign",
      },
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Failed to reassign agent: ${message}` }],
      isError: true,
    };
  }
}
