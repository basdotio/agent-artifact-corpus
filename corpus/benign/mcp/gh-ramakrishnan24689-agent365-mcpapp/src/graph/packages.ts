/**
 * Graph API — Copilot Packages (agent registry)
 */
import type { Agent, AgentDetail, DataSource, GraphCopilotPackage, GraphCopilotPackageDetail, GraphRiskyServicePrincipal, RegistryData, RegistryMetrics } from "../types.js";
import { transformPackageToAgent, enrichWithRisk } from "../types.js";
import { useMockData, graphFetch } from "./client.js";
import { MOCK_AGENTS } from "../mock/packages.js";

// Short-lived cache to prevent duplicate Graph API calls when platform retries.
// Note: assumes single-tenant deployment — for multi-tenant, key by tenant ID from JWT.
let registryCache: { data: RegistryData; timestamp: number } | null = null;
const CACHE_TTL_MS = 15_000; // 15 seconds

export async function getAgentRegistry(incomingToken?: string): Promise<RegistryData> {
  // Return cached data if fresh
  if (registryCache && Date.now() - registryCache.timestamp < CACHE_TTL_MS) {
    return registryCache.data;
  }

  let agents: Agent[];
  let dataSource: DataSource = "live";
  if (useMockData()) {
    agents = MOCK_AGENTS;
    dataSource = "mock";
  } else {
    // Fetch agent packages — filter to Copilot-hosted only (matches admin portal "All agents" view)
    interface PagedResponse { value: GraphCopilotPackage[]; "@odata.nextLink"?: string }
    let allPackages: GraphCopilotPackage[] = [];
    let nextUrl: string | undefined = "/copilot/admin/catalog/packages?$count=true&$filter=supportedHosts/any(h:%20h%20eq%20'Copilot')&$top=999";
    while (nextUrl) {
      const page: PagedResponse = await graphFetch<PagedResponse>(
        nextUrl,
        incomingToken,
      );
      allPackages = allPackages.concat(page.value);
      nextUrl = page["@odata.nextLink"];
      if (nextUrl && process.env.DEBUG === "true") console.log(`  Paging... fetched ${allPackages.length} so far`);
    }

    if (process.env.DEBUG === "true") console.log(`Fetched ${allPackages.length} Copilot-hosted packages`);
    // Log distinct type values for debugging publisher classification
    if (process.env.DEBUG === "true") {
      const typeCounts = new Map<string, number>();
      for (const pkg of allPackages) {
        typeCounts.set(pkg.type, (typeCounts.get(pkg.type) ?? 0) + 1);
      }
      console.log(`  Package type distribution: ${[...typeCounts.entries()].map(([k, v]) => `${k}(${v})`).join(", ")}`);
    }
    agents = allPackages.map(transformPackageToAgent);

    // Enrich with risk data
    const riskResponse = await graphFetch<{ value: GraphRiskyServicePrincipal[] }>(
      "/identityProtection/riskyServicePrincipals?$top=200",
      incomingToken,
    );
    agents = enrichWithRisk(agents, riskResponse.value);
  }

  const metrics: RegistryMetrics = {
    total: agents.length,
    atRisk: agents.filter((a) => a.riskLevel !== "none").length,
    noOwner: agents.filter((a) => !a.owner).length,
    blocked: agents.filter((a) => a.status === "Blocked").length,
    active: agents.filter((a) => a.status === "Active").length,
  };

  const result = { agents, metrics, dataSource };
  registryCache = { data: result, timestamp: Date.now() };
  return result;
}

export async function getAgentById(id: string, incomingToken?: string): Promise<Agent | null> {
  if (useMockData()) {
    return MOCK_AGENTS.find((a) => a.id === id) ?? null;
  }

  const pkg = await graphFetch<GraphCopilotPackage>(
    `/copilot/admin/catalog/packages/${id}`,
    incomingToken,
  );
  return transformPackageToAgent(pkg);
}

export async function blockAgent(id: string, _reason: string, incomingToken?: string): Promise<void> {
  if (useMockData()) {
    const agent = MOCK_AGENTS.find((a) => a.id === id);
    if (agent) agent.status = "Blocked";
    return;
  }

  // Graph uses dedicated action endpoint (POST, no body)
  await graphFetch(`/copilot/admin/catalog/packages/${id}/block`, incomingToken, {
    method: "POST",
  });
}

