/**
 * Shared TypeScript types for Agent 365 MCP App.
 * 
 * Two layers:
 *   1. GraphCopilotPackage — raw shape from /beta/copilot/admin/catalog/packages
 *   2. Agent — our enriched UI model (transformed from Graph + joined data)
 */

// ===========================
// Layer 1: Raw Graph API types
// ===========================

/** Microsoft Graph: packageType enum */
export type GraphPackageType = "microsoft" | "firstParty" | "thirdParty" | "external" | "shared" | "custom" | "unknownFutureValue" | string;

/** Microsoft Graph: packageStatus — actual values from API */
export type GraphPackageStatus = "allowedForAll" | "allowedForSome" | "allowedForNone" | "acquiredForAll" | "acquiredForSome" | "acquiredForNone" | "all" | "some" | "none" | "unknownFutureValue" | string;

/** Raw response from GET /beta/copilot/admin/catalog/packages */
export interface GraphCopilotPackage {
  id: string;
  displayName: string;
  type: GraphPackageType;
  shortDescription?: string;
  longDescription?: string;
  isBlocked: boolean;
  availableTo: GraphPackageStatus;
  deployedTo: GraphPackageStatus;
  lastModifiedDateTime: string;
  supportedHosts: string[]; // "Copilot", "Teams", "Outlook", "Word", "Office", etc.
  elementTypes: string[]; // "Bots", "ComposeExtensions", "ConfigurableTabs", "StaticTabs", etc.
  publisher: string;
  publisherName?: string; // Some responses use this instead of publisher
  platform: string; // "Not Available", "teams", "web", "outlook"
  version: string;
  manifestVersion?: string;
  manifestId?: string; // Bridge to Teams App Catalog (= teamsApp.externalId)
  appId: string | null;
  assetId?: string;
  ownerId?: string | null;
  activeUsers?: number;
  channels?: string[]; // Alternative to supportedHosts in some responses
}

/** Extended detail from GET /beta/copilot/admin/catalog/packages/{id} */
export interface GraphCopilotPackageDetail extends GraphCopilotPackage {
  longDescription?: string;
  categories?: string[];
  sensitivity?: string;
  acquireUsersAndGroups?: GraphPackageAccessEntity[];
  allowedUsersAndGroups?: GraphPackageAccessEntity[];
  elementDetails?: GraphPackageElementDetail[];
}

export interface GraphPackageAccessEntity {
  resourceId: string;
  resourceType: "user" | "group";
}

export interface GraphPackageElementDetail {
  elementType: string;
  elements: { id: string; definition: string }[];
}

/** Raw response from GET /v1.0/identityProtection/riskyServicePrincipals */
export interface GraphRiskyServicePrincipal {
  id: string;
  appId: string;
  servicePrincipalType: string;
  displayName: string;
  riskLevel: "low" | "medium" | "high" | "hidden" | "none" | "unknownFutureValue";
  riskState: "atRisk" | "confirmedCompromised" | "remediated" | "dismissed" | "unknownFutureValue";
  riskDetail: string;
  riskLastUpdatedDateTime: string;
}

// ===========================
// Layer 2: UI Model types
// ===========================

export type PublisherType = "Microsoft" | "CopilotStudio" | "AgentBuilder" | "ThirdParty" | "AgentsToolkit" | "Others";
export type AgentStatus = "Active" | "Blocked";
export type RiskLevel = "high" | "medium" | "low" | "none" | "hidden";

export interface Agent {
  id: string;
  displayName: string;
  description: string;
  publisherType: PublisherType;
  publisherName: string;
  platform: string;
  status: AgentStatus;
  channels: string[]; // supportedHosts mapped
  elementTypes: string[];
  activeUsers: number; // acquireUsersAndGroups.length or 0
  deployedTo: string; // "all" | "some" | "none"
  availableTo: string;
  createdDateTime?: string;
  lastModifiedDateTime: string;
  owner?: AgentOwner;
  riskLevel: RiskLevel;
  sensitivity?: string;
  categories?: string[];
  appId?: string;
  manifestId?: string; // Bridge to Teams App Catalog for icon lookup
  ownerId?: string;
  version?: string;
  /** Inline detail extracted from elementDetails (if available from $expand) */
  detail?: AgentDetail;
}

