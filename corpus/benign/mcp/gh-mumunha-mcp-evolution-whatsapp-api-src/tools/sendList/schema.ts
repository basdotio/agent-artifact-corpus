import { z } from 'zod';

const listRowSchema = z.object({
  title: z.string().describe('Title of the row'),
  description: z.string().optional().describe('Description of the row'),
  rowId: z.string().describe('Unique identifier for the row')
});

const listSectionSchema = z.object({
  title: z.string().describe('Title of the section'),
  rows: z.array(listRowSchema).min(1).describe('Array of rows in this section')
});

export const sendListSchema = z.object({
  instanceName: z.string().describe('Name of the WhatsApp instance to use'),
  number: z.string().describe('Phone number to send the list to (with country code)'),
  title: z.string().describe('Title of the list message'),
  description: z.string().describe('Description of the list message'),
  buttonText: z.string().describe('Text to display on the button that opens the list'),
  footerText: z.string().optional().describe('Optional footer text at the bottom of the list message'),
  sections: z.array(listSectionSchema).min(1).describe('Array of sections for the list'),
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
  }).optional().describe('Message to quote when sending the list'),
  mentionsEveryOne: z.boolean().optional().describe('Mention everyone on a group message'),
  mentioned: z.array(z.string()).optional().describe('Array of phone numbers to mention in the message')
});

export type SendListSchema = z.infer<typeof sendListSchema>; 