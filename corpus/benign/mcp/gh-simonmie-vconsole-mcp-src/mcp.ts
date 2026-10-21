import { McpServer } from '@modelcontextprotocol/server';
import * as z from 'zod/v4';
import type { VConsoleBridge } from './bridge.js';

const readOnlyAnnotations = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
};

const executeAnnotations = {
  readOnlyHint: false,
  destructiveHint: true,
  idempotentHint: false,
  openWorldHint: true,
};

function result(value: unknown) {
  return {
    content: [{ type: 'text' as const, text: JSON.stringify(value, null, 2) }],
  };
}

function failure(error: unknown) {
  return {
    content: [{
      type: 'text' as const,
      text: error instanceof Error ? error.message : String(error),
    }],
    isError: true,
  };
}

export function createMCPServer(bridge: VConsoleBridge): McpServer {
  const server = new McpServer({
    name: 'vconsole-mcp',
    version: '0.1.0',
  }, {
    instructions: 'Use list_pages to identify connected mobile H5 pages. Read console output with get_console_logs and captured Fetch/XHR traffic with get_network_requests; these read tools may omit pageId when only one page is connected. execute_javascript requires pageId, may mutate page state, storage, or send network requests, and runs only after the mobile user authorizes it in vConsole.',
  });

  server.registerTool(
    'list_pages',
    {
      description: 'List mobile H5 pages currently connected through vConsole.',
      inputSchema: z.object({}),
      annotations: readOnlyAnnotations,
    },
    async () => result(bridge.listPages()),
  );

  server.registerTool(
    'get_console_logs',
    {
      description: 'Read the latest console logs captured by vConsole on a connected mobile H5 page.',
      inputSchema: z.object({
        pageId: z.string().optional(),
        level: z.enum(['log', 'info', 'debug', 'warn', 'error']).optional(),
        pluginId: z.string().optional().default('default'),
        limit: z.number().int().min(1).max(100).optional().default(50),
      }),
      annotations: readOnlyAnnotations,
    },
    async ({ pageId, level, pluginId, limit }) => {
      try {
        return result(await bridge.request(pageId, 'console.list', { level, pluginId, limit }));
      } catch (error) {
        return failure(error);
      }
    },
  );

  server.registerTool(
    'get_network_requests',
    {
      description: 'Read the latest network requests captured by vConsole on a connected mobile H5 page.',
      inputSchema: z.object({
        pageId: z.string().optional(),
        failedOnly: z.boolean().optional().default(false),
        urlIncludes: z.string().optional(),
        includeBody: z.boolean().optional().default(false),
        limit: z.number().int().min(1).max(100).optional().default(50),
      }),
      annotations: readOnlyAnnotations,
    },
    async ({ pageId, failedOnly, urlIncludes, includeBody, limit }) => {
      try {
        return result(await bridge.request(pageId, 'network.list', {
          failedOnly,
          urlIncludes,
          includeBody,
          limit,
        }));
      } catch (error) {
        return failure(error);
      }
    },
  );

  server.registerTool(
    'execute_javascript',
    {
      description: 'Execute JavaScript in a connected mobile H5 page after explicit authorization in vConsole. Arbitrary code may mutate page state or storage, expose sensitive data, and send network requests.',
      inputSchema: z.object({
        pageId: z.string().min(1),
        code: z.string().min(1).max(100_000),
        timeout: z.number().int().min(100).max(30_000).optional().default(8_000),
      }),
      annotations: executeAnnotations,
    },
    async ({ pageId, code, timeout }) => {
      try {
        return result(await bridge.request(pageId, 'runtime.evaluate', { code }, timeout));
      } catch (error) {
        return failure(error);
      }
    },
  );

  return server;
}
