/**
 * @packageDocumentation
 * MCP tool module exposing build provenance and record counts for every
 * bundled FAA snapshot the server loads. Lets an LLM client report exactly
 * which NASR cycle and registry vintage answered a query - critical context
 * for aviation use, where stale data is a real safety concern.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers the `get_dataset_status` tool on the given MCP server. The tool
 * takes no input and reports the NASR cycle date, generation timestamp, and
 * record counts for each loaded snapshot. The lazily-loaded ICAO registry
 * reports its load state without being initialized as a side effect.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerDatasetTools(server: McpServer): void;
//# sourceMappingURL=datasets.d.ts.map