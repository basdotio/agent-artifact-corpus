import { z } from "zod"
import { ticker } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

export const insiderActivityCatalog: ToolCatalog = {
  id: "uw_insider",
  summary: `Access UnusualWhales insider trading data including transactions and flow.

Available commands:
- transactions: Get insider transactions with filters. Use ticker_symbol for comma-separated tickers (e.g., AAPL,INTC)
- sector_flow: Get aggregated insider flow for a sector (sector required)
- ticker_flow: Get aggregated insider flow for a ticker (ticker required)
- insiders: Get all insiders for a ticker (ticker required)`,
  commands: [
    {
      name: "transactions",
      route: "/api/insider/transactions",
      params: z.object({
        ticker_symbol: z.string().describe("Comma-separated list of ticker symbols (e.g., AAPL,INTC). Prefix with - to exclude.").optional(),
        limit: z.number().int().min(1).max(500).default(500).optional(),
        page: z.number().describe("Page number").optional(),
        min_value: z.number().describe("Minimum transaction value").optional(),
        max_value: z.number().describe("Maximum transaction value").optional(),
        min_price: z.number().describe("Minimum stock price").optional(),
        max_price: z.number().describe("Maximum stock price").optional(),
        owner_name: z.string().describe("Name of insider").optional(),
        sectors: z.string().describe("Filter by sectors").optional(),
        industries: z.string().describe("Filter by industries").optional(),
        is_director: z.boolean().describe("Filter for directors").optional(),
        is_officer: z.boolean().describe("Filter for officers").optional(),
        is_ten_percent_owner: z.boolean().describe("Filter for 10% owners").optional(),
        is_s_p_500: z.boolean().describe("Only S&P 500 companies").optional(),
        transaction_codes: z.string().describe("Transaction codes (P=Purchase, S=Sale)").optional(),
        min_marketcap: z.number().int().min(0).describe("Minimum market capitalization in USD").optional(),
        max_marketcap: z.number().int().min(0).describe("Maximum market capitalization in USD").optional(),
        market_cap_size: z.string().describe("Market cap size category (small, mid, large)").optional(),
        min_earnings_dte: z.number().int().nonnegative().describe("Minimum days until earnings").optional(),
        max_earnings_dte: z.number().int().nonnegative().describe("Maximum days until earnings").optional(),
        min_amount: z.number().int().nonnegative().describe("Minimum number of shares").optional(),
        max_amount: z.number().int().nonnegative().describe("Maximum number of shares").optional(),
        common_stock_only: z.boolean().describe("Only common stock transactions").optional(),
        security_ad_codes: z.string().describe("Security acquisition/disposition codes (A/D)").optional(),
        start_date: z.string().describe("Filter for transaction dates on or after this date (YYYY-MM-DD)").optional(),
        end_date: z.string().describe("Filter for transaction dates on or before this date (YYYY-MM-DD)").optional(),
        group: z.boolean().describe("Group insider transactions with the same person and trade code").optional(),
      }),
      queryRenames: { transaction_codes: "transaction_codes[]" },
    },
    { name: "sector_flow", route: "/api/insider/{sector}/sector-flow", params: z.object({ sector: z.string().describe("Market sector"), limit: z.number().int().min(1).max(500).describe("Maximum number of results").optional(), page: z.number().int().min(1).describe("Page number for paginated results").optional() }) },
    { name: "ticker_flow", route: "/api/insider/{ticker}/ticker-flow", params: z.object({ ticker: ticker.describe("Stock ticker symbol"), limit: z.number().int().min(1).max(500).describe("Maximum number of results").optional(), page: z.number().int().min(1).describe("Page number for paginated results").optional() }) },
    { name: "insiders", route: "/api/insider/{ticker}", params: z.object({ ticker: ticker.describe("Stock ticker symbol") }) },
  ],
}
