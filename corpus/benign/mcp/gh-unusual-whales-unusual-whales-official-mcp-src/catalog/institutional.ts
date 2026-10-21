import { z } from "zod"
import { ticker, dateStr, resultLimit, sortDir, instActivityOrderBy, instHoldingsOrderBy, instListOrderBy, instOwnershipOrderBy, instFilingsOrderBy } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

export const institutionalCatalog: ToolCatalog = {
  id: "uw_institutions",
  summary: `Access UnusualWhales institutional holdings and ownership data.

Available commands:
- list: List institutions with filters
- holdings: Get holdings for an institution (name required)
- activity: Get trading activity for an institution (name required)
- activity_v2: Get trading activity v2 with enhanced data for an institution (name required; date, start_date, end_date optional)
- sectors: Get sector exposure for an institution (name required)
- ownership: Get institutional ownership of a ticker (ticker required)
- latest_filings: Get latest institutional filings`,
  commands: [
    { name: "list", route: "/api/institutions", params: z.object({ name: z.string().optional(), limit: resultLimit.default(500).optional(), page: z.number().optional(), order: instListOrderBy.optional(), order_direction: sortDir.default("desc").optional(), min_total_value: z.number().optional(), max_total_value: z.number().optional(), min_share_value: z.number().optional(), max_share_value: z.number().optional(), tags: z.string().optional() }) },
    { name: "holdings", route: "/api/institution/{name}/holdings", params: z.object({ name: z.string().describe("Institution name"), ticker_symbol: z.string().describe("Filter holdings by ticker").optional(), date: dateStr.optional(), start_date: z.string().optional(), end_date: z.string().optional(), limit: resultLimit.default(500).optional(), page: z.number().optional(), order: instHoldingsOrderBy.optional(), order_direction: sortDir.default("desc").optional(), security_types: z.string().optional() }) },
    { name: "activity", route: "/api/institution/{name}/activity", params: z.object({ name: z.string().describe("Institution name"), date: dateStr.optional(), limit: resultLimit.default(500).optional(), page: z.number().optional(), order: instActivityOrderBy.optional(), order_direction: sortDir.default("desc").optional() }) },
    { name: "activity_v2", route: "/api/institution/{name}/activity/v2", params: z.object({ name: z.string().describe("Institution name"), ticker_symbol: z.string().describe("Filter activity by ticker").optional(), date: dateStr.optional(), start_date: z.string().optional(), end_date: z.string().optional(), limit: resultLimit.default(500).optional(), page: z.number().optional(), order: instActivityOrderBy.optional(), order_direction: sortDir.default("desc").optional() }) },
    { name: "sectors", route: "/api/institution/{name}/sectors", params: z.object({ name: z.string().describe("Institution name"), date: dateStr.optional(), limit: resultLimit.default(500).optional(), page: z.number().optional() }) },
    { name: "ownership", route: "/api/institution/{ticker}/ownership", params: z.object({ ticker: ticker.describe("Ticker symbol"), date: dateStr.optional(), start_date: z.string().optional(), end_date: z.string().optional(), tags: z.string().optional(), limit: resultLimit.default(500).optional(), page: z.number().optional(), order: instOwnershipOrderBy.optional(), order_direction: sortDir.default("desc").optional() }), queryRenames: { tags: "tags[]" } },
    { name: "latest_filings", route: "/api/institutions/latest_filings", params: z.object({ name: z.string().optional(), date: dateStr.optional(), limit: resultLimit.default(500).optional(), page: z.number().optional(), order: instFilingsOrderBy.optional(), order_direction: sortDir.default("desc").optional() }) },
  ],
}
