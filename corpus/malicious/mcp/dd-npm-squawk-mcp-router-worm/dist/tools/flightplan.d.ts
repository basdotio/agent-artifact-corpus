/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/flightplan` route-string parsing and
 * great-circle distance computation. The flightplan resolver composes the
 * shared airport, navaid, fix, airway, and procedure resolvers from
 * {@link ../resolvers.js}.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers flight plan parsing and route distance tools on the given MCP
 * server. The flightplan resolver is built once at registration time and
 * shares the bundled NASR data via the resolver singletons.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerFlightplanTools(server: McpServer): void;
//# sourceMappingURL=flightplan.d.ts.map