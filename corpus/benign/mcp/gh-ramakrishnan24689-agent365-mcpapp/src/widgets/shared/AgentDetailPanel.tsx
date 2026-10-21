/**
 * AgentDetailPanel — Shared detail panel matching Microsoft Agent 365 admin center layout.
 * Used by both Agent Registry and Agent Map widgets.
 *
 * Layout:
 *   ✕ close button (top-right)
 *   Tabs: Details | Users | Data & tools | Security | Permissions | Activity
 *   Details tab:
 *     - Card: "About this agent" with version + description
 *     - Card: "Overview" 2-column key-value grid
 *     - Card: "Instructions" collapsible with chevron
 */
import React, { useState } from "react";
import {
  Text,
  Button,
  MessageBar,
  MessageBarBody,
  MessageBarTitle,
  Tab,
  TabList,
  Skeleton,
  SkeletonItem,
  Menu,
  MenuTrigger,
  MenuPopover,
  MenuList,
  MenuItem,
  makeStyles,
  mergeClasses,
  tokens,
} from "@fluentui/react-components";
import {
  DismissRegular,
  ShieldCheckmarkRegular,
  WarningRegular,
  ProhibitedRegular,
  CheckmarkCircleRegular,
  ChevronDownRegular,
  ChevronUpRegular,
  PersonAddRegular,
  PlugConnectedRegular,
  GlobeRegular,
  MoreHorizontalRegular,
  DeleteRegular,
} from "@fluentui/react-icons";
import type { Agent, AgentDetail } from "../../../src/types";

export interface AgentDetailPanelProps {
  agent: Agent;
  agentDetail?: AgentDetail | null;
  detailLoading?: boolean;
  onClose: () => void;
  onBlock?: (agentId: string) => void;
  onUnblock?: (agentId: string) => void;
  onAssignOwner?: () => void;
  onDelete?: (agentId: string) => void;
}

const useStyles = makeStyles({
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.3)",
    zIndex: 1000,
  },
  panel: {
    position: "fixed",
    top: 0,
    right: 0,
    bottom: 0,
    width: "580px",
    maxWidth: "90vw",
    backgroundColor: "#f5f5f5",
    boxShadow: tokens.shadow64,
    zIndex: 1001,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    transition: "width 0.2s ease",
  },
  panelExpanded: {
    width: "700px",
  },
  header: {
    padding: "12px 24px",
    backgroundColor: tokens.colorNeutralBackground1,
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-end",
    gap: "8px",
  },
  content: {
    flex: 1,
    overflow: "auto",
    padding: "20px 24px",
  },
  /* Card container — each section wrapped in a card with shadow */
  card: {
    backgroundColor: tokens.colorNeutralBackground1,
    borderRadius: "8px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.08), 0 0 2px rgba(0,0,0,0.04)",
    padding: "20px 24px",
    marginBottom: "16px",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "12px",
  },
  cardHeaderClickable: {
    cursor: "pointer",
  },
  aboutDescription: {
    padding: "16px",
    backgroundColor: tokens.colorNeutralBackground2,
    borderRadius: "6px",
    lineHeight: "1.6",
    fontSize: "13px",
    color: tokens.colorNeutralForeground2,
  },
  overviewGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0",
  },
  overviewCell: {
    padding: "12px 16px",
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    "&:nth-last-child(-n+2)": {
      borderBottom: "none",
    },
  },
  overviewLabel: {
    display: "block",
    fontSize: "12px",
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
    marginBottom: "4px",
  },
  overviewValue: {
    display: "block",
    fontSize: "13px",
    fontWeight: 400,
    color: tokens.colorNeutralForeground1,
  },
  instructionsBox: {
    whiteSpace: "pre-wrap" as const,
    lineHeight: "1.6",
    fontSize: "13px",
    color: tokens.colorNeutralForeground2,
    maxHeight: "400px",
    overflow: "auto",
    padding: "8px 16px",
  },
  capabilityChip: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 12px",
    borderRadius: "6px",
    backgroundColor: tokens.colorNeutralBackground3,
    fontSize: "13px",
    fontWeight: 500,
    marginRight: "8px",
    marginBottom: "8px",
  },
  actionCard: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "12px 16px",
    borderRadius: "8px",
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    marginBottom: "8px",
  },
});

