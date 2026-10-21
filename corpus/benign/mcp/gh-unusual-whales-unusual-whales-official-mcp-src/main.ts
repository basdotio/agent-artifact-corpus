#!/usr/bin/env node

/**
 * Unusual Whales MCP Server
 *
 * Connects any MCP-compatible client to 100+ market data endpoints covering
 * options flow, dark pool, congressional trading, Greek exposure, volatility,
 * and more.
 */

import { createRequire } from "module"
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js"
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js"

import { log, faultJson } from "./gateway.js"
import { allTools } from "./catalog/index.js"
import { initializeDocs } from "./docs/index.js"
import { prompts, handlers as workflowHandlers } from "./workflows/index.js"
import type { ToolOutput } from "./engine.js"

const require = createRequire(import.meta.url)
const { version } = require("../package.json") as { version: string }

const SERVER_NAME = "unusual-whales"
const SERVER_VERSION = version

// Build documentation from compiled tools
const { resources, handlers: docHandlers } = initializeDocs(allTools)

const server = new McpServer({
  name: SERVER_NAME,
  version: SERVER_VERSION,
})

// ---------------------------------------------------------------------------
// Detect error payloads in JSON strings
// ---------------------------------------------------------------------------

function looksLikeFault(json: string): boolean {
  try {
    const obj = JSON.parse(json)
    return obj !== null && typeof obj === "object" && "error" in obj
  } catch {
    return false
  }
}

// ---------------------------------------------------------------------------
// Register tools from compiled catalog
// ---------------------------------------------------------------------------

for (const tool of allTools) {
  if (!tool.zodInputSchema) {
    log.error(`No Zod schema for tool: ${tool.name}`)
    continue
  }

  server.registerTool(
    tool.name,
    {
      description: tool.description,
      inputSchema: tool.zodInputSchema,
      annotations: tool.annotations || {},
    },
    async (args: any) => {
      try {
        const result = await tool.handler(args)

        // Structured response (ToolOutput)
        if (typeof result === "object" && result !== null && "text" in result) {
          const out = result as ToolOutput

          if (looksLikeFault(out.text)) {
            throw new Error(out.text)
          }

          if (
            out.structuredContent !== undefined &&
            out.structuredContent !== null &&
            (typeof out.structuredContent !== "object" ||
              Object.keys(out.structuredContent).length > 0)
          ) {
            return {
              content: [{ type: "text" as const, text: out.text }],
              structuredContent: out.structuredContent as Record<string, unknown>,
            }
          }

          return { content: [{ type: "text" as const, text: out.text }] }
        }

        // Legacy string response
        if (looksLikeFault(result)) {
          throw new Error(result)
        }

        return { content: [{ type: "text" as const, text: result }] }
      } catch (error) {
        throw new Error(
          faultJson(`Tool execution failed: ${error instanceof Error ? error.message : String(error)}`),
        )
      }
    },
  )
}

// ---------------------------------------------------------------------------
// Register documentation resources
// ---------------------------------------------------------------------------

for (const res of resources) {
  const handler = docHandlers[res.uri]
  if (!handler) {
    log.error(`No handler for resource: ${res.uri}`)
    continue
  }

  server.registerResource(
    res.name,
    res.uri,
    { description: res.description, mimeType: res.mimeType },
    async () => {
      try {
        const content = await handler()
        return { contents: [{ uri: res.uri, text: content, mimeType: res.mimeType }] }
      } catch (error) {
        throw new Error(
          faultJson(`Resource read failed: ${error instanceof Error ? error.message : String(error)}`),
        )
      }
    },
  )
}

// ---------------------------------------------------------------------------
// Register workflow prompts
// ---------------------------------------------------------------------------

for (const prompt of prompts) {
  const handler = workflowHandlers[prompt.name]
  if (!handler) {
    log.error(`No handler for prompt: ${prompt.name}`)
    continue
  }

  server.registerPrompt(
    prompt.name,
    { description: prompt.description ?? "" },
    async () => {
      try {
        const messages = await handler({})
        return { messages }
      } catch (error) {
        throw new Error(
          faultJson(`Prompt execution failed: ${error instanceof Error ? error.message : String(error)}`),
        )
      }
    },
  )
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function boot(): Promise<void> {
  const transport = new StdioServerTransport()
  await server.connect(transport)
  log.info("Server started", { name: SERVER_NAME, version: SERVER_VERSION })
}

async function shutdown(): Promise<void> {
  log.info("Shutting down")
  await server.close()
  process.exit(0)
}

process.on("SIGINT", shutdown)
process.on("SIGTERM", shutdown)

boot().catch((error) => {
  log.error("Fatal error", { error })
  process.exit(1)
})
