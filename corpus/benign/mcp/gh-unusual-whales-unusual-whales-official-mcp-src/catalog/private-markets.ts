import { z } from "zod"
import { dateStr } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

const npmTicker = z
  .string()
  .min(1)
  .describe("Nasdaq Private Markets ticker for the company (e.g., \"OPENAI\", \"SPACEX\").")

const limitField = z.number().int().min(1).max(500).describe("Maximum number of results.").optional()
const offsetField = z.number().int().min(0).describe("Result offset for pagination.").optional()

export const privateMarketsCatalog: ToolCatalog = {
  id: "uw_private_markets",
  premium: true,
  summary: `PREMIUM TOOL. Requires the "private-markets" scope on your API token. Contact dev@unusualwhales.com to upgrade.

Access UnusualWhales' Nasdaq Private Markets data: pre-IPO companies, valuations, funding rounds, investors, and management.

Available commands:
- companies: List private-markets companies (optional filters: sector, name).
- company_profile: Profile for one company including latest implied price, total funding, and investor count.
- funding: Funding round history for a single company.
- investors: Disclosed investors for a single company.
- management: Disclosed leadership for a single company.
- pricing: Historical implied per-share pricing for a single company.
- top_investors: Most prolific investors across the dataset by distinct company count.
- investor_profile: Portfolio of companies for a specific investor name.
- search: Substring search across companies and investors.`,
  commands: [
    {
      name: "companies",
      route: "/api/private-markets/companies",
      params: z.object({
        sector: z.string().describe("Exact-match sector (e.g., \"Technology\").").optional(),
        name: z.string().describe("Case-insensitive substring of company name.").optional(),
        limit: limitField,
        offset: offsetField,
      }),
    },
    {
      name: "company_profile",
      route: "/api/private-markets/companies/{npm_ticker}",
      params: z.object({
        npm_ticker: npmTicker,
      }),
    },
    {
      name: "funding",
      route: "/api/private-markets/companies/{npm_ticker}/funding",
      params: z.object({
        npm_ticker: npmTicker,
        limit: limitField,
        offset: offsetField,
      }),
    },
    {
      name: "investors",
      route: "/api/private-markets/companies/{npm_ticker}/investors",
      params: z.object({
        npm_ticker: npmTicker,
        limit: limitField,
        offset: offsetField,
      }),
    },
    {
      name: "management",
      route: "/api/private-markets/companies/{npm_ticker}/management",
      params: z.object({
        npm_ticker: npmTicker,
        limit: limitField,
        offset: offsetField,
      }),
    },
    {
      name: "pricing",
      route: "/api/private-markets/companies/{npm_ticker}/pricing",
      params: z.object({
        npm_ticker: npmTicker,
        start_date: dateStr.describe("Inclusive lower bound on pricing date.").optional(),
        end_date: dateStr.describe("Inclusive upper bound on pricing date.").optional(),
        limit: limitField,
        offset: offsetField,
      }),
    },
    {
      name: "top_investors",
      route: "/api/private-markets/investors",
      params: z.object({
        limit: limitField,
        offset: offsetField,
      }),
    },
    {
      name: "investor_profile",
      route: "/api/private-markets/investors/{name}",
      params: z.object({
        name: z.string().describe("The investor's name (URL-encoded server-side).").min(1),
      }),
    },
    {
      name: "search",
      route: "/api/private-markets/search",
      params: z.object({
        query: z.string().min(1).describe("Search string (case-insensitive substring match)."),
        limit: z.number().int().min(1).max(50).default(10).describe("Max results per category (1-50).").optional(),
      }),
    },
  ],
}
