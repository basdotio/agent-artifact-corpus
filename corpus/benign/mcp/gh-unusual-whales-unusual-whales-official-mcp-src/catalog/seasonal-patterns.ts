import { z } from "zod"
import { ticker, seasonalityOrderBy, minYears, sp500NasdaqOnly, seasonalityLimit, seasonalitySortDir } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

export const seasonalPatternsCatalog: ToolCatalog = {
  id: "uw_seasonality",
  summary: `Access UnusualWhales seasonality data showing historical performance patterns.

Available commands:
- market: Get market-wide seasonality data
- performers: Get top/bottom performers for a month (month required, 1-12)
  Optional filters: min_years, ticker_for_sector, s_p_500_nasdaq_only, min_oi, limit, order, order_direction
- monthly: Get monthly seasonality for a ticker (ticker required)
- year_month: Get year-month breakdown for a ticker (ticker required)`,
  commands: [
    { name: "market", route: "/api/seasonality/market", params: z.object({}) },
    { name: "performers", route: "/api/seasonality/{month}/performers", params: z.object({ month: z.number().min(1).max(12).describe("Month number (1-12)"), min_years: minYears.optional(), ticker_for_sector: ticker.describe("A ticker whose sector will filter results").optional(), s_p_500_nasdaq_only: sp500NasdaqOnly.optional(), min_oi: z.number().int().min(0).describe("Minimum open interest filter").optional(), limit: seasonalityLimit.optional(), order: seasonalityOrderBy.optional(), order_direction: seasonalitySortDir.optional() }) },
    { name: "monthly", route: "/api/seasonality/{ticker}/monthly", params: z.object({ ticker }) },
    { name: "year_month", route: "/api/seasonality/{ticker}/year-month", params: z.object({ ticker }) },
  ],
}
