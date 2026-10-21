#!/usr/bin/env node
/**
 * Android Docs MCP Server
 *
 * Exposes developer.android.com documentation to any MCP-compatible AI agent
 * via five tools: search, get-doc, get-api-reference, list-packages, get-release-notes.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import {
    searchToolName,
    searchToolDescription,
    searchToolSchema,
    searchToolHandler,
} from "./tools/search.js";

import {
    getDocToolName,
    getDocToolDescription,
    getDocToolSchema,
    getDocToolHandler,
} from "./tools/get-doc.js";

import {
    getApiReferenceToolName,
    getApiReferenceToolDescription,
    getApiReferenceToolSchema,
    getApiReferenceToolHandler,
} from "./tools/get-api-reference.js";

import {
    listPackagesToolName,
    listPackagesToolDescription,
    listPackagesToolSchema,
    listPackagesToolHandler,
} from "./tools/list-packages.js";

import {
    getReleaseNotesToolName,
    getReleaseNotesToolDescription,
    getReleaseNotesToolSchema,
    getReleaseNotesToolHandler,
} from "./tools/get-release-notes.js";

// ─── Create server ─────────────────────────────────────────────────────────

const server = new McpServer({
    name: "android-docs-mcp",
    version: "1.0.1",
});

// ─── Register tools ────────────────────────────────────────────────────────

server.registerTool(
    searchToolName,
    { description: searchToolDescription, inputSchema: searchToolSchema },
    async (args) => ({
        content: [{ type: "text" as const, text: await searchToolHandler(args) }],
    }),
);

server.registerTool(
    getDocToolName,
    { description: getDocToolDescription, inputSchema: getDocToolSchema },
    async (args) => ({
        content: [{ type: "text" as const, text: await getDocToolHandler(args) }],
    }),
);

server.registerTool(
    getApiReferenceToolName,
    {
        description: getApiReferenceToolDescription,
        inputSchema: getApiReferenceToolSchema,
    },
    async (args) => ({
        content: [
            { type: "text" as const, text: await getApiReferenceToolHandler(args) },
        ],
    }),
);

server.registerTool(
    listPackagesToolName,
    {
        description: listPackagesToolDescription,
        inputSchema: listPackagesToolSchema,
    },
    async (args) => ({
        content: [
            { type: "text" as const, text: await listPackagesToolHandler(args) },
        ],
    }),
);

server.registerTool(
    getReleaseNotesToolName,
    {
        description: getReleaseNotesToolDescription,
        inputSchema: getReleaseNotesToolSchema,
    },
    async (args) => ({
        content: [
            { type: "text" as const, text: await getReleaseNotesToolHandler(args) },
        ],
    }),
);

// ─── Start server ──────────────────────────────────────────────────────────

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Android Docs MCP server running on stdio");
}

main().catch((err) => {
    console.error("Fatal error:", err);
    process.exit(1);
});
