import { z } from "zod";

export const setEvolutionSettingsSchema = z.object({
  instanceName: z.string().describe("The name of the WhatsApp instance to configure settings for"),
  rejectCall: z.boolean().default(false).describe("Whether to automatically reject calls"),
  msgCall: z.string().optional().describe("Message to send when rejecting a call"),
  groupsIgnore: z.boolean().default(false).describe("Whether to ignore group messages"),
  alwaysOnline: z.boolean().default(false).describe("Whether to keep WhatsApp status as always online"),
  readMessages: z.boolean().default(false).describe("Whether to send read receipts for messages"),
  syncFullHistory: z.boolean().default(false).describe("Whether to sync full message history"),
  readStatus: z.boolean().default(false).describe("Whether to show read status for messages")
});

export type SetEvolutionSettingsSchema = z.infer<typeof setEvolutionSettingsSchema>; 