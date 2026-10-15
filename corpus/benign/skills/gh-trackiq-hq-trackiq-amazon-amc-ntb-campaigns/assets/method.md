# Method

## 1. Per campaign, per month

```
purchases = ntb_purchases + non_ntb_purchases
ntb_share = ntb_purchases / purchases
```

Campaigns with fewer than **30** purchases in the focus month are listed as
thin and not classified.

## 2. Recruiter, harvester, mixed

Take the account's **purchase-weighted** new-to-brand share for the focus
month: total `ntb_purchases` over total purchases, across non-thin campaigns.
Not the median campaign — brand and remarketing campaigns sit near zero by
design, and a median dragged down by them makes every campaign look like a
recruiter, or none.

| Class | Rule | Judged on |
|---|---|---|
| **Recruiter** | `ntb_share` at least 15 points above the account share | cost per new customer |
| **Harvester** | `ntb_share` at least 15 points below the account share | ROAS |
| **Mixed** | between | both |

Brand, remarketing and retargeting campaigns are expected to be harvesters.
Say so rather than presenting them as a problem.

## 3. Cost per new customer

Only for campaigns whose name matched a spend row:

```
cost_per_ntb = campaign spend / ntb_purchases     (focus month)
```

Rank recruiters by it, cheapest first. A recruiter whose cost per new
customer rose more than 30% on the prior month is flagged, with both months
shown. Only recruiters are flagged — mixed campaigns move for other reasons.

Show a dash, not a number, in the cost-per-new-customer column for
harvesters. A remarketing line at several hundred dollars per new customer
is doing its job, and a figure there reads like a failure.

## 4. The movement

For campaigns present in all three months: `ntb_share` in each month side by
side, and the direction. A recruiter drifting toward harvesting is usually
running out of new audience — the recommendation is fresh targeting, not
more budget.

## 5. The headline

"N campaigns recruited M% of the focus month's new-to-brand purchases on K% of
the matched spend." Name the month, and state the matched-spend coverage.

## 6. The recommendation

At most three lines: fund the cheapest steady recruiter, refresh the drifting
one, and leave the harvesters alone unless their ROAS has also fallen.
