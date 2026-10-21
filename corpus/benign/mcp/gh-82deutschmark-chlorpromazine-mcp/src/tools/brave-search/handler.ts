/**
 * Brave Search tool handler
 */

import { braveSearchArgsValidator, braveSearchResultValidator } from './schema.js';
import type { BraveSearchArgs, BraveSearchResult } from '../../types/tool-types.js';
import type { ToolCallResult } from '../../types/mcp-types.js';
import { logger } from '../../utils/logger.js';
import { config } from '../../config/environment.js';

/**
 * Execute Brave Search
 */
export async function executeBraveSearch(
  params: unknown,
  context: { rateLimitId: string }
): Promise<ToolCallResult> {
  try {
    // Validate input
    const args = braveSearchArgsValidator.parse(params);
    const count = args.count || 5;
    
    // Check if API key is configured
    if (!config.braveSearchApiKey) {
      logger.warn('Brave Search API key not configured', { context });
      return {
        isError: true,
        content: [{ 
          type: 'text', 
          text: 'Brave Search API key not configured. Set BRAVE_SEARCH_API_KEY environment variable.'
        }],
      };
    }
    
    // Call Brave Search API
    logger.info('Performing Brave Search', { 
      query: args.query, 
      count,
      context 
    });
    
    const response = await fetch(`https://api.search.brave.com/res/v1/web/search`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'X-Subscription-Token': config.braveSearchApiKey,
      },
      signal: AbortSignal.timeout(5000),
    });
    
    if (!response.ok) {
      const error = await response.text();
      logger.error('Brave Search API error', { 
        status: response.status, 
        error,
        context 
      });
      return {
        isError: true,
        content: [{ 
          type: 'text', 
          text: `Brave Search API error: ${response.status}` 
        }],
      };
    }
    
    interface BraveResponse {
      web?: Array<{
        title?: string;
        url?: string;
        description?: string;
      }>;
    }

    const data = (await response.json()) as BraveResponse;
    
    // Process results
    const results = (data.web || [])
      .slice(0, count)
      .map(item => ({
        title: item.title || 'Untitled',
        url: item.url || '',
        snippet: item.description || ''
      }));
    
    // Validate result
    const result: BraveSearchResult = {
      results,
      query: args.query,
      resultCount: results.length
    };
    
    braveSearchResultValidator.parse(result);
    
    logger.info('Brave Search completed', { 
      resultCount: results.length,
      context 
    });
    
    return {
      isError: false,
      content: [{
        type: 'text',
        text: JSON.stringify(result, null, 2)
      }],
    };
    
  } catch (error) {
    const errorMessage = error instanceof Error 
      ? error.message 
      : 'Unknown error during Brave Search';
    
    logger.error('Brave Search execution failed', { 
      error: errorMessage,
      context
    });
    
    return {
      isError: true,
      content: [{ 
        type: 'text', 
        text: `Brave Search failed: ${errorMessage}` 
      }],
    };
  }
}
