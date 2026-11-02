/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/icao-registry` aircraft registration
 * lookup, backed by the FAA ReleasableAircraft snapshot in
 * `@squawk/icao-registry-data`.
 *
 * The registry data package is an **optional peer dependency** of
 * `@squawk/mcp`. The tool is always registered with the MCP server so it
 * appears in the catalog, but the data is loaded lazily on the first tool
 * invocation through {@link getIcaoRegistry}. When the peer is not installed
 * the tool returns a structured `isError: true` result naming the package and
 * the install command, rather than crashing the server.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers ICAO aircraft registration lookup tools on the given MCP server.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerIcaoRegistryTools(server: McpServer): void;
//# sourceMappingURL=icao-registry.d.ts.map