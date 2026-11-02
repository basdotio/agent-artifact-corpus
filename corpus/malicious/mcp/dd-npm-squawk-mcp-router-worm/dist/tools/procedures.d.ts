/**
 * @packageDocumentation
 * MCP tool module wrapping `@squawk/procedures` SID / STAR / IAP lookup,
 * filtering, and expansion methods, backed by the FAA CIFP snapshot in
 * `@squawk/procedure-data`.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Registers procedure lookup tools (SIDs, STARs, and IAPs) on the given
 * MCP server. Uses the shared {@link procedureResolver} built at module
 * load time from the bundled FAA CIFP snapshot.
 *
 * @param server - The MCP server instance to register tools on.
 */
export declare function registerProcedureTools(server: McpServer): void;
//# sourceMappingURL=procedures.d.ts.map