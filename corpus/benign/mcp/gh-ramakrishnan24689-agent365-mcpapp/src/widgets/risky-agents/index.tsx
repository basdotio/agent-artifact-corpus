/**
 * Risky Agents Widget — Entry point.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import { FluentProvider, webLightTheme, webDarkTheme } from "@fluentui/react-components";
import { McpAppProvider, useMcpTheme } from "../shared/McpAppProvider";
import { RiskyAgents } from "./RiskyAgents";

function App() {
  const theme = useMcpTheme();
  return (
    <FluentProvider theme={theme === "dark" ? webDarkTheme : webLightTheme}>
      <RiskyAgents />
    </FluentProvider>
  );
}

const root = createRoot(document.getElementById("root")!);
root.render(
  <McpAppProvider name="agent365-risky">
    <App />
  </McpAppProvider>
);
