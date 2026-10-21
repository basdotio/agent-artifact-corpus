#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import express from 'express';
import type { Request, Response } from 'express';
import {
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type CallToolRequest,
  isInitializeRequest,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import fs from 'fs';
import dotenv from 'dotenv';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { randomUUID } from 'node:crypto';

import { getTreeOperation } from './operations/get_tree.js';
import { getHatByIdOperation } from './operations/get_hat_by_id.js';
import { getWearerOperation } from './operations/get_wearer.js';
import { getEligibilityOperation } from './operations/get_eligibility.js';
import { compareJsonDraftOperation } from './operations/compare_json_draft.js';
import { createErrorResponse, createJsonResponse } from './utils/response.js';
import * as createDraft from './operations/create_draft.js';
import { compareDraftOperation } from './operations/compare_draft.js';
import { operation as mintHatOperation } from './operations/mint_hat.js';
import { operation as renounceHatOperation } from './operations/renounce_hat.js';
import { operation as transferHatOperation } from './operations/transfer_hat.js';
import { operation as changeHatEligibilityOperation } from './operations/change_hat_eligibility.js';
import { operation as checkHatStatusOperation } from './operations/check_hat_status.js';
import { operation as setHatStatusOperation } from './operations/set_hat_status.js';
import { operation as mintTopHatOperation } from './operations/mint_top_hat.js';
import { operation as setHatWearerStatusOperation } from './operations/set_hat_wearer_status.js';
import { operation as checkHatWearerStatusOperation } from './operations/check_hat_wearer_status.js';
import { operation as changeHatMaxSupplyOperation } from './operations/change_hat_max_supply.js';
import { operation as changeHatToggleOperation } from './operations/change_hat_toggle.js';
import { operation as changeHatDetailsOperation } from './operations/change_hat_details.js';
import { operation as changeHatImageOperation } from './operations/change_hat_image.js';
import { operation as createHatOperation } from './operations/create_hat.js';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Debug logging
const debug = (...args: any[]) => {
  console.error('\n=== MCP Server Debug ===');
  console.error(...args);
};

// Configure global error handlers
process.on('uncaughtException', (error) => {
  console.error('\n=== Uncaught Exception ===');
  console.error('Error:', error);
  console.error('Stack:', error.stack);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('\n=== Unhandled Rejection ===');
  console.error('Promise:', promise);
  console.error('Reason:', reason);
});

// Server configuration
const SERVER_CONFIG = {
  name: 'hats-mcp-server',
  version: '0.0.1',
} as const;

// Define available tools
const TOOLS = [
  {
    name: 'get_tree',
    description: getTreeOperation.description,
    inputSchema: zodToJsonSchema(getTreeOperation.parameters),
  },
  {
    name: 'get_hat_by_id',
    description: getHatByIdOperation.description,
    inputSchema: zodToJsonSchema(getHatByIdOperation.parameters),
  },
  {
    name: 'get_wearer',
    description: getWearerOperation.description,
    inputSchema: zodToJsonSchema(getWearerOperation.parameters),
  },
  {
    name: 'get_eligibility',
    description: getEligibilityOperation.description,
    inputSchema: zodToJsonSchema(getEligibilityOperation.parameters),
  },
  // temporarily unregister these while we improve the tools (TODO: re-enable BUILD-536)
  // {
  //   name: 'compare_json_draft',
  //   description: compareJsonDraftOperation.description,
  //   inputSchema: zodToJsonSchema(compareJsonDraftOperation.parameters),
  // },
  {
    name: 'compare_draft',
    description: compareDraftOperation.description,
    inputSchema: zodToJsonSchema(compareDraftOperation.parameters),
  },
  {
    name: 'create_draft',
    description: createDraft.description,
    inputSchema: zodToJsonSchema(createDraft.parameters),
  },
  {
    name: 'mint_top_hat',
    description: mintTopHatOperation.description,
    inputSchema: zodToJsonSchema(mintTopHatOperation.parameters),
  },
  {
    name: 'create_hat',
    description: createHatOperation.description,
    inputSchema: zodToJsonSchema(createHatOperation.parameters),
  },
  {
    name: 'mint_hat',
    description: mintHatOperation.description,
    inputSchema: zodToJsonSchema(mintHatOperation.parameters),
  },
  {
    name: 'renounce_hat',
    description: renounceHatOperation.description,
    inputSchema: zodToJsonSchema(renounceHatOperation.parameters),
  },
  {
    name: 'transfer_hat',
    description: transferHatOperation.description,
    inputSchema: zodToJsonSchema(transferHatOperation.parameters),
  },
  {
    name: 'change_hat_eligibility',
    description: changeHatEligibilityOperation.description,
    inputSchema: zodToJsonSchema(changeHatEligibilityOperation.parameters),
  },
  {
    name: 'check_hat_status',
    description: checkHatStatusOperation.description,
    inputSchema: zodToJsonSchema(checkHatStatusOperation.parameters),
  },
  {
    name: 'set_hat_status',
    description: setHatStatusOperation.description,
    inputSchema: zodToJsonSchema(setHatStatusOperation.parameters),
  },
  {
    name: 'set_hat_wearer_status',
    description: setHatWearerStatusOperation.description,
    inputSchema: zodToJsonSchema(setHatWearerStatusOperation.parameters),
  },
  {
    name: 'check_hat_wearer_status',
    description: checkHatWearerStatusOperation.description,
    inputSchema: zodToJsonSchema(checkHatWearerStatusOperation.parameters),
  },
  {
    name: 'change_hat_max_supply',
    description: changeHatMaxSupplyOperation.description,
    inputSchema: zodToJsonSchema(changeHatMaxSupplyOperation.parameters),
  },
  {
    name: 'change_hat_toggle',
    description: changeHatToggleOperation.description,
    inputSchema: zodToJsonSchema(changeHatToggleOperation.parameters),
  },
  {
    name: 'change_hat_details',
    description: changeHatDetailsOperation.description,
    inputSchema: zodToJsonSchema(changeHatDetailsOperation.parameters),
  },
  {
    name: 'change_hat_image',
    description: changeHatImageOperation.description,
    inputSchema: zodToJsonSchema(changeHatImageOperation.parameters),
  },
] as const;

// Create server instance with configuration
const server = new Server(SERVER_CONFIG, {
  capabilities: {
    resources: {
      listChanged: true,
      subscribe: true,
    },
    tools: {
      get_tree: true,
      get_hat_by_id: true,
      get_wearer: true,
      get_eligibility: true,
      // temporarily unregister these while we improve the tools (TODO: re-enable BUILD-536)
      compare_draft: true,
      create_draft: true,
      mint_top_hat: true,
      create_hat: true,
      mint_hat: true,
      renounce_hat: true,
      change_hat_max_supply: true,
      change_hat_toggle: true,
      change_hat_image: true,
    },
  },
});

// Set up resource handlers
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: 'mcp://documentation/llms-full.txt',
        name: 'MCP Documentation',
        mimeType: 'text/plain',
      },
    ],
  };
});

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  debug('Resource handler called for URI:', request.params.uri);
  if (request.params.uri === 'mcp://documentation/llms-full.txt') {
    try {
      const content = await fs.promises.readFile(
        path.join(__dirname, 'resources', 'llms-full.txt'),
        'utf-8'
      );
      debug('Successfully read documentation file');
      return {
        contents: [
          {
            uri: request.params.uri,
            text: content,
            mimeType: 'text/plain',
          },
        ],
      };
    } catch (error) {
      debug('Error reading documentation file:', error);
      throw error;
    }
  }
  throw new Error(`Resource not found: ${request.params.uri}`);
});

