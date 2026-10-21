/**
 * Handler registry and exports
 */

import { registerToolHandlers } from './tools-handler.js';
import { registerPromptHandlers } from './prompts-handler.js';
import { registerMessageHandler } from './message-handler.js';
import type { Server } from '@modelcontextprotocol/sdk/server/index.js';
import type { ChlorpromazineRequest } from '../types/mcp-types.js';

/**
 * Register all MCP handlers with the server
 */
export function registerAllHandlers(
  server: Server<ChlorpromazineRequest, any, any>
): void {
  registerToolHandlers(server);
  registerPromptHandlers(server);
  registerMessageHandler(server);
}

// Re-export individual handler registration functions
export {
  registerToolHandlers,
  registerPromptHandlers,
  registerMessageHandler,
};