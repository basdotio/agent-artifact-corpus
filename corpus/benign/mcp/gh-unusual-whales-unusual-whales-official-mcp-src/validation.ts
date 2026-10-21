/**
 * Shared Zod schema primitives used across endpoint catalogs.
 */

import { z } from "zod"

// ---------------------------------------------------------------------------
// Utility: convert a Zod schema to a JSON-schema-like object for MCP
// ---------------------------------------------------------------------------

export function zodToJsonSchema<T extends z.core.$ZodType>(schema: T): {
  type: "object"
  properties: Record<string, unknown>
  required: string[]
} {
  const full = z.toJSONSchema(schema)
  const { $schema: _, ...rest } = full as Record<string, unknown>
  return rest as {
    type: "object"
    properties: Record<string, unknown>
    required: string[]
  }
}

// ---------------------------------------------------------------------------
// Common parameter schemas
// ---------------------------------------------------------------------------

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

export const ticker = z.string()
  .min(1, "Ticker symbol is required")
  .max(10, "Ticker symbol too long")
  .describe("Stock ticker symbol (e.g., AAPL, MSFT)")

export const dateStr = z.string()
  .regex(DATE_RE, "Date must be in YYYY-MM-DD format")
  .describe("Date in YYYY-MM-DD format")

export const expiry = z.string()
  .regex(DATE_RE, "Expiry date must be in YYYY-MM-DD format")
  .describe("Option expiry date in YYYY-MM-DD format")

export const resultLimit = z.number()
  .int("Limit must be an integer")
  .min(1, "Limit must be at least 1")
  .max(500, "Limit cannot exceed 500")
  .describe("Maximum number of results")

export const optionKind = z.enum(["call", "put", "Call", "Put"]).describe("Option type (call or put)")

export const tradeSide = z.enum(["ALL", "ASK", "BID", "MID"]).describe("Trade side (ALL, ASK, BID, or MID)")

export const sortDir = z.enum(["asc", "desc"]).describe("Sort direction").default("desc")

export const pageNum = z.number()
  .int("Page must be an integer")
  .min(1, "Page must be at least 1")
  .describe("Page number for paginated results")

export const candleSize = z.enum([
  "1m", "5m", "10m", "15m", "30m", "1h", "4h", "1d",
]).describe("Candle size (1m, 5m, 10m, 15m, 30m, 1h, 4h, 1d)")

export const timeframe = z.string()
  .describe("Timeframe for historical data (e.g., '1y', '6m', '3m', '1m')")
  .default("1Y")

export const timespan = z.string()
  .describe("Timespan for IV rank calculation (e.g., '1y' for 1-year lookback)")

export const delta = z.enum(["10", "25"])
  .describe("Delta value for risk reversal skew (10 or 25)")

// ---------------------------------------------------------------------------
// Flow schemas
// ---------------------------------------------------------------------------

export const flowGroup = z.enum([
  "airline", "bank", "basic materials", "china", "communication services",
  "consumer cyclical", "consumer defensive", "crypto", "cyber", "energy",
  "financial services", "gas", "gold", "healthcare", "industrials", "mag7",
  "oil", "real estate", "refiners", "reit", "semi", "silver", "technology",
  "uranium", "utilities",
]).describe("Flow group (e.g., mag7, semi, bank, energy, crypto)")

export const flowAlertOutput = z.object({
  ticker: z.string().describe("Stock ticker symbol"),
  option_symbol: z.string().describe("Option contract symbol"),
  timestamp: z.union([z.string(), z.number()]).describe("Transaction timestamp"),
  premium: z.number().describe("Transaction premium amount"),
  size: z.number().describe("Transaction size/quantity"),
  strike: z.number().describe("Strike price"),
  expiry: z.string().describe("Expiration date"),
  option_type: z.enum(["call", "put"]).describe("Option type"),
  side: z.string().optional().describe("Trade side (ask, bid, mid)"),
  volume: z.number().optional().describe("Contract volume"),
  open_interest: z.number().optional().describe("Open interest"),
  is_sweep: z.boolean().optional().describe("Whether trade is an intermarket sweep"),
  is_floor: z.boolean().optional().describe("Whether trade is from the floor"),
  is_multi_leg: z.boolean().optional().describe("Whether trade is multi-leg"),
})

export const netFlowOutput = z.object({
  expiry: z.string().describe("Expiration date"),
  net_premium: z.number().describe("Net premium amount"),
  call_premium: z.number().optional().describe("Total call premium"),
  put_premium: z.number().optional().describe("Total put premium"),
  volume: z.number().optional().describe("Total volume"),
  transactions: z.number().optional().describe("Number of transactions"),
})

export const greekFlowOutput = z.object({
  ticker: z.string().optional().describe("Stock ticker symbol"),
  date: z.string().optional().describe("Date of the data"),
  delta: z.number().optional().describe("Delta flow"),
  vega: z.number().optional().describe("Vega flow"),
  gamma: z.number().optional().describe("Gamma flow"),
  theta: z.number().optional().describe("Theta flow"),
})

