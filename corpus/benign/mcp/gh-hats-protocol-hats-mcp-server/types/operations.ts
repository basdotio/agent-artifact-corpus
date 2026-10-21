import { z } from 'zod';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';

// Base operation interface that all operations should implement
export interface BaseOperation<T extends z.ZodType> {
  description: string;
  parameters: T;
  execute: (args: z.infer<T>) => Promise<CallToolResult>;
}

// Helper type for creating operation types
export type Operation<T extends z.ZodType> = {
  description: string;
  parameters: T;
  execute: (args: z.infer<T>) => Promise<CallToolResult>;
};

// Helper function to create a properly typed operation
export function createOperation<T extends z.ZodType>(
  operation: Operation<T>
): Operation<T> {
  return operation;
}
