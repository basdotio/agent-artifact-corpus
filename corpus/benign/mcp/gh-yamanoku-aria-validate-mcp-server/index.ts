#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/server";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import process from "node:process";

import {
  validateRole,
  ValidateRoleInputSchema,
} from "./tools/validate-role.ts";
import {
  validateAriaAttribute,
  validateAriaInputSchema,
} from "./tools/validate-aria.ts";
import {
  listAriaData,
  ListAriaDataInputSchema,
} from "./tools/list-aria-data.ts";

import DenoJSON from "./deno.json" with { type: "json" };

// MCPサーバーの初期化
const server = new McpServer({
  name: "ARIA Validate MCP Server",
  version: DenoJSON.version,
}, {
  capabilities: {
    tools: {},
  },
});

// Tools
server.registerTool(
  "validate_role_attribute",
  {
    description:
      "指定されたARIAロールが有効かどうかを検証し、そのプロパティ、必須属性、サポートされている属性を返します",
    inputSchema: ValidateRoleInputSchema,
  },
  async ({ role }) => {
    const result = await validateRole({ role });
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      structuredContent: result as unknown as { [x: string]: unknown },
    };
  },
);

server.registerTool(
  "validate_aria_attribute",
  {
    description:
      "ARIA属性が存在するか確認し、指定されたロールとの互換性をチェックし、属性値を検証します",
    inputSchema: validateAriaInputSchema,
  },
  async ({ attribute, value }) => {
    const result = await validateAriaAttribute({ attribute, value });
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      structuredContent: result as unknown as { [x: string]: unknown },
    };
  },
);

server.registerTool(
  "list_arias_roles_data",
  {
    description:
      "aria-queryから利用可能なすべてのARIAロールおよび属性をリスト表示します。",
    inputSchema: ListAriaDataInputSchema,
  },
  async ({ type }) => {
    const result = await listAriaData({ type });
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      structuredContent: result as unknown as { [x: string]: unknown },
    };
  },
);

// 起動
async function setMCPServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("ARIA Attribute Server running on stdio");
}

setMCPServer().catch((error) => {
  console.error("Fatal error in setMCPServer():", error);
  process.exit(1);
});
