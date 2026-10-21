import { z } from "zod"
import { dateStr, resultLimit, tradeSide } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

export const derivativesCatalog: ToolCatalog = {
  id: "uw_options",
  summary: `Access UnusualWhales option contract data including flow, historic prices, intraday data, and volume profiles.

Available commands:
- flow: Get option contract flow (id required; side, min_premium, limit, date optional)
- historic: Get historic option contract data (id required; limit optional)
- intraday: Get intraday option contract data (id required; date optional)
- volume_profile: Get volume profile for option contract (id required; date optional)

The 'id' parameter is the option contract symbol (e.g., AAPL240119C00150000).`,
  commands: [
    { name: "flow", route: "/api/option-contract/{id}/flow", params: z.object({ id: z.string().describe("Option contract ID/symbol (e.g., AAPL240119C00150000)"), side: tradeSide.describe("Trade side (ALL, ASK, BID, or MID)").default("ALL").optional(), min_premium: z.number().int().nonnegative().describe("Minimum premium filter").default(0).optional(), limit: resultLimit.optional(), date: dateStr.optional() }) },
    { name: "historic", route: "/api/option-contract/{id}/historic", params: z.object({ id: z.string().describe("Option contract ID/symbol (e.g., AAPL240119C00150000)"), limit: resultLimit.optional() }) },
    { name: "intraday", route: "/api/option-contract/{id}/intraday", params: z.object({ id: z.string().describe("Option contract ID/symbol (e.g., AAPL240119C00150000)"), date: dateStr.optional() }) },
    { name: "volume_profile", route: "/api/option-contract/{id}/volume-profile", params: z.object({ id: z.string().describe("Option contract ID/symbol (e.g., AAPL240119C00150000)"), date: dateStr.optional() }) },
  ],
}
