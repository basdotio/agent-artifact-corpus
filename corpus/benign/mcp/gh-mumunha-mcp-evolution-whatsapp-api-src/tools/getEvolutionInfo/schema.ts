import * as z from "zod";

// Empty schema since the getInformation endpoint doesn't need parameters
export const getEvolutionInfoSchema = z.object({});

export type GetEvolutionInfoSchema = z.infer<typeof getEvolutionInfoSchema>; 