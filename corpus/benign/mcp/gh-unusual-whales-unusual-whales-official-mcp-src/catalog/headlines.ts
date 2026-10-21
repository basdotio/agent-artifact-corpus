import { z } from "zod"
import { ticker, pageNum } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

const newsLimit = z.number().int().min(1).max(500).default(50).describe("Maximum number of results (default 50, max 500)")

export const headlinesCatalog: ToolCatalog = {
  id: "uw_news",
  summary: `Access UnusualWhales news headlines.

Available commands:
- headlines: Get news headlines with optional filters (ticker, sources, search_term, major_only, page)`,
  commands: [
    { name: "headlines", route: "/api/news/headlines", params: z.object({ ticker: ticker.describe("Filter by ticker symbol").optional(), limit: newsLimit.optional(), sources: z.string().describe("Filter by news sources").optional(), search_term: z.string().describe("Search term to filter headlines").optional(), major_only: z.boolean().default(false).optional(), page: pageNum.optional() }) },
  ],
}
