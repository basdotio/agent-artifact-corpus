/**
 * Chlorpromazine MCP Server - Modular Implementation (v0.3.0)
 * 
 * A secure, modular Model Context Protocol server that helps prevent
 * LLM agents from "hallucinating" by providing grounding tools and prompts.
 */

import 'dotenv/config';
import type { IncomingMessage, ServerResponse } from 'http';
import http from 'node:http';
import { randomUUID } from 'node:crypto';

// MCP SDK imports
import type { AuthInfo } from '@modelcontextprotocol/sdk/server/auth/types.js';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  StreamableHTTPServerTransport,
  type StreamableHTTPServerTransportOptions,
} from '@modelcontextprotocol/sdk/server/streamableHttp.js';

// Application imports
import { config } from './config/environment.js';
import { SERVER_INFO } from './config/constants.js';
import { logger } from './utils/logger.js';
import { registerAllHandlers } from './handlers/index.js';
import { rateLimiter } from './services/rate-limiter.js';
import { serpApiClient } from './services/serpapi.js';
import type { ChlorpromazineRequest, ChlorpromazineResult, ChlorpromazineNotification } from './types/mcp-types.js';
import type { HealthStatus } from './types/app-types.js';

/**
 * Create and configure the MCP server instance
 */
function createServer(): Server<ChlorpromazineRequest, ChlorpromazineNotification, ChlorpromazineResult> {
  const server = new Server<ChlorpromazineRequest, ChlorpromazineNotification, ChlorpromazineResult>(
    {
      name: SERVER_INFO.name,
      version: SERVER_INFO.version,
    },
    {
      capabilities: {
        experimental: {},
        tools: {},
        prompts: {},
      },
    }
  );

  // Register all MCP handlers
  registerAllHandlers(server);

  return server;
}

/**
 * Create health check response
 */
function createHealthResponse(): HealthStatus {
  const uptime = process.uptime();
  
  return {
    status: 'ok',
    timestamp: new Date().toISOString(),
    version: SERVER_INFO.version,
    uptime: Math.floor(uptime),
    checks: {
      serpApi: serpApiClient.isConfigured(),
      rateLimiter: true, // Rate limiter is always available
    }
  };
}

/**
 * Handle HTTP requests for the server
 */
async function handleHttpRequest(
  req: IncomingMessage,
  res: ServerResponse,
  transport: StreamableHTTPServerTransport
): Promise<void> {
  const startTime = Date.now();
  const method = req.method || 'UNKNOWN';
  const url = req.url || '/';
  
  try {
    // Handle health check endpoint
    if (url === '/healthz' && method === 'GET') {
      const health = createHealthResponse();
      res.writeHead(200, { 
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
      });
      res.end(JSON.stringify(health, null, 2));
      
      logger.request(method, url, { 
        status: 200, 
        durationMs: Date.now() - startTime,
        health: health.status
      });
      return;
    }

    // Handle CORS preflight
    if (method === 'OPTIONS') {
      res.writeHead(200, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '86400'
      });
      res.end();
      
      logger.request(method, url, { 
        status: 200, 
        durationMs: Date.now() - startTime,
        type: 'cors-preflight'
      });
      return;
    }

    // MCP requests are POST
    if (method === 'POST') {
      let body = '';
      
      req.on('data', chunk => {
        body += chunk.toString();
        
        // Prevent huge requests
        if (body.length > 1024 * 1024) { // 1MB limit
          res.writeHead(413, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Request too large' }));
          logger.security('Request too large', { 
            url, 
            bodyLength: body.length,
            durationMs: Date.now() - startTime
          });
          return;
        }
      });
      
      req.on('end', async () => {
        try {
          const parsedBody = JSON.parse(body);
          
          // Log the MCP request
          logger.request(method, url, {
            jsonrpc: parsedBody.jsonrpc,
            method: parsedBody.method,
            id: parsedBody.id,
            bodyLength: body.length
          });
          
          // Pass to the MCP transport
          await transport.handleRequest(
            req as IncomingMessage & { auth?: AuthInfo }, 
            res, 
            parsedBody
          );
          
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          res.writeHead(400, { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          });
          res.end(JSON.stringify({ 
            error: 'Invalid JSON RPC request', 
            details: errorMessage 
          }));
          
          logger.error('Invalid JSON RPC request', {
            url,
            error: errorMessage,
            bodyLength: body.length,
            durationMs: Date.now() - startTime
          });
        }
      });
      
      return;
    }

    // Handle SSE connections for established sessions
    if (method === 'GET' && req.headers.accept === 'text/event-stream') {
      logger.request(method, url, { type: 'sse-connection' });
      await transport.handleRequest(
        req as IncomingMessage & { auth?: AuthInfo }, 
        res
      );
      return;
    }

    // Method not allowed
    res.writeHead(405, { 
      'Content-Type': 'text/plain',
      'Access-Control-Allow-Origin': '*'
    });
    res.end('Method Not Allowed');
    
    logger.request(method, url, { 
      status: 405, 
      durationMs: Date.now() - startTime 
    });
    
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    
    if (!res.headersSent) {
      res.writeHead(500, { 
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      });
      res.end(JSON.stringify({ error: 'Internal server error' }));
    }
    
    logger.error('HTTP request handler error', {
      method,
      url,
      error: errorMessage,
      durationMs: Date.now() - startTime
    });
  }
}

