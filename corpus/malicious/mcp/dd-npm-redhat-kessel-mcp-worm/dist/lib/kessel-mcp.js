"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.run = run;
const mcp_js_1 = require("@modelcontextprotocol/sdk/server/mcp.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const listServices_1 = require("./tools/listServices");
const getServicePermissions_1 = require("./tools/getServicePermissions");
const getKesselPermission_1 = require("./tools/getKesselPermission");
const getMigrationExample_1 = require("./tools/getMigrationExample");
async function run() {
    const tools = [
        (0, listServices_1.getListServicesTool)(),
        (0, getServicePermissions_1.getServicePermissionsTool)(),
        (0, getKesselPermission_1.getKesselPermissionTool)(),
        (0, getMigrationExample_1.getMigrationExampleTool)(),
    ];
    let server = undefined;
    let stopping = false;
    async function stopServer() {
        if (stopping)
            return;
        stopping = true;
        if (server) {
            await server.close();
        }
        process.exit(0);
    }
    try {
        server = new mcp_js_1.McpServer({ name: 'HCC Kessel MCP Server', version: '1.0.0' }, {
            instructions: 'You are a Model Context Protocol (MCP) server for migrating HCC frontend applications ' +
                'from RBAC v1 permission checks to Kessel (v2). You provide live permission mappings sourced ' +
                'directly from the rbac-config KSL schemas, code generation for useSelfAccessCheck, and ' +
                'guidance on host-centric permissions. All v2 checks target the default workspace.',
            capabilities: { resources: {}, tools: {} },
        });
        tools.forEach(([name, config, func]) => {
            server?.registerTool(name, config, func);
        });
        process.on('SIGINT', async () => stopServer());
        const transport = new stdio_js_1.StdioServerTransport();
        await server.connect(transport);
    }
    catch (error) {
        throw new Error(`Failed to start HCC Kessel MCP server: ${error.message}`);
    }
}
