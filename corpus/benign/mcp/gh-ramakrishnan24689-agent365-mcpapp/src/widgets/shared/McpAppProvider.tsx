/**
 * MCP App Provider — manages app lifecycle, tool data, and theme.
 * Reusable across all Agent 365 widgets.
 *
 * Pattern (per official docs):
 *   - ontoolresult: receives the initial tool result when widget first renders
 *   - callServerTool: returns a promise with the result (use await in components)
 */
import React, { createContext, useContext, useState, useEffect } from "react";
import type { App, McpUiHostContext } from "@modelcontextprotocol/ext-apps";
import { useApp } from "@modelcontextprotocol/ext-apps/react";

interface McpAppContextValue {
  app: App | null;
  toolData: unknown;
  theme: "light" | "dark";
  hostContext: McpUiHostContext | undefined;
}

const McpAppContext = createContext<McpAppContextValue>({
  app: null,
  toolData: null,
  theme: "light",
  hostContext: undefined,
});

export function McpAppProvider({
  name,
  children,
}: {
  name: string;
  children: React.ReactNode;
}) {
  const [toolData, setToolData] = useState<unknown>(null);
  const [hostContext, setHostContext] = useState<McpUiHostContext | undefined>();

  const { app, error } = useApp({
    appInfo: { name, version: "1.0.0" },
    capabilities: {},
    onAppCreated: (app: App) => {
      // Initial tool result pushed by the host when widget renders
      app.ontoolresult = async (result) => {
        setToolData(result.structuredContent ?? null);
      };

      app.onhostcontextchanged = (ctx) => {
        setHostContext((prev) => ({ ...prev, ...ctx }));
      };

      app.onteardown = async () => ({});
      app.onerror = console.error;
    },
  });

  useEffect(() => {
    if (app) {
      setHostContext(app.getHostContext());
    }
  }, [app]);

  const theme: "light" | "dark" =
    hostContext?.theme === "dark" ? "dark" : "light";

  if (error) {
    return (
      <div style={{ padding: 16, color: "#c93c37" }}>
        <strong>MCP App Error:</strong> {error.message}
      </div>
    );
  }

  if (!app) {
    return (
      <div style={{ padding: 16, opacity: 0.6 }}>Connecting…</div>
    );
  }

  return (
    <McpAppContext.Provider value={{ app, toolData, theme, hostContext }}>
      {children}
    </McpAppContext.Provider>
  );
}

/** Full context (app, toolData, theme, hostContext) */
export function useMcpApp() {
  return useContext(McpAppContext);
}

/** Returns the structured tool data cast to T */
export function useMcpToolData<T>(): T | null {
  const { toolData } = useContext(McpAppContext);
  return (toolData as T) ?? null;
}

/** Returns the current theme ("light" | "dark") */
export function useMcpTheme(): "light" | "dark" {
  const { theme } = useContext(McpAppContext);
  return theme;
}
