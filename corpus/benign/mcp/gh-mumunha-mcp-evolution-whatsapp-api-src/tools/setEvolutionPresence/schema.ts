import * as z from "zod";

export const setEvolutionPresenceSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to set presence for"),
  presence: z.enum(["available", "unavailable"]).describe("Presence status: 'available' to appear online, 'unavailable' to appear offline"),
});

export type SetEvolutionPresenceSchema = z.infer<typeof setEvolutionPresenceSchema>; 