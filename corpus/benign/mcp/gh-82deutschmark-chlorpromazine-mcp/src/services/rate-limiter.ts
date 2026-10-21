/**
 * Rate limiting service to prevent abuse
 */

import { logger } from '../utils/logger.js';
import type { RateLimitConfig, RateLimitInfo } from '../types/app-types.js';
import { RATE_LIMITS } from '../config/constants.js';

export class RateLimiter {
  private requests = new Map<string, RateLimitInfo>();
  
  constructor(private defaultConfig: RateLimitConfig = {
    maxRequests: RATE_LIMITS.DEFAULT_MAX_REQUESTS,
    windowMs: RATE_LIMITS.DEFAULT_WINDOW_MS
  }) {}
  
  /**
   * Check if a request should be allowed based on rate limits
   */
  public checkLimit(
    identifier: string, 
    config: RateLimitConfig = this.defaultConfig
  ): boolean {
    const now = Date.now();
    const windowStart = now - config.windowMs;
    
    // Get or create request history for this identifier
    let info = this.requests.get(identifier);
    if (!info) {
      info = {
        identifier,
        requests: [],
        lastRequest: 0
      };
      this.requests.set(identifier, info);
    }
    
    // Filter out requests outside the current window
    info.requests = info.requests.filter(time => time > windowStart);
    
    // Check if we've exceeded the limit
    if (info.requests.length >= config.maxRequests) {
      logger.rateLimit(identifier, config.maxRequests, config.windowMs);
      return false;
    }
    
    // Record this request
    info.requests.push(now);
    info.lastRequest = now;
    
    return true;
  }
  
  /**
   * Get current request count for an identifier
   */
  public getRequestCount(identifier: string, windowMs: number = this.defaultConfig.windowMs): number {
    const info = this.requests.get(identifier);
    if (!info) return 0;
    
    const windowStart = Date.now() - windowMs;
    return info.requests.filter(time => time > windowStart).length;
  }
  
  /**
   * Clear old entries to prevent memory leaks
   */
  public cleanup(): void {
    const cutoff = Date.now() - (this.defaultConfig.windowMs * 2); // Keep double the window
    
    for (const [identifier, info] of this.requests.entries()) {
      if (info.lastRequest < cutoff) {
        this.requests.delete(identifier);
      }
    }
    
    logger.debug(`Rate limiter cleanup: ${this.requests.size} identifiers remaining`);
  }
  
  /**
   * Reset rate limit for a specific identifier (for testing/admin)
   */
  public reset(identifier: string): void {
    this.requests.delete(identifier);
    logger.debug(`Rate limit reset for identifier: ${identifier}`);
  }
  
  /**
   * Get statistics about current rate limiting
   */
  public getStats(): { totalIdentifiers: number; totalRequests: number } {
    let totalRequests = 0;
    for (const info of this.requests.values()) {
      totalRequests += info.requests.length;
    }
    
    return {
      totalIdentifiers: this.requests.size,
      totalRequests
    };
  }
}

// Create singleton instance
export const rateLimiter = new RateLimiter();

// Cleanup interval to prevent memory leaks
setInterval(() => {
  rateLimiter.cleanup();
}, RATE_LIMITS.DEFAULT_WINDOW_MS); // Cleanup every window period