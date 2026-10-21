#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import {
  ReadWebPageSchema,
  ReaderResponseSchema,
  SearchWebSchema,
  SearchResponseSchema,
  GroundingSchema,
  GroundingResponseSchema,
} from './schemas.js'

// Get your Jina AI API key for free: https://jina.ai/
const JINA_API_KEY = process.env.JINA_API_KEY;

if (!JINA_API_KEY) {
  console.error("JINA_API_KEY environment variable is not set. You can get a key at https://jina.ai/");
  process.exit(1);
}

const server = new Server({
  name: "jina-mcp-server",
  version: "0.1.0",
}, {
  capabilities: {
    tools: {}
  }
});

async function readWebPage(params: z.infer<typeof ReadWebPageSchema>) {
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${JINA_API_KEY}`,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  };

  if (params.with_links) headers['X-With-Links-Summary'] = 'true';
  if (params.with_images) headers['X-With-Images-Summary'] = 'true';
  if (params.with_generated_alt) headers['X-With-Generated-Alt'] = 'true';
  if (params.no_cache) headers['X-No-Cache'] = 'true';

  const response = await fetch('https://r.jina.ai/', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      url: params.url,
      options: params.format || 'Default'
    })
  });

  if (!response.ok) {
    throw new Error(`Jina AI API error: ${response.statusText}`);
  }

  return ReaderResponseSchema.parse(await response.json());
}

async function searchWeb(params: z.infer<typeof SearchWebSchema>) {
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${JINA_API_KEY}`,
    'Accept': 'application/json',
    'X-Retain-Images': params.retain_images,
    'X-With-Generated-Alt': params.with_generated_alt.toString(),
    'X-Return-Format': params.return_format
  };

  const queryString = encodeURIComponent(params.query);
  const url = `https://s.jina.ai/${queryString}?count=${params.count}`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`Jina AI Search API error: ${response.statusText}`);
  }

  return SearchResponseSchema.parse(await response.json());
}

async function groundStatement(params: z.infer<typeof GroundingSchema>) {
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${JINA_API_KEY}`,
    'Accept': 'application/json'
  };

  const statementQuery = encodeURIComponent(params.statement);
  const url = `https://g.jina.ai/${statementQuery}${params.deepdive ? '?deepdive=true' : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`Jina AI Grounding API error: ${response.statusText}`);
  }

  return GroundingResponseSchema.parse(await response.json());
}

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "read_webpage",
        description: "Extract content from a webpage in a format optimized for LLMs",
        inputSchema: zodToJsonSchema(ReadWebPageSchema)
      },
      {
        name: "search_web",
        description: "Search the web using Jina AI's search API",
        inputSchema: zodToJsonSchema(SearchWebSchema)
      },
      {
        name: "fact_check",
        description: "Fact-check a statement using Jina AI's grounding engine",
        inputSchema: zodToJsonSchema(GroundingSchema)
      }
    ]
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    if (!request.params.arguments) {
      throw new Error("Arguments are required");
    }

    switch (request.params.name) {
      case "read_webpage": {
        const args = ReadWebPageSchema.parse(request.params.arguments);
        const result = await readWebPage(args);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "search_web": {
        const args = SearchWebSchema.parse(request.params.arguments);
        const result = await searchWeb(args);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "fact_check": {
        const args = GroundingSchema.parse(request.params.arguments);
        const result = await groundStatement(args);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      default:
        throw new Error(`Unknown tool: ${request.params.name}`);
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new Error(`Invalid arguments: ${error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join(', ')}`);
    }
    throw error;
  }
});

async function runServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Jina AI MCP Server running on stdio");
}

runServer().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});