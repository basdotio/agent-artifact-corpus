/**
 * Tool: show_agent_registry — Returns agent inventory data + widget.
 */
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { getAgentRegistry, getAgentDetailsMap } from "../graph/packages.js";
import { getAssignableUsers } from "../graph/users.js";

export async function handleShowRegistry(incomingToken?: string): Promise<CallToolResult> {
  try {
    const data = await getAgentRegistry(incomingToken);
    const [detailMap, assignableUsers] = await Promise.all([
      getAgentDetailsMap(data.agents, incomingToken),
      getAssignableUsers(incomingToken),
    ]);

    return {
      content: [
        {
          type: "text",
          text: `Agent Registry: ${data.metrics.total} total agents (${data.metrics.active} active, ${data.metrics.blocked} blocked, ${data.metrics.atRisk} at risk, ${data.metrics.noOwner} without owners)`,
        },
      ],
      structuredContent: { ...data, detailMap, assignableUsers } as unknown as Record<string, unknown>,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Failed to load agent registry: ${message}` }],
      isError: true,
    };
  }
}
