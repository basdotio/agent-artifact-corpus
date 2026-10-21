import { z } from "zod"
import type { ToolCatalog } from "../engine.js"

const calculationsHelp =
  "Comma-separated list. Supported: MIN, MAX, MEAN, MEDIAN, CUMULATIVE_RETURN, VARIANCE, STDDEV, MAX_DRAWDOWN, HISTOGRAM, AUTOCORRELATION, COVARIANCE, CORRELATION."

const intervalEnum = z.enum([
  "1min",
  "5min",
  "15min",
  "30min",
  "60min",
  "DAILY",
  "WEEKLY",
  "MONTHLY",
])

const ohlcEnum = z.enum(["open", "high", "low", "close"])

export const intelCatalog: ToolCatalog = {
  id: "uw_intel",
  premium: true,
  summary: `PREMIUM TOOL. Requires API Advanced, Enterprise Startup, Enterprise Startup + Kafka, or Enterprise tier. Contact dev@unusualwhales.com to upgrade.

Cross-market intelligence: pre-computed market movers, IPO and listing calendars, and flexible statistical analytics across baskets of tickers.

Available commands:
- movers: Today's top gainers, top losers, and most actively traded US tickers, pre-ranked, no input needed. Returns {last_updated, top_gainers:[...], top_losers:[...], most_active:[...]} with {ticker, price, change, change_percent, volume} per row. Use for "what's moving today?".
- ipo_calendar: Upcoming IPOs over the next 3 months with name, ticker, date, price-range, currency, and exchange. Use for "what's IPO'ing this week?".
- listings: Master list of US-traded securities. Pass status="active" (default) for the current universe or status="delisted" with an optional date for historical delistings. Useful for ticker validation, universe construction, or detecting recent delistings.
- analytics_window: Fixed-window statistical analytics across one or more tickers. Pass symbols (comma-separated), range (ISO date or shorthand like "2month"/"full"), interval (1min..60min/DAILY/WEEKLY/MONTHLY), ohlc (open/high/low/close), and calculations (comma-separated: MIN, MAX, MEAN, MEDIAN, CUMULATIVE_RETURN, VARIANCE, STDDEV, MAX_DRAWDOWN, HISTOGRAM, AUTOCORRELATION, COVARIANCE, CORRELATION). Use for cross-asset stats (e.g. "correlation between AAPL and SPY over the past 60 days").
- analytics_sliding: Sliding-window version of the above. Same params plus window_size (default 20). Use for rolling statistics over time (e.g. rolling 20-day correlation).`,
  commands: [
    {
      name: "movers",
      route: "/api/market/movers",
      params: z.object({}),
    },
    {
      name: "ipo_calendar",
      route: "/api/calendar/ipo",
      params: z.object({}),
    },
    {
      name: "listings",
      route: "/api/companies/listings",
      params: z.object({
        status: z.enum(["active", "delisted"]).default("active").optional(),
        date: z
          .string()
          .regex(/^\d{4}-\d{2}-\d{2}$/, "Date must be YYYY-MM-DD")
          .describe("Only used when status=delisted.")
          .optional(),
      }),
    },
    {
      name: "analytics_window",
      route: "/api/analytics/window",
      params: z.object({
        symbols: z.string().min(1).describe("Comma-separated tickers, e.g. AAPL,IBM,MSFT."),
        range: z
          .string()
          .min(1)
          .describe("Either an ISO start date or a relative shorthand like '2month' or 'full'."),
        range_end: z.string().describe("Optional end date if `range` is an ISO start date.").optional(),
        interval: intervalEnum.default("DAILY").optional(),
        ohlc: ohlcEnum.default("close").optional(),
        calculations: z.string().min(1).describe(calculationsHelp),
      }),
    },
    {
      name: "analytics_sliding",
      route: "/api/analytics/sliding",
      params: z.object({
        symbols: z.string().min(1).describe("Comma-separated tickers."),
        range: z.string().min(1).describe("Either an ISO start date or a relative shorthand."),
        range_end: z.string().optional(),
        interval: intervalEnum.default("DAILY").optional(),
        ohlc: ohlcEnum.default("close").optional(),
        window_size: z.number().int().min(1).default(20).optional(),
        calculations: z.string().min(1).describe(calculationsHelp),
      }),
    },
  ],
}
