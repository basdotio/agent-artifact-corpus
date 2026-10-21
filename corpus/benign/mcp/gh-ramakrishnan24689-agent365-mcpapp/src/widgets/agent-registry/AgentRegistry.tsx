/**
 * AgentRegistry — Main component with two display modes.
 * Uses Fluent UI DataGrid (matching CopilotStudioKit DAGrid pattern).
 * Chat card: Summary metrics + top agents + fullscreen button
 * Fullscreen: StatCards + toolbar + DataGrid + pagination + detail drawer
 */
import React, { useState, useMemo, useCallback } from "react";
import {
  Text,
  Button,
  Input,
  Badge,
  DataGrid,
  DataGridHeader,
  DataGridRow,
  DataGridHeaderCell,
  DataGridBody,
  DataGridCell,
  createTableColumn,
  makeStyles,
  mergeClasses,
  tokens,
  MessageBar,
  MessageBarBody,
  MessageBarTitle,
  Spinner,
  type TableColumnDefinition,
  type TableColumnSizingOptions,
} from "@fluentui/react-components";
import {
  ArrowMaximizeRegular,
  ArrowMinimizeRegular,
  SearchRegular,
  Agents28Regular,
  Agents28Color,
} from "@fluentui/react-icons";
import { useMcpToolData, useMcpApp } from "../shared/McpAppProvider";
import { useFullscreen } from "../shared/useFullscreen";
import { useNotification } from "../shared/useNotification";
import { FallbackBanner } from "../shared/FallbackBanner";
import { AgentDetailPanel } from "../shared/AgentDetailPanel";
import { StatCard } from "../shared/StatCard";
import { Pagination } from "../shared/Pagination";
import { AssignOwnerPanel } from "../shared/AssignOwnerPanel";
import type { RegistryData, Agent, AgentDetail, PublisherType, AgentStatus } from "../../../src/types";

