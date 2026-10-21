/**
 * Sober Thinking tool schema definitions
 */

import { 
  SoberThinkingArgsSchema, 
  SoberThinkingResultSchema,
  SoberThinkingArgsJsonSchema,
  SoberThinkingResultJsonSchema
} from '../../types/tool-types.js';

export const soberThinkingInputSchema = SoberThinkingArgsJsonSchema;
export const soberThinkingOutputSchema = SoberThinkingResultJsonSchema;
export const soberThinkingArgsValidator = SoberThinkingArgsSchema;
export const soberThinkingResultValidator = SoberThinkingResultSchema;