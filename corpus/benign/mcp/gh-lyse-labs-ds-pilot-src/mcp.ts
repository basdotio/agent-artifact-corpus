import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { createScannerCache } from "./scanner/cache.js";
import { searchComponents, getComponentWithProps, listTokens, getToken } from "./tools.js";

interface MCPConfig {
  componentsDir: string;
  tokensFile?: string;
}

export async function startMCPServer(config: MCPConfig) {
  const server = new McpServer({
    name: "ds-pilot",
    version: "0.3.2",
  });

  const cache = createScannerCache(config.componentsDir, config.tokensFile);

  server.tool(
    "search_components",
    "Search for existing components in the design system by name",
    { query: z.string().describe("Search term (e.g. 'button', 'card', 'modal')") },
    async ({ query }) => {
      try {
        const results = searchComponents(cache.getComponents(), query);
        return {
          content: [{ type: "text" as const, text: JSON.stringify(results, null, 2) }],
        };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error searching components: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "get_component_props",
    "Get the props/API of a specific component",
    { name: z.string().describe("Exact component name (e.g. 'Button', 'Card')") },
    async ({ name }) => {
      try {
        const result = getComponentWithProps(cache.getComponents(), name);
        if (!result) {
          return {
            content: [{ type: "text" as const, text: `Component "${name}" not found. Use search_components to find available components.` }],
          };
        }
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error getting component props: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "list_tokens",
    "List all design tokens, optionally filtered by type (color, dimension, fontFamily, etc.)",
    { type: z.string().optional().describe("Token type filter (e.g. 'color', 'dimension')") },
    async ({ type }) => {
      try {
        const results = listTokens(cache.getTokens(), type);
        return {
          content: [{ type: "text" as const, text: JSON.stringify(results, null, 2) }],
        };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error listing tokens: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "get_token",
    "Get a specific design token by its full name",
    { name: z.string().describe("Token name in dot notation (e.g. 'color.primary', 'spacing.md')") },
    async ({ name }) => {
      try {
        const result = getToken(cache.getTokens(), name);
        if (!result) {
          return {
            content: [{ type: "text" as const, text: `Token "${name}" not found. Use list_tokens to see available tokens.` }],
          };
        }
        return {
          content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
        };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error getting token: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true,
        };
      }
    }
  );

  const transport = new StdioServerTransport();
  await server.connect(transport);
}
