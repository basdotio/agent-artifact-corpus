import { z } from "zod"
import type { ToolCatalog } from "../engine.js"

const symbol = z.string().min(1).max(10).describe("Digital asset symbol, e.g. BTC, ETH.")
const market = z
  .string()
  .min(2)
  .max(5)
  .describe("Fiat market currency code, e.g. USD, EUR.")

const intradayInterval = z.enum(["1min", "5min", "15min", "30min", "60min"])
const historyInterval = z.enum(["daily", "weekly", "monthly"])

export const digitalCurrenciesCatalog: ToolCatalog = {
  id: "uw_digital_currencies",
  premium: true,
  summary: `PREMIUM TOOL. Requires API Advanced, Enterprise Startup, Enterprise Startup + Kafka, or Enterprise tier. Contact dev@unusualwhales.com to upgrade.

Standard market-rate OHLC bars for digital assets (BTC, ETH, etc.) priced against a fiat market. This is distinct from uw_crypto, which surfaces UnusualWhales' on-chain whale-tracking data. Use this catalog when you want a clean price chart or backtest of a digital asset against USD, EUR, or other fiat.

Available commands:
- intraday: Intraday OHLC bars for a digital asset against a fiat market. Intervals: 1min, 5min, 15min, 30min, 60min (default 5min). Pass {symbol: "BTC", market: "USD", interval: "5min"}. Returns {symbol, market, interval, time_zone, bars:[{timestamp, open, high, low, close, volume}]}.
- history: Daily, weekly, or monthly OHLC bars. Use interval=daily | weekly | monthly (default daily). Same response shape as intraday.`,
  commands: [
    {
      name: "intraday",
      route: "/api/digital-currencies/intraday",
      params: z.object({
        symbol,
        market,
        interval: intradayInterval.default("5min").optional(),
      }),
    },
    {
      name: "history",
      route: "/api/digital-currencies/history",
      params: z.object({
        symbol,
        market,
        interval: historyInterval.default("daily").optional(),
      }),
    },
  ],
}
