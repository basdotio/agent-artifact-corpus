# Before you send it

## 1. The pulls are complete

- One `get_amc_ntb_purchases` call per month, and none returned exactly
  `limit` rows.
- DSP spend was pulled with `state='all'`.

## 2. Months are never added

- Every figure names its month. No total spans two months.

## 3. The spend join is honest

- Spend was matched on exact normalised name only. No AMC `campaign_id`
  was joined to anything.
- The share of AMC purchases with matched spend is printed. Below 80%, the
  report says cost per new customer covers part of the account.
- Spend was pulled for the prior month as well, so the 30% flag compares
  like with like.
- Harvesters show a dash for cost per new customer.
- Unmatched campaigns appear, without a cost, not silently dropped.

## 4. The classes are fair

- The account's purchase-weighted new-to-brand share is printed.
- Thin campaigns are listed separately.
- Brand and remarketing harvesters are described as doing their job.
- No sentence says a campaign caused a purchase.

## 5. Render check

```js
({ overflows: document.documentElement.scrollWidth > window.innerWidth,
   rows: [...document.querySelectorAll('table')].map(t => t.querySelectorAll('tbody tr').length),
   tokens: (document.body.innerText.match(/\{\{[A-Z_]+\}\}/g) || []).length })
```
