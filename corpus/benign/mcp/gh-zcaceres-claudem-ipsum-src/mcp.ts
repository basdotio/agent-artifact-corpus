#!/usr/bin/env node
/**
 * MCP (Model Context Protocol) server over the public library API. Like the CLI,
 * it imports only ./index.js and adds no generation logic of its own — the
 * library stays the single source of truth. Speaks JSON-RPC over stdio.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { generate } from "./index.js";

const server = new McpServer({ name: "claudem-ipsum", version: "0.1.0" });

server.registerTool(
  "generate_claudem_ipsum",
  {
    title: "Generate claudem-ipsum",
    description:
      "Filler/placeholder text in Claude's voice: hedged first-person clauses, " +
      "hyphenated compounds, quoted jargon, parenthetical status tags, and " +
      "ownership deferrals. Sized by words, sentences, or paragraphs; seedable " +
      "for reproducible output.",
    inputSchema: {
      count: z.number().int().min(0).default(50).describe("How many units to generate."),
      unit: z
        .enum(["words", "sentences", "paragraphs"])
        .default("words")
        .describe("What `count` measures."),
      seed: z
        .union([z.string(), z.number()])
        .optional()
        .describe("Seed for reproducible output; omit for fresh random text."),
    },
    outputSchema: {
      text: z.string(),
      stats: z.object({
        words: z.number().int(),
        sentences: z.number().int(),
        paragraphs: z.number().int(),
      }),
    },
  },
  async ({ count, unit, seed }) => {
    const result = generate({ count, unit, seed });
    return {
      content: [{ type: "text", text: result.text }],
      // Cast only to satisfy the SDK's Record<string, unknown> shape; the public
      // GenerateResult type stays clean and index-signature-free.
      structuredContent: result as unknown as Record<string, unknown>,
    };
  },
);

await server.connect(new StdioServerTransport());
