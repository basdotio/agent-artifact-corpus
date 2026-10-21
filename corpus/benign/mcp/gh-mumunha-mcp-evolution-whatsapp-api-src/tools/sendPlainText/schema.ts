import * as z from "zod";

export const sendPlainTextSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to use"),
  number: z.string().describe("Phone number to send the message to (with country code, e.g., 5511999999999)"),
  text: z.string().describe("Message text content"),
  delay: z.number().optional().describe("Presence time in milliseconds before sending message"),
  linkPreview: z.boolean().optional().describe("Shows a preview of the target website if there's a link within the message"),
  mentionsEveryOne: z.boolean().optional().describe("Mention everyone on a group message"),
  mentioned: z.array(z.string()).optional().describe("Array of phone numbers to mention"),
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
  }).optional().describe("Message to be quoted when sending this message")
});

export type SendPlainTextSchema = z.infer<typeof sendPlainTextSchema>; 