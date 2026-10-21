import { z } from "zod"
import { ticker } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

export const shortSellingCatalog: ToolCatalog = {
  id: "uw_shorts",
  summary: `Access UnusualWhales short selling data including short interest, FTDs, and volume.

Available commands:
- data: Get short data for a ticker (ticker required)
- ftds: Get failure to deliver data (ticker required)
- interest_float: Get short interest as percent of float (ticker required)
- volume_ratio: Get short volume and ratio (ticker required)
- volumes_by_exchange: Get short volumes by exchange (ticker required)
- interest_float_v2: Get short interest as percent of float v2 with enhanced data (ticker required)
- short_screener: Screen for stocks by short interest metrics (all params optional)`,
  commands: [
    { name: "data", route: "/api/shorts/{ticker}/data", params: z.object({ ticker, newer_than: z.string().describe("Return records newer than this value (date or ID)").optional(), older_than: z.string().describe("Return records older than this value (date or ID)").optional() }) },
    { name: "ftds", route: "/api/shorts/{ticker}/ftds", params: z.object({ ticker }) },
    { name: "interest_float", route: "/api/shorts/{ticker}/interest-float", params: z.object({ ticker }) },
    { name: "volume_ratio", route: "/api/shorts/{ticker}/volume-and-ratio", params: z.object({ ticker }) },
    { name: "volumes_by_exchange", route: "/api/shorts/{ticker}/volumes-by-exchange", params: z.object({ ticker, newer_than: z.string().describe("Return records newer than this value (date or ID)").optional(), older_than: z.string().describe("Return records older than this value (date or ID)").optional() }) },
    { name: "interest_float_v2", route: "/api/shorts/{ticker}/interest-float/v2", params: z.object({ ticker }) },
    {
      name: "short_screener",
      route: "/api/short_screener",
      params: z.object({
        limit: z.number().int().min(50).max(500).default(50).optional(),
        offset: z.number().int().min(0).describe("Number of results to skip").optional(),
        page: z.number().int().min(1).optional(),
        tickers: z.string().describe("Comma-separated list of ticker symbols").optional(),
        min_market_date: z.string().describe("Minimum market date (YYYY-MM-DD)").optional(),
        max_market_date: z.string().describe("Maximum market date (YYYY-MM-DD)").optional(),
        min_short_interest: z.number().optional(),
        max_short_interest: z.number().optional(),
        min_days_to_cover: z.number().optional(),
        max_days_to_cover: z.number().optional(),
        min_si_float: z.number().optional(),
        max_si_float: z.number().optional(),
        min_si_float_with_synth_long_pct_of_total_shares: z.number().optional(),
        max_si_float_with_synth_long_pct_of_total_shares: z.number().optional(),
        min_total_float: z.number().optional(),
        max_total_float: z.number().optional(),
        min_short_shares_available: z.number().optional(),
        max_short_shares_available: z.number().optional(),
        min_rebate_rate: z.number().optional(),
        max_rebate_rate: z.number().optional(),
        min_fee_rate: z.number().optional(),
        max_fee_rate: z.number().optional(),
        order_by: z.string().optional(),
        order_direction: z.enum(["asc", "desc"]).default("desc").optional(),
      }),
    },
  ],
}
