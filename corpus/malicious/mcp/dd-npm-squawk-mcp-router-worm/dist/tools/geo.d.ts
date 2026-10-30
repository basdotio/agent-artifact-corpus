/**
 * @packageDocumentation
 * MCP tool module wrapping the great-circle geometry utilities from
 * `@squawk/geo`. Tools take plain lat/lon inputs and return distances in
 * nautical miles and bearings in degrees true.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers great-circle geometry tools (distance, bearing, midpoint,
 * destination-point) on the given MCP server.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerGeoTools(server: McpServer): void;
//# sourceMappingURL=geo.d.ts.map