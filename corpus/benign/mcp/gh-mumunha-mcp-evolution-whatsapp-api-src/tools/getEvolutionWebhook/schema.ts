import { z } from "zod";

export const getEvolutionWebhookSchema = z.object({
  instanceName: z.string().describe("The name of the WhatsApp instance to get webhook configuration for")
});

export type GetEvolutionWebhookSchema = z.infer<typeof getEvolutionWebhookSchema>; 