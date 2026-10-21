import { z } from 'zod';

export const sendPollSchema = z.object({
  instanceName: z.string().describe('Name of the WhatsApp instance to use'),
  number: z.string().describe('Phone number to send the poll to (with country code)'),
  name: z.string().describe('Title/name of the poll'),
  selectableCount: z.number().int().min(1).describe('How many options each person can select'),
  values: z.array(z.string()).min(2).describe('Array of poll options to choose from'),
  delay: z.number().int().optional().describe('Presence time in milliseconds before sending message'),
  quoted: z.object({
    key: z.object({
      remoteJid: z.string().describe('Receiver phone number with country code'),
      fromMe: z.boolean().describe('If the message is from the owner number'),
      id: z.string().describe('Message ID'),
      participant: z.string().optional().describe('Participant ID for group messages')
    }),
    message: z.object({
      conversation: z.string().describe('Quoted message content')
    })
  }).optional().describe('Message to quote when sending the poll'),
  mentionsEveryOne: z.boolean().optional().describe('Mention everyone on a group message'),
  mentioned: z.array(z.string()).optional().describe('Array of phone numbers to mention in the message')
});

export type SendPollSchema = z.infer<typeof sendPollSchema>; 