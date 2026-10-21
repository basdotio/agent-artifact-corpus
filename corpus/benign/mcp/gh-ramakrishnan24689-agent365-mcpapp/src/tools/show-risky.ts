/**
 * Tool: show_risky_agents — Returns agents with active risk signals.
 */
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { getRiskyAgents } from "../graph/risk.js";

export async function handleShowRisky(incomingToken?: string): Promise<CallToolResult> {
  try {
    const data = await getRiskyAgents(incomingToken);

    return {
      content: [
        {
          type: "text",
          text: `Risky Agents: ${data.metrics.total} agents with risk signals (${data.metrics.high} high, ${data.metrics.medium} medium, ${data.metrics.low} low)`,
        },
      ],
      structuredContent: data as unknown as Record<string, unknown>,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Failed to load risky agents: ${message}` }],
      isError: true,
    };
  }
}