export interface AgentOwner {
  id: string;
  displayName: string;
  mail: string;
}

// --- Agent Detail (drill-down from single package) ---

export interface AgentCapability {
  name: string;
  config?: Record<string, unknown>;
}

export interface AgentAction {
  id: string;
  file?: string;
}

export interface AgentDetail {
  agentId: string;
  instructions?: string;
  capabilities: AgentCapability[];
  actions: AgentAction[];
  conversationStarters?: { title: string; text: string }[];
  botId?: string;
  elementTypes: string[];
}

// --- Risk types ---

export interface RiskyAgent {
  id: string;
  agentId: string; // appId to cross-reference with packages
  displayName: string;
  riskLevel: "high" | "medium" | "low";
  riskState: "atRisk" | "confirmedCompromised" | "remediated" | "dismissed";
  riskDetail: string;
  riskLastUpdatedDateTime: string;
  publisherType: PublisherType;
  platform: string;
}

// --- User types ---

export interface User {
  id: string;
  displayName: string;
  mail: string;
  jobTitle?: string;
  department?: string;
}

// --- Tool response types ---

export type DataSource = "live" | "mock";

export interface RegistryData {
  agents: Agent[];
  metrics: RegistryMetrics;
  dataSource: DataSource;
  detailMap?: Record<string, AgentDetail>;
  assignableUsers?: User[];
}

export interface RegistryMetrics {
  total: number;
  atRisk: number;
  noOwner: number;
  blocked: number;
  active: number;
}

export interface AgentMapData {
  agents: Agent[];
  groups: AgentMapGroup[];
  dataSource: DataSource;
  detailMap?: Record<string, AgentDetail>;
  assignableUsers?: User[];
}

export interface AgentMapGroup {
  name: string;
  type: PublisherType;
  count: number;
  color: string;
}

export interface RiskyAgentsData {
  riskyAgents: RiskyAgent[];
  metrics: RiskMetrics;
  dataSource: DataSource;
}

export interface RiskMetrics {
  total: number;
  high: number;
  medium: number;
  low: number;
}

// --- Action result types ---

export interface ActionResult {
  success: boolean;
  message: string;
  agentId: string;
  action: "block" | "unblock" | "reassign";
}

// ===========================
// Transformer: Graph → UI Model
// ===========================

/** Map Graph packageType to our PublisherType */
export function mapPackageType(graphType: GraphPackageType, elementTypes?: string[]): PublisherType {
  const normalized = (graphType ?? "").toLowerCase();
  switch (normalized) {
    case "microsoft":
    case "firstparty": return "Microsoft";
    case "thirdparty":
    case "external": return "ThirdParty";
    case "shared": {
      // Distinguish Agent Builder (declarative agents) from Copilot Studio (custom engine)
      const types = elementTypes?.map(t => t.toLowerCase()) ?? [];
      if (types.includes("declarativecopilots")) return "AgentBuilder";
      if (types.includes("customenginecopilots")) return "CopilotStudio";
      return "CopilotStudio"; // default for shared
    }
    case "custom":
    case "sideloaded": return "AgentsToolkit";
    default: return "Others";
  }
}

