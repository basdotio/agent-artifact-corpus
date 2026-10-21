/**
 * Prompt registry and exports
 */

import { soberThinkingPrompt } from './sober-thinking.js';
import { buzzkillPrompt } from './buzzkill.js';
import type { GetPromptResult } from '../types/mcp-types.js';

// Prompt handler interface
export interface PromptHandler {
  name: string;
  description: string;
  arguments: Array<{ name: string; description: string; required: boolean }>;
  render(args: unknown): Promise<GetPromptResult>;
}

// Prompt registry mapping
export const promptRegistry = new Map<string, PromptHandler>([
  ['sober_thinking', soberThinkingPrompt],
  ['buzzkill', buzzkillPrompt],
]);

// Prompt definitions for MCP registration
export const promptDefinitions = [
  {
    name: soberThinkingPrompt.name,
    description: soberThinkingPrompt.description,
    arguments: soberThinkingPrompt.arguments,
  },
  {
    name: buzzkillPrompt.name,
    description: buzzkillPrompt.description,
    arguments: buzzkillPrompt.arguments,
  },
];

// Get prompt handler by name
export function getPromptHandler(promptName: string): PromptHandler | undefined {
  return promptRegistry.get(promptName);
}

// Check if prompt exists
export function hasPromptHandler(promptName: string): boolean {
  return promptRegistry.has(promptName);
}

// Get all prompt names
export function getPromptNames(): string[] {
  return Array.from(promptRegistry.keys());
}

// Re-export individual prompts for convenience
export {
  soberThinkingPrompt,
  buzzkillPrompt,
};