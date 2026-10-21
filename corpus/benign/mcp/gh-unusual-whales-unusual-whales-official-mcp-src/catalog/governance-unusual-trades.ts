import { z } from "zod"
import { dateStr, resultLimit } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

const tradeTypes = z.enum([
  "committee_conflict",
  "first_person_to_trade",
  "low_marketcap",
  "unusual_industry",
  "unusually_large_trade",
  "fec_donation_conflict",
])

export const unusualTradesCatalog: ToolCatalog = {
  id: "uw_unusual_trades",
  premium: true,
  summary: `PREMIUM TOOL. Requires the "unusual-trades" scope on your API token. Contact dev@unusualwhales.com to upgrade.

Access UnusualWhales congressional "unusual trades" / committee conflict-of-interest data.

Available commands:
- recent: List unusual congressional trades, optionally filtered by reason tag(s).
- by_tickers: List unusual trades filtered by ticker(s), date range, transaction type, or politician name.
- chart_data: Trade points + SPY benchmark closes over a date range, suitable for plotting.
- stats: Aggregate overview statistics (top politicians, party/chamber breakdowns, committees, industries, top tickers).`,
  commands: [
    {
      name: "recent",
      route: "/api/congress/unusual-trades",
      params: z.object({
        types: z
          .union([tradeTypes, z.array(tradeTypes), z.string()])
          .describe(
            "Reason tag(s) to filter by. Pass a single tag, a comma-separated string, or an array. Returns all unusual trades when omitted.",
          )
          .optional(),
        limit: resultLimit.min(1).max(500).default(100).describe("Results per page (max 500)").optional(),
        page: z.number().int().min(1).default(1).describe("Page number, 1-indexed").optional(),
      }),
    },
    {
      name: "by_tickers",
      route: "/api/congress/unusual-trades/by-tickers",
      params: z.object({
        tickers: z
          .union([z.string(), z.array(z.string())])
          .describe("Ticker(s) to filter by. Pass a comma-separated string or an array.")
          .optional(),
        transaction_type: z.enum(["buy", "sell"]).describe("Filter to buy- or sell-side transactions.").optional(),
        date_from: dateStr.describe("Inclusive lower bound on transaction_date.").optional(),
        date_to: dateStr.describe("Inclusive upper bound on transaction_date.").optional(),
        politician: z.string().describe("Case-insensitive substring of politician's full name.").optional(),
        limit: resultLimit.min(1).max(500).default(100).describe("Results per page (max 500)").optional(),
        page: z.number().int().min(1).default(1).describe("Page number, 1-indexed").optional(),
      }),
    },
    {
      name: "chart_data",
      route: "/api/congress/unusual-trades/chart-data",
      params: z.object({
        date_from: dateStr.describe("Inclusive lower bound on transaction_date.").optional(),
        date_to: dateStr.describe("Inclusive upper bound on transaction_date.").optional(),
      }),
    },
    {
      name: "stats",
      route: "/api/congress/unusual-trades/stats",
      params: z.object({}),
    },
  ],
}
