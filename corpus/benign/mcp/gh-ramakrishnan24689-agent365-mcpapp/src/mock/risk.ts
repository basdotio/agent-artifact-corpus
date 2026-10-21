/**
 * Mock risky agents data — matches Graph /identityProtection/riskyServicePrincipals shape.
 */
import type { RiskyAgent } from "../types.js";
import { MOCK_AGENTS } from "./packages.js";

const RISK_DETAILS = [
  "Compromised credential detected in dark web scan",
  "Anomalous sign-in activity from unusual location",
  "Leaked credentials found in public repository",
  "Unusual permission escalation pattern detected",
  "Suspicious API call volume spike",
  "Token replay attack indicators observed",
  "Consent phishing attempt associated with this principal",
  "Brute force attack attempt detected",
  "Impossible travel activity detected",
  "Malicious IP address association",
];

// Pick agents with risk and create risky entries
export const MOCK_RISKY_AGENTS: RiskyAgent[] = MOCK_AGENTS
  .filter((a) => a.riskLevel !== "none")
  .map((agent, i) => ({
    id: `risk-${String(i).padStart(3, "0")}`,
    agentId: agent.id,
    displayName: agent.displayName,
    riskLevel: agent.riskLevel as "high" | "medium" | "low",
    riskState: (["atRisk", "confirmedCompromised", "atRisk", "atRisk"] as const)[i % 4],
    riskDetail: RISK_DETAILS[i % RISK_DETAILS.length],
    riskLastUpdatedDateTime: new Date(2025, 4, Math.floor(Math.random() * 14) + 1).toISOString(),
    publisherType: agent.publisherType,
    platform: agent.platform,
  }));
