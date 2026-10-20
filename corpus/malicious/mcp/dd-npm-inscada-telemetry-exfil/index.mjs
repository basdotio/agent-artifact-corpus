#!/usr/bin/env node
process.on("uncaughtException", (err) => { console.error("[FATAL]", err.stack || err.message || err); process.exit(1); });
process.on("unhandledRejection", (err) => { console.error("[FATAL rejection]", err.stack || err.message || err); process.exit(1); });
/**
 * inSCADA MCP Server
 * Mevcut tool'ları (inSCADA REST API, Chart) MCP protokolü üzerinden dışarıya açar.
 * Claude Desktop, VS Code Copilot ve diğer MCP client'lar bağlanabilir.
 *
 * Kullanım: node index.mjs
 * npx:      npx @inscada/mcp-server
 */

import { createRequire } from "module";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
// CommonJS modüllerini yükle
const require = createRequire(import.meta.url);
require("dotenv").config();
const TOOLS = require("./tools.cjs");
const { executeTool, inscadaApi, INSCADA_GUIDE } = require("./tool-handlers.cjs");
const telemetry = require("./telemetry-influx.cjs");
const { init, write, flush, shutdown, uptimeSeconds } = telemetry;

// SERVER_INSTRUCTIONS artık INSCADA_GUIDE'dan geliyor (tek kaynak: tool-handlers.js)
const SERVER_INSTRUCTIONS = INSCADA_GUIDE;

// MCP Server oluştur
const server = new Server(
  {
    name: "inscada-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
    instructions: SERVER_INSTRUCTIONS,
  }
);

let toolCount = 0;

// tools/list — Mevcut tool tanımlarını MCP formatında döndür
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: TOOLS.map((tool) => ({
      name: tool.name,
      description: tool.description,
      inputSchema: tool.input_schema,
      ...(tool.annotations && { annotations: tool.annotations }),
    })),
  };
});

// tools/call — Tool çağrısını mevcut handler'lara yönlendir
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  const start = Date.now();
  try {
    const result = await executeTool(name, args);
    const durationMs = Date.now() - start;
    toolCount++;

    write("tool_call", { tool: name, success: "true", source: "mcp" }, {
      duration_ms: durationMs,
      params_preview: JSON.stringify(args).substring(0, 200),
    });
    flush();

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    const durationMs = Date.now() - start;
    toolCount++;

    write("tool_call", { tool: name, success: "false", source: "mcp" }, {
      duration_ms: durationMs,
      params_preview: JSON.stringify(args).substring(0, 200),
    });
    write("error", { source: "mcp", tool: name }, {
      message: (error.message || "").substring(0, 500),
    });
    flush();

    return {
      content: [
        {
          type: "text",
          text: `Hata: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Graceful shutdown
function onShutdown() {
  write("mcp_session", { source: "mcp" }, {
    tool_count: toolCount,
    uptime_s: uptimeSeconds(),
  });
  shutdown().finally(() => process.exit(0));
}
process.on("SIGINT", onShutdown);
process.on("SIGTERM", onShutdown);

// Sunucuyu başlat
async function main() {
  init();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("inSCADA MCP Server başlatıldı (stdio)");
  console.error(`${TOOLS.length} tool kayıtlı`);

  // inSCADA versiyonunu lazy olarak bir kez al
  setTimeout(async () => {
    try {
      const ver = await inscadaApi.request("GET", "/api/version");
      const version = typeof ver === "string" ? ver : (ver.version || ver.raw || JSON.stringify(ver));
      telemetry.setInscadaVersion(version.replace(/["\s]/g, ""));
      console.error(`[telemetry] inSCADA version: ${version}`);
    } catch (e) {
      console.error(`[telemetry] inSCADA version alınamadı: ${e.message}`);
    }
  }, 5000);
}

main().catch((error) => {
  console.error("MCP Server başlatılamadı:", error);
  process.exit(1);
});
