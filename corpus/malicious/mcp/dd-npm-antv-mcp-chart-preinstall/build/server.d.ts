import { Server } from "@modelcontextprotocol/sdk/server/index.js";
/**
 * Creates and configures an MCP server for chart generation.
 */
export declare function createServer(): Server;
/**
 * Runs the server with stdio transport.
 */
export declare function runStdioServer(): Promise<void>;
/**
 * Runs the server with SSE transport.
 */
export declare function runSSEServer(host?: string, port?: number, endpoint?: string): Promise<void>;
/**
 * Runs the server with HTTP streamable transport.
 */
export declare function runHTTPStreamableServer(host?: string, port?: number, endpoint?: string): Promise<void>;
