/**
 * Secure SerpAPI client with rate limiting and timeout protection
 */

import { config } from '../config/environment.js';
import { logger } from '../utils/logger.js';
import { sanitizeSearchQuery } from '../utils/security.js';
import { rateLimiter } from './rate-limiter.js';
import type { SerpApiResponse, SerpApiResult } from '../types/app-types.js';
import { ToolExecutionError } from '../types/app-types.js';
import { RATE_LIMITS, TIMEOUTS } from '../config/constants.js';

export class SerpApiClient {
  private readonly baseUrl = 'https://serpapi.com/search.json';
  
  /**
   * Perform a search with security and rate limiting
   */
  async search(query: string, rateLimitId: string): Promise<string> {
    const startTime = Date.now();
    
    try {
      // Rate limiting check
      if (!rateLimiter.checkLimit(rateLimitId, {
        maxRequests: RATE_LIMITS.SERPAPI_MAX_REQUESTS,
        windowMs: RATE_LIMITS.SERPAPI_WINDOW_MS
      })) {
        throw new ToolExecutionError('kill_trip', 'Rate limit exceeded for SerpAPI requests');
      }
      
      // Input sanitization
      const sanitizedQuery = sanitizeSearchQuery(query);
      logger.debug('Sanitized search query', { original: query, sanitized: sanitizedQuery });
      
      // Build search URL with site filter
      const sitePart = `site:(${config.searchSites.join(' OR ')})`;
      const searchUrl = new URL(this.baseUrl);
      searchUrl.searchParams.set('engine', 'google');
      searchUrl.searchParams.set('q', `${sitePart} ${sanitizedQuery}`);
      searchUrl.searchParams.set('api_key', config.serpApiKey);
      
      logger.info('SerpAPI search initiated', { 
        query: sanitizedQuery, 
        sites: config.searchSites.length 
      });
      
      // Make request with timeout
      const response = await fetch(searchUrl.toString(), {
        signal: AbortSignal.timeout(TIMEOUTS.SERPAPI_TIMEOUT_MS),
        headers: {
          'User-Agent': 'ChlorpromazineMCP/0.3.0',
          'Accept': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new ToolExecutionError(
          'kill_trip', 
          `SerpAPI request failed with status ${response.status}: ${response.statusText}`
        );
      }
      
      const data = await response.json() as SerpApiResponse;
      const duration = Date.now() - startTime;
      
      // Check for API errors
      if (data.error) {
        throw new ToolExecutionError('kill_trip', `SerpAPI error: ${data.error}`);
      }
      
      // Extract first result
      const result = this.extractBestResult(data);
      
      logger.toolCall('kill_trip', true, duration);
      logger.info('SerpAPI search completed', { 
        query: sanitizedQuery, 
        durationMs: duration,
        hasResult: !!result
      });
      
      return result;
      
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.toolCall('kill_trip', false, duration);
      
      if (error instanceof ToolExecutionError) {
        throw error;
      }
      
      if (error instanceof Error) {
        if (error.name === 'TimeoutError') {
          throw new ToolExecutionError('kill_trip', 'SerpAPI request timed out');
        }
        
        if (error.name === 'AbortError') {
          throw new ToolExecutionError('kill_trip', 'SerpAPI request was aborted');
        }
        
        throw new ToolExecutionError('kill_trip', `SerpAPI request failed: ${error.message}`);
      }
      
      throw new ToolExecutionError('kill_trip', 'Unknown error during SerpAPI request');
    }
  }
  
  /**
   * Extract the best search result from SerpAPI response
   */
  private extractBestResult(data: SerpApiResponse): string {
    const results = data.organic_results;
    
    if (!results || results.length === 0) {
      return 'No relevant documentation found. The query may be too specific or the information might not be available in the configured documentation sites.';
    }
    
    const topResult = results[0];
    
    // Validate result structure
    if (!topResult.title || !topResult.snippet) {
      return 'Search completed but no detailed results were available.';
    }
    
    // Format the result nicely
    const formattedResult = [
      `**${topResult.title}**`,
      '',
      topResult.snippet,
      '',
      `📖 Source: ${topResult.link}`
    ].join('\n');
    
    return formattedResult;
  }
  
  /**
   * Check if SerpAPI is properly configured
   */
  isConfigured(): boolean {
    return !!config.serpApiKey && config.serpApiKey !== 'test_key';
  }
  
  /**
   * Get current rate limit status for an identifier
   */
  getRateLimitStatus(rateLimitId: string): { requests: number; limit: number; resetTime: number } {
    const requests = rateLimiter.getRequestCount(rateLimitId, RATE_LIMITS.SERPAPI_WINDOW_MS);
    const resetTime = Date.now() + RATE_LIMITS.SERPAPI_WINDOW_MS;
    
    return {
      requests,
      limit: RATE_LIMITS.SERPAPI_MAX_REQUESTS,
      resetTime
    };
  }
}

// Export singleton instance
export const serpApiClient = new SerpApiClient();