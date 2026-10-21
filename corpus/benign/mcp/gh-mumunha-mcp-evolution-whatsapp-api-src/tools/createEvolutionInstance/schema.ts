import * as z from "zod";

export const createEvolutionInstanceSchema = z.object({
  instanceName: z.string().describe("Name for the WhatsApp instance (required)"),
  token: z.string().optional().describe("API key (optional, can be left empty to create dynamically)"),
  number: z.string().optional().describe("Instance owner phone number with country code (e.g., 559999999999)"),
  qrcode: z.boolean().optional().describe("Create QR Code automatically after creation"),
  integration: z.enum(["WHATSAPP-BAILEYS", "WHATSAPP-BUSINESS"]).optional().describe("WhatsApp engine to use"),
  reject_call: z.boolean().optional().describe("Reject WhatsApp calls automatically"),
  msgCall: z.string().optional().describe("Message to be sent when a call is rejected"),
  groupsIgnore: z.boolean().optional().describe("Ignore group messages"),
  alwaysOnline: z.boolean().optional().describe("Keep WhatsApp always online"),
  readMessages: z.boolean().optional().describe("Send read receipts to received messages"),
  readStatus: z.boolean().optional().describe("Show sent messages read status"),
  syncFullHistory: z.boolean().optional().describe("Whether to sync full message history"),
  webhookUrl: z.string().optional().describe("URL for webhooks to be sent"),
  webhookByEvents: z.boolean().optional().describe("Enable event-based webhooks"),
});

export type CreateEvolutionInstanceSchema = z.infer<typeof createEvolutionInstanceSchema>; 