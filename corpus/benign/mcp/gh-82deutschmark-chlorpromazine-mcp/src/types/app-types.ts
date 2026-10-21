/**
 * Application-specific type definitions
 */

// Error types
export class ChlorpromazineError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = 'ChlorpromazineError';
  }
}

export class ToolExecutionError extends ChlorpromazineError {
  constructor(toolName: string, message: string, details?: unknown) {
    super(`Tool '${toolName}' execution failed: ${message}`, 'TOOL_EXECUTION_ERROR', details);
    this.name = 'ToolExecutionError';
  }
}

export class ConfigurationError extends ChlorpromazineError {
  constructor(message: string, details?: unknown) {
    super(message, 'CONFIGURATION_ERROR', details);
    this.name = 'ConfigurationError';
  }
}

// Request context for logging and security
export interface RequestContext {
  id: string;
  method: string;
  timestamp: Date;
  rateLimitId: string;
}

// Tool execution context
export interface ToolExecutionContext {
  toolName: string;
  toolRunId: string;
  startTime: Date;
  requestContext: RequestContext;
}

// Rate limiting types
export interface RateLimitConfig {
  maxRequests: number;
  windowMs: number;
}

export interface RateLimitInfo {
  identifier: string;
  requests: number[];
  lastRequest: number;
}

// SerpAPI response types
export interface SerpApiResult {
  title: string;
  snippet: string;
  link: string;
}

export interface SerpApiResponse {
  organic_results?: SerpApiResult[];
  error?: string;
}

// File reading types
export interface FileContent {
  filename: string;
  content: string;
  size: number;
  lastModified?: Date;
}

// Server health check
export interface HealthStatus {
  status: 'ok' | 'error';
  timestamp: string;
  version: string;
  uptime: number;
  checks?: Record<string, boolean>;
}

// Prompt argument types
export interface SoberThinkingPromptArgs {
  QUESTION_TEXT: string;
}

export interface FactCheckedAnswerPromptArgs {
  USER_QUERY: string;
}

export interface BuzzkillPromptArgs {
  ISSUE_DESCRIPTION: string;
  RECENT_CHANGES?: string;
  EXPECTED_BEHAVIOR?: string;
  ACTUAL_BEHAVIOR?: string;
}