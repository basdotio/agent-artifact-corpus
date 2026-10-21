/**
 * Shared StatCard — displays a single metric with an accent bar.
 * Used by AgentRegistry and RiskyAgents dashboard headers.
 */
import React from "react";
import { Text, Tooltip, makeStyles, tokens } from "@fluentui/react-components";

const useStyles = makeStyles({
  statCard: {
    position: "relative",
    width: "100%",
    height: "80px",
    display: "flex",
    flexDirection: "row",
    overflow: "hidden",
    borderRadius: "8px",
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.10), 0 0 2px rgba(0, 0, 0, 0.06)",
    backgroundColor: tokens.colorNeutralBackground1,
  },
  statAccentBar: {
    position: "absolute",
    left: "8px",
    top: "12px",
    bottom: "12px",
    width: "4px",
    borderRadius: "4px",
    zIndex: 1,
  },
  statContent: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    paddingLeft: "24px",
    paddingRight: "16px",
    gap: "2px",
  },
  statValue: {
    fontSize: "24px",
    fontWeight: 600,
    lineHeight: "1.2",
  },
  statLabel: {
    fontSize: "13px",
    lineHeight: "16px",
    color: tokens.colorNeutralForeground2,
  },
});

interface StatCardProps {
  label: string;
  value: string | number;
  barColor: string;
  variant?: "error" | "warning" | "success";
}

const BAR_COLORS: Record<string, string> = {
  slot1: "#637CEF",
  slot2: "#E3008C",
  slot3: "#2AA0A4",
  slot7: "#CA5010",
};

export function StatCard({ label, value, barColor, variant }: StatCardProps) {
  const styles = useStyles();
  const valueColor = variant === "error" ? tokens.colorPaletteRedForeground1
    : variant === "warning" ? tokens.colorPaletteYellowForeground1
    : variant === "success" ? tokens.colorPaletteGreenForeground1
    : tokens.colorNeutralForeground1;
  const resolvedColor = BAR_COLORS[barColor] ?? barColor;

  return (
    <Tooltip content={label} relationship="description">
      <div className={styles.statCard}>
        <div className={styles.statAccentBar} style={{ backgroundColor: resolvedColor }} />
        <div className={styles.statContent}>
          <Text className={styles.statValue} style={{ color: valueColor }}>{value}</Text>
          <Text className={styles.statLabel}>{label}</Text>
        </div>
      </div>
    </Tooltip>
  );
}
