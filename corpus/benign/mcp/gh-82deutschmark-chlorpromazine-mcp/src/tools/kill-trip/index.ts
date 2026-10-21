/**
 * Kill Trip tool exports
 */

export { executeKillTrip } from './handler.js';
export { 
  killTripInputSchema, 
  killTripOutputSchema,
  killTripArgsValidator,
  killTripResultValidator
} from './schema.js';

import { killTripInputSchema, killTripOutputSchema } from './schema.js';

export const killTripDefinition = {
  name: 'kill_trip',
  description: 'Performs documentation search using SerpAPI. Use this tool when the user is upset or says you are wrong or mistaken or says phrases like "stop!" or "quit tripping!" or "quit hallucinating", "check the docs", or asks to verify information against official sources. Also use this tool if the user seems upset or is questioning what the agent is doing.',
  inputSchema: killTripInputSchema,
  outputSchema: killTripOutputSchema,
} as const;