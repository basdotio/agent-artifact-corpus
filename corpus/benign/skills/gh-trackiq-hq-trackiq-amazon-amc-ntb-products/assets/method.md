# Method

## 1. Per ASIN, per month

```
ntb_share   = ntb_users / all_users
ntb_revenue = ntb_total_product_sales
```

Drop to a **thin** list any ASIN with fewer than **50** `all_users` in the
focus month. It is shown, never classified.

## 2. Classify against the account

Take the median `ntb_share` of the non-thin ASINs in the focus month.

| Class | Rule |
|---|---|
| **Gateway** | `ntb_share` at least 10 points above the median |
| **Retention** | `ntb_share` at least 10 points below the median |
| **Mixed** | everything between |

Use the two earlier months as a check, not an input. Classify each month
against **that month's own median**. A gateway in all three months is
**steady**; one that only qualifies in the focus month is **new this month**
and gets a note, not a funding recommendation.

## 3. Their share of new customers

```
ntb_contribution = asin ntb_users / sum of ntb_users across non-thin ASINs  (focus month only)
```

This is the share of the month's new customers who started with that
product. It sums to 100% within one month and must never be computed across
months.

## 4. The funding gap

```
spend_share = asin ad spend (SP + SD) / total SP + SD spend on non-thin ASINs
gap         = ntb_contribution - spend_share
```

- **Underfunded recruiter**: any product that is not Retention, has
  `ntb_share` at or above the median, was non-thin in all three months, and
  has `gap` above **+5 points**. These are the recommendations. Do not limit
  them to Gateways: the product that brings in the most new customers is
  often Mixed — a best-seller whose share sits a few points above the median
  on far more buyers than any gateway.
- **Halo check.** `ntb_users` counts new customers who bought the product
  after seeing *any* of the brand's ads, not only its own. A product with
  almost no ad spend can still post a large share of new customers. When a
  product's own spend is under 1% of the total, call the gap a test to run,
  not a return already proven.
- **Overfunded retention**: a retention product with `gap` below
  **−5 points**. Name it; recommend moving the difference, not cutting it.

The recommended move is the smaller of the two gaps in dollars, in two
steps, because a gateway's new-to-brand share tends to fall as its spend
rises. State that assumption.

## 5. The headline

"New customers most often start with X and Y — together N% of the month's
new-to-brand customers, on M% of the ad spend." Name the month.
