import { z } from "zod"
import { ticker } from "../validation.js"
import type { ToolCatalog } from "../engine.js"

const reportType = z.enum(["annual", "quarterly"]).describe("Report type: annual or quarterly").optional()

export const financialsCatalog: ToolCatalog = {
  id: "uw_fundamentals",
  summary: `Access fundamental financial data for stocks including financial statements, earnings, and revenue breakdowns.

Available commands:
- fundamental_breakdown: Get fundamental breakdown with revenue segments, EPS, RSU data, and dividends for a ticker
- financials: Get combined financial data (income statements, balance sheets, cash flows, and earnings) for a ticker
- income_statements: Get income statement data (revenue, expenses, net income, EBITDA, etc.)
- balance_sheets: Get balance sheet data (assets, liabilities, equity, debt, etc.)
- cash_flows: Get cash flow data (operating, investing, financing cash flows, capex, dividends, etc.)
- financial_earnings: Get reported and estimated EPS, earnings surprises`,
  commands: [
    { name: "fundamental_breakdown", route: "/api/stock/{ticker}/fundamental-breakdown", params: z.object({ ticker }) },
    { name: "financials", route: "/api/stock/{ticker}/financials", params: z.object({ ticker }) },
    { name: "income_statements", route: "/api/stock/{ticker}/income-statements", params: z.object({ ticker, report_type: reportType }) },
    { name: "balance_sheets", route: "/api/stock/{ticker}/balance-sheets", params: z.object({ ticker, report_type: reportType }) },
    { name: "cash_flows", route: "/api/stock/{ticker}/cash-flows", params: z.object({ ticker, report_type: reportType }) },
    { name: "financial_earnings", route: "/api/stock/{ticker}/earnings", params: z.object({ ticker, report_type: reportType }) },
  ],
}
