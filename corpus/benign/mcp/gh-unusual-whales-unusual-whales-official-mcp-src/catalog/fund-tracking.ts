import { z } from "zod"
import { ticker } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

export const fundTrackingCatalog: ToolCatalog = {
  id: "uw_etf",
  summary: `Access UnusualWhales ETF data including holdings, exposure, inflows/outflows, and weights.

Available commands:
- info: Get ETF information (ticker required)
- holdings: Get ETF holdings (ticker required)
- exposure: Get ETFs that hold a ticker (ticker required)
- in_outflow: Get ETF inflow/outflow data (ticker required)
- weights: Get sector and country weights (ticker required)`,
  commands: [
    { name: "info", route: "/api/etfs/{ticker}/info", params: z.object({ ticker: ticker.describe("ETF ticker symbol (e.g., SPY, QQQ)") }) },
    { name: "holdings", route: "/api/etfs/{ticker}/holdings", params: z.object({ ticker: ticker.describe("ETF ticker symbol (e.g., SPY, QQQ)") }) },
    { name: "exposure", route: "/api/etfs/{ticker}/exposure", params: z.object({ ticker: ticker.describe("ETF ticker symbol (e.g., SPY, QQQ)") }) },
    { name: "in_outflow", route: "/api/etfs/{ticker}/in-outflow", params: z.object({ ticker: ticker.describe("ETF ticker symbol (e.g., SPY, QQQ)"), start_date: z.string().describe("Start date (YYYY-MM-DD)").optional(), end_date: z.string().describe("End date (YYYY-MM-DD)").optional() }) },
    { name: "weights", route: "/api/etfs/{ticker}/weights", params: z.object({ ticker: ticker.describe("ETF ticker symbol (e.g., SPY, QQQ)") }) },
  ],
}
