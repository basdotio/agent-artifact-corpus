/**
 * Structured logging utility
 */

import { config } from '../config/environment.js';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogContext {
  [key: string]: unknown;
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: LogContext;
}

class Logger {
  private shouldLog(level: LogLevel): boolean {
    if (config.isTest) {
      return false; // Suppress logs during testing
    }
    
    if (config.isProduction && level === 'debug') {
      return false; // No debug logs in production
    }
    
    return true;
  }
  
  private formatLogEntry(level: LogLevel, message: string, context?: LogContext): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      ...(context && Object.keys(context).length > 0 && { context })
    };
  }
  
  private output(entry: LogEntry): void {
    const logString = JSON.stringify(entry);
    
    if (entry.level === 'error') {
      console.error(logString);
    } else if (entry.level === 'warn') {
      console.warn(logString);
    } else {
      console.log(logString);
    }
  }
  
  debug(message: string, context?: LogContext): void {
    if (this.shouldLog('debug')) {
      this.output(this.formatLogEntry('debug', message, context));
    }
  }
  
  info(message: string, context?: LogContext): void {
    if (this.shouldLog('info')) {
      this.output(this.formatLogEntry('info', message, context));
    }
  }
  
  warn(message: string, context?: LogContext): void {
    if (this.shouldLog('warn')) {
      this.output(this.formatLogEntry('warn', message, context));
    }
  }
  
  error(message: string, context?: LogContext): void {
    if (this.shouldLog('error')) {
      this.output(this.formatLogEntry('error', message, context));
    }
  }
  
  /**
   * Log HTTP request details
   */
  request(method: string, url: string, context?: LogContext): void {
    this.info(`${method} ${url}`, context);
  }
  
  /**
   * Log tool execution
   */
  toolCall(toolName: string, success: boolean, duration?: number): void {
    this.info(`Tool ${toolName} ${success ? 'succeeded' : 'failed'}`, {
      tool: toolName,
      success,
      ...(duration && { durationMs: duration })
    });
  }
  
  /**
   * Log security events
   */
  security(event: string, context?: LogContext): void {
    this.warn(`Security event: ${event}`, context);
  }
  
  /**
   * Log rate limiting events
   */
  rateLimit(identifier: string, limit: number, window: number): void {
    this.warn('Rate limit exceeded', {
      identifier,
      limit,
      windowMs: window
    });
  }
}

// Export singleton instance
export const logger = new Logger();

// Legacy compatibility function for existing code
export function log(level: LogLevel, message: string, meta: LogContext = {}): void {
  logger[level](message, meta);
}