export const flowOutput = z.union([
  z.array(flowAlertOutput),
  z.array(netFlowOutput),
  z.array(greekFlowOutput),
  z.array(z.unknown()),
  z.record(z.string(), z.unknown()),
])

// ---------------------------------------------------------------------------
// Stock-specific
// ---------------------------------------------------------------------------

export const intradayFilter = z.enum(["NetPremium", "Volume", "Trades"])
  .describe("Filter type for intraday flow")
  .default("NetPremium")

// ---------------------------------------------------------------------------
// Screener order-by enums
// ---------------------------------------------------------------------------

export const stockScreenerOrderBy = z.enum([
  "avg_30_day_call_oi", "avg_30_day_call_volume", "avg_30_day_put_oi", "avg_30_day_put_volume",
  "avg_3_day_call_volume", "avg_3_day_put_volume", "avg_7_day_call_volume", "avg_7_day_put_volume",
  "bearish_premium", "bullish_premium", "call_oi_change", "call_oi_change_perc",
  "call_open_interest", "call_premium", "call_premium_ask_side", "call_premium_bid_side",
  "call_volume", "call_volume_ask_side", "call_volume_bid_side", "cum_dir_delta",
  "cum_dir_gamma", "cum_dir_vega", "date", "flex_oi", "flex_option_chains",
  "implied_move", "implied_move_perc", "iv30d", "iv30d_1d", "iv30d_1m", "iv30d_1w",
  "iv_rank", "marketcap", "net_call_premium", "net_premium", "net_put_premium",
  "new_chains", "next_dividend_date", "next_earnings_date", "perc_call_vol_ask",
  "perc_call_vol_bid", "perc_change", "perc_put_vol_ask", "perc_put_vol_bid",
  "premium", "put_call_ratio", "put_oi_change", "put_oi_change_perc",
  "put_open_interest", "put_premium", "put_premium_ask_side", "put_premium_bid_side",
  "put_volume", "put_volume_ask_side", "put_volume_bid_side", "ticker",
  "total_oi_change", "total_oi_change_perc", "total_open_interest", "volatility", "volume",
]).describe("Order by field for stock screener")

export const contractScreenerOrderBy = z.enum([
  "bid_ask_vol", "bull_bear_vol", "contract_pricing", "daily_perc_change",
  "diff", "dte", "earnings", "expires", "expiry", "floor_volume",
  "floor_volume_ratio", "from_high", "from_low", "iv", "multileg_volume",
  "open_interest", "premium", "spread", "stock_price", "tape_time", "ticker",
  "total_multileg_volume_ratio", "trades", "volume", "volume_oi_ratio",
  "volume_ticker_vol_ratio",
]).describe("Order by field for option contract screener")

// ---------------------------------------------------------------------------
// Seasonality
// ---------------------------------------------------------------------------

export const seasonalityOrderBy = z.enum([
  "month", "positive_closes", "years", "positive_months_perc",
  "median_change", "avg_change", "max_change", "min_change",
]).describe("Column to order seasonality results by")

export const minYears = z.number().int().min(1).describe("Minimum years of data required").default(10)
export const sp500NasdaqOnly = z.boolean().describe("Only return tickers in S&P 500 or Nasdaq 100").default(false)
export const seasonalityLimit = z.number().int("Limit must be an integer").min(1).describe("Maximum number of results").default(50)
export const seasonalitySortDir = z.enum(["asc", "desc"]).describe("Sort direction").default("desc")

// ---------------------------------------------------------------------------
// Institution order-by enums
// ---------------------------------------------------------------------------

export const instActivityOrderBy = z.enum([
  "ticker", "security_type", "units", "units_change",
]).describe("Order by field for institutional activity")

export const instHoldingsOrderBy = z.enum([
  "date", "ticker", "security_type", "put_call", "first_buy", "price_first_buy",
  "units", "units_change", "historical_units", "value", "avg_price", "close",
  "shares_outstanding",
]).describe("Order by field for institutional holdings")

export const instListOrderBy = z.enum([
  "name", "call_value", "put_value", "share_value", "call_holdings", "put_holdings",
  "share_holdings", "total_value", "warrant_value", "fund_value", "pfd_value",
  "debt_value", "total_holdings", "warrant_holdings", "fund_holdings", "pfd_holdings",
  "debt_holdings", "percent_of_total", "date", "buy_value", "sell_value",
]).describe("Order by field for institutional list")

export const instOwnershipOrderBy = z.enum([
  "name", "short_name", "filing_date", "first_buy", "units", "units_change",
  "units_changed", "value", "avg_price", "perc_outstanding", "perc_units_changed",
  "activity", "perc_inst_value", "perc_share_value",
]).describe("Order by field for institutional ownership")

export const instFilingsOrderBy = z.enum([
  "name", "short_name", "cik",
]).describe("Order by field for latest institutional filings")
