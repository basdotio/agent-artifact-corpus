/**
 * MCP Tools handlers (tools/list and tools/call)
 */

import { 
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import type { 
  ListToolsResult, 
  CallToolResult,
  ChlorpromazineRequest
} from '../types/mcp-types.js';
import { toolDefinitions, getToolExecutor } from '../tools/index.js';
import { generateRateLimitId, sanitizeErrorMessage } from '../utils/security.js';
import { logger } from '../utils/logger.js';
import { config } from '../config/environment.js';
import type { Server } from '@modelcontextprotocol/sdk/server/index.js';

export function registerToolHandlers(
  server: Server<ChlorpromazineRequest, any, any>
): void {
  // Handler for tools/list
  server.setRequestHandler(
    ListToolsRequestSchema,
    async (request): Promise<ListToolsResult> => {
      logger.info('Handling tools/list request', { 
        params: request.params 
      });
      
      return {
        tools: toolDefinitions.map(tool => ({
          name: tool.name,
          description: tool.description,
          inputSchema: tool.inputSchema,
          outputSchema: tool.outputSchema,
        }))
      };
    }
  );

  // Handler for tools/call
  server.setRequestHandler(
    CallToolRequestSchema,
    async (request, extra): Promise<CallToolResult> => {
      const params = request.params;
      const startTime = Date.now();
      
      // Generate rate limit identifier  
      const rateLimitId = generateRateLimitId({ headers: {} });
      
      logger.info('Handling tools/call request', {
        toolName: params.name,
        rateLimitId
      });
      
      try {
        // Get tool executor
        const executor = getToolExecutor(params.name);
        if (!executor) {
          const errorMsg = `Tool '${params.name}' not found`;
          logger.warn(errorMsg, { availableTools: Array.from(toolDefinitions.map(t => t.name)) });
          
          return {
            isError: true,
            content: [{ type: 'text', text: errorMsg }],
          };
        }
        
        // Execute tool
        const result = await executor(params, { rateLimitId });
        const duration = Date.now() - startTime;
        
        logger.info('Tool execution completed', {
          toolName: params.name,
          success: !result.isError,
          durationMs: duration
        });
        
        return result;
        
      } catch (error) {
        const duration = Date.now() - startTime;
        const errorMessage = sanitizeErrorMessage(error, config.isProduction);
        
        logger.error('Tool execution failed', {
          toolName: params.name,
          error: errorMessage,
          durationMs: duration
        });
        
        return {
          isError: true,
          content: [{ type: 'text', text: errorMessage }],
        };
      }
    }
  );
}