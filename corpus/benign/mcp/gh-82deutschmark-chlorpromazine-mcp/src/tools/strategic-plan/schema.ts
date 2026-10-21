/**
 * Strategic Plan tool schema definitions (simplified placeholder)
 */
import { z } from 'zod';

export const StrategicPlanArgsSchema = z.object({
  prompt: z.string().min(10).describe('Brief description of the plan request'),
  speed_vs_detail: z.enum(['fast', 'all']).optional().default('fast'),
});

export type StrategicPlanArgs = z.infer<typeof StrategicPlanArgsSchema>;

export const strategicPlanArgsValidator = StrategicPlanArgsSchema;
