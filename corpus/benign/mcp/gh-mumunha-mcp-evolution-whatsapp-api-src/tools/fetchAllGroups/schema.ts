import { z } from "zod";

export const fetchAllGroupsSchema = z.object({
  instanceName: z.string().describe("The name of the evolution instance to interact with."),
  getParticipants: z.boolean().optional().describe("Whether to get the group members or not")
});

export type FetchAllGroupsSchema = z.infer<typeof fetchAllGroupsSchema>; 