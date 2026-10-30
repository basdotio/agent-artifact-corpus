/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/airports` airport lookup methods, backed
 * by the US NASR snapshot in `@squawk/airport-data`. The dataset is loaded
 * and indexed eagerly when the shared {@link airportResolver} is imported.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers airport lookup tools (by FAA ID, by ICAO code, nearest, text
 * search) on the given MCP server. Tools share the {@link airportResolver}
 * singleton built at module load time from the bundled US NASR dataset.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerAirportTools(server: McpServer): void;
//# sourceMappingURL=airports.d.ts.map