import { z } from "zod";

export const getEvolutionSettingsSchema = z.object({
  instanceName: z.string().describe("The name of the WhatsApp instance to get settings for")
});

export type GetEvolutionSettingsSchema = z.infer<typeof getEvolutionSettingsSchema>; 