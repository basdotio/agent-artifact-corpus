import { z } from "zod"
import type { ToolCatalog } from "../engine.js"

const COMMODITY_NAMES = [
  "wti",
  "brent",
  "natural-gas",
  "copper",
  "aluminum",
  "wheat",
  "corn",
  "cotton",
  "sugar",
  "coffee",
  "all-commodities",
] as const

const COMMODITY_INTERVALS = ["daily", "weekly", "monthly", "quarterly", "annual"] as const

const ECON_INDICATORS = [
  "gdp",
  "gdp-per-capita",
  "treasury-yield",
  "fed-funds",
  "cpi",
  "inflation",
  "retail-sales",
  "durables",
  "unemployment",
  "payrolls",
] as const

const ECON_INTERVALS = ["daily", "weekly", "monthly", "quarterly", "annual", "semiannual"] as const
const TREASURY_MATURITIES = ["3month", "2year", "5year", "7year", "10year", "30year"] as const

export const macroCatalog: ToolCatalog = {
  id: "uw_macro",
  premium: true,
  summary: `PREMIUM TOOL. Requires API Advanced, Enterprise Startup, Enterprise Startup + Kafka, or Enterprise tier. Contact dev@unusualwhales.com to upgrade.

Long-running global commodity prices and US economic indicator time-series. Use this for macro context like "where is oil right now", "is CPI accelerating", "10y treasury yield trend", "what's the fed funds rate history". Also useful for backtests that need to overlay equity moves against the macro backdrop.

Available commands:
- commodity: Price series for a single commodity. Names: wti, brent, natural-gas, copper, aluminum, wheat, corn, cotton, sugar, coffee, all-commodities. Optional interval (daily, weekly, monthly, quarterly, annual; default monthly). Returns name, unit (e.g. "dollars per barrel"), and an array of {date, value}.
- economy: US economic indicator series. Indicators: gdp, gdp-per-capita, treasury-yield, fed-funds, cpi, inflation, retail-sales, durables, unemployment, payrolls. Optional interval (daily, weekly, monthly, quarterly, annual, semiannual). For treasury-yield, also pass maturity (3month, 2year, 5year, 7year, 10year, 30year). Returns the same {name, unit, data:[{date, value}]} shape.`,
  commands: [
    {
      name: "commodity",
      route: "/api/commodities/{name}",
      params: z.object({
        name: z.enum(COMMODITY_NAMES).describe("Commodity name"),
        interval: z.enum(COMMODITY_INTERVALS).default("monthly").describe("Series cadence").optional(),
      }),
    },
    {
      name: "economy",
      route: "/api/economy/{indicator}",
      params: z.object({
        indicator: z.enum(ECON_INDICATORS).describe("Indicator name"),
        interval: z.enum(ECON_INTERVALS).describe("Series cadence (only some indicators support this).").optional(),
        maturity: z
          .enum(TREASURY_MATURITIES)
          .describe("Only used for treasury-yield.")
          .optional(),
      }),
    },
  ],
}
