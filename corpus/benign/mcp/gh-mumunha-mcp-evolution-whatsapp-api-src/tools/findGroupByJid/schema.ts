import { z } from "zod";

export const findGroupByJidSchema = z.object({
  instanceName: z.string().describe("Name of the Evolution API instance"),
  groupJid: z.string().describe("Group remote JID (group ID with @g.us suffix)")
});

export type FindGroupByJidSchema = z.infer<typeof findGroupByJidSchema>; 