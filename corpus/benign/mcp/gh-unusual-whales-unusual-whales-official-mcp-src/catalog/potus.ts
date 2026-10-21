import { z } from "zod"
import { dateStr, pageNum } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

const potusLimit = z.number()
  .int("Limit must be an integer")
  .min(1, "Limit must be at least 1")
  .max(200, "Limit cannot exceed 200")
  .describe("Maximum number of results (1-200)")

export const potusCatalog: ToolCatalog = {
  id: "uw_potus",
  summary: `Access UnusualWhales data on the President of the United States, including social-media posts and the public schedule. Useful for tracking potentially market-moving statements and events.

Available commands:
- posts: Get the President's recent posts (limit, page, search_term optional)
- schedule: Get the President's public schedule (date, limit, page optional)`,
  commands: [
    { name: "posts", route: "/api/potus/posts", params: z.object({ limit: potusLimit.optional(), page: pageNum.optional(), search_term: z.string().describe("Filter posts by search term").optional() }) },
    { name: "schedule", route: "/api/potus/schedule", params: z.object({ date: dateStr.optional(), limit: potusLimit.optional(), page: pageNum.optional() }) },
  ],
}