/**
 * Main server startup function
 */
async function main(): Promise<void> {
  try {
    logger.info('Chlorpromazine MCP Server starting...', {
      version: SERVER_INFO.version,
      nodeEnv: config.nodeEnv,
      port: config.port
    });

    // Create MCP server
    const server = createServer();
    logger.info('MCP server instance created');

    // Configure transport
    const transportOptions: StreamableHTTPServerTransportOptions = {
      sessionIdGenerator: () => randomUUID(),
      onsessioninitialized: (sessionId: string) => {
        logger.info('MCP session initialized', { sessionId });
      },
    };

    const transport = new StreamableHTTPServerTransport(transportOptions);
    logger.info('StreamableHTTPServerTransport initialized');

    // Connect transport to server
    await server.connect(transport);
    logger.info('MCP transport connected to server');

    // Create HTTP server
    const httpServer = http.createServer((req, res) => {
      handleHttpRequest(req, res, transport).catch(error => {
        logger.error('Unhandled HTTP request error', {
          error: error instanceof Error ? error.message : 'Unknown error',
          url: req.url,
          method: req.method
        });
      });
    });

    // Start listening
    httpServer.listen(config.port, () => {
      logger.info('Chlorpromazine MCP Server ready', {
        port: config.port,
        environment: config.nodeEnv,
        capabilities: {
          tools: ['kill_trip', 'sober_thinking'],
          prompts: ['sober_thinking', 'fact_checked_answer', 'buzzkill'],
          sampling: true
        },
        endpoints: {
          health: `/healthz`,
          mcp: '/ (POST for JSON-RPC)',
          sse: '/ (GET with Accept: text/event-stream)'
        }
      });
    });

    // Graceful shutdown handling
    const gracefulShutdown = (signal: string) => {
      logger.info(`${signal} received: starting graceful shutdown`);
      
      httpServer.close((error) => {
        if (error) {
          logger.error('Error closing HTTP server', { error: error.message });
        } else {
          logger.info('HTTP server closed');
        }
        
        try {
          server.close();
          logger.info('MCP server closed');
        } catch (error) {
          logger.error('Error closing MCP server', {
            error: error instanceof Error ? error.message : 'Unknown error'
          });
        }
        
        process.exit(error ? 1 : 0);
      });
    };

    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));

  } catch (error) {
    logger.error('Failed to start server', {
      error: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined
    });
    process.exit(1);
  }
}

// Start the server
main().catch(error => {
  console.error('Unhandled startup error:', error);
  process.exit(1);
});