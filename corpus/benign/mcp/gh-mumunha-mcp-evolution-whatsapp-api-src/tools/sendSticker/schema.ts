import * as z from "zod";

export const sendStickerSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to use"),
  number: z.string().describe("Phone number to send the sticker to (with country code, e.g., 5511999999999)"),
  sticker: z.string().describe("URL or base64 content of the sticker image"),
  delay: z.number().optional().describe("Presence time in milliseconds before sending message"),
  quoted: z.object({
    key: z.object({
      remoteJid: z.string().describe("Receiver phone number with country code"),
      fromMe: z.boolean().describe("If the message is from the owner number"),
      id: z.string().describe("Message ID"),
      participant: z.string().optional().describe("Group participant ID")
    }),
    message: z.object({
      conversation: z.string().describe("Quoted message content")
    })
  }).optional().describe("Message to be quoted when sending this sticker"),
  mentionsEveryOne: z.boolean().optional().describe("Mention everyone on a group message"),
  mentioned: z.array(z.string()).optional().describe("Array of phone numbers to mention")
});

export type SendStickerSchema = z.infer<typeof sendStickerSchema>; 