# The pull sequence

## 0. Account

`list_marketplaces` first. Never print `account_id`. **More than one TrackIQ
MCP can be connected at once, with identical tool names and different brands
behind them.** Call `list_marketplaces` on each and match on `name`.

## 1. The window

The three most recent **complete** calendar months. AMC data is monthly; a
partial month compares badly with full ones.

## 2. The pulls

| # | Call | Arguments | Gives you |
|---|---|---|---|
| 1–3 | `get_amc_ntb_asins` | **one call per month**, `limit=500` | one row per tracked ASIN for that month |
| 4 | `get_product_ads` | `ad_type='all'`, `state='all'`, the focus month | SP and SD spend and sales by ASIN |
| 5 | `get_product_performance` | the focus month | title and ordered revenue by ASIN |

One month per AMC call. Large accounts track hundreds of ASINs and a
three-month call can truncate at `limit` without saying so. If a call returns
exactly `limit` rows, raise the limit and pull again.

## 3. The fields, and how they mislead

Each `get_amc_ntb_asins` row carries `month_start`, `month_end`,
`tracked_asin`, `title`, `all_users`, `ntb_users`, `repeat_users`,
`ntb_users_pct`, `total_purchases`, `ntb_total_purchases`,
`ntb_purchases_pct`, `total_product_sales`, `ntb_total_product_sales`,
`ntb_sales_pct`, `total_units_sold`, `ntb_total_units_sold`.

1. **`tracked_asin` is lowercase.** Uppercase it before joining to anything.
2. **Most counts arrive as strings** (`"851"`), some as floats. Cast all of
   them before arithmetic.
3. **`title` is often null.** Take the title from `get_product_performance`.
4. **Users, not purchases, define new-to-brand share.** Use `ntb_users` /
   `all_users` for the classification. `ntb_purchases_pct` counts a repeat
   purchase by a new customer as new-to-brand too.
5. **Rows are one per month. Never add them.** A customer can appear in
   several months.

## 4. Ad spend by ASIN

`get_product_ads` returns one row per product ad, so an ASIN in five ad
groups has five rows. Sum spend and sales by uppercase ASIN over enabled and
paused ads — spend happened whether or not the ad is live today.
