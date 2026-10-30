/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/weather` parsing utilities and the live
 * `@squawk/weather/fetch` client for the Aviation Weather Center text API.
 *
 * Parsing tools accept user-pasted METAR/TAF/SIGMET/AIRMET/PIREP strings and
 * return the parsed objects. Fetch tools issue HTTP requests to the AWC API
 * and return both the parsed records and any per-record parse errors so the
 * model can surface partial failures.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers weather parsing and live-fetch tools on the given MCP server.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerWeatherTools(server: McpServer): void;
//# sourceMappingURL=weather.d.ts.map