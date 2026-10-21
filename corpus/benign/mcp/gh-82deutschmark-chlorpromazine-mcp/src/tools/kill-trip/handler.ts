/**
 * Kill Trip tool implementation
 */

import { serpApiClient } from '../../services/serpapi.js';
import { validateToolInput, generateRateLimitId, sanitizeErrorMessage } from '../../utils/security.js';
import { logger } from '../../utils/logger.js';
import { config } from '../../config/environment.js';
import type { ToolCallParams, ToolCallResult } from '../../types/mcp-types.js';
import type { KillTripArgs } from '../../types/tool-types.js';
import { killTripArgsValidator } from './schema.js';

export async function executeKillTrip(
  params: ToolCallParams,
  context: { rateLimitId: string }
): Promise<ToolCallResult> {
  const startTime = Date.now();
  
  try {
    // Validate input
    const args = validateToolInput(killTripArgsValidator, params.arguments) as KillTripArgs;
    
    logger.info('Kill trip tool execution started', { 
      query: args.query,
      rateLimitId: context.rateLimitId
    });
    
    // Check if SerpAPI is configured
    if (!serpApiClient.isConfigured()) {
      const errorMsg = 'SerpAPI not configured. Please set SERPAPI_KEY environment variable.';
      logger.warn(errorMsg);
      
      return {
        isError: true,
        content: [{ type: 'text', text: errorMsg }],
      };
    }
    
    // Perform search
    const searchResult = await serpApiClient.search(args.query, context.rateLimitId);
    const duration = Date.now() - startTime;
    
    logger.info('Kill trip tool execution completed', {
      durationMs: duration,
      hasResult: !!searchResult
    });
    
    return {
      isError: false,
      content: [{ type: 'text', text: searchResult }],
      structuredContent: { result: searchResult },
    };
    
  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = sanitizeErrorMessage(error, config.isProduction);
    
    logger.error('Kill trip tool execution failed', {
      error: errorMessage,
      durationMs: duration
    });
    
    return {
      isError: true,
      content: [{ type: 'text', text: errorMessage }],
    };
  }
}