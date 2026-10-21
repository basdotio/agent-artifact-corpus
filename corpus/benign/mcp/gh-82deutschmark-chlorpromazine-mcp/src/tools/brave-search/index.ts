/**
 * Brave Search tool exports
 */

export { executeBraveSearch } from './handler.js';
export { 
  braveSearchInputSchema, 
  braveSearchOutputSchema,
  braveSearchArgsValidator,
  braveSearchResultValidator
} from './schema.js';

import { braveSearchInputSchema, braveSearchOutputSchema } from './schema.js';

export const braveSearchDefinition = {
  name: 'brave_search',
  description: 'Search the web using Brave Search API. Use this tool to find current information, verify facts, or research topics. Provide a search query and optionally specify how many results you want (1-10, default 5).',
  inputSchema: braveSearchInputSchema,
  outputSchema: braveSearchOutputSchema,
} as const;
