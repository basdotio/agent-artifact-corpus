#!/usr/bin/env node
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const node_util_1 = require("node:util");
const server_1 = require("./server.js");
const logger_1 = require("./utils/logger.js");
// Parse command line arguments
const { values } = (0, node_util_1.parseArgs)({
    options: {
        transport: {
            type: "string",
            short: "t",
            default: "stdio",
        },
        host: {
            type: "string",
            short: "h",
            default: "localhost",
        },
        port: {
            type: "string",
            short: "p",
            default: "1122",
        },
        endpoint: {
            type: "string",
            short: "e",
            default: "", // We'll handle defaults per transport type
        },
        help: {
            type: "boolean",
            short: "H",
        },
    },
});
// Display help information if requested
if (values.help) {
    console.log(`
MCP Server Chart CLI

Options:
  --transport, -t  Specify the transport protocol: "stdio", "sse", or "streamable" (default: "stdio")
  --host, -h       Specify the host for SSE or streamable transport (default: localhost)
  --port, -p       Specify the port for SSE or streamable transport (default: 1122)
  --endpoint, -e   Specify the endpoint for the transport:
                   - For SSE: default is "/sse"
                   - For streamable: default is "/mcp"
  --help, -H       Show this help message
  `);
    process.exit(0);
}
// Run in the specified transport mode
const transport = values.transport.toLowerCase();
if (transport === "sse") {
    logger_1.logger.setIsStdio(false);
    const port = Number.parseInt(values.port, 10);
    // Use provided endpoint or default to "/sse" for SSE
    const endpoint = values.endpoint || "/sse";
    const host = values.host || "localhost";
    (0, server_1.runSSEServer)(host, port, endpoint).catch(console.error);
}
else if (transport === "streamable") {
    logger_1.logger.setIsStdio(false);
    const port = Number.parseInt(values.port, 10);
    // Use provided endpoint or default to "/mcp" for streamable
    const endpoint = values.endpoint || "/mcp";
    const host = values.host || "localhost";
    (0, server_1.runHTTPStreamableServer)(host, port, endpoint).catch(console.error);
}
else {
    logger_1.logger.setIsStdio(true);
    (0, server_1.runStdioServer)().catch(console.error);
}
