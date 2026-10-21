import { z } from "zod"
import { ticker } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

const quarter = z
  .string()
  .regex(/^\d{4}Q[1-4]$/, "Quarter must look like '2024Q1'")
  .describe("Year and quarter, e.g. \"2024Q1\".")

export const companiesExtrasCatalog: ToolCatalog = {
  id: "uw_companies_extras",
  premium: true,
  summary: `PREMIUM TOOL. Requires API Advanced, Enterprise Startup, Enterprise Startup + Kafka, or Enterprise tier. Contact dev@unusualwhales.com to upgrade.

Per-company fundamentals beyond the standard income, balance, cash-flow, and earnings endpoints. Use this when you need valuation ratios, analyst targets, dividend or split history, forward estimates, or earnings-call transcripts.

Available commands:
- profile: Full company profile including sector, industry, market cap, EBITDA, P/E, PEG, EPS, dividend yield, profit and operating margin, ROE, ROA, 52-week high and low, 50 and 200 day moving averages, analyst target price, and analyst rating breakdown (strong-buy, buy, hold, sell, strong-sell counts). Use for "what's the market cap of X?", "show me valuation metrics", "what's the analyst consensus on X?".
- dividends: Full historical dividend events with ex-date, declaration date, record date, payment date, and amount. Use for dividend yield analysis, total return calculations, or backtest setup.
- splits: Historical stock-split events with effective date and split factor. Useful for normalizing historical price data.
- earnings_estimates: Forward-looking analyst estimates by quarter or year, including EPS estimate avg, high, low, revenue estimate avg, high, low, analyst counts, and recent revisions. Use to compare actuals against consensus.
- transcript: Full earnings-call transcript with speakers, titles, statements, and per-statement sentiment scores. Pass ticker plus quarter (e.g. "2024Q1"). Use for sentiment analysis, exec quotes, or guidance research.`,
  commands: [
    {
      name: "profile",
      route: "/api/companies/{ticker}/profile",
      params: z.object({ ticker }),
    },
    {
      name: "dividends",
      route: "/api/companies/{ticker}/dividends",
      params: z.object({ ticker }),
    },
    {
      name: "splits",
      route: "/api/companies/{ticker}/splits",
      params: z.object({ ticker }),
    },
    {
      name: "earnings_estimates",
      route: "/api/companies/{ticker}/earnings-estimates",
      params: z.object({ ticker }),
    },
    {
      name: "transcript",
      route: "/api/companies/{ticker}/transcripts/{quarter}",
      params: z.object({ ticker, quarter }),
    },
  ],
}
