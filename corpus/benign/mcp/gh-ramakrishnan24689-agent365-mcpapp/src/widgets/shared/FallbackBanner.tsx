/**
 * FallbackBanner — Subtle info bar shown when using mock data.
 */
import React from "react";
import { Text, tokens } from "@fluentui/react-components";
import type { DataSource } from "../../../src/types";

interface FallbackBannerProps {
  dataSource: DataSource;
}

export function FallbackBanner({ dataSource }: FallbackBannerProps) {
  if (dataSource === "live") return null;

  return (
    <div style={{
      padding: "6px 12px",
      borderRadius: "4px",
      backgroundColor: tokens.colorNeutralBackground3,
      border: `1px solid ${tokens.colorNeutralStroke2}`,
      display: "flex",
      alignItems: "center",
      gap: "6px",
      marginBottom: "8px",
    }}>
      <Text size={100} style={{ color: tokens.colorNeutralForeground3 }}>
        ℹ️ Preview mode — showing sample data
      </Text>
    </div>
  );
}
