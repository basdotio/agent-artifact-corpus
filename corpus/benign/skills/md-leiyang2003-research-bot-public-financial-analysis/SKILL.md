---
name: Public Financial Analysis
description: Generate a VC-oriented public-company financial analysis by assembling the whole user request into one detailed LLM prompt.
script: "public_financial_analysis.py"
scriptArgs: ["{company}", "--depth", "{depth}", "--output", "{output_dir}", "--request", "{request}"]
metadata: {"openclaw":{"requires":{"env":[]}}}
---

Use this when user asks for a public company financial analysis.

The script now uses one detailed prompt for the LLM, including:
1. Company and user request details
2. Executive summary and business quality review
3. Financial snapshot / growth trends
4. Valuation and risk framing with requested metrics (Revenue/Net Income 5Y, growth trends, PE/forward PE/PS, FCF trends, EV proxies)
5. Diligence-oriented conclusion and follow-up questions
