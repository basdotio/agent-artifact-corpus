import { z } from "zod";

export const sendButtonsSchema = z.object({
  instanceName: z.string().describe("The name of the instance to use"),
  number: z.string().describe("Phone number with country code to send the message to"),
  title: z.string().describe("Title of the button message"),
  description: z.string().describe("Main content of the message"),
  footer: z.string().optional().describe("Footer text displayed at the bottom of the message"),
  buttons: z.array(z.object({
    buttonId: z.string().describe("Unique identifier for the button"),
    buttonText: z.string().describe("Text displayed on the button")
  })).describe("Array of buttons to include in the message"),
  delay: z.number().optional().describe("Delay in milliseconds before sending the message"),
  quoted: z.object({
    key: z.object({
      remoteJid: z.string().describe("JID of the chat where the original message is"),
      fromMe: z.boolean().describe("Whether the original message was sent by the bot"),
      id: z.string().describe("Unique identifier of the original message"),
      participant: z.string().optional().describe("The participant who sent the original message in a group")
    }),
    message: z.object({
      conversation: z.string().describe("Content of the original message")
    })
  }).optional().describe("Quote a message in reply"),
  mentionsEveryOne: z.boolean().optional().describe("Mention all participants in a group"),
  mentioned: z.array(z.string()).optional().describe("Phone numbers with country code to mention")
});

export type SendButtonsSchema = z.infer<typeof sendButtonsSchema>; 