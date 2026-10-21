/**
 * MCP Prompts handlers (prompts/list and prompts/get)
 */

import { 
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import type { 
  ListPromptsResult, 
  GetPromptResult,
  ChlorpromazineRequest
} from '../types/mcp-types.js';
import { promptDefinitions, getPromptHandler } from '../prompts/index.js';
import { sanitizeErrorMessage } from '../utils/security.js';
import { logger } from '../utils/logger.js';
import { config } from '../config/environment.js';
import type { Server } from '@modelcontextprotocol/sdk/server/index.js';

export function registerPromptHandlers(
  server: Server<ChlorpromazineRequest, any, any>
): void {
  // Handler for prompts/list
  server.setRequestHandler(
    ListPromptsRequestSchema,
    async (request): Promise<ListPromptsResult> => {
      logger.info('Handling prompts/list request', { 
        params: request.params 
      });
      
      return {
        prompts: promptDefinitions.map(prompt => ({
          name: prompt.name,
          description: prompt.description,
          arguments: prompt.arguments,
        }))
      };
    }
  );

  // Handler for prompts/get
  server.setRequestHandler(
    GetPromptRequestSchema,
    async (request): Promise<GetPromptResult> => {
      const params = request.params;
      const startTime = Date.now();
      
      logger.info('Handling prompts/get request', {
        promptName: params.name,
        hasArguments: !!params.arguments && Object.keys(params.arguments).length > 0
      });
      
      try {
        // Get prompt handler
        const handler = getPromptHandler(params.name);
        if (!handler) {
          const errorMsg = `Prompt '${params.name}' not found`;
          logger.warn(errorMsg, { availablePrompts: promptDefinitions.map(p => p.name) });
          throw new Error(errorMsg);
        }
        
        // Render prompt with provided arguments
        const result = await handler.render(params.arguments || {});
        const duration = Date.now() - startTime;
        
        logger.info('Prompt rendering completed', {
          promptName: params.name,
          messagesCount: result.messages.length,
          durationMs: duration
        });
        
        return result;
        
      } catch (error) {
        const duration = Date.now() - startTime;
        const errorMessage = sanitizeErrorMessage(error, config.isProduction);
        
        logger.error('Prompt rendering failed', {
          promptName: params.name,
          error: errorMessage,
          durationMs: duration
        });
        
        // For prompt errors, we still return a valid response but with error content
        return {
          messages: [{
            role: 'assistant',
            content: {
              type: 'text',
              text: `Error rendering prompt '${params.name}': ${errorMessage}`
            }
          }]
        };
      }
    }
  );
}