/** Transform raw Graph package into our Agent UI model */
export function transformPackageToAgent(pkg: GraphCopilotPackage | GraphCopilotPackageDetail): Agent {
  const detail = pkg as GraphCopilotPackageDetail;
  const agent: Agent = {
    id: pkg.id,
    displayName: pkg.displayName,
    description: stripHtml(detail.longDescription ?? pkg.shortDescription ?? ""),
    publisherType: mapPackageType(pkg.type, pkg.elementTypes),
    publisherName: pkg.publisherName ?? pkg.publisher ?? "Unknown",
    platform: pkg.platform ?? "Not Available",
    status: pkg.isBlocked ? "Blocked" : "Active",
    channels: pkg.channels ?? pkg.supportedHosts ?? [],
    elementTypes: pkg.elementTypes ?? [],
    activeUsers: pkg.activeUsers ?? detail.acquireUsersAndGroups?.length ?? 0,
    deployedTo: pkg.deployedTo ?? "none",
    availableTo: pkg.availableTo ?? "none",
    lastModifiedDateTime: pkg.lastModifiedDateTime,
    riskLevel: "none", // enriched separately from riskyServicePrincipals
    sensitivity: detail.sensitivity,
    categories: detail.categories,
    appId: pkg.appId ?? undefined,
    manifestId: pkg.manifestId ?? undefined,
    ownerId: pkg.ownerId ?? undefined,
    version: pkg.version,
    owner: undefined, // enriched separately from agentRegistrations
  };

  // Extract inline detail from elementDetails if present (from $expand)
  if (detail.elementDetails && detail.elementDetails.length > 0) {
    const agentDetail: AgentDetail = {
      agentId: pkg.id,
      capabilities: [],
      actions: [],
      elementTypes: [],
    };
    for (const group of detail.elementDetails) {
      agentDetail.elementTypes.push(group.elementType);
      for (const el of group.elements) {
        try {
          const def = JSON.parse(el.definition);
          if (group.elementType.toLowerCase() === "declarativeagent" || group.elementType === "declarativeAgent" || group.elementType.toLowerCase() === "declarativecopilots") {
            const bo = def.behavior_overrides;
            const instr = def.instructions ?? (typeof bo === "string" ? bo : null) ?? bo?.instructions ?? bo?.instruction;
            if (instr && typeof instr === "string") agentDetail.instructions = instr;
            if (def.capabilities) {
              agentDetail.capabilities = (def.capabilities as Array<Record<string, unknown>>).map((c) => ({
                name: c.name as string,
                config: Object.fromEntries(Object.entries(c).filter(([k]) => k !== "name")),
              }));
            }
            if (def.actions) {
              agentDetail.actions = (def.actions as Array<{ id: string; file?: string }>).map((a) => ({
                id: a.id,
                file: a.file,
              }));
            }
            if (def.conversation_starters) {
              agentDetail.conversationStarters = def.conversation_starters;
            }
          }
          if (group.elementType.toLowerCase() === "bot") {
            agentDetail.botId = def.botId;
          }
        } catch { /* skip unparseable definitions */ }
      }
    }
    agent.detail = agentDetail;
  }

  return agent;
}

/** Strip HTML tags from a string (Graph may return HTML in descriptions) */
export function stripHtml(html: string): string {
  // Replace block-level tags with newlines for readability
  let text = html.replace(/<br\s*\/?>/gi, "\n").replace(/<\/(?:p|div|li|h[1-6])>/gi, "\n");
  // Remove all remaining tags
  text = text.replace(/<[^>]*>/g, "");
  // Decode common HTML entities
  text = text.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, " ");
  // Collapse multiple newlines/spaces
  text = text.replace(/\n{3,}/g, "\n\n").replace(/[ \t]+/g, " ");
  return text.trim();
}

/** Enrich agents with risk data from riskyServicePrincipals (joined by appId) */
export function enrichWithRisk(agents: Agent[], risks: GraphRiskyServicePrincipal[]): Agent[] {
  const riskByAppId = new Map(risks.map(r => [r.appId, r]));
  return agents.map(a => {
    const risk = a.appId ? riskByAppId.get(a.appId) : undefined;
    if (risk && risk.riskLevel !== "none" && risk.riskLevel !== "unknownFutureValue") {
      return { ...a, riskLevel: risk.riskLevel as RiskLevel };
    }
    return a;
  });
}
