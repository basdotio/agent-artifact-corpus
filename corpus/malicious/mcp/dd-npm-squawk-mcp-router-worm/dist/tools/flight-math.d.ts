/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/flight-math` E6B-style flight computer
 * calculations. Each tool corresponds to a single function from one of the
 * package's namespaces (atmosphere, airspeed, wind, descent, navigation,
 * turn, glide, solar, magnetic, planning).
 *
 * Trivially-simple operations (single multiplications, divisions, or
 * trig calls) are intentionally not exposed as tools - LLMs handle those
 * accurately on their own. The selected tools cover the cases where the
 * underlying implementation embeds a non-trivial constant, formula, or
 * lookup (the WMM2025 spherical harmonics, the NOAA solar algorithm,
 * compressible-flow pitot equations, holding-pattern sector logic, and
 * so on).
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers flight-math computation tools on the given MCP server.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerFlightMathTools(server: McpServer): void;
//# sourceMappingURL=flight-math.d.ts.map