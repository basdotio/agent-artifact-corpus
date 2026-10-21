import { z } from "zod"
import type { ToolCatalog } from "../engine.js"

const currencyCode = z
  .string()
  .min(3)
  .max(5)
  .describe("ISO 4217 currency code (e.g. USD, EUR, JPY).")

const intradayInterval = z.enum(["1min", "5min", "15min", "30min", "60min"])
const historyInterval = z.enum(["daily", "weekly", "monthly"])

export const forexCatalog: ToolCatalog = {
  id: "uw_forex",
  premium: true,
  summary: `PREMIUM TOOL. Requires API Advanced, Enterprise Startup, Enterprise Startup + Kafka, or Enterprise tier. Contact dev@unusualwhales.com to upgrade.

Foreign-exchange (FX) spot rates and OHLC bars across major and exotic currency pairs. Use for "what's USD/EUR right now", "show me JPY trend", multi-currency P&L conversion, or correlation work between FX and equities.

Available commands:
- rate: Live spot exchange rate for a currency pair, including bid and ask. Pass "from" and "to" (ISO 4217 codes, e.g. USD, EUR, JPY, GBP). Returns {from, to, rate, bid, ask, last_refreshed, time_zone}.
- intraday: Intraday OHLC bars for a currency pair. Intervals: 1min, 5min, 15min, 30min, 60min (default 5min). Returns {from, to, interval, time_zone, bars:[{timestamp, open, high, low, close}]}.
- history: Daily, weekly, or monthly OHLC bars. Use interval=daily | weekly | monthly (default daily). Same response shape as intraday.`,
  commands: [
    {
      name: "rate",
      route: "/api/forex/rate",
      params: z.object({ from: currencyCode, to: currencyCode }),
    },
    {
      name: "intraday",
      route: "/api/forex/intraday",
      params: z.object({
        from: currencyCode,
        to: currencyCode,
        interval: intradayInterval.default("5min").optional(),
      }),
    },
    {
      name: "history",
      route: "/api/forex/history",
      params: z.object({
        from: currencyCode,
        to: currencyCode,
        interval: historyInterval.default("daily").optional(),
      }),
    },
  ],
}
