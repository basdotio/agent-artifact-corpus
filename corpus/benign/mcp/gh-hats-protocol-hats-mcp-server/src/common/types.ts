import { z } from 'zod';

// Base MCP response type
export interface MCPResponse<T> {
  data: T;
  metadata: {
    timestamp: string;
    version: string;
    source: string;
  };
  error?: {
    code: string;
    message: string;
  };
}

// Common schema for metadata
export const metadataSchema = z.object({
  timestamp: z.string(),
  version: z.string(),
  source: z.string(),
});

// Common schema for error
export const errorSchema = z
  .object({
    code: z.string(),
    message: z.string(),
  })
  .optional();
