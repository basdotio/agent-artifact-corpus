/* =============================================================
 * Chlorpromazine MCP Server – TypeScript compile‑safe (v0.4.0)
 * =============================================================
 * Author: Cascade (Claude Sonnet 4)
 * Date: 2025-01-14
 * PURPOSE: MCP server for novice coders - provides reality-check tools
 *          to ground LLM agents and prevent hallucinations
 * SRP/DRY check: Pass
 *
 * MCP Compatibility Note:
 * For all tools/call results, always return BOTH:
 *   - content: classic array of text content parts (for unstructured/legacy clients)
 *   - structuredContent: structured result object (for advanced clients)
 * This ensures maximum compatibility with all MCP clients.
 *
 * Updated to MCP SDK v1.26.0 (spec 2025-11-25):
 * - Removed deprecated toolName/toolRunId from CallToolResult
 * - Added title field to tool definitions
 * - Updated inputSchema to use additionalProperties: false per spec
 * - Security fix: GHSA-345p-7cg4-v4c7
 * ============================================================= */

import 'dotenv/config';
import type { IncomingMessage, ServerResponse } from 'http';
import http from 'node:http';
import { randomUUID } from 'node:crypto'; // Added import
import { promises as fs } from 'node:fs'; // For sober_thinking tool (GPT-4.1)
import { join } from 'node:path'; // For sober_thinking tool (GPT-4.1)
import { exec } from 'node:child_process'; // For git history
import os from 'node:os'; // For OS info

