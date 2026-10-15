# Before you send it

## 1. Months are never added

- Every figure is labelled with the month it belongs to.
- No total combines two months. Search the report for any sum across the
  month columns.
- New-to-brand contribution sums to 100% within the focus month only.

## 2. Joins worked

- ASINs were uppercased before joining. If most gateway products show zero
  ad spend, the join failed — check case first.
- Every product has a title from `get_product_performance`, not a null.
- The funding table says Sponsored Brands spend is not included.

## 3. Classification is fair

- Thin products (under 50 purchasers) are listed separately and never ranked.
- The account median is printed, so the classes can be understood.
- Gateways that only qualify this month carry a note, not a recommendation.
- Each earlier month was classified against its own median, not the focus
  month's.
- A recommended product with almost no ad spend of its own is framed as a
  test (the halo check), not a proven return.

## 4. Language

- No sentence says a product drives or causes new customers.
- New-to-brand is defined once, near the top.

## 5. Render check

```js
({ overflows: document.documentElement.scrollWidth > window.innerWidth,
   rows: [...document.querySelectorAll('table')].map(t => t.querySelectorAll('tbody tr').length),
   tokens: (document.body.innerText.match(/\{\{[A-Z_]+\}\}/g) || []).length })
```
