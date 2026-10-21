/**
 * Kill Trip tool schema definitions
 */

import { 
  KillTripArgsSchema, 
  KillTripResultSchema,
  KillTripArgsJsonSchema,
  KillTripResultJsonSchema
} from '../../types/tool-types.js';

export const killTripInputSchema = KillTripArgsJsonSchema;
export const killTripOutputSchema = KillTripResultJsonSchema;
export const killTripArgsValidator = KillTripArgsSchema;
export const killTripResultValidator = KillTripResultSchema;