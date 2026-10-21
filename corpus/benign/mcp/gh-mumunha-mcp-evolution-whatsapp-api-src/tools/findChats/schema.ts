import { z } from "zod";

export const findChatsSchema = z.object({
  instanceName: z.string().describe("Name of the Evolution API instance"),
  where: z
    .object({
      id: z.string().optional().describe("Filter by chat ID/phone number"),
      name: z.string().optional().describe("Filter by chat name"),
      archived: z.boolean().optional().describe("Filter by archived status")
    })
    .optional()
    .describe("Filter criteria for chats")
});

export type FindChatsSchema = z.infer<typeof findChatsSchema>; 