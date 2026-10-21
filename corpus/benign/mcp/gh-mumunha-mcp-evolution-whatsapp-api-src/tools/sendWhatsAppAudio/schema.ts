import * as z from "zod";

export const sendWhatsAppAudioSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to use"),
  number: z.string().describe("Phone number to send the audio to (with country code, e.g., 5511999999999)"),
  audio: z.string().describe("URL or base64 content of the audio file"),
  delay: z.number().optional().describe("Presence time in milliseconds before sending message"),
  encoding: z.boolean().optional().describe("Encode audio into WhatsApp default format (allows audio to be sped up)"),
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
  }).optional().describe("Message to be quoted when sending this audio"),
  mentionsEveryOne: z.boolean().optional().describe("Mention everyone on a group message"),
  mentioned: z.array(z.string()).optional().describe("Array of phone numbers to mention")
});

export type SendWhatsAppAudioSchema = z.infer<typeof sendWhatsAppAudioSchema>; 