function formatDeployStatus(value: string): string {
  switch (value) {
    case "acquiredForAll": return "All users";
    case "acquiredForSome": return "Some users";
    case "acquiredForNone": return "Not deployed";
    case "allowedForAll": return "All users";
    case "allowedForSome": return "Some users";
    case "allowedForNone": return "Not available";
    case "all": return "All users";
    case "some": return "Some users";
    case "none": return "None";
    default: return value || "—";
  }
}

function formatCapabilityName(name: string): string {
  const names: Record<string, string> = {
    WebSearch: "Web Search",
    OneDriveAndSharePoint: "OneDrive & SharePoint",
    GraphConnectors: "Graph Connectors",
    GraphicArt: "Image Generation",
    CodeInterpreter: "Code Interpreter",
    Dataverse: "Dataverse",
    TeamsMessages: "Teams Messages",
    Email: "Email",
    People: "People",
    Meetings: "Meetings",
    EmbeddedKnowledge: "Embedded Knowledge",
  };
  return names[name] ?? name;
}

export function AgentDetailPanel({ agent, agentDetail: agentDetailProp, detailLoading: detailLoadingProp, onClose, onBlock, onUnblock, onAssignOwner, onDelete }: AgentDetailPanelProps) {
  const styles = useStyles();
  const [activeTab, setActiveTab] = useState("details");
  const [aboutExpanded, setAboutExpanded] = useState(true);
  const [instructionsExpanded, setInstructionsExpanded] = useState(true);

  const agentDetail = agentDetailProp ?? agent.detail ?? null;
  const detailLoading = detailLoadingProp ?? false;

  const tabs = ["Details", "Users", "Data & tools", "Security", "Permissions", "Activity"];

  return (
    <>
      <div className={styles.overlay} onClick={onClose} />
      <div className={mergeClasses(styles.panel)}>
        {/* Agent name + icon header */}
        <div style={{ padding: "20px 24px 12px", display: "flex", alignItems: "center", gap: "12px", borderBottom: `1px solid ${tokens.colorNeutralStroke2}` }}>
          <div style={{ width: 40, height: 40, borderRadius: "8px", backgroundColor: tokens.colorNeutralBackground3, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span dangerouslySetInnerHTML={{ __html: `<svg viewBox="0 0 28 28" width="24" height="24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8.31 24.6 14.36 3H18a6.5 6.5 0 0 0 .12 0c1.16 0 2.23.62 2.81 1.63l4.77 8.25c.4.7.4 1.55 0 2.24l-5.06 8.76c-.4.7-1.14 1.12-1.94 1.12H9.88c-.56 0-1.1-.14-1.57-.4Z" fill="url(#pd_a)"/><path d="M8.31 24.6 14.36 3H18a6.5 6.5 0 0 0 .12 0c1.16 0 2.23.62 2.81 1.63l4.77 8.25c.4.7.4 1.55 0 2.24l-5.06 8.76c-.4.7-1.14 1.12-1.94 1.12H9.88c-.56 0-1.1-.14-1.57-.4Z" fill="url(#pd_b)" fill-opacity=".5"/><path d="M16.02 5.2a2.5 2.5 0 0 1 2.3-2.2H9.3c-.8 0-1.54.43-1.95 1.13L2.3 12.88c-.4.7-.4 1.55 0 2.24l4.76 8.26c.1.16.2.31.33.45a2.5 2.5 0 0 0 4.59-1.02l4.04-17.6Z" fill="url(#pd_c)"/><path d="M16.02 5.2a2.5 2.5 0 0 1 2.3-2.2H9.3c-.8 0-1.54.43-1.95 1.13L2.3 12.88c-.4.7-.4 1.55 0 2.24l4.76 8.26c.1.16.2.31.33.45a2.5 2.5 0 0 0 4.59-1.02l4.04-17.6Z" fill="url(#pd_d)" fill-opacity=".4"/><defs><radialGradient id="pd_a" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="rotate(-87.78 24.2 7.07) scale(32.08 26.98)"><stop stop-color="#FFC470"/><stop offset=".25" stop-color="#FF835C"/><stop offset=".58" stop-color="#F24A9D"/><stop offset=".87" stop-color="#B339F0"/><stop offset="1" stop-color="#C354FF"/></radialGradient><radialGradient id="pd_b" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="matrix(-14.42 -13.52 13.65 -14.57 15.57 22.46)"><stop offset=".71" stop-color="#FFB357" stop-opacity="0"/><stop offset=".94" stop-color="#FFB357"/></radialGradient><radialGradient id="pd_c" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="rotate(-159.14 13.87 9.23) scale(30 26.54)"><stop offset=".22" stop-color="#4E46E2"/><stop offset=".58" stop-color="#625DF6"/><stop offset=".95" stop-color="#E37DFF"/></radialGradient><linearGradient id="pd_d" x1="6.96" y1="12.11" x2="14.03" y2="13.69" gradientUnits="userSpaceOnUse"><stop stop-color="#7563F7" stop-opacity="0"/><stop offset=".99" stop-color="#4916AE"/></linearGradient></defs></svg>` }} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Text size={500} weight="semibold" style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {agent.displayName}
            </Text>
            <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>
              {agent.publisherName}
            </Text>
          </div>
          <Button appearance="subtle" size="small" icon={<DismissRegular />} onClick={onClose} aria-label="Close panel" />
        </div>

        {/* Header — action buttons */}
        <div className={styles.header}>
          <Button appearance="secondary" size="small" icon={<PersonAddRegular />}
            onClick={onAssignOwner}>
            Assign new owner
          </Button>
          {agent.status !== "Blocked" ? (
            <Button appearance="secondary" size="small" icon={<ProhibitedRegular />}
              onClick={() => onBlock?.(agent.id)}>
              Block
            </Button>
          ) : (
            <Button appearance="secondary" size="small" icon={<CheckmarkCircleRegular />}
              onClick={() => onUnblock?.(agent.id)}>
              Unblock
            </Button>
          )}
          <Menu>
            <MenuTrigger disableButtonEnhancement>
              <Button appearance="secondary" size="small" icon={<MoreHorizontalRegular />}
                style={{ minWidth: "32px", padding: "0 6px" }} aria-label="More actions" />
            </MenuTrigger>
            <MenuPopover>
              <MenuList>
                <MenuItem icon={<DeleteRegular />} onClick={() => onDelete?.(agent.id)}>
                  Delete agent
                </MenuItem>
              </MenuList>
            </MenuPopover>
          </Menu>
        </div>

        {/* Tabs — Fluent UI TabList */}
        <div style={{ padding: "0 24px", backgroundColor: tokens.colorNeutralBackground1 }}>
          <TabList
            selectedValue={activeTab}
            onTabSelect={(_, data) => setActiveTab(data.value as string)}
            size="small"
          >
            {tabs.map((tab) => (
              <Tab key={tab} value={tab.toLowerCase()}>{tab}</Tab>
            ))}
          </TabList>
        </div>

        {/* Content */}
        <div className={styles.content}>
          {activeTab === "details" && (
            <>
              {/* Card: About this agent */}
              <div className={styles.card}>
                <div className={mergeClasses(styles.cardHeader, styles.cardHeaderClickable)} onClick={() => setAboutExpanded(!aboutExpanded)}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Text size={400} weight="semibold">About this agent</Text>
                    {agent.version && (
                      <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>
                        · Version {agent.version}
                      </Text>
                    )}
                  </div>
                  {aboutExpanded ? <ChevronUpRegular /> : <ChevronDownRegular />}
                </div>
                {aboutExpanded && (
                  agent.description ? (
                    <div className={styles.aboutDescription}>
                      {agent.description}
                    </div>
                  ) : (
                    <Text size={200} style={{ color: tokens.colorNeutralForeground3, fontStyle: "italic" }}>
                      No description available.
                    </Text>
                  )
                )}
              </div>

              {/* Card: Overview */}
              <div className={styles.card}>
                <div className={styles.cardHeader}>
                  <Text size={400} weight="semibold">Overview</Text>
                </div>
                <div className={styles.overviewGrid}>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Creation date</span>
                    <span className={styles.overviewValue}>
                      {agent.createdDateTime
                        ? new Date(agent.createdDateTime).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
                        : "—"}
                    </span>
                  </div>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Channel</span>
                    <span className={styles.overviewValue}>{agent.channels.join(", ") || "—"}</span>
                  </div>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Last updated</span>
                    <span className={styles.overviewValue}>
                      {agent.lastModifiedDateTime
                        ? new Date(agent.lastModifiedDateTime).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
                        : "—"}
                    </span>
                  </div>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Publisher</span>
                    <span className={styles.overviewValue}>{agent.publisherName || "—"}</span>
                  </div>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Publisher type</span>
                    <span className={styles.overviewValue}>{agent.publisherType}</span>
                  </div>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Owner</span>
                    <span className={styles.overviewValue}>{agent.owner?.displayName || "—"}</span>
                  </div>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Available to</span>
                    <span className={styles.overviewValue}>{formatDeployStatus(agent.availableTo)}</span>
                  </div>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Installed for</span>
                    <span className={styles.overviewValue}>{formatDeployStatus(agent.deployedTo)}</span>
                  </div>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Entra agent ID</span>
                    <span className={styles.overviewValue} style={{ fontSize: "12px", wordBreak: "break-all" }}>{agent.appId || "—"}</span>
                  </div>
                  <div className={styles.overviewCell}>
                    <span className={styles.overviewLabel}>Sensitivity</span>
                    <span className={styles.overviewValue}>{agent.sensitivity || "None"}</span>
                  </div>
                </div>
              </div>

              {/* Card: Instructions */}
              <div className={styles.card}>
                <div className={mergeClasses(styles.cardHeader, styles.cardHeaderClickable)} onClick={() => setInstructionsExpanded(!instructionsExpanded)}>
                  <Text size={400} weight="semibold">Instructions</Text>
                  {instructionsExpanded ? <ChevronUpRegular /> : <ChevronDownRegular />}
                </div>
                {instructionsExpanded && (
                  <>
                    {detailLoading ? (
                      <Skeleton>
                        <SkeletonItem style={{ height: "16px", marginBottom: "8px" }} />
                        <SkeletonItem style={{ height: "16px", marginBottom: "8px", width: "80%" }} />
                        <SkeletonItem style={{ height: "16px", width: "60%" }} />
                      </Skeleton>
                    ) : agentDetail?.instructions ? (
                      <div className={styles.instructionsBox}>
                        {agentDetail.instructions}
                      </div>
                    ) : (
                      <Text size={200} style={{ color: tokens.colorNeutralForeground3, fontStyle: "italic" }}>
                        No instructions available.
                      </Text>
                    )}
                    {agentDetail?.conversationStarters && agentDetail.conversationStarters.length > 0 && (
                      <div style={{ marginTop: "16px" }}>
                        <Text size={300} weight="semibold" style={{ display: "block", marginBottom: "8px" }}>
                          Conversation starters
                        </Text>
                        {agentDetail.conversationStarters.map((cs, i) => (
                          <div key={i} style={{ padding: "8px 12px", borderRadius: "6px", backgroundColor: tokens.colorNeutralBackground2, marginBottom: "6px" }}>
                            <Text size={200} weight="semibold" style={{ display: "block" }}>{cs.title}</Text>
                            <Text size={200} style={{ color: tokens.colorNeutralForeground2 }}>{cs.text}</Text>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            </>
          )}

          {activeTab === "users" && (
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <Text size={400} weight="semibold">Users & Access</Text>
              </div>
              <div className={styles.overviewGrid}>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Active Users</span>
                  <span className={styles.overviewValue}>{agent.activeUsers.toLocaleString()}</span>
                </div>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Available to</span>
                  <span className={styles.overviewValue}>{formatDeployStatus(agent.availableTo)}</span>
                </div>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Deployed to</span>
                  <span className={styles.overviewValue}>{formatDeployStatus(agent.deployedTo)}</span>
                </div>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Owner</span>
                  <span className={styles.overviewValue}>{agent.owner?.displayName || "—"}</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === "data & tools" && (
            <>
              {/* Card: Knowledge Sources */}
              <div className={styles.card}>
                <div className={styles.cardHeader}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <GlobeRegular style={{ color: tokens.colorBrandForeground1 }} />
                    <Text size={400} weight="semibold">Knowledge Sources</Text>
                  </div>
                </div>
                {detailLoading ? (
                  <Skeleton>
                    <SkeletonItem style={{ height: "32px", marginBottom: "8px", borderRadius: "16px", width: "120px" }} />
                    <SkeletonItem style={{ height: "32px", borderRadius: "16px", width: "140px" }} />
                  </Skeleton>
                ) : agentDetail?.capabilities && agentDetail.capabilities.length > 0 ? (
                  <>
                    <div style={{ display: "flex", flexWrap: "wrap" }}>
                      {agentDetail.capabilities.map((cap, i) => (
                        <div key={i} className={styles.capabilityChip}>
                          <span>{formatCapabilityName(cap.name)}</span>
                        </div>
                      ))}
                    </div>
                    {agentDetail.capabilities.filter(c => c.config && Object.keys(c.config).length > 0).map((cap, i) => (
                      <div key={i} style={{ marginTop: "12px", padding: "12px 16px", borderRadius: "8px", border: `1px solid ${tokens.colorNeutralStroke2}` }}>
                        <Text size={200} weight="semibold" style={{ display: "block", marginBottom: "4px" }}>{formatCapabilityName(cap.name)}</Text>
                        <Text size={200} style={{ color: tokens.colorNeutralForeground3, wordBreak: "break-all" }}>
                          {JSON.stringify(cap.config, null, 2)}
                        </Text>
                      </div>
                    ))}
                  </>
                ) : (
                  <Text size={200} style={{ color: tokens.colorNeutralForeground3, fontStyle: "italic" }}>
                    No knowledge sources configured.
                  </Text>
                )}
              </div>

              {/* Card: Actions & Plugins */}
              <div className={styles.card}>
                <div className={styles.cardHeader}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <PlugConnectedRegular style={{ color: tokens.colorBrandForeground1 }} />
                    <Text size={400} weight="semibold">Actions & Plugins</Text>
                  </div>
                </div>
                {detailLoading ? (
                  <Skeleton>
                    <SkeletonItem style={{ height: "48px", marginBottom: "8px" }} />
                    <SkeletonItem style={{ height: "48px" }} />
                  </Skeleton>
                ) : agentDetail?.actions && agentDetail.actions.length > 0 ? (
                  agentDetail.actions.map((action, i) => (
                    <div key={i} className={styles.actionCard}>
                      <PlugConnectedRegular style={{ color: tokens.colorNeutralForeground3, fontSize: "20px" }} />
                      <div>
                        <Text size={300} weight="semibold" style={{ display: "block" }}>{action.id}</Text>
                        {action.file && (
                          <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>{action.file}</Text>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <Text size={200} style={{ color: tokens.colorNeutralForeground3, fontStyle: "italic" }}>
                    No actions or plugins configured.
                  </Text>
                )}
              </div>
            </>
          )}

          {activeTab === "security" && (
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <Text size={400} weight="semibold">Security & Risk</Text>
              </div>
              {agent.riskLevel !== "none" ? (
                <MessageBar intent="error" icon={<WarningRegular />}>
                  <MessageBarBody>
                    <MessageBarTitle>Risk Level: {agent.riskLevel.toUpperCase()}</MessageBarTitle>
                    This agent has active risk signals from Microsoft Entra Identity Protection.
                    Consider blocking if the risk is not remediated.
                  </MessageBarBody>
                </MessageBar>
              ) : (
                <MessageBar intent="success" icon={<ShieldCheckmarkRegular />}>
                  <MessageBarBody>
                    <MessageBarTitle>No Risk Signals</MessageBarTitle>
                    This agent has no active risk signals from identity protection.
                  </MessageBarBody>
                </MessageBar>
              )}
            </div>
          )}

          {activeTab === "permissions" && (
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <Text size={400} weight="semibold">Permissions</Text>
              </div>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3, fontStyle: "italic" }}>
                Permissions information is not yet available through the Graph API.
              </Text>
            </div>
          )}

          {activeTab === "activity" && (
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <Text size={400} weight="semibold">Activity & Metadata</Text>
              </div>
              <div className={styles.overviewGrid}>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Last Modified</span>
                  <span className={styles.overviewValue}>
                    {new Date(agent.lastModifiedDateTime).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}
                  </span>
                </div>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Version</span>
                  <span className={styles.overviewValue}>{agent.version || "—"}</span>
                </div>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Element Types</span>
                  <span className={styles.overviewValue}>{agent.elementTypes.join(", ") || "—"}</span>
                </div>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Categories</span>
                  <span className={styles.overviewValue}>{agent.categories?.join(", ") || "—"}</span>
                </div>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Package ID</span>
                  <span className={styles.overviewValue} style={{ fontSize: "11px", wordBreak: "break-all" }}>{agent.id}</span>
                </div>
                <div className={styles.overviewCell}>
                  <span className={styles.overviewLabel}>Manifest ID</span>
                  <span className={styles.overviewValue} style={{ fontSize: "11px", wordBreak: "break-all" }}>{agent.manifestId || "—"}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
