import * as z from "zod";

export const deleteEvolutionInstanceSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to permanently delete"),
});

export type DeleteEvolutionInstanceSchema = z.infer<typeof deleteEvolutionInstanceSchema>; 