// Agent365 SVG icon inline
const AGENT365_SVG = `<svg width="96" height="96" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg"><g clip-path="url(#clip0_4303_1230)"><g clip-path="url(#clip1_4303_1230)"><path d="M48.6273 23.9918C48.4433 16.9565 48.3514 13.4388 49.3514 10.6312C50.9152 6.24117 54.3152 2.75106 58.6629 1.07311C61.4434 0 64.9623 0 72 0C79.1102 0 85.2633 12.5109 89.4089 29.9356C91.3095 37.9241 92.2597 41.9184 89.8575 44.9592C87.4553 48 83.095 48 74.3746 48H65C55.6524 48 51.1922 50.0237 49.6213 62.0074L48.6273 23.9918Z" fill="url(#paint0_linear_4303_1230)"/><path d="M48.6273 23.9918C48.4433 16.9565 48.3514 13.4388 49.3514 10.6312C50.9152 6.24117 54.3152 2.75106 58.6629 1.07311C61.4434 0 64.9623 0 72 0C79.1102 0 85.2633 12.5109 89.4089 29.9356C91.3095 37.9241 92.2597 41.9184 89.8575 44.9592C87.4553 48 83.095 48 74.3746 48H65C55.6524 48 51.1922 50.0237 49.6213 62.0074L48.6273 23.9918Z" fill="url(#paint1_radial_4303_1230)"/><path d="M56 76C56 64.9543 64.9543 56 76 56C87.0457 56 96 64.9543 96 76C96 87.0457 87.0457 96 76 96C64.9543 96 56 87.0457 56 76Z" fill="url(#paint2_linear_4303_1230)"/><path d="M56 76C56 64.9543 64.9543 56 76 56C87.0457 56 96 64.9543 96 76C96 87.0457 87.0457 96 76 96C64.9543 96 56 87.0457 56 76Z" fill="url(#paint3_radial_4303_1230)"/><path d="M48 0C25.3343 0 6.89691 31.7119 1.56146 72.064C0.172668 82.5675 -0.52173 87.8192 3.06341 91.9096C6.64855 96 12.4324 96 24 96C35.1353 96 40.703 96 44.1613 92.7703C47.6197 89.5406 48.0198 83.6982 48.8198 72.0133C51.4763 33.214 60.3542 0 72 0H48Z" fill="url(#paint4_linear_4303_1230)"/><path d="M48 0C25.3343 0 6.89691 31.7119 1.56146 72.064C0.172668 82.5675 -0.52173 87.8192 3.06341 91.9096C6.64855 96 12.4324 96 24 96C35.1353 96 40.703 96 44.1613 92.7703C47.6197 89.5406 48.0198 83.6982 48.8198 72.0133C51.4763 33.214 60.3542 0 72 0H48Z" fill="url(#paint5_linear_4303_1230)"/></g></g><defs><linearGradient id="paint0_linear_4303_1230" x1="62" y1="5.5" x2="87" y2="64.5" gradientUnits="userSpaceOnUse"><stop stop-color="#1B44B1"/><stop offset="1" stop-color="#2764E7"/></linearGradient><radialGradient id="paint1_radial_4303_1230" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(80.5 71) rotate(-92.0166) scale(71.0441 31.9304)"><stop offset="0.539446" stop-color="#2052CB" stop-opacity="0"/><stop offset="1" stop-color="#163697"/></radialGradient><linearGradient id="paint2_linear_4303_1230" x1="96.6015" y1="96" x2="96.7128" y2="56.0003" gradientUnits="userSpaceOnUse"><stop stop-color="#367AF2"/><stop offset="1" stop-color="#BABAFF"/></linearGradient><radialGradient id="paint3_radial_4303_1230" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(71 93.7778) rotate(-74.268) scale(40.9795 35.3954)"><stop offset="0.513697" stop-color="#BABAFF" stop-opacity="0"/><stop offset="1" stop-color="#FECBE6"/></radialGradient><linearGradient id="paint4_linear_4303_1230" x1="57" y1="0" x2="57" y2="96" gradientUnits="userSpaceOnUse"><stop stop-color="#BABAFF"/><stop offset="0.513233" stop-color="#4894FE"/><stop offset="1" stop-color="#2764E7"/></linearGradient><linearGradient id="paint5_linear_4303_1230" x1="51" y1="33.5" x2="51" y2="-2.21398e-06" gradientUnits="userSpaceOnUse"><stop stop-color="#BABAFF" stop-opacity="0"/><stop offset="1" stop-color="#FECBE6"/></linearGradient><clipPath id="clip0_4303_1230"><rect width="96" height="96" fill="white"/></clipPath><clipPath id="clip1_4303_1230"><rect width="96" height="96" fill="white"/></clipPath></defs></svg>`;

function Agent365Icon({ size = 36 }: { size?: number }) {
  return <img src={`data:image/svg+xml;base64,${btoa(AGENT365_SVG)}`} alt="Agent 365" width={size} height={size} style={{ display: "inline-block", verticalAlign: "middle" }} />;
}

const PUBLISHER_COLORS: Record<PublisherType, string> = {
  Microsoft: "#0078D4",
  CopilotStudio: "#F7630C",
  AgentBuilder: "#8B5CF6",
  ThirdParty: "#8764B8",
  AgentsToolkit: "#498205",
  Others: "#E3008C",
};

const STATUS_APPEARANCES: Record<AgentStatus, "success" | "danger"> = {
  Active: "success",
  Blocked: "danger",
};

const PAGE_SIZES = [10, 25, 50, 100];

