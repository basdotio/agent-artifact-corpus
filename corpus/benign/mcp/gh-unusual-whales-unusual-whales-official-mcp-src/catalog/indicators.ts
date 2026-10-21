import { z } from "zod"
import { ticker } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

const technicalFn = z.enum([
  "SMA", "EMA", "RSI", "MACD", "BBANDS", "STOCH", "ADX", "ATR",
  "OBV", "VWAP", "CCI", "WILLR", "AROON", "MFI",
]).describe("Technical indicator function")

const interval = z.enum([
  "1min", "5min", "15min", "30min", "60min", "daily", "weekly", "monthly",
]).describe("Time interval for data points").default("daily").optional()

const seriesType = z.enum([
  "close", "open", "high", "low",
]).describe("Price series to use for calculation").default("close").optional()

export const indicatorsCatalog: ToolCatalog = {
  id: "uw_technicals",
  summary: `Access technical indicator data for stocks.

Available commands:
- technical_indicator: Get technical indicator time series data for a ticker

Supported indicators: SMA, EMA, RSI, MACD, BBANDS, STOCH, ADX, ATR, OBV, VWAP, CCI, WILLR, AROON, MFI`,
  commands: [
    {
      name: "technical_indicator",
      route: "/api/stock/{ticker}/technical-indicator/{function}",
      params: z.object({
        ticker,
        function: technicalFn,
        interval,
        time_period: z.number().int().min(1).max(500).describe("Number of data points for calculation (e.g., 14 for RSI-14, 200 for SMA-200)").default(14).optional(),
        series_type: seriesType,
        month: z.string().describe("Query a specific month in history for intraday intervals (YYYY-MM format, e.g. 2009-01)").optional(),
      }),
    },
  ],
}