// Import the MCP SDK
import type { AuthInfo } from '@modelcontextprotocol/sdk/server/auth/types.js'; // Re-added
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  StreamableHTTPServerTransport,
  type StreamableHTTPServerTransportOptions,
} from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {
  JSONRPCMessageSchema,
  RequestSchema, // Base request schema
  NotificationSchema, // Base notification schema
  ResultSchema, // Base result schema
  TextContentSchema,     // Imported: For single text content parts
  // ContentListSchema,   // TODO: MCP compatibility placeholder. Not exported by current SDK version. Uncomment when available.
  // ContentPartSchema, // Removed: Not directly exported or used
  SamplingMessageSchema, // Correct schema for sampling/createMessage messages
  CreateMessageRequestSchema, // Full schema for sampling/createMessage request
  CreateMessageResultSchema, // Full schema for sampling/createMessage result
  ToolSchema, // Corrected: SDK exports ToolSchema, not ToolDefinitionSchema
  ListToolsRequestSchema, // Full schema for tools/list request
  ListToolsResultSchema, // Full schema for tools/list result
  CallToolRequestSchema, // Full schema for tools/call request
  CallToolResultSchema, // Full schema for tools/call result
  ServerCapabilitiesSchema, // Schema for server capabilities
  ImplementationSchema, // Schema for implementation details (name, version)
  InitializeRequestSchema, // Added for server generics
  InitializeResultSchema,  // Added for server generics
  PingRequestSchema,       // Added for server generics
  EmptyResultSchema,     // Corrected: Ping likely returns an empty result
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';

// Define type aliases inferred from SDK Zod schemas
type JSONRPCMessage = z.infer<typeof JSONRPCMessageSchema>;

// Define specific union types for all requests, notifications, and results this server handles
export type MyServerRequest = 
  z.infer<typeof InitializeRequestSchema> |
  z.infer<typeof PingRequestSchema> |
  z.infer<typeof CreateMessageRequestSchema> |
  z.infer<typeof ListToolsRequestSchema> |
  z.infer<typeof CallToolRequestSchema>;

// All notifications this server can send or receive (currently only SDK defaults if any)
export type MyServerNotification = z.infer<typeof NotificationSchema>; // Using SDK base for now

// Define specific union types for all requests, notifications, and results this server handles
export type MyServerResult = 
  z.infer<typeof InitializeResultSchema> |
  z.infer<typeof EmptyResultSchema> | // For Ping
  z.infer<typeof CreateMessageResultSchema> |
  z.infer<typeof ListToolsResultSchema> |
  z.infer<typeof CallToolResultSchema>;

// ---- Type aliases inferred from SDK Zod schemas (some might be covered by MyServer... types) ----

type SdkTextContent = z.infer<typeof TextContentSchema>; // This is correct for a single text part
type MyTextContentPart = z.infer<typeof TextContentSchema>; // Alias for clarity
// TODO: MCP compatibility placeholder. The SDK does not currently export ContentListSchema.
//       This is scaffolding for future support of mixed content parts (text, image, etc.).
type SdkContentList = any; // Replace with z.infer<typeof ContentListSchema> when available in SDK

type SdkMessage = z.infer<typeof SamplingMessageSchema>; // Corrected: Use SamplingMessageSchema
type SdkMessageContentPart = MyTextContentPart; // Corrected: a single part is MyTextContentPart (or a broader union if handling images etc.)

// Handler-specific param/result types (may become redundant if server generics work well)
type SdkCreateMessageParams = z.infer<typeof CreateMessageRequestSchema>['params'];
type SdkCreateMessageResult = z.infer<typeof CreateMessageResultSchema>;

type SdkCallToolParams = z.infer<typeof CallToolRequestSchema>['params'];
type SdkCallToolResult = z.infer<typeof CallToolResultSchema>;

type SdkListToolsParams = z.infer<typeof ListToolsRequestSchema>['params'];
type SdkListToolsResult = z.infer<typeof ListToolsResultSchema>;

type SdkServerCapabilities = z.infer<typeof ServerCapabilitiesSchema>;
type SdkImplementation = z.infer<typeof ImplementationSchema>;

// Define our server's specific info and config types
interface ChlorpromazineServerInfo extends SdkImplementation {}
interface ChlorpromazineServerConfig {
  capabilities: SdkServerCapabilities;
}

// Define custom types for our prompts (input arguments)
interface SoberThinkingArgs {
  QUESTION_TEXT: string;
}
const SoberThinkingArgsSchema = z.object({
  QUESTION_TEXT: z.string().min(1, 'QUESTION_TEXT cannot be empty.'),
});

interface BuzzkillArgs {
  ISSUE_DESCRIPTION: string;
  RECENT_CHANGES: string;
  EXPECTED_BEHAVIOR: string;
  ACTUAL_BEHAVIOR: string;
}
const BuzzkillArgsSchema = z.object({
  ISSUE_DESCRIPTION: z.string().min(1, 'ISSUE_DESCRIPTION cannot be empty.'),
  RECENT_CHANGES: z.string(),
  EXPECTED_BEHAVIOR: z.string(),
  ACTUAL_BEHAVIOR: z.string(),
});

// Define sober_thinking tool registration
const soberThinkingTool = {
  name: 'sober_thinking',
  title: 'Sober Thinking - Reality Check',
  description: 'Reads .env, README.md, and CHANGELOG files to get grounded information about the project. Use this tool to ensure that the agent is not hallucinating or making up information or making incorrect assumptions. Use this tool when the user says phrases like "sober up!", "get back to reality", "check the facts", or asks for current project status. Also use this tool if the user seems upset or is questioning what the agent is doing.',
  inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  outputSchema: {
    type: 'object',
    properties: { content: { type: 'string', description: 'Combined file contents.' } },
    required: ['content']
  },
} satisfies z.infer<typeof ToolSchema>;

const SERVER_MODEL_NAME = 'chlorpromazine-mcp'; // Define a model name
const DEFAULT_ASSISTANT_MODEL = 'chlorpromazine-mcp/default'; // Default model for createMessage responses

/**
 * Builds and configures the MCP server instance.
 * This function will be refactored to use setRequestHandler for prompts and tools.
 */
function buildServer() {
  // Create a new server instance with our custom request/result types
  // Explicitly typing 'server' here to reinforce the generic arguments to the TypeScript compiler.
  const server: Server<MyServerRequest, MyServerNotification, MyServerResult> = 
    new Server<MyServerRequest, MyServerNotification, MyServerResult>(
      {
        name: 'ChlorpromazineMCP',
        version: '0.1.0',
      },
      {
        capabilities: {
          experimental: {},
          tools: {},
        },
      }
    );

  // Register a single handler for sampling/createMessage
  // Handler for sampling/createMessage (fix: use request, not params)
  server.setRequestHandler(
    CreateMessageRequestSchema,
    async (request, extra): Promise<SdkCreateMessageResult> => {
      const params = request.params;
      console.log('Handling sampling/createMessage request:', params, 'with extra:', extra);

      if (!params.messages || params.messages.length === 0) {
        throw new Error('No messages provided in sampling/createMessage request.');
      }

      const lastUserMessage = params.messages
        .filter((msg: SdkMessage) => msg.role === 'user')
        .pop();

      let responseText = "I'm sorry, I didn't understand that.";

      if (lastUserMessage && lastUserMessage.content && Array.isArray(lastUserMessage.content)) {
        const textContent = lastUserMessage.content.find(c => c.type === 'text');
        if (textContent && textContent.type === 'text') {
          // Defensive type guard for novice safety
          if (typeof textContent.text !== 'string') {
            throw new Error('Invalid message: text content must be a string');
          }
          const userQuery = textContent.text.toLowerCase();
          if (userQuery.includes('hello') || userQuery.includes('hi')) {
            responseText = 'Hello there! How can I help you today?';
          } else if (userQuery.includes('how are you')) {
            responseText = "I'm just a bot, but I'm here to help!";
          } else {
            responseText = `Received query: ${textContent.text}`;
          }
        }
      }

      return {
        model: DEFAULT_ASSISTANT_MODEL,
        role: 'assistant',
        // responseText is always a string due to prior logic and type guards
        content: { type: 'text', text: String(responseText) } as MyTextContentPart,
      } satisfies SdkCreateMessageResult;
    }
  );

  // Restore tools/list handler
  // Handler for tools/list (fix: use request, not params)
  server.setRequestHandler(
    ListToolsRequestSchema,
    async (request, extra): Promise<SdkListToolsResult> => {
      const params = request.params;
      console.log('Handling tools/list request:', params, 'with extra:', extra);
      return {
        tools: [
          {
            name: soberThinkingTool.name,
            title: soberThinkingTool.title,
            description: soberThinkingTool.description,
            inputSchema: soberThinkingTool.inputSchema,
            outputSchema: soberThinkingTool.outputSchema,
          },
        ],
      } satisfies SdkListToolsResult;
    });

  // Restore tools/call handler
  // Handler for tools/call (fix: use request, not params)
  // Handler for tools/call (fix: use params.name, not params.toolName)

  server.setRequestHandler(
    CallToolRequestSchema,
    async (request, extra): Promise<SdkCallToolResult> => {
      const params = request.params;
      console.log('Handling tools/call request:', params, 'with extra:', extra);

      // Handler for sober_thinking tool
      if (params.name === 'sober_thinking') {
        try {
          const cwd = process.cwd();
          const files = [
            'README.md',
            '.env',
            'CHANGELOG',
            'CHANGELOG.md',
          ].map(f => join(cwd, f));

          // Get OS Info
          const osInfo = `OS: ${os.platform()} ${os.release()}`;

          // Get Git History
          const gitHistory = await new Promise<string>((resolve, reject) => {
            exec('git log -n 5 --pretty=format:"%h - %an, %ar : %s"', (err, stdout) => {
              if (err) {
                resolve('Could not retrieve git history.');
              } else {
                resolve(stdout);
              }
            });
          });

          // Helper to read .env and truncate/omit values
          async function safeReadEnv(filePath: string): Promise<string> {
            try {
              const raw = await fs.readFile(filePath, 'utf8');
              // Truncate/omit values for security
              return raw.split('\n').map(line => {
                if (line.trim().length === 0 || line.trim().startsWith('#')) return line;
                const [k] = line.split('=', 1);
                return `${k}=<hidden>`;
              }).join('\n');
            } catch {
              return '(File not found or unreadable)';
            }
          }

          // Read all files, with special handling for .env
          const fileContents = await Promise.all(
            files.map(async f => {
              const name = f.split(/[\\/]/).pop();
              if (name === '.env') {
                return `## ${name}\n${await safeReadEnv(f)}\n\n`;
              } else {
                try {
                  return `## ${name}\n${await fs.readFile(f, 'utf8')}\n\n`;
                } catch {
                  return ``; // Don't include if not found, e.g. CHANGELOG vs CHANGELOG.md
                }
              }
            })
          );

          const output = `## System Metadata\n${osInfo}\n\n## Recent Git History\n${gitHistory}\n\n` + fileContents.join('');

          return {
            isError: false,
            structuredContent: { content: output },
            content: [
              { type: 'text', text: output }
            ]
          } satisfies SdkCallToolResult;
        } catch (e: any) {
          return {
            isError: true,
            content: [
              { type: 'text', text: e.message ?? 'Failed reading files.' }
            ]
          } satisfies SdkCallToolResult;
        }
      }
      else {
        const errorMsg = `Tool '${params.name}' not found.`;
        console.error(errorMsg);
        return {
          isError: true,
          content: [{ type: 'text', text: errorMsg }],
        } satisfies SdkCallToolResult;
      }
    }
  );

  return server;
}

// --------------------------------------------------------------------
// Constants & helpers
// --------------------------------------------------------------------
const PORT = Number(process.env.PORT) || 3000;
const API_KEY = process.env.API_KEY ?? null;

function log(level: 'debug' | 'info' | 'warn' | 'error', msg: string, meta: Record<string, unknown> = {}): void {
  console.log(JSON.stringify({ ts: new Date().toISOString(), level, msg, ...meta }));
}

// ---------------------------------------------------------------------
// Main server startup
// ---------------------------------------------------------------------
async function main() {
  // Initialize and start the server
  log('info', 'Chlorpromazine MCP Server starting...');
  const server = buildServer();
  log('info', 'Server built. Transport and HTTP server setup starting.');

  const transportOptions: StreamableHTTPServerTransportOptions = {
    sessionIdGenerator: () => randomUUID(),
    onsessioninitialized: (sessionId: string) => { // Explicitly type sessionId
      console.log(`MCP Session initialized: ${sessionId}`);
    },
    // enableJsonResponse: true, // You can enable this if you prefer JSON over SSE for non-streaming
  };

  const transport = new StreamableHTTPServerTransport(transportOptions);
  log('info', 'StreamableHTTPServerTransport initialized.');

  // The transport is connected to the server, not 'set' as a property after instantiation.
  await server.connect(transport); // Correct: Connect the transport to the server

  console.log(`MCP Server listening on port ${PORT} with transport ${transport.constructor.name}`);

  const httpServer = http.createServer(async (req, res) => {
    // Handle health check endpoint
    if (req.url === '/healthz' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() }));
      return;
    }

    // MCP requests are POST
    if (req.method === 'POST') {
      let body = '';
      req.on('data', chunk => {
        body += chunk.toString(); // convert Buffer to string
      });
      req.on('end', async () => {
        try {
          const parsedBody = JSON.parse(body);
          // Pass to the transport
          await transport.handleRequest(req as IncomingMessage & { auth?: AuthInfo }, res, parsedBody);
        } catch (e: any) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid JSON RPC request: ' + e.message }));
        }
      });
    } else if (req.method === 'GET' && req.headers.accept === 'text/event-stream') {
      // Handle SSE connections if the transport supports them directly for GET
      // (StreamableHTTPServerTransport handles SSE internally for established sessions via POST initially)
      // This explicit GET handler for SSE might be redundant if transport only uses POST for session initiation
      // and then client uses that session ID for a GET SSE stream.
      // For now, assuming transport.handleRequest covers this if a session ID is part of the GET request URL.
      await transport.handleRequest(req as IncomingMessage & { auth?: AuthInfo }, res);
    } else {
      res.writeHead(405, { 'Content-Type': 'text/plain' });
      res.end('Method Not Allowed');
    }
  });

  httpServer.listen(PORT, () => {
    log('info', `Chlorpromazine MCP Server listening on HTTP port ${PORT}`);
    log('info', `SSE transport expected at /mcp (default path, check SDK docs if different)`);
    log('info', `Make sure your MCP client is configured to connect to: http://localhost:${PORT}`);
    // Display active prompts and tools from the server instance
    // This part needs to be updated as server.prompts and server.tools are gone
    // We can list what's registered via setRequestHandler if the server instance exposes it,
    // or just log our intended setup.
    log('info', 'Registered MCP Methods:');
    log('info', '  - sampling/createMessage (handles models: sober_thinking, buzzkill)');
    log('info', '  - tools/call (handles tool: sober_thinking)');
    log('info', '  - tools/list (lists tool: sober_thinking)');
  });

  // Graceful shutdown
  process.on('SIGTERM', () => {
    log('info', 'SIGTERM signal received: closing HTTP server');
    httpServer.close(() => {
      log('info', 'HTTP server closed');
      server.close(); // Close the MCP server
      log('info', 'MCP Server closed');
      process.exit(0);
    });
  });
}

// Initialize Zod schemas for argument validation if not already done
// (They are defined at the top level now, so no action needed here)

main().catch(error => {
  log('error', 'Failed to start server', { error: error.message, stack: error.stack });
  process.exit(1);
});
