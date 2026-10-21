/**
 * Tool: show_agent_map — Returns all agents grouped for circle-packing visualization.
 */
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { getAgentRegistry, getAgentDetailsMap } from "../graph/packages.js";
import { getAssignableUsers } from "../graph/users.js";
import type { AgentMapGroup, PublisherType } from "../types.js";

const GROUP_COLORS: Record<PublisherType, string> = {
  Microsoft: "#0078D4",
  CopilotStudio: "#F7630C",
  AgentBuilder: "#8B5CF6",
  ThirdParty: "#8764B8",
  AgentsToolkit: "#498205",
  Others: "#E3008C",
};

export async function handleShowAgentMap(incomingToken?: string): Promise<CallToolResult> {
  try {
    const { agents, dataSource } = await getAgentRegistry(incomingToken);
    const [detailMap, assignableUsers] = await Promise.all([
      getAgentDetailsMap(agents, incomingToken),
      getAssignableUsers(incomingToken),
    ]);

    // Group agents by publisher type
    const groupMap = new Map<PublisherType, number>();
    for (const agent of agents) {
      groupMap.set(agent.publisherType, (groupMap.get(agent.publisherType) ?? 0) + 1);
    }

    const groups: AgentMapGroup[] = Array.from(groupMap.entries()).map(([type, count]) => ({
      name: type,
      type,
      count,
      color: GROUP_COLORS[type],
    }));

    return {
      content: [
        {
          type: "text",
          text: `Agent Map: ${agents.length} agents across ${groups.length} publisher types. ${groups.map((g) => `${g.name}: ${g.count}`).join(", ")}`,
        },
      ],
      structuredContent: { agents, groups, dataSource, detailMap, assignableUsers } as unknown as Record<string, unknown>,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Failed to load agent map: ${message}` }],
      isError: true,
    };
  }
}
