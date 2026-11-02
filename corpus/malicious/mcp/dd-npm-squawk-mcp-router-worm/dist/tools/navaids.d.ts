/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/navaids` navaid lookup methods, backed
 * by the US NASR snapshot in `@squawk/navaid-data`.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers navaid lookup tools on the given MCP server. Uses the shared
 * {@link navaidResolver} built at module load time.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerNavaidTools(server: McpServer): void;
//# sourceMappingURL=navaids.d.ts.map