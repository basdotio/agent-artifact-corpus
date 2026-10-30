/**
 * @packageDocumentation
 * Server factory for @squawk/mcp. Assembles an {@link McpServer} preloaded
 * with every squawk aviation tool module.
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
/**
 * Number of tool modules registered by {@link createSquawkMcpServer}. Exposed
 * so the stdio entrypoint can include the count in its startup diagnostic
 * without re-counting at runtime.
 */
export declare const TOOL_MODULE_COUNT: number;
/**
 * Package name as published to npm. Convenient for diagnostic logs that want
 * to identify the running server without re-reading `package.json`.
 */
export declare const PACKAGE_NAME: string;
/**
 * Package version pulled from `package.json` at module load. Mirrored as the
 * server's `version` field and reused by the stdio entrypoint diagnostic.
 */
export declare const PACKAGE_VERSION: string;
/**
 * Creates an MCP server preloaded with every squawk aviation tool module.
 *
 * Tool registration triggers eager construction of the shared resolver
 * singletons in `./resolvers.js` for every domain except the ICAO aircraft
 * registry, which loads on first lookup. Live weather fetch tools issue
 * outbound HTTPS requests to the Aviation Weather Center text API only when
 * invoked.
 *
 * ```typescript
 * import { createSquawkMcpServer } from '@squawk/mcp';
 * import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
 *
 * const server = createSquawkMcpServer();
 * await server.connect(new StdioServerTransport());
 * ```
 *
 * @returns A fully configured MCP server instance. Connect it to a transport
 *          (typically `StdioServerTransport` for CLI use) via
 *          `server.connect(transport)` to begin handling protocol messages.
 */
export declare function createSquawkMcpServer(): McpServer;
//# sourceMappingURL=server.d.ts.map