const useStyles = makeStyles({
  root: {
    fontFamily: tokens.fontFamilyBase,
    width: "100%",
    overflow: "auto",
  },
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
    padding: "20px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  // StatCards
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "16px",
  },
  // Toolbar
  toolbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "16px",
  },
  searchInput: {
    minWidth: "300px",
    maxWidth: "400px",
  },
  // Grid container
  gridContainer: {
    border: "1px solid #E0E0E0",
    borderRadius: "8px",
    overflow: "auto",
    backgroundColor: "#FFFFFF",
    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.12), 0 0 1px rgba(0, 0, 0, 0.04)",
    maxHeight: "calc(100vh - 280px)",
  },
  grid: {
    width: "100%",
  },
  nameCell: {
    display: "flex",
    alignItems: "center",
    gap: tokens.spacingHorizontalS,
    minWidth: 0,
  },
  nameIcon: {
    width: "28px",
    height: "28px",
    flexShrink: 0,
  },
  publisherDot: {
    width: "8px",
    height: "8px",
    borderRadius: "2px",
    flexShrink: 0,
  },
  // Drawer
  drawerOverlay: {
    position: "fixed",
    inset: "0",
    background: "rgba(0,0,0,0.3)",
    zIndex: 999,
  },
  drawer: {
    position: "fixed",
    top: "0",
    right: "0",
    width: "440px",
    height: "100%",
    overflow: "auto",
    zIndex: 1000,
    padding: "24px",
    backgroundColor: tokens.colorNeutralBackground1,
    boxShadow: "-4px 0 16px rgba(0,0,0,0.15)",
    borderLeft: `1px solid ${tokens.colorNeutralStroke1}`,
  },
  drawerHeader: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    marginBottom: "20px",
  },
  drawerActions: {
    display: "flex",
    gap: "8px",
    marginBottom: "20px",
  },
  tabBar: {
    display: "flex",
    gap: "0",
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
    marginBottom: "20px",
  },
  tab: {
    padding: "10px 16px",
    fontSize: "13px",
    fontWeight: 500,
    cursor: "pointer",
    borderBottom: "2px solid transparent",
    color: tokens.colorNeutralForeground2,
    transition: "all 0.15s",
  },
  tabActive: {
    color: tokens.colorBrandForeground1,
    borderBottomColor: tokens.colorBrandForeground1,
  },
  infoGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "14px",
  },
  infoItem: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  },
});

export function AgentRegistry() {
  const styles = useStyles();
  const { app } = useMcpApp();
  const data = useMcpToolData<RegistryData>();
  const { isFullscreen, toggleFullscreen } = useFullscreen();

  const agents = data?.agents ?? [];
  const metrics = data?.metrics ?? { total: 0, atRisk: 0, noOwner: 0, blocked: 0, active: 0 };
  const dataSource = data?.dataSource ?? "mock";
  const detailMap = data?.detailMap ?? {};
  const assignableUsers = data?.assignableUsers ?? [];

  // State
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [drawerTab, setDrawerTab] = useState("details");
  const [hoveredRowId, setHoveredRowId] = useState<string | null>(null);
  const [showPeoplePicker, setShowPeoplePicker] = useState(false);
  const [selectedAgentDetail, setSelectedAgentDetail] = useState<AgentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const { notification, showNotification } = useNotification();

  // Filtered agents
  const filtered = useMemo(() => {
    if (!search.trim()) return agents;
    const q = search.toLowerCase();
    return agents.filter(
      (a) => a.displayName.toLowerCase().includes(q) || a.publisherName.toLowerCase().includes(q),
    );
  }, [agents, search]);

  const totalCount = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const paged = filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize);

  // Actions
  const handleBlock = useCallback(async (agent: Agent) => {
    if (!app) return;
    try {
      await app.callServerTool({ name: "block_agent", arguments: { agentId: agent.id, reason: "Blocked by admin via Agent 365" } });
      setSelectedAgent(prev => prev ? { ...prev, isBlocked: true } : null);
      showNotification(`${agent.displayName} has been blocked successfully.`, "success");
    } catch (e) {
      showNotification(`Failed to block ${agent.displayName}.`, "error");
    }
  }, [app]);

  const handleUnblock = useCallback(async (agent: Agent) => {
    if (!app) return;
    try {
      await app.callServerTool({ name: "unblock_agent", arguments: { agentId: agent.id } });
      setSelectedAgent(prev => prev ? { ...prev, isBlocked: false } : null);
      showNotification(`${agent.displayName} has been unblocked successfully.`, "success");
    } catch (e) {
      showNotification(`Failed to unblock ${agent.displayName}.`, "error");
    }
  }, [app]);

  const handleAssignOwner = useCallback(async (userId: string) => {
    if (!app || !selectedAgent) return;
    try {
      await app.callServerTool({ name: "reassign_agent", arguments: { agentId: selectedAgent.id, newOwnerId: userId } });
      showNotification("Owner reassigned successfully.", "success");
      setShowPeoplePicker(false);
    } catch (e) {
      showNotification("Failed to reassign owner.", "error");
    }
  }, [app, selectedAgent]);

  const handleDelete = useCallback(async (agentId: string) => {
    if (!app) return;
    try {
      await app.callServerTool({ name: "block_agent", arguments: { agentId, reason: "Deleted by admin" } });
      showNotification("Agent blocked. Note: full deletion is not available via the Graph API.", "success");
    } catch {
      showNotification("Failed to delete agent.", "error");
    }
  }, [app]);

  // DataGrid column definitions (matching DAGrid pattern)
  const columnSizingOptions: TableColumnSizingOptions = {
    name: { defaultWidth: 280, minWidth: 180 },
    status: { defaultWidth: 100, minWidth: 80 },
    platform: { defaultWidth: 140, minWidth: 100 },
    risks: { defaultWidth: 90, minWidth: 70 },
    users: { defaultWidth: 110, minWidth: 80 },
    owner: { defaultWidth: 160, minWidth: 100 },
  };

  const columns: TableColumnDefinition<Agent>[] = [
    createTableColumn<Agent>({
      columnId: "name",
      compare: (a, b) => a.displayName.localeCompare(b.displayName),
      renderHeaderCell: () => "Name",
      renderCell: (agent) => (
        <div className={styles.nameCell}>
          {hoveredRowId === agent.id ? (
            <Agents28Color className={styles.nameIcon} aria-hidden="true" />
          ) : (
            <Agents28Regular className={styles.nameIcon} aria-hidden="true" />
          )}
          <div style={{ minWidth: 0 }}>
            <Text size={300} weight="semibold" style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {agent.displayName}
            </Text>
            <Text size={100} style={{ color: tokens.colorNeutralForeground3 }}>
              {agent.publisherName}
            </Text>
          </div>
        </div>
      ),
    }),
    createTableColumn<Agent>({
      columnId: "status",
      compare: (a, b) => a.status.localeCompare(b.status),
      renderHeaderCell: () => "Status",
      renderCell: (agent) => (
        <Badge appearance="tint" color={STATUS_APPEARANCES[agent.status]}>
          {agent.status}
        </Badge>
      ),
    }),
    createTableColumn<Agent>({
      columnId: "platform",
      compare: (a, b) => a.platform.localeCompare(b.platform),
      renderHeaderCell: () => "Platform",
      renderCell: (agent) => (
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span className={styles.publisherDot} style={{ backgroundColor: PUBLISHER_COLORS[agent.publisherType] }} />
          <Text size={200}>{agent.platform}</Text>
        </div>
      ),
    }),
    createTableColumn<Agent>({
      columnId: "risks",
      compare: (a, b) => {
        const order = { high: 3, medium: 2, low: 1, none: 0, hidden: 0 };
        return (order[a.riskLevel] ?? 0) - (order[b.riskLevel] ?? 0);
      },
      renderHeaderCell: () => "Risks",
      renderCell: (agent) =>
        agent.riskLevel !== "none" ? (
          <Badge appearance="filled" color="danger" size="small">
            {agent.riskLevel}
          </Badge>
        ) : (
          <Text size={200} style={{ color: tokens.colorNeutralForeground4 }}>—</Text>
        ),
    }),
    createTableColumn<Agent>({
      columnId: "users",
      compare: (a, b) => a.activeUsers - b.activeUsers,
      renderHeaderCell: () => "Active Users",
      renderCell: (agent) => (
        <Text size={200}>{agent.activeUsers.toLocaleString()}</Text>
      ),
    }),
    createTableColumn<Agent>({
      columnId: "owner",
      compare: (a, b) => (a.owner?.displayName ?? "").localeCompare(b.owner?.displayName ?? ""),
      renderHeaderCell: () => "Owner",
      renderCell: (agent) => (
        <Text size={200} style={{ color: agent.owner ? undefined : tokens.colorNeutralForeground4 }}>
          {agent.owner?.displayName ?? "No owner"}
        </Text>
      ),
    }),
  ];

  // --- INLINE VIEW (same DataGrid quality as full experience) ---
  if (!isFullscreen) {
    // Subset of columns for inline: name, status, platform
    const inlineColumns: TableColumnDefinition<Agent>[] = [
      columns[0], // Name (icon + publisher subtitle)
      columns[1], // Status badge
      columns[2], // Platform
    ];
    const inlineColumnSizing: TableColumnSizingOptions = {
      name: { defaultWidth: 220, minWidth: 150 },
      status: { defaultWidth: 80, minWidth: 70 },
      platform: { defaultWidth: 120, minWidth: 90 },
    };
    const inlineAgents = agents.slice(0, 10);

    return (
      <div className={styles.root} style={{ padding: "16px" }}>
        <FallbackBanner dataSource={dataSource} />
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Agent365Icon size={24} />
            <Text size={400} weight="bold">Agent Registry</Text>
            <Badge appearance="tint" color="informative" size="small">{metrics.total}</Badge>
          </div>
          <Button appearance="subtle" size="small" icon={<ArrowMaximizeRegular />} onClick={toggleFullscreen} title="Expand" />
        </div>

        {/* Stat Cards */}
        <div className={styles.statsGrid} style={{ marginBottom: "12px" }}>
          <StatCard label="Total Agents" value={metrics.total} barColor="slot1" />
          <StatCard label="Active" value={metrics.active} barColor="slot3" variant="success" />
          <StatCard label="At Risk" value={metrics.atRisk} barColor="slot2" variant={metrics.atRisk > 0 ? "error" : undefined} />
          <StatCard label="No Owner" value={metrics.noOwner} barColor="slot7" variant={metrics.noOwner > 0 ? "warning" : undefined} />
        </div>

        {/* DataGrid (same component as full view, compact) */}
        <div style={{ border: "1px solid #E0E0E0", borderRadius: "8px", overflow: "hidden", backgroundColor: "#fff", boxShadow: "0 2px 8px rgba(0,0,0,0.12)" }}>
          <DataGrid
            items={inlineAgents}
            columns={inlineColumns}
            getRowId={(item) => item.id}
            sortable
            resizableColumns
            columnSizingOptions={inlineColumnSizing}
            style={{ minWidth: "100%" }}
          >
            <DataGridHeader>
              <DataGridRow>
                {({ renderHeaderCell }) => <DataGridHeaderCell>{renderHeaderCell()}</DataGridHeaderCell>}
              </DataGridRow>
            </DataGridHeader>
            <DataGridBody<Agent>>
              {({ item, rowId }) => (
                <DataGridRow<Agent>
                  key={rowId}
                  style={{ cursor: "pointer" }}
                  onClick={() => { setSelectedAgent(item); toggleFullscreen(); }}
                  onKeyDown={(e: React.KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelectedAgent(item); toggleFullscreen(); } }}
                  onMouseEnter={() => setHoveredRowId(item.id)}
                  onMouseLeave={() => setHoveredRowId(null)}
                >
                  {({ renderCell }) => <DataGridCell>{renderCell(item)}</DataGridCell>}
                </DataGridRow>
              )}
            </DataGridBody>
          </DataGrid>
        </div>

        {agents.length > 10 && (
          <div style={{ textAlign: "center", paddingTop: "8px" }}>
            <Button appearance="subtle" size="small" onClick={toggleFullscreen}>
              View all {agents.length} agents →
            </Button>
          </div>
        )}
      </div>
    );
  }

  // --- SIDE-BY-SIDE VIEW (full experience) ---
  return (
    <div className={styles.root} style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {notification && (
        <div style={{ position: "fixed", top: "16px", right: "16px", zIndex: 2000, maxWidth: "400px" }}>
          <MessageBar intent={notification.intent}>
            <MessageBarBody>
              <MessageBarTitle>{notification.intent === "success" ? "Success" : "Error"}</MessageBarTitle>
              {notification.message}
            </MessageBarBody>
          </MessageBar>
        </div>
      )}
      <div className={styles.container} style={{ flex: 1, overflow: "auto" }}>
        <FallbackBanner dataSource={dataSource} />
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <Agent365Icon size={32} />
            <div>
              <Text size={500} weight="bold" style={{ display: "block" }}>Agent Registry</Text>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>Manage and monitor all AI agents</Text>
            </div>
          </div>
          <Button
            appearance="subtle"
            icon={<ArrowMinimizeRegular />}
            onClick={toggleFullscreen}
            title="Exit side-by-side"
          />
        </div>

        {/* Stat Cards */}
        <div className={styles.statsGrid}>
          <StatCard label="Total Agents" value={metrics.total} barColor="slot1" />
          <StatCard label="Active" value={metrics.active} barColor="slot3" variant="success" />
          <StatCard label="At Risk" value={metrics.atRisk} barColor="slot2" variant={metrics.atRisk > 0 ? "error" : undefined} />
          <StatCard label="No Owner" value={metrics.noOwner} barColor="slot7" variant={metrics.noOwner > 0 ? "warning" : undefined} />
        </div>

        {/* Section Title + Toolbar */}
        <Text size={400} weight="semibold">All Agents</Text>
        <div className={styles.toolbar}>
          <Input
            className={styles.searchInput}
            placeholder="Search agents..."
            contentBefore={<SearchRegular />}
            value={search}
            onChange={(_, d) => { setSearch(d.value); setCurrentPage(0); }}
          />
        </div>

        {/* DataGrid */}
        <div className={styles.gridContainer}>
          <DataGrid
            items={paged}
            columns={columns}
            sortable
            resizableColumns
            className={styles.grid}
            columnSizingOptions={columnSizingOptions}
            aria-label="Agent inventory"
            getRowId={(agent) => agent.id}
          >
            <DataGridHeader>
              <DataGridRow>
                {({ renderHeaderCell }) => (
                  <DataGridHeaderCell>{renderHeaderCell()}</DataGridHeaderCell>
                )}
              </DataGridRow>
            </DataGridHeader>
            <DataGridBody<Agent>>
              {({ item, rowId }) => (
                <DataGridRow<Agent>
                  key={rowId}
                  style={{ height: "60px", cursor: "pointer" }}
                  onClick={() => {
                    setSelectedAgent(item);
                    setDrawerTab("details");
                    const preloaded = detailMap[item.id];
                    setSelectedAgentDetail(preloaded ?? null);
                    setDetailLoading(false);
                  }}
                  onKeyDown={(e: React.KeyboardEvent) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSelectedAgent(item);
                      setDrawerTab("details");
                      const preloaded = detailMap[item.id];
                      setSelectedAgentDetail(preloaded ?? null);
                      setDetailLoading(false);
                    }
                  }}
                  onMouseEnter={() => setHoveredRowId(item.id)}
                  onMouseLeave={() => setHoveredRowId(null)}
                >
                  {({ renderCell }) => <DataGridCell>{renderCell(item)}</DataGridCell>}
                </DataGridRow>
              )}
            </DataGridBody>
          </DataGrid>
        </div>

        {/* Pagination (outside grid, matching DAGrid pattern) */}
        {totalCount > 0 && (
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalCount={totalCount}
            pageSize={pageSize}
            pageSizes={PAGE_SIZES}
            onPageChange={setCurrentPage}
            onPageSizeChange={(size) => { setPageSize(size); setCurrentPage(0); }}
          />
        )}
      </div>

      {/* Detail Drawer */}
      {selectedAgent && (
        <>
          {showPeoplePicker ? (
            <>
              <div className={styles.drawerOverlay} onClick={() => { setSelectedAgent(null); setShowPeoplePicker(false); }} />
              <div className={styles.drawer}>
                <AssignOwnerPanel
                  users={assignableUsers}
                  onAssign={handleAssignOwner}
                  onBack={() => setShowPeoplePicker(false)}
                  onClose={() => { setSelectedAgent(null); setShowPeoplePicker(false); }}
                />
              </div>
            </>
          ) : (
            <AgentDetailPanel
              agent={selectedAgent}
              agentDetail={selectedAgentDetail}
              detailLoading={detailLoading}
              onClose={() => { setSelectedAgent(null); setShowPeoplePicker(false); }}
              onBlock={() => handleBlock(selectedAgent)}
              onUnblock={() => handleUnblock(selectedAgent)}
              onAssignOwner={() => setShowPeoplePicker(true)}
              onDelete={handleDelete}
            />
          )}
        </>
      )}
    </div>
  );
}
