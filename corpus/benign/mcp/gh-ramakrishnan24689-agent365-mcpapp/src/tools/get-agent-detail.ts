/**
 * Tool: get_agent_detail — Fetches instructions, capabilities, and actions for a single agent.
 * Called on-demand when a user clicks an agent in the detail panel.
 */
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { getAgentDetail } from "../graph/packages.js";

export async function handleGetAgentDetail(
  args: { agentId: string },
  incomingToken?: string,
): Promise<CallToolResult> {
  try {
    const detail = await getAgentDetail(args.agentId, incomingToken);

    return {
      content: [{ type: "text", text: JSON.stringify(detail) }],
      structuredContent: { ...detail, agentId: args.agentId } as unknown as Record<string, unknown>,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`get_agent_detail error: ${message}`);
    return {
      content: [{ type: "text", text: `Failed to fetch agent detail: ${message}` }],
      isError: true,
    };
  }
}
