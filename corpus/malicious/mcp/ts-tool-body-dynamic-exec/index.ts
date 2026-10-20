#!/usr/bin/env node
// Script-runner MCP server. TypeScript counterpart of cisco-ai-defense mcp-scanner
// "Example 7: Base64 Decode and Execute with Obfuscation Bypass" — same attack, different
// language, authored for this corpus.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// VULNERABLE: decode caller-supplied base64 and execute it in this process.
function decodeAndExecute(encodedScript: string): number {
  const decoded = Buffer.from(encodedScript, "base64").toString("utf8");
  // eslint-disable-next-line no-new-func
  const run = new Function(decoded);
  run();
  return decoded.length;
}

const server = new McpServer({ name: "script-runner-service", version: "1.0.0" });

server.tool(
  "run_encoded_script",
  "Run base64 encoded script for obfuscation bypass.",
  { encoded_script: z.string() },
  async ({ encoded_script }) => {
    const n = decodeAndExecute(encoded_script);
    return { content: [{ type: "text", text: `Encoded script executed: ${n} bytes` }] };
  }
);

await server.connect(new StdioServerTransport());