export async function unblockAgent(id: string, incomingToken?: string): Promise<void> {
  if (useMockData()) {
    const agent = MOCK_AGENTS.find((a) => a.id === id);
    if (agent) agent.status = "Active";
    return;
  }

  await graphFetch(`/copilot/admin/catalog/packages/${id}/unblock`, incomingToken, {
    method: "POST",
  });
}

export async function reassignAgent(
  id: string,
  newOwnerId: string,
  incomingToken?: string,
): Promise<void> {
  if (useMockData()) {
    const agent = MOCK_AGENTS.find((a) => a.id === id);
    if (agent) {
      agent.owner = { id: newOwnerId, displayName: "New Owner", mail: "new.owner@contoso.com" };
    }
    return;
  }

  // Reassign via catalog admin endpoint
  await graphFetch(`/copilot/admin/catalog/packages/${id}`, incomingToken, {
    method: "PATCH",
    body: { ownerId: newOwnerId },
  });
}

/** Fetch full detail for a single package, including elementDetails with instructions/capabilities/actions. */
export async function getAgentDetail(id: string, incomingToken?: string): Promise<AgentDetail> {
  if (useMockData()) {
    return {
      agentId: id,
      instructions: "You are a helpful assistant that helps users with their tasks.",
      capabilities: [{ name: "WebSearch" }, { name: "GraphConnectors" }],
      actions: [{ id: "sample-plugin", file: "plugin.json" }],
      conversationStarters: [{ title: "Get started", text: "How can I help you?" }],
      elementTypes: ["declarativeAgent"],
    };
  }

  const pkg = await graphFetch<GraphCopilotPackageDetail>(
    `/copilot/admin/catalog/packages/${id}`,
    incomingToken,
  );

  if (process.env.DEBUG === "true") {
    console.log(`Package detail for ${pkg.displayName}: ${pkg.elementDetails?.length ?? 0} element groups`);
  }

  const result: AgentDetail = {
    agentId: id,
    capabilities: [],
    actions: [],
    elementTypes: [],
  };

  if (!pkg.elementDetails) return result;

  for (const group of pkg.elementDetails) {
    result.elementTypes.push(group.elementType);

    for (const el of group.elements) {
      try {
        const def = JSON.parse(el.definition);

        if (group.elementType.toLowerCase() === "declarativeagent" || group.elementType === "declarativeAgent" || group.elementType.toLowerCase() === "declarativecopilots") {
          // Extract instructions from known schema locations
          const bo = def.behavior_overrides;
          const instr = def.instructions
            ?? (typeof bo === "string" ? bo : null)
            ?? bo?.instructions
            ?? bo?.instruction;
          if (instr && typeof instr === "string") result.instructions = instr;
          if (def.capabilities) {
            result.capabilities = (def.capabilities as Array<Record<string, unknown>>).map((c) => ({
              name: c.name as string,
              config: Object.fromEntries(Object.entries(c).filter(([k]) => k !== "name")),
            }));
          }
          if (def.actions) {
            result.actions = (def.actions as Array<{ id: string; file?: string }>).map((a) => ({
              id: a.id,
              file: a.file,
            }));
          }
          if (def.conversation_starters) {
            result.conversationStarters = def.conversation_starters;
          }
        }

        if (group.elementType.toLowerCase() === "bot") {
          result.botId = def.botId;
        }
      } catch {
        // Non-parseable element definition — skip silently
      }
    }
  }

  return result;
}

/** Batch-fetch details for multiple agents in parallel. Returns a map of agentId → AgentDetail. */
export async function getAgentDetailsMap(
  agents: Agent[],
  incomingToken?: string,
): Promise<Record<string, AgentDetail>> {
  const customAgents = agents.filter(a => a.publisherType === "CopilotStudio" || a.publisherType === "AgentBuilder");
  if (customAgents.length === 0) return {};

  if (process.env.DEBUG === "true") console.log(`Preloading details for ${customAgents.length} custom agents...`);
  const results = await Promise.allSettled(
    customAgents.map(a => getAgentDetail(a.id, incomingToken))
  );

  const detailMap: Record<string, AgentDetail> = {};
  results.forEach((result, i) => {
    if (result.status === "fulfilled") {
      detailMap[customAgents[i].id] = result.value;
    }
  });

  if (process.env.DEBUG === "true") console.log(`Preloaded details for ${Object.keys(detailMap).length}/${customAgents.length} custom agents`);
  return detailMap;
}
