import * as z from "zod";

export const sendStatusSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to use"),
  type: z.enum(["text", "image", "audio"]).describe("Type of status (text, image, or audio)"),
  content: z.string().describe("Text content for type 'text' or file URL for type 'image' and 'audio'"),
  caption: z.string().optional().describe("Text caption for type 'image' status"),
  backgroundColor: z.string().optional().describe("Background hex color (e.g., #008000)"),
  font: z.number().optional().describe("Font style (1=SERIF, 2=NORICAN_REGULAR, 3=BRYNDAN_WRITE, 4=BEBASNEUE_REGULAR, 5=OSWALD_HEAVY)"),
  allContacts: z.boolean().describe("True to send to all contacts or false to send to statusJidList"),
  statusJidList: z.array(z.string()).optional().describe("Array of phone numbers with country code to send status to (required if allContacts is false)")
});

export type SendStatusSchema = z.infer<typeof sendStatusSchema>; 