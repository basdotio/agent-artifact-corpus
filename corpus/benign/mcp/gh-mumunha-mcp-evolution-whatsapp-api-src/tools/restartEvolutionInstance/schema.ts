import { z } from "zod";

export const restartEvolutionInstanceSchema = z.object({
  instanceName: z.string().describe("The name of the WhatsApp instance to restart")
});

export type RestartEvolutionInstanceSchema = z.infer<typeof restartEvolutionInstanceSchema>; 