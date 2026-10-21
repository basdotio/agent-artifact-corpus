/**
 * Agent Registry Widget — Entry point.
 * Immersive agent inventory with grid, filters, and detail drawer.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import { FluentProvider, webLightTheme, webDarkTheme } from "@fluentui/react-components";
import { McpAppProvider, useMcpTheme } from "../shared/McpAppProvider";
import { AgentRegistry } from "./AgentRegistry";

function App() {
  const theme = useMcpTheme();
  return (
    <FluentProvider theme={theme === "dark" ? webDarkTheme : webLightTheme}>
      <AgentRegistry />
    </FluentProvider>
  );
}

const root = createRoot(document.getElementById("root")!);
root.render(
  <McpAppProvider name="agent365-registry">
    <App />
  </McpAppProvider>
);
