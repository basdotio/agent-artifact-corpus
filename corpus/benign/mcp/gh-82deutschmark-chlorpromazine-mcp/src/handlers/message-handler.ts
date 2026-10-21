/**
 * MCP Message handler (sampling/createMessage)
 */

import { CreateMessageRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import type { 
  CreateMessageResult,
  ChlorpromazineRequest,
  MCPMessage,
  TextContent
} from '../types/mcp-types.js';
import { sanitizeErrorMessage } from '../utils/security.js';
import { logger } from '../utils/logger.js';
import { config } from '../config/environment.js';
import { DEFAULT_ASSISTANT_MODEL } from '../config/constants.js';
import type { Server } from '@modelcontextprotocol/sdk/server/index.js';

export function registerMessageHandler(
  server: Server<ChlorpromazineRequest, any, any>
): void {
  // Handler for sampling/createMessage
  server.setRequestHandler(
    CreateMessageRequestSchema,
    async (request): Promise<CreateMessageResult> => {
      const params = request.params;
      const startTime = Date.now();
      
      logger.info('Handling sampling/createMessage request', {
        messagesCount: params.messages?.length || 0
      });
      
      try {
        if (!params.messages || params.messages.length === 0) {
          throw new Error('No messages provided in sampling/createMessage request');
        }

        // Find the last user message
        const lastUserMessage = params.messages
          .filter((msg: MCPMessage) => msg.role === 'user')
          .pop();

        let responseText = "I'm sorry, I didn't understand that.";

        if (lastUserMessage && lastUserMessage.content && Array.isArray(lastUserMessage.content)) {
          // Content is now an array of content parts
          const textContent = lastUserMessage.content.find(c => c.type === 'text');
          
          if (textContent && textContent.type === 'text') {
            // Defensive type guard for safety
            if (typeof textContent.text !== 'string') {
              throw new Error('Invalid message: text content must be a string');
            }
            
            const userQuery = textContent.text.toLowerCase();
            
            // Simple response logic based on content
            if (userQuery.includes('hello') || userQuery.includes('hi')) {
              responseText = `Hello! I'm the Chlorpromazine MCP server. I can help you stop "tripping" and get grounded in reality. Use the tools available to fact-check information and stay grounded in your project.`;
            } else if (userQuery.includes('how are you')) {
              responseText = `I'm functioning well and ready to help you avoid hallucinations and stay grounded in facts. My tools can help you verify information and understand your current project state.`;
            } else {
              // Default response that explains the server's purpose
              responseText = `I received your message about "${textContent.text}". As the Chlorpromazine MCP server, I'm designed to help you stay grounded in reality and avoid AI hallucinations.

Available tools:
- **kill_trip**: Search official documentation when you need to verify information
- **sober_thinking**: Read current project files to understand the actual state

Available prompts:
- **sober_thinking**: Ground yourself in project reality before answering
- **fact_checked_answer**: Verify answers against official documentation  
- **buzzkill**: Systematic debugging with reality-checking

How can I help you stay grounded in facts today?`;
            }
          }
        }

        const duration = Date.now() - startTime;
        
        logger.info('Message creation completed', {
          responseLength: responseText.length,
          durationMs: duration
        });

        return {
          model: DEFAULT_ASSISTANT_MODEL,
          role: 'assistant',
          content: { type: 'text', text: responseText } as TextContent,
        };
        
      } catch (error) {
        const duration = Date.now() - startTime;
        const errorMessage = sanitizeErrorMessage(error, config.isProduction);
        
        logger.error('Message creation failed', {
          error: errorMessage,
          durationMs: duration
        });
        
        // Return a valid response even for errors
        return {
          model: DEFAULT_ASSISTANT_MODEL,
          role: 'assistant',
          content: { 
            type: 'text', 
            text: `I encountered an error: ${errorMessage}. Please try again or use the available tools to get grounded information.`
          } as TextContent,
        };
      }
    }
  );
}