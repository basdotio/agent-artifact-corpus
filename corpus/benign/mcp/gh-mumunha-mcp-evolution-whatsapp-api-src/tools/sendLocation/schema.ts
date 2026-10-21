import * as z from "zod";

export const sendLocationSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to use"),
  number: z.string().describe("Phone number to send the location to (with country code, e.g., 5511999999999)"),
  name: z.string().describe("Name of the location"),
  address: z.string().describe("Address of the location"),
  latitude: z.number().describe("Latitude coordinates of the location"),
  longitude: z.number().describe("Longitude coordinates of the location"),
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
  }).optional().describe("Message to be quoted when sending this location"),
  mentionsEveryOne: z.boolean().optional().describe("Mention everyone on a group message"),
  mentioned: z.array(z.string()).optional().describe("Array of phone numbers to mention")
});

export type SendLocationSchema = z.infer<typeof sendLocationSchema>; 