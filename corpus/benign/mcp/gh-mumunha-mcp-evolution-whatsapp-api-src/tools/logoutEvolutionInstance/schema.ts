import * as z from "zod";

export const logoutEvolutionInstanceSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to logout from"),
});

export type LogoutEvolutionInstanceSchema = z.infer<typeof logoutEvolutionInstanceSchema>; 