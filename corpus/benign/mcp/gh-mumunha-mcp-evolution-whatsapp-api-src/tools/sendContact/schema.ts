import { z } from "zod";

export const sendContactSchema = z.object({
  instanceName: z.string().describe("The name of the evolution instance to interact with."),
  number: z.string().describe("Number to receive the message (with country code)"),
  contact: z.array(
    z.object({
      fullName: z.string().optional().describe("Contact full name"),
      wuid: z.string().describe("Phone number non-stylized with country code (e.g., 553198296801)"),
      phoneNumber: z.string().describe("Phone number stylized (e.g., +55 31 9 9999-9999)"),
      organization: z.string().optional().describe("Organization name for the contact"),
      email: z.string().optional().describe("Contact email address"),
      url: z.string().optional().describe("Page URL")
    })
  ).describe("Array of contact information to send"),
  delay: z.number().optional().describe("Presence time in milliseconds before sending message"),
  quoted: z.object({
    key: z.object({
      remoteJid: z.string(),
      fromMe: z.boolean(),
      id: z.string(),
      participant: z.string().optional()
    }),
    message: z.object({
      conversation: z.string()
    })
  }).optional().describe("Information of the quoted message"),
  mentionsEveryOne: z.boolean().optional().describe("Mention everyone on a group message"),
  mentioned: z.array(z.string()).optional().describe("Array of phone numbers to mention in the message")
});

export type SendContactSchema = z.infer<typeof sendContactSchema>; 