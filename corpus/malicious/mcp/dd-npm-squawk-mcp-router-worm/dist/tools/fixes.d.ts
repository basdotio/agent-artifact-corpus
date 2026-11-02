/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/fixes` fix/waypoint lookup methods,
 * backed by the US NASR snapshot in `@squawk/fix-data`.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers fix/waypoint lookup tools on the given MCP server. Uses the
 * shared {@link fixResolver} built at module load time.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerFixTools(server: McpServer): void;
//# sourceMappingURL=fixes.d.ts.map