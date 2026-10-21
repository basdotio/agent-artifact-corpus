import * as z from "zod";

export const getConnectionStateSchema = z.object({
  instanceName: z.string().describe("Name of the WhatsApp instance to check connection state"),
});

export type GetConnectionStateSchema = z.infer<typeof getConnectionStateSchema>; 