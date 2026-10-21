/**
 * RiskyAgents — Risk monitoring widget with gold-standard Fluent DataGrid.
 */
import React, { useState, useMemo, useCallback } from "react";
import {
  Text,
  Button,
  Badge,
  DataGrid,
  DataGridHeader,
  DataGridRow,
  DataGridHeaderCell,
  DataGridBody,
  DataGridCell,
  createTableColumn,
  makeStyles,
  tokens,
  type TableColumnDefinition,
  type TableColumnSizingOptions,
} from "@fluentui/react-components";
import {
  ArrowMaximizeRegular,
  ArrowMinimizeRegular,
  ProhibitedRegular,
  WarningRegular,
  ShieldErrorRegular,
  Agents28Regular,
  Agents28Color,
} from "@fluentui/react-icons";
import { useMcpToolData, useMcpApp } from "../shared/McpAppProvider";
import { useFullscreen } from "../shared/useFullscreen";
import { FallbackBanner } from "../shared/FallbackBanner";
import { StatCard } from "../shared/StatCard";
import { Pagination } from "../shared/Pagination";
import type { RiskyAgentsData, RiskyAgent } from "../../../src/types";

const STATE_LABELS: Record<string, string> = {
  atRisk: "At Risk",
  confirmedCompromised: "Compromised",
  remediated: "Remediated",
  dismissed: "Dismissed",
};

const RISK_BADGE_COLORS: Record<string, "danger" | "warning" | "success"> = {
  high: "danger",
  medium: "warning",
  low: "success",
};

const BAR_COLORS: Record<string, string> = {
  high: "#D13438",
  medium: "#CA5010",
  low: "#2AA0A4",
  total: "#637CEF",
};

const PAGE_SIZES = [10, 25, 50];

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
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "16px",
  },
  gridContainer: {
    border: "1px solid #E0E0E0",
    borderRadius: "8px",
    overflow: "hidden",
    backgroundColor: "#FFFFFF",
    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.12), 0 0 1px rgba(0, 0, 0, 0.04)",
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
});

