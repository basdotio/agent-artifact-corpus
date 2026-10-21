import { z } from "zod"
import { ticker, dateStr, pageNum } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

const earningsLimit = z.number().int().min(1).max(100).default(50).describe("Maximum number of results (default 50, max 100)")

export const calendarEventsCatalog: ToolCatalog = {
  id: "uw_earnings",
  summary: `Access UnusualWhales earnings data including premarket and afterhours earnings schedules.

Available commands:
- premarket: Get premarket earnings for a date
- afterhours: Get afterhours earnings for a date
- ticker: Get historical earnings for a ticker (ticker required)`,
  commands: [
    { name: "premarket", route: "/api/earnings/premarket", params: z.object({ date: dateStr.optional(), limit: earningsLimit.optional(), page: pageNum.optional() }) },
    { name: "afterhours", route: "/api/earnings/afterhours", params: z.object({ date: dateStr.optional(), limit: earningsLimit.optional(), page: pageNum.optional() }) },
    { name: "ticker", route: "/api/earnings/{ticker}", params: z.object({ ticker: ticker.describe("Ticker symbol (required)") }) },
  ],
}
