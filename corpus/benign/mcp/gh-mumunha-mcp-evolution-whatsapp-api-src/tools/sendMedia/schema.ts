import * as z from "zod";

export const sendMediaSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to use"),
  number: z.string().describe("Phone number to send the media to (with country code, e.g., 5511999999999)"),
  mediatype: z.enum(["image", "video", "audio", "document"]).describe("Type of media to send (image, video, audio, or document)"),
  media: z.string().describe("URL or base64 content of the media file"),
  mimetype: z.string().optional().describe("MIME type of the media (e.g., image/jpeg, video/mp4, audio/mpeg, application/pdf)"),
  fileName: z.string().optional().describe("Filename to be used for the media attachment"),
  caption: z.string().optional().describe("Caption text to be displayed with the media"),
  delay: z.number().optional().describe("Presence time in milliseconds before sending message"),
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
  }).optional().describe("Message to be quoted when sending this media")
});

export type SendMediaSchema = z.infer<typeof sendMediaSchema>; 