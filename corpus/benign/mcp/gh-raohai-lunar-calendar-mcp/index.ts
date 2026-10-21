#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, } from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";
import { SolarDay } from "tyme4ts";

// Server setup
const server = new Server({
  name: "mcp-server/chinese-lunar-calendar",
  version: "0.1.0",
}, {
  capabilities: {
    tools: {},
  },
});


const TOOLS = [
  {
    name: "get_lunar",
    description: "获取当天的农历日期",
    inputSchema: {
      type: "object",
      properties: {
        date: {
          type: "string",
          description: "今天的日期，格式为 YYYY-MM-DD"
        },
      }
    }
  },
  {
    name: "get_taboo",
    description: "获取当天的凶吉",
    inputSchema: {
      type: "object",
      properties: {
        date: {
          type: "string",
          description: "今天的日期，格式为 YYYY-MM-DD"
        },
      }
    }
  }
];

function handleLunar(dateStr: string) {
  const date = new Date(dateStr);
  const solar = SolarDay.fromYmd(date.getFullYear(), date.getMonth(), date.getDay());
  return solar.getLunarDay();
}

 function handelTabbo(dateStr: string) {
  const lunar = handleLunar(dateStr);
  const goods = lunar.getRecommends();
  const avoids = lunar.getAvoids();
  return {
    toString() {
      return `
      - 吉：${goods.map(g => g.getName())}
      - 凶：${avoids.map(g => g.getName())}
      `
    }
  }
}

// Set up request handlers
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { date } = request.params.arguments!;
  switch (request.params.name) {
    case 'get_lunar':
      return {
        content: [{
          type: 'text',
          text: handleLunar(date as string).toString(),
        }],
      }
    case 'get_taboo':
      return {
        content: [{
          type: 'text',
          text: handelTabbo(date as string).toString(),
        }],
      }
    default:
      return {
        content: [{
                type: "text",
                text: `Unknown tool: ${request.params.name}`
            }],
        isError: true
    };
  }
});


async function runServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Chinese Luar Calendar MCP Server running on stdio");
}

runServer().catch((error) => {
  console.error("Fatal error running server:", error);
  process.exit(1);
});