// Set up tool handlers
server.setRequestHandler(ListToolsRequestSchema, async () => {
  debug('Number of tools registered:', TOOLS.length);
  TOOLS.forEach((tool) => {
    debug(`- ${tool.name}: ${tool.description}`);
  });

  return { tools: TOOLS };
});

server.setRequestHandler(
  CallToolRequestSchema,
  async (request: CallToolRequest) => {
    debug('Tool Call Request:', request.params.name);
    debug('Arguments:', JSON.stringify(request.params.arguments, null, 2));

    try {
      if (!request.params.arguments) {
        throw new Error('Arguments are required');
      }

      switch (request.params.name) {
        case 'get_tree': {
          const args = getTreeOperation.parameters.parse(
            request.params.arguments
          );
          return await getTreeOperation.execute(args);
        }
        case 'get_hat_by_id': {
          const args = getHatByIdOperation.parameters.parse(
            request.params.arguments
          );
          return await getHatByIdOperation.execute(args);
        }
        case 'get_wearer': {
          const args = getWearerOperation.parameters.parse(
            request.params.arguments
          );
          return await getWearerOperation.execute(args);
        }
        case 'get_eligibility': {
          const args = getEligibilityOperation.parameters.parse(
            request.params.arguments
          );
          return await getEligibilityOperation.execute(args);
        }
        // temporarily unregister these while we improve the tools (TODO: re-enable BUILD-536)
        case 'compare_draft': {
          const args = compareDraftOperation.parameters.parse(
            request.params.arguments
          );
          return await compareDraftOperation.execute(args);
        }
        case 'create_draft': {
          const args = createDraft.parameters.parse(request.params.arguments);
          return await createDraft.execute(args);
        }
        case 'mint_top_hat': {
          const args = mintTopHatOperation.parameters.parse(
            request.params.arguments
          );
          return await mintTopHatOperation.execute(args);
        }
        case 'create_hat': {
          const args = createHatOperation.parameters.parse(
            request.params.arguments
          );
          return await createHatOperation.execute(args);
        }
        case 'mint_hat': {
          const args = mintHatOperation.parameters.parse(
            request.params.arguments
          );
          return await mintHatOperation.execute(args);
        }
        case 'renounce_hat': {
          const args = renounceHatOperation.parameters.parse(
            request.params.arguments
          );
          return await renounceHatOperation.execute(args);
        }
        case 'transfer_hat': {
          const args = transferHatOperation.parameters.parse(
            request.params.arguments
          );
          return await transferHatOperation.execute(args);
        }
        case 'change_hat_eligibility': {
          const args = changeHatEligibilityOperation.parameters.parse(
            request.params.arguments
          );
          return await changeHatEligibilityOperation.execute(args);
        }
        case 'check_hat_status': {
          const args = checkHatStatusOperation.parameters.parse(
            request.params.arguments
          );
          return await checkHatStatusOperation.execute(args);
        }
        case 'set_hat_status': {
          const args = setHatStatusOperation.parameters.parse(
            request.params.arguments
          );
          return await setHatStatusOperation.execute(args);
        }
        case 'set_hat_wearer_status': {
          const args = setHatWearerStatusOperation.parameters.parse(
            request.params.arguments
          );
          return await setHatWearerStatusOperation.execute(args);
        }
        case 'check_hat_wearer_status': {
          const args = checkHatWearerStatusOperation.parameters.parse(
            request.params.arguments
          );
          return await checkHatWearerStatusOperation.execute(args);
        }
        case 'change_hat_max_supply': {
          const args = changeHatMaxSupplyOperation.parameters.parse(
            request.params.arguments
          );
          return await changeHatMaxSupplyOperation.execute(args);
        }
        case 'change_hat_toggle': {
          const args = changeHatToggleOperation.parameters.parse(
            request.params.arguments
          );
          return await changeHatToggleOperation.execute(args);
        }
        case 'change_hat_details': {
          const args = changeHatDetailsOperation.parameters.parse(
            request.params.arguments
          );
          return await changeHatDetailsOperation.execute(args);
        }
        case 'change_hat_image': {
          const args = changeHatImageOperation.parameters.parse(
            request.params.arguments
          );
          return await changeHatImageOperation.execute(args);
        }
        default:
          throw new Error(`Unknown tool: ${request.params.name}`);
      }
    } catch (error) {
      debug('Tool Call Error:', error);
      return createErrorResponse(
        error instanceof Error ? error : String(error)
      );
    }
  }
);

