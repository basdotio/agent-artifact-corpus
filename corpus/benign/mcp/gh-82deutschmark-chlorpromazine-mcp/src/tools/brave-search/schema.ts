/**
 * Brave Search tool schema definitions
 */

import { 
  BraveSearchArgsSchema,
  BraveSearchResultSchema,
  BraveSearchArgsJsonSchema,
  BraveSearchResultJsonSchema
} from '../../types/tool-types.js';

export const braveSearchInputSchema = BraveSearchArgsJsonSchema;
export const braveSearchOutputSchema = BraveSearchResultJsonSchema;
export const braveSearchArgsValidator = BraveSearchArgsSchema;
export const braveSearchResultValidator = BraveSearchResultSchema;
