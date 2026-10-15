---
name: trackiq-amazon-amc-ntb-products
description: Uses Amazon Marketing Cloud to find which products bring new customers into a brand and which mostly sell to people who already buy it — new-to-brand share by ASIN, month by month, the gateway products worth more ad weight, the retention products that need less, and how much Sponsored Products and Display spend each group gets today. Use when the user asks which products bring in new customers, new-to-brand by product or ASIN, gateway or acquisition products, first-purchase products, which ASINs to advertise for growth, or customer acquisition by product.
---

# AMC New-to-Brand Products

Answers one question with Amazon Marketing Cloud data: **which products do
new customers buy first?** Those are the gateway products — the ones worth
advertising for growth. The rest mostly sell to people who already know the
brand, and advertising them buys sales the brand would largely get anyway.

Run it monthly, after AMC has settled the previous month.

## Requires

- The TrackIQ MCP, for `list_marketplaces`, `get_amc_ntb_asins`,
  `get_product_ads` and `get_product_performance`.
- **AMC enabled on the account.** If `get_amc_ntb_asins` returns no rows for
  the last three complete months, stop and say so — there is nothing to
  estimate from.
- Nothing else. No filesystem or internet needed.
- **Without the MCP:** works from an AMC new-to-brand-by-ASIN export plus an
  advertised-product report.

## First run

Fill in a copy of `assets/account.example.md` saved as account.md beside the
skill. Every TrackIQ skill reads the same file, so an account already set up
for another TrackIQ report needs nothing added here.

If the runtime has no filesystem, print the same block and ask the user to
paste it into their project instructions once.

## Read first

- `assets/pulls.md` — the pulls, and how AMC's per-ASIN rows mislead
- `assets/method.md` — gateway, retention and mixed, and the funding gap
- `assets/checks.md` — what to verify before anything is sent
- `assets/report-template.html` — the report. Replace every `{{TOKEN}}`.

## Non-negotiables

1. **Never sum AMC rows across months.** Each month is a separate customer
   cohort — a shopper new in July and again counted in August is one person.
   Show months side by side and label every figure with its month.
2. **A product needs volume to be called a gateway.** Below **50 purchasers**
   in a month its new-to-brand share is noise. List it as thin, never rank it.
3. **Classify against the account's own median, not a fixed number.** A
   brand whose median ASIN is 70% new-to-brand is young; one at 25% is
   mature. The same 45% means opposite things in each.
4. **Say what new-to-brand means.** A customer who has not bought from the
   brand on Amazon in the previous twelve months. Not "a new customer to
   Amazon".
5. **AMC's ASIN is lowercase and its numbers are strings.** Uppercase the
   ASIN before joining, cast every figure before arithmetic. A string join
   finds no matches and reports every product as unadvertised.
6. **Ad spend by ASIN covers Sponsored Products and Display only.** Sponsored
   Brands has no product ads, so SB spend is not in the funding table — say
   so beside it.
7. **Never say a product caused a new customer.** It was the first thing
   they bought. Write "new customers most often start with…", not "…drives
   new customers".
8. **Never print `account_id`.**

## What it pairs with

`trackiq-amazon-amc-ntb-campaigns` says which campaigns recruit;
this says which products they should be recruiting with.
`trackiq-amazon-amc-media-mix` puts both in the budget conversation.

## Delivery

The output is produced in the chat first. Delivery is the last step and the
method comes from the Delivery block in account.md — never ask per run.

| Method | What to do | Needs |
|---|---|---|
| `in-chat` | Return the report. The default, and the fallback for every other method. | nothing |
| `file` | Write it beside the skill, dated. | a filesystem |
| `slack` | Post the headline findings as text, then upload the file. | a connected Slack tool |
| `n8n` | POST it to the configured webhook. | network access |
| `email` | Hand it to the connected mail tool. | a connected mail tool |

Confirm before the first outward send of a session, fall back to in-chat
loudly when a method is unavailable, and never substitute a different
outward channel.

## Version

`trackiq-amazon-amc-ntb-products` v1.1.1 (2026-10-06).

If the user asks whether this skill is current, fetch
`https://trackiq.com/skills/registry.json`, compare the `version` field for
`trackiq-amazon-amc-ntb-products`, and if it is newer, give them the download link and
the one-line changelog. Do not fetch at any other time.
