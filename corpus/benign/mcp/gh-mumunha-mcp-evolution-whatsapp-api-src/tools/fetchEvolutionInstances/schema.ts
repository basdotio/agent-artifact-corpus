import * as z from "zod";

export const fetchEvolutionInstancesSchema = z.object({
  instanceName: z.string().optional().describe("Optional. Name of a specific instance to fetch"),
});

export type FetchEvolutionInstancesSchema = z.infer<typeof fetchEvolutionInstancesSchema>; 