/**
 * Tool registry and exports
 */

import { killTripDefinition, executeKillTrip } from './kill-trip/index.js';
import { soberThinkingDefinition, executeSoberThinking } from './sober-thinking/index.js';
import { braveSearchDefinition, executeBraveSearch } from './brave-search/index.js';
import type { ToolCallParams, ToolCallResult, Tool } from '../types/mcp-types.js';

// Tool registry interface
export interface ToolExecutor {
  (params: ToolCallParams, context: { rateLimitId: string }): Promise<ToolCallResult>;
}

// Tool registry mapping
export const toolRegistry = new Map<string, ToolExecutor>([
  ['kill_trip', executeKillTrip],
  ['sober_thinking', executeSoberThinking],
  ['brave_search', executeBraveSearch],
]);

// Tool definitions for MCP registration
export const toolDefinitions: Tool[] = [
  killTripDefinition,
  soberThinkingDefinition,
  braveSearchDefinition,
];

// Get tool executor by name
export function getToolExecutor(toolName: string): ToolExecutor | undefined {
  return toolRegistry.get(toolName);
}

// Check if tool exists
export function hasToolExecutor(toolName: string): boolean {
  return toolRegistry.has(toolName);
}

// Get all tool names
export function getToolNames(): string[] {
  return Array.from(toolRegistry.keys());
}

// Re-export individual tools for convenience
export {
  killTripDefinition,
  executeKillTrip,
  soberThinkingDefinition,
  executeSoberThinking,
  braveSearchDefinition,
  executeBraveSearch,
};