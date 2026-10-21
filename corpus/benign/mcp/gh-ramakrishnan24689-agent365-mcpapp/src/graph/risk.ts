/**
 * Graph API — Risky Service Principals
 */
import type { DataSource, GraphRiskyServicePrincipal, RiskyAgent, RiskyAgentsData, RiskMetrics } from "../types.js";
import { useMockData, graphFetch } from "./client.js";
import { MOCK_RISKY_AGENTS } from "../mock/risk.js";

export async function getRiskyAgents(incomingToken?: string): Promise<RiskyAgentsData> {
  let riskyAgents: RiskyAgent[];
  let dataSource: DataSource = "live";

  if (useMockData()) {
    riskyAgents = MOCK_RISKY_AGENTS;
    dataSource = "mock";
  } else {
    const response = await graphFetch<{ value: GraphRiskyServicePrincipal[] }>(
      "/identityProtection/riskyServicePrincipals?$filter=riskLevel ne 'none'&$top=100",
      incomingToken,
    );

    riskyAgents = response.value.map((item) => ({
      id: item.id,
      agentId: item.appId,
      displayName: item.displayName,
      riskLevel: item.riskLevel as "high" | "medium" | "low",
      riskState: item.riskState as RiskyAgent["riskState"],
      riskDetail: item.riskDetail,
      riskLastUpdatedDateTime: item.riskLastUpdatedDateTime,
      publisherType: "Others" as const,
      platform: item.servicePrincipalType ?? "Unknown",
    }));
  }

  const metrics: RiskMetrics = {
    total: riskyAgents.length,
    high: riskyAgents.filter((a) => a.riskLevel === "high").length,
    medium: riskyAgents.filter((a) => a.riskLevel === "medium").length,
    low: riskyAgents.filter((a) => a.riskLevel === "low").length,
  };

  return { riskyAgents, metrics, dataSource };
}
