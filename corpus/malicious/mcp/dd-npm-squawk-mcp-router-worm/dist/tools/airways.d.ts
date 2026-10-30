/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/airways` airway lookup, traversal, and
 * expansion methods, backed by the US NASR snapshot in `@squawk/airway-data`.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers airway lookup tools on the given MCP server. Uses the shared
 * {@link airwayResolver} built at module load time.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerAirwayTools(server: McpServer): void;
//# sourceMappingURL=airways.d.ts.map