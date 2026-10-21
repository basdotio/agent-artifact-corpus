#!/usr/bin/env node

import { createRequire } from "node:module";
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import {
  checkMarkingCodeSchema,
  handleCheckMarkingCode,
  getProductInfoSchema,
  handleGetProductInfo,
} from "./tools/check.js";
import { checkBatchSchema, handleCheckBatch } from "./tools/batch.js";
import { searchProductsSchema, handleSearchProducts } from "./tools/search.js";
import { getCisInfoSchema, handleGetCisInfo } from "./tools/cis-info.js";

const require = createRequire(import.meta.url);
const { version } = require("../package.json") as { version: string };

/** Run a tool handler, mapping its result to structuredContent + text, and any thrown
 * error to an `isError` result so MCP clients see a real error (not a fake success). */
async function runTool<T extends object>(
  handler: () => Promise<T>,
): Promise<CallToolResult> {
  try {
    const data = await handler();
    return {
      structuredContent: data as Record<string, unknown>,
      content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: JSON.stringify({ error: message }, null, 2) }],
      isError: true,
    };
  }
}

// --- Output schemas (typed, tolerant — fields nullable since live shapes are unverified) ---

const checkOutputShape = {
  code: z.string(),
  found: z.boolean(),
  valid: z.boolean(),
  status: z.string().nullable(),
};

const productInfoOutputShape = {
  ...checkOutputShape,
  productName: z.string().nullable(),
  category: z.string().nullable(),
  producerName: z.string().nullable(),
  ownerName: z.string().nullable(),
  ownerInn: z.string().nullable(),
};

const batchOutputShape = {
  total: z.number(),
  results: z.array(
    z.object({
      code: z.string(),
      found: z.boolean(),
      valid: z.boolean(),
      status: z.string().nullable(),
      productName: z.string().nullable().optional(),
      error: z.string().optional(),
    }),
  ),
};

const searchOutputShape = {
  query: z.string(),
  total: z.number(),
  results: z.array(
    z.object({
      gtin: z.string().nullable(),
      productName: z.string().nullable(),
      producerName: z.string().nullable(),
      brand: z.string().nullable(),
    }),
  ),
};

const cisOutputShape = {
  cis: z.string(),
  gtin: z.string().nullable(),
  productName: z.string().nullable(),
  producerName: z.string().nullable(),
  producerInn: z.string().nullable(),
  status: z.string().nullable(),
};

export function createServer(): McpServer {
  const server = new McpServer({
    name: "chestnyznak-mcp",
    version,
  });

  // --- Public tools (no auth) ---

  server.registerTool(
    "check_marking_code",
    {
      description: "Проверка подлинности товара по коду маркировки Честный ЗНАК.",
      inputSchema: checkMarkingCodeSchema.shape,
      outputSchema: checkOutputShape,
    },
    (params) => runTool(() => handleCheckMarkingCode(params)),
  );

  server.registerTool(
    "get_product_info",
    {
      description:
        "Подробная информация о товаре по коду маркировки: название, группа, производитель, владелец.",
      inputSchema: getProductInfoSchema.shape,
      outputSchema: productInfoOutputShape,
    },
    (params) => runTool(() => handleGetProductInfo(params)),
  );

  server.registerTool(
    "check_batch",
    {
      description: "Пакетная проверка до 50 кодов маркировки за один запрос.",
      inputSchema: checkBatchSchema.shape,
      outputSchema: batchOutputShape,
    },
    (params) => runTool(() => handleCheckBatch(params)),
  );

  // --- Auth-required tools (CHESTNYZNAK_TOKEN) ---

  server.registerTool(
    "search_products",
    {
      description:
        "Информация о товаре по GTIN из True API. Требует CHESTNYZNAK_TOKEN. (Поиск по названию — Нацкаталог, вне API.)",
      inputSchema: searchProductsSchema.shape,
      outputSchema: searchOutputShape,
    },
    (params) => runTool(() => handleSearchProducts(params)),
  );

  server.registerTool(
    "get_cis_info",
    {
      description: "Информация о CIS (коде идентификации) из True API. Требует CHESTNYZNAK_TOKEN.",
      inputSchema: getCisInfoSchema.shape,
      outputSchema: cisOutputShape,
    },
    (params) => runTool(() => handleGetCisInfo(params)),
  );

  return server;
}

function parseArg(args: string[], name: string, fallback: string): string {
  return args.find((a) => a.startsWith(`--${name}=`))?.split("=")[1] ?? fallback;
}

async function main() {
  const args = process.argv.slice(2);
  const httpMode = args.includes("--http");
  const port = parseInt(parseArg(args, "port", "3000"), 10);
  // Bind to loopback by default; exposing publicly requires explicit opt-in.
  const host = parseArg(args, "host", "127.0.0.1");

  if (httpMode) {
    const { StreamableHTTPServerTransport } = await import(
      "@modelcontextprotocol/sdk/server/streamableHttp.js"
    );
    const http = await import("node:http");

    // Include the actual bind host so DNS-rebinding protection doesn't reject a
    // non-loopback --host (e.g. a container hostname or LAN IP).
    const allowedHosts = [
      "localhost",
      "127.0.0.1",
      `localhost:${port}`,
      `127.0.0.1:${port}`,
      host,
      `${host}:${port}`,
    ];

    const setCors = (res: import("node:http").ServerResponse) => {
      res.setHeader("Access-Control-Allow-Origin", "*");
      res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
      res.setHeader(
        "Access-Control-Allow-Headers",
        "Content-Type, mcp-session-id, mcp-protocol-version",
      );
    };

    const httpServer = http.createServer(async (req, res) => {
      setCors(res);
      if (req.method === "OPTIONS") {
        res.writeHead(204);
        res.end();
        return;
      }

      const url = new URL(req.url ?? "/", `http://${host}:${port}`);

      if (url.pathname === "/health") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "ok", tools: 5, version }));
        return;
      }

      if (url.pathname === "/mcp") {
        if (req.method !== "POST") {
          res.writeHead(405, { Allow: "POST, OPTIONS" });
          res.end("Method Not Allowed");
          return;
        }
        // Stateless: a fresh server + transport per request avoids cross-client
        // state bleed and request-id collisions under concurrency.
        const reqServer = createServer();
        const transport = new StreamableHTTPServerTransport({
          sessionIdGenerator: undefined,
          enableDnsRebindingProtection: true,
          allowedHosts,
        });
        res.on("close", () => {
          void transport.close();
          void reqServer.close();
        });
        try {
          await reqServer.connect(transport);
          await transport.handleRequest(req, res);
        } catch (err) {
          console.error("[chestnyznak-mcp] Ошибка транспорта:", err);
          if (!res.headersSent) {
            res.writeHead(500, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ error: "Internal Server Error" }));
          }
        }
        return;
      }

      res.writeHead(404);
      res.end("Not Found");
    });

    httpServer.listen(port, host, () => {
      console.error(
        `[chestnyznak-mcp] HTTP сервер на ${host}:${port}. 5 инструментов. POST /mcp`,
      );
    });
  } else {
    const server = createServer();
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("[chestnyznak-mcp] Сервер запущен (stdio). 5 инструментов.");
  }
}

main().catch((error) => {
  console.error("[chestnyznak-mcp] Ошибка:", error);
  process.exit(1);
});
