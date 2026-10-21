#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod/v3";

// Parse --ttl-mins arg
const ttlIndex = process.argv.indexOf("--ttl-mins");
const TTL_MINS =
  ttlIndex !== -1 && process.argv[ttlIndex + 1]
    ? parseInt(process.argv[ttlIndex + 1], 10)
    : 1440; // 24 hours

// API endpoints
const GET_URL = "https://memo-upstash.vercel.app/api/get";
const SET_URL = "https://memo-upstash.vercel.app/api/set";

const server = new McpServer({
  name: "memo-mcp-server",
  version: "1.0.0",
});

server.registerTool(
  "memo_get",
  {
    title: "Memo Get",
    description:
      "Retrieve saved conversation context by ID. Use when user says 'memo get <id>' or pastes a memo ID.",
    inputSchema: {
      id: z.string().describe("The memo ID (e.g., 4tJ630XqhCV5gQelx98pu)"),
    },
  },
  async ({ id }: { id: string }) => {
    try {
      const response = await fetch(`${GET_URL}?id=${encodeURIComponent(id)}`);
      if (!response.ok) {
        return {
          content: [
            {
              type: "text",
              text: `Error: HTTP ${response.status} - ${response.statusText}`,
            },
          ],
        };
      }
      const data = await response.json();
      if (data.error) {
        return {
          content: [{ type: "text", text: `Error: ${data.error}` }],
        };
      }

      // Try to parse and format structured context, fall back to raw text
      try {
        const ctx = JSON.parse(data.summary);
        const formatted = `# Previous Session Context

This is context from a previous conversation. Use this to continue the work where it left off. Start by reviewing the pending tasks and relevant files.

## Goal
${ctx.goal}

## Completed
${ctx.completed?.map((t: string) => `- ${t}`).join("\n") || "None"}

## Pending
${ctx.pending?.length ? ctx.pending.map((t: string) => `- ${t}`).join("\n") : "None"}

## Key Decisions
${ctx.decisions?.length ? ctx.decisions.map((d: string) => `- ${d}`).join("\n") : "None"}

## Relevant Files
${ctx.files?.length ? ctx.files.map((f: string) => `- ${f}`).join("\n") : "None"}

## Additional Context
${ctx.context || "None"}`;

        return {
          content: [{ type: "text", text: formatted }],
        };
      } catch {
        // Fall back to raw text if not valid JSON
        return {
          content: [{ type: "text", text: data.summary }],
        };
      }
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Network error: ${error instanceof Error ? error.message : "Failed to connect"}`,
          },
        ],
      };
    }
  },
);

const contextSchema = z.object({
  goal: z.string().describe("What the user was trying to accomplish"),
  completed: z.array(z.string()).describe("Tasks/changes that were completed"),
  pending: z
    .array(z.string())
    .optional()
    .describe("Tasks that remain unfinished"),
  decisions: z
    .array(z.string())
    .optional()
    .describe("Key technical decisions made and why"),
  files: z
    .array(z.string())
    .optional()
    .describe("Key files that were modified or are relevant"),
  context: z.string().optional().describe("Any other important context"),
});

type Context = z.infer<typeof contextSchema>;

server.registerTool(
  "memo_set",
  {
    title: "Memo Set",
    description:
      "Save conversation context for another AI agent. Use when user says 'memo set' or asks to save/store the conversation.",
    inputSchema: {
      context: contextSchema,
    },
  },
  async ({ context }: { context: Context }) => {
    try {
      const response = await fetch(SET_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: JSON.stringify(context),
          ttlMins: TTL_MINS,
        }),
      });
      if (!response.ok) {
        return {
          content: [
            {
              type: "text",
              text: `Error: HTTP ${response.status} - ${response.statusText}`,
            },
          ],
        };
      }
      const data = await response.json();
      const id = data.id;
      if (!id) {
        console.warn("Warning: No ID returned from set API", data);
        return {
          content: [
            {
              type: "text",
              text: `Warning: Failed to save summary. No ID was returned.\n\nResponse: ${JSON.stringify(data, null, 2)}`,
            },
          ],
        };
      }
      return {
        content: [
          {
            type: "text",
            text: `Conversation summary saved!\n\nTo restore this context later, copy and paste:\n\n\`\`\`\nmemo get ${id}\n\`\`\``,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Network error: ${error instanceof Error ? error.message : "Failed to connect"}`,
          },
        ],
      };
    }
  },
);

// Register prompt for "memo set" command
server.registerPrompt(
  "memo set",
  {
    description:
      "Save structured conversation context for another AI agent to continue the work",
  },
  async () => {
    return {
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: "Please save our conversation context using the 'memo_set' tool with structured data: goal (what we were trying to accomplish), completed (tasks done), pending (remaining tasks), decisions (key technical choices made), files (relevant files), and any other important context.",
          },
        },
      ],
    };
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
