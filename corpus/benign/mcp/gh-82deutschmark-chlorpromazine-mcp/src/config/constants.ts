/**
 * Application constants and default values
 */

export const DEFAULT_SITES = [
  'stackoverflow.com',
  'stackexchange.com',
  'reddit.com',
  'github.com',
  'docs.python.org',
  'docs.oracle.com',
  'learn.microsoft.com',
  'developer.mozilla.org',
  'kotlinlang.org',
  'go.dev',
  'rust-lang.org',
  'docs.ruby-lang.org',
  'nodejs.org',
  'pypi.org',
  'maven.apache.org',
  'platform.openai.com',
  'docs.anthropic.com',
  'ai.google.dev',
  'platform.openai.com/docs',
  'platform.openai.com/api-reference',
  'docs.anthropic.com/claude',
  'ai.google.dev/gemini',
  'modelcontextprotocol.io',
  'modelcontextprotocol.io/tutorials',
  'modelcontextprotocol.io/docs',
  'modelcontextprotocol.io/examples'
] as const;

export const SERVER_INFO = {
  name: 'ChlorpromazineMCP',
  version: '0.3.0',
  description: 'Chlorpromazine Model Context Protocol (MCP) Server'
} as const;

export const DEFAULT_ASSISTANT_MODEL = 'chlorpromazine-mcp/default';

export const RATE_LIMITS = {
  DEFAULT_MAX_REQUESTS: 10,
  DEFAULT_WINDOW_MS: 60000,
  SERPAPI_MAX_REQUESTS: 5,
  SERPAPI_WINDOW_MS: 60000
} as const;

export const TIMEOUTS = {
  SERPAPI_TIMEOUT_MS: 5000,
  FILE_READ_TIMEOUT_MS: 2000
} as const;

export const SECURITY = {
  MAX_QUERY_LENGTH: 200,
  MAX_FILE_SIZE: 1024 * 1024, // 1MB
  ALLOWED_QUERY_CHARS: /^[\w\s\-_.]+$/
} as const;