async function runStdioServer() {
  debug('Starting MCP Server with stdio transport');
  const transport = new StdioServerTransport();
  await server.connect(transport);
  debug('Server initialized and connected via stdio');
}

async function runHttpServer() {
  const app = express();
  const port = process.env.PORT || 3001;
  app.use(express.json());

  // Store transports for each session type
  const transports = {
    streamable: {} as Record<string, StreamableHTTPServerTransport>,
    sse: {} as Record<string, SSEServerTransport>,
  };

  // Basic request logging
  app.use((req: Request, res: Response, next) => {
    debug(`${req.method} ${req.path}`);
    next();
  });

  // Health check endpoint
  app.get('/health', (_req: Request, res: Response) => {
    res.json({
      status: 'ok',
      version: SERVER_CONFIG.version,
      name: SERVER_CONFIG.name,
    });
  });

  // Modern StreamableHTTP endpoint
  app.post('/mcp', async (req: Request, res: Response) => {
    // Check for existing session ID
    const sessionId = req.headers['mcp-session-id'] as string | undefined;
    let transport: StreamableHTTPServerTransport;

    if (sessionId && transports.streamable[sessionId]) {
      // Reuse existing transport
      transport = transports.streamable[sessionId];
    } else if (!sessionId && isInitializeRequest(req.body)) {
      // New initialization request
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        onsessioninitialized: (sessionId) => {
          debug(`New StreamableHTTP session initialized: ${sessionId}`);
          transports.streamable[sessionId] = transport;
        },
      });

      // Clean up transport when closed
      transport.onclose = () => {
        if (transport.sessionId) {
          debug(`Cleaning up StreamableHTTP session: ${transport.sessionId}`);
          delete transports.streamable[transport.sessionId];
        }
      };

      // Connect to the MCP server
      await server.connect(transport);
    } else {
      // Invalid request
      res.status(400).json({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: 'Bad Request: No valid session ID provided',
        },
        id: null,
      });
      return;
    }

    // Handle the request
    await transport.handleRequest(req, res, req.body);
  });

  // Legacy SSE endpoint for older clients
  app.get('/sse', async (req: Request, res: Response) => {
    debug('New SSE connection established');
    const transport = new SSEServerTransport('/messages', res);
    transports.sse[transport.sessionId] = transport;

    res.on('close', () => {
      debug(`Cleaning up SSE session: ${transport.sessionId}`);
      delete transports.sse[transport.sessionId];
    });

    await server.connect(transport);
  });

  // Legacy message endpoint for older clients
  app.post('/messages', async (req: Request, res: Response) => {
    const sessionId = req.query.sessionId as string;
    debug(`Handling POST message for session ${sessionId}`);
    const transport = transports.sse[sessionId];
    if (transport) {
      const startTime = Date.now();
      debug(`Starting message processing at ${startTime}`);
      try {
        await transport.handlePostMessage(req, res, req.body);
        const endTime = Date.now();
        debug(`Message processed in ${endTime - startTime}ms`);
      } catch (error) {
        debug('Error processing message:', error);
        res
          .status(500)
          .json({ error: 'Internal server error during message processing' });
      }
    } else {
      debug(`No active SSE connection found for session ${sessionId}`);
      res
        .status(400)
        .json({ error: 'No active SSE connection found for session' });
    }
  });

  // Reusable handler for GET and DELETE requests (StreamableHTTP)
  const handleSessionRequest = async (req: Request, res: Response) => {
    const sessionId = req.headers['mcp-session-id'] as string | undefined;
    if (!sessionId || !transports.streamable[sessionId]) {
      res.status(400).send('Invalid or missing session ID');
      return;
    }

    const transport = transports.streamable[sessionId];
    await transport.handleRequest(req, res);
  };

  // Handle GET requests for server-to-client notifications
  app.get('/mcp', handleSessionRequest);

  // Handle DELETE requests for session termination
  app.delete('/mcp', handleSessionRequest);

  app.listen(port, () => {
    debug(`HTTP server listening on port ${port}`);
    debug('Supported protocols: StreamableHTTP (/mcp) and SSE (/sse)');
  });
}

// Determine server mode from environment variable
const serverMode = process.env.SERVER_MODE || 'stdio';

if (serverMode === 'http') {
  runHttpServer().catch((error) => {
    console.error('Fatal HTTP server error:', error);
    process.exit(1);
  });
} else {
  runStdioServer().catch((error) => {
    console.error('Fatal stdio server error:', error);
    process.exit(1);
  });
}

export const operations = {
  // ... existing operations ...
  create_draft: createDraft,
  mint_top_hat: mintTopHatOperation,
  mint_hat: mintHatOperation,
  renounce_hat: renounceHatOperation,
  transfer_hat: transferHatOperation,
  change_hat_eligibility: changeHatEligibilityOperation,
  check_hat_status: checkHatStatusOperation,
  set_hat_status: setHatStatusOperation,
  set_hat_wearer_status: setHatWearerStatusOperation,
  check_hat_wearer_status: checkHatWearerStatusOperation,
  change_hat_max_supply: changeHatMaxSupplyOperation,
  change_hat_toggle: changeHatToggleOperation,
  change_hat_details: changeHatDetailsOperation,
  change_hat_image: changeHatImageOperation,
} as const;
