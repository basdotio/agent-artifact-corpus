#!/usr/bin/env node

import { JSDOM } from "jsdom";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import * as z from "zod/v4";

// Set up a minimal DOM environment before mermaid is loaded.
// Mermaid's parsers for some diagram types (classDiagram, pie, gantt, etc.)
// require a window/document global to initialise DOMPurify correctly.
const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
  url: "http://localhost",
});
(globalThis as Record<string, unknown>).window = dom.window;
(globalThis as Record<string, unknown>).document = dom.window.document;

// Dynamic import ensures mermaid picks up the globals we set above.
const { default: mermaid } = await import("mermaid");

// Create an MCP server
const server = new McpServer({
  name: "mermaid-validator-mcp",
  version: "1.0.2",
});

// Add a mermaid validation tool
server.registerTool(
  "validate_mermaid",
  {
    description: "Validate mermaid diagram syntax. Returns success with the detected diagram type, or a detailed error message.",
    inputSchema: {
      diagram: z.string().describe("The mermaid diagram text to validate"),
    },
  },
  async ({ diagram }) => {
    try {
      const result = await mermaid.parse(diagram);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              valid: true,
              diagramType: result?.diagramType ?? "unknown",
            }),
          },
        ],
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({ valid: false, error: message }),
          },
        ],
      };
    }
  },
);

// Start receiving messages on stdin and sending messages on stdout
const transport = new StdioServerTransport();

const app = async () => {
  await server.connect(transport);
};

app();
