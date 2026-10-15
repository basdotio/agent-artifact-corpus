# The pull sequence

## 0. Account

`list_marketplaces` first. Never print `account_id`. **More than one TrackIQ
MCP can be connected at once, with identical tool names and different brands
behind them.** Call `list_marketplaces` on each and match on `name`.

## 1. The window

The most recent **complete** calendar month is the focus; the two before it
are the comparison.

## 2. The pulls

| # | Call | Arguments | Gives you |
|---|---|---|---|
| 1–3 | `get_amc_ntb_purchases` | **one call per month**, `limit=500` | one row per campaign: NTB and non-NTB purchases and sales |
| 4–5 | `get_campaigns` | `ad_type='all'`, `state='all'`, **the focus month and the month before**, one call each | Sponsored Ads spend by campaign name |
| 6–7 | `get_dsp_performance` | `dimension='campaign'`, `state='all'`, **the focus month and the month before**, one call each | DSP spend by campaign name |

The prior month's spend is what the cost-per-new-customer trend in
`method.md` compares against. Without it the "rose more than 30%" flag
cannot be computed.

## 3. The fields, and how they mislead

Each `get_amc_ntb_purchases` row carries `month_start`, `month_end`,
`campaign_id`, `campaign_name`, `campaign_type`, `advertiser`,
`ntb_purchases`, `non_ntb_purchases`, `ntb_purchases_pct`,
`ntb_product_sales`, `non_ntb_product_sales`, `ntb_sales_pct`.

1. **It truncates silently.** A three-month call at `limit=100` returns 100
   rows from the newest month and nothing from the others. One month per call;
   if rows == limit, raise it.
2. **Numbers arrive as strings.** Cast before arithmetic.
3. **`campaign_id` is AMC's own small integer.** It does not match
   `get_campaigns` or DSP IDs. Never join on it.
4. **`campaign_type` values** include `SPONSORED_PRODUCTS`,
   `SPONSORED_BRANDS`, `SPONSORED_DISPLAY` and `DSP`. Group channels on it.
5. **Never add months.** Each is a separate cohort.

## 4. Matching spend

Normalise names (trim, collapse whitespace, case-fold) and match AMC
`campaign_name` exactly against `get_campaigns.name` for Sponsored Ads types
and against the DSP campaign name for `DSP`. No fuzzy matching: a near-miss
match attaches one campaign's spend to another's customers.

`get_dsp_performance` defaults to `state='ACTIVE'`. Pass `'all'`, or a paused
DSP campaign's spend disappears from the month.

Report the share of AMC purchases whose campaign matched a spend row. Below
80%, say cost per new customer covers only part of the account.
