/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/airspace` queries (point-in-airspace and
 * per-airport lookups), backed by the US NASR airspace GeoJSON snapshot in
 * `@squawk/airspace-data`.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers airspace query tools on the given MCP server. The bundled US
 * airspace GeoJSON snapshot is decoded and indexed eagerly via the shared
 * {@link airspaceResolver}.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerAirspaceTools(server: McpServer): void;
//# sourceMappingURL=airspace.d.ts.map