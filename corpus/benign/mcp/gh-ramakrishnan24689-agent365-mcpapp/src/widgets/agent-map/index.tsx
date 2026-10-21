/**
 * Agent Map Widget — Entry point.
 * Circle-packing visualization of agents grouped by publisher type.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import { FluentProvider, webLightTheme, webDarkTheme } from "@fluentui/react-components";
import { McpAppProvider, useMcpTheme } from "../shared/McpAppProvider";
import { AgentMap } from "./AgentMap";

function App() {
  const theme = useMcpTheme();
  return (
    <FluentProvider theme={theme === "dark" ? webDarkTheme : webLightTheme}>
      <AgentMap />
    </FluentProvider>
  );
}

const root = createRoot(document.getElementById("root")!);
root.render(
  <McpAppProvider name="agent365-map">
    <App />
  </McpAppProvider>
);
