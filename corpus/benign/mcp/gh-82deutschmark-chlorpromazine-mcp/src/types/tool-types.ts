/**
 * Tool-specific type definitions and schemas
 */

import { z } from 'zod';

// Kill Trip Tool Types
export const KillTripArgsSchema = z.object({
  query: z.string().min(1, 'Query cannot be empty').max(200, 'Query too long').describe('The search query for SerpAPI'),
});

export type KillTripArgs = z.infer<typeof KillTripArgsSchema>;

export const KillTripResultSchema = z.object({
  result: z.string().describe('Search result from SerpAPI'),
});

export type KillTripResult = z.infer<typeof KillTripResultSchema>;

// Sober Thinking Tool Types
export const SoberThinkingArgsSchema = z.object({
  // No arguments required for sober thinking tool
});

export type SoberThinkingArgs = z.infer<typeof SoberThinkingArgsSchema>;

export const SoberThinkingResultSchema = z.object({
  content: z.string().describe('Combined file contents from project'),
});

export type SoberThinkingResult = z.infer<typeof SoberThinkingResultSchema>;

// JSON Schema definitions for MCP tool registration
export const KillTripArgsJsonSchema = {
  type: 'object' as const,
  properties: {
    query: { 
      type: 'string' as const, 
      description: 'The search query for SerpAPI',
      minLength: 1,
      maxLength: 200
    },
  },
  required: ['query'],
};

export const KillTripResultJsonSchema = {
  type: 'object' as const,
  properties: {
    result: { 
      type: 'string' as const, 
      description: 'Search result from SerpAPI' 
    },
  },
  required: ['result'],
};

export const SoberThinkingArgsJsonSchema = {
  type: 'object' as const,
  properties: {},
  required: [] as string[],
};

export const SoberThinkingResultJsonSchema = {
  type: 'object' as const,
  properties: {
    content: { 
      type: 'string' as const, 
      description: 'Combined file contents from project' 
    },
  },
  required: ['content'],
};

// Brave Search Tool Types
export const BraveSearchArgsSchema = z.object({
  query: z.string().min(1, 'Query cannot be empty').max(500, 'Query too long').describe('Search query string'),
  count: z.number().int().min(1).max(10).default(5).describe('Number of results to return'),
});

export type BraveSearchArgs = z.infer<typeof BraveSearchArgsSchema>;

export const BraveSearchResultSchema = z.object({
  results: z.array(z.object({
    title: z.string(),
    url: z.string(),
    snippet: z.string(),
  })).describe('Array of search results'),
  query: z.string().describe('The search query used'),
  resultCount: z.number().describe('Number of results returned'),
});

export type BraveSearchResult = z.infer<typeof BraveSearchResultSchema>;

// JSON Schema definitions for MCP tool registration
export const BraveSearchArgsJsonSchema = {
  type: 'object' as const,
  properties: {
    query: { 
      type: 'string' as const, 
      description: 'Search query string (what to search for)',
      minLength: 1,
      maxLength: 500
    },
    count: {
      type: 'number' as const,
      description: 'Number of results to return (1-10, default: 5)',
      minimum: 1,
      maximum: 10,
    }
  },
  required: ['query'],
};

export const BraveSearchResultJsonSchema = {
  type: 'object' as const,
  properties: {
    results: {
      type: 'array' as const,
      description: 'Array of search results',
      items: {
        type: 'object' as const,
        properties: {
          title: { type: 'string' as const },
          url: { type: 'string' as const },
          snippet: { type: 'string' as const }
        }
      }
    },
    query: { 
      type: 'string' as const, 
      description: 'The search query used' 
    },
    resultCount: { 
      type: 'number' as const, 
      description: 'Number of results returned' 
    },
  },
  required: ['results', 'query', 'resultCount'],
};

// Strategic Plan Tool Types (PlanExe integration)
export const StrategicPlanArgsSchema = z.object({
  prompt: z.string().min(10).max(5000).describe('Brief description of what you want to plan (business, project, workflow, etc.)'),
});

export type StrategicPlanArgs = z.infer<typeof StrategicPlanArgsSchema>;

export const StrategicPlanResultSchema = z.object({
  task_id: z.string().optional().describe('PlanExe task ID for status tracking'),
  status: z.string().describe('Task status (queued, running, completed, failed)'),
  message: z.string().optional().describe('Status message or error details'),
});

export type StrategicPlanResult = z.infer<typeof StrategicPlanResultSchema>;

// JSON Schema definitions for MCP tool registration
export const StrategicPlanArgsJsonSchema = {
  type: 'object' as const,
  properties: {
    prompt: { 
      type: 'string' as const, 
      description: 'Brief description of what you want to plan (business, project, workflow, etc.)',
      minLength: 10,
      maxLength: 5000
    },
  },
  required: ['prompt'],
};

export const StrategicPlanResultJsonSchema = {
  type: 'object' as const,
  properties: {
    task_id: { 
      type: 'string' as const, 
      description: 'PlanExe task ID for status tracking' 
    },
    status: { 
      type: 'string' as const, 
      description: 'Task status (queued, running, completed, failed)' 
    },
    message: { 
      type: 'string' as const, 
      description: 'Status message or error details' 
    },
  },
  required: ['status'],
};

// Tool registration interfaces
export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
}

// Generic tool handler interface
export interface ToolHandler<TArgs = unknown, TResult = unknown> {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
  execute(args: TArgs): Promise<TResult>;
}