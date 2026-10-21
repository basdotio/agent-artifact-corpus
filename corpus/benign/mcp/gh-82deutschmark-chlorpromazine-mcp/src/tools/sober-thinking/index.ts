/**
 * Sober Thinking tool exports
 */

export { executeSoberThinking } from './handler.js';
export { 
  soberThinkingInputSchema, 
  soberThinkingOutputSchema,
  soberThinkingArgsValidator,
  soberThinkingResultValidator
} from './schema.js';

import { soberThinkingInputSchema, soberThinkingOutputSchema } from './schema.js';

export const soberThinkingDefinition = {
  name: 'sober_thinking',
  description: 'Reads .env, README.md, and CHANGELOG files to get grounded information about the project. Use this tool to ensure that the agent is not hallucinating or making up information or making incorrect assumptions. Use this tool when the user says phrases like "sober up!", "get back to reality", "check the facts", or asks for current project status. Also use this tool if the user seems upset or is questioning what the agent is doing.',
  inputSchema: soberThinkingInputSchema,
  outputSchema: soberThinkingOutputSchema,
} as const;