export function RiskyAgents() {
  const styles = useStyles();
  const { app } = useMcpApp();
  const data = useMcpToolData<RiskyAgentsData>();
  const { isFullscreen, toggleFullscreen } = useFullscreen();

  const riskyAgents = data?.riskyAgents ?? [];
  const metrics = data?.metrics ?? { total: 0, high: 0, medium: 0, low: 0 };
  const dataSource = data?.dataSource ?? "mock";

  const [currentPage, setCurrentPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [hoveredRowId, setHoveredRowId] = useState<string | null>(null);

  const totalCount = riskyAgents.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const paged = riskyAgents.slice(currentPage * pageSize, (currentPage + 1) * pageSize);

  const handleBlock = useCallback(async (agent: RiskyAgent) => {
    if (!app) return;
    await app.callServerTool({ name: "block_agent", arguments: { agentId: agent.agentId, reason: `Blocked due to risk: ${agent.riskDetail}` } });
  }, [app]);

  const columnSizingOptions: TableColumnSizingOptions = {
    name: { defaultWidth: 240, minWidth: 160 },
    severity: { defaultWidth: 100, minWidth: 80 },
    state: { defaultWidth: 140, minWidth: 100 },
    detail: { defaultWidth: 280, minWidth: 160 },
    action: { defaultWidth: 100, minWidth: 80 },
  };

  const columns: TableColumnDefinition<RiskyAgent>[] = [
    createTableColumn<RiskyAgent>({
      columnId: "name",
      compare: (a, b) => a.displayName.localeCompare(b.displayName),
      renderHeaderCell: () => "Agent",
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
              {agent.platform}
            </Text>
          </div>
        </div>
      ),
    }),
    createTableColumn<RiskyAgent>({
      columnId: "severity",
      compare: (a, b) => {
        const order = { high: 3, medium: 2, low: 1 };
        return (order[a.riskLevel] ?? 0) - (order[b.riskLevel] ?? 0);
      },
      renderHeaderCell: () => "Severity",
      renderCell: (agent) => (
        <Badge appearance="tint" color={RISK_BADGE_COLORS[agent.riskLevel]}>
          {agent.riskLevel}
        </Badge>
      ),
    }),
    createTableColumn<RiskyAgent>({
      columnId: "state",
      compare: (a, b) => a.riskState.localeCompare(b.riskState),
      renderHeaderCell: () => "State",
      renderCell: (agent) => (
        <Text size={200}>{STATE_LABELS[agent.riskState] ?? agent.riskState}</Text>
      ),
    }),
    createTableColumn<RiskyAgent>({
      columnId: "detail",
      compare: (a, b) => a.riskDetail.localeCompare(b.riskDetail),
      renderHeaderCell: () => "Risk Detail",
      renderCell: (agent) => (
        <Text size={200} style={{ color: tokens.colorNeutralForeground2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {agent.riskDetail}
        </Text>
      ),
    }),
    createTableColumn<RiskyAgent>({
      columnId: "action",
      renderHeaderCell: () => "Action",
      renderCell: (agent) => (
        <Button size="small" appearance="outline" icon={<ProhibitedRegular />} onClick={(e) => { e.stopPropagation(); handleBlock(agent); }}>
          Block
        </Button>
      ),
    }),
  ];

  // --- INLINE VIEW (lightweight chat card per UX guidelines) ---
  if (!isFullscreen) {
    const topRisky = riskyAgents.slice(0, 5);
    return (
      <div className={styles.root} style={{ padding: "24px" }}>
        <FallbackBanner dataSource={dataSource} />
        <div className={styles.header} style={{ marginBottom: "16px" }}>
          <div className={styles.headerLeft}>
            <ShieldErrorRegular style={{ fontSize: "28px", color: tokens.colorPaletteRedForeground1 }} />
            <div>
              <Text size={500} weight="bold" style={{ display: "block" }}>Risky Agents</Text>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>
                {metrics.total} agents with active risk signals
              </Text>
            </div>
          </div>
          <Button
            appearance="subtle"
            icon={<ArrowMaximizeRegular />}
            onClick={toggleFullscreen}
            title="Open in side-by-side"
          />
        </div>

        {/* Stat Cards (same component as side-by-side) */}
        <div className={styles.statsGrid} style={{ marginBottom: "16px" }}>
          <StatCard label="Total Risky" value={metrics.total} barColor={BAR_COLORS.total} />
          <StatCard label="High" value={metrics.high} barColor={BAR_COLORS.high} variant="error" />
          <StatCard label="Medium" value={metrics.medium} barColor={BAR_COLORS.medium} variant="warning" />
          <StatCard label="Low" value={metrics.low} barColor={BAR_COLORS.low} variant="success" />
        </div>

        {/* Top risky agents in grid-styled container */}
        {topRisky.length > 0 && (
          <div className={styles.gridContainer}>
            <div style={{ padding: "12px 16px", borderBottom: `1px solid #E0E0E0`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Text size={300} weight="semibold" style={{ color: tokens.colorNeutralForeground2 }}>Top Risks</Text>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>{topRisky.length} of {riskyAgents.length}</Text>
            </div>
            {topRisky.map((agent, i) => (
              <div
                key={agent.id}
                style={{
                  display: "flex", alignItems: "center", gap: "10px",
                  padding: "10px 16px",
                  borderBottom: i < topRisky.length - 1 ? `1px solid ${tokens.colorNeutralStroke3}` : undefined,
                }}
                onMouseEnter={() => setHoveredRowId(agent.id)}
                onMouseLeave={() => setHoveredRowId(null)}
              >
                <span style={{ width: "20px", height: "20px", flexShrink: 0, display: "inline-flex" }}>
                  {hoveredRowId === agent.id
                    ? <Agents28Color style={{ width: "20px", height: "20px" }} />
                    : <Agents28Regular style={{ width: "20px", height: "20px", color: tokens.colorNeutralForeground3 }} />}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text size={300} weight="medium" style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {agent.displayName}
                  </Text>
                  <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>
                    {agent.riskDetail}
                  </Text>
                </div>
                <Badge appearance="tint" color={RISK_BADGE_COLORS[agent.riskLevel]} size="small">{agent.riskLevel}</Badge>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // --- SIDE-BY-SIDE VIEW (full experience) ---
  return (
    <div className={styles.root} style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <div className={styles.container} style={{ flex: 1, overflow: "auto" }}>
        <FallbackBanner dataSource={dataSource} />
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <ShieldErrorRegular style={{ fontSize: "32px", color: tokens.colorPaletteRedForeground1 }} />
            <div>
              <Text size={500} weight="bold" style={{ display: "block" }}>Risky Agents</Text>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>Agents with active risk signals</Text>
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
          <StatCard label="Total Risky" value={metrics.total} barColor={BAR_COLORS.total} />
          <StatCard label="High Severity" value={metrics.high} barColor={BAR_COLORS.high} variant="error" />
          <StatCard label="Medium Severity" value={metrics.medium} barColor={BAR_COLORS.medium} variant="warning" />
          <StatCard label="Low Severity" value={metrics.low} barColor={BAR_COLORS.low} variant="success" />
        </div>

        {/* DataGrid */}
        <Text size={400} weight="semibold">All Risky Agents</Text>
        <div className={styles.gridContainer}>
          <DataGrid
            items={paged}
            columns={columns}
            sortable
            resizableColumns
            className={styles.grid}
            columnSizingOptions={columnSizingOptions}
            aria-label="Risky agents"
            getRowId={(agent) => agent.id}
          >
            <DataGridHeader>
              <DataGridRow>
                {({ renderHeaderCell }) => (
                  <DataGridHeaderCell>{renderHeaderCell()}</DataGridHeaderCell>
                )}
              </DataGridRow>
            </DataGridHeader>
            <DataGridBody<RiskyAgent>>
              {({ item, rowId }) => (
                <DataGridRow<RiskyAgent>
                  key={rowId}
                  style={{ height: "60px", cursor: "pointer" }}
                  onMouseEnter={() => setHoveredRowId(item.id)}
                  onMouseLeave={() => setHoveredRowId(null)}
                >
                  {({ renderCell }) => <DataGridCell>{renderCell(item)}</DataGridCell>}
                </DataGridRow>
              )}
            </DataGridBody>
          </DataGrid>
        </div>

        {/* Pagination */}
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
    </div>
  );
}
