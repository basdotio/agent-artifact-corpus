---
name: trackiq-amazon-amc-ntb-campaigns
description: Ranks every campaign Amazon Marketing Cloud can see — Sponsored Products, Sponsored Brands, Sponsored Display and DSP — by how many of its purchases came from new-to-brand customers, month over month, and where the campaign's spend can be matched, what each new customer cost; so the campaigns that recruit are funded and the ones that only harvest repeat buyers are named. Use when the user asks about new-to-brand by campaign, which campaigns bring in new customers, cost per new customer by campaign, acquisition versus retention campaigns, recruiting versus harvesting, or an NTB campaign scorecard.
---

# AMC New-to-Brand Campaign Scorecard

A campaign-by-campaign scorecard from Amazon Marketing Cloud: which campaigns
**recruit** customers who have not bought from the brand in a year, and which
mostly **harvest** people who already do. Both have a job; the scorecard
makes sure each is judged on the right one.

Run it monthly, after AMC has settled the previous month.

## Requires

- The TrackIQ MCP, for `list_marketplaces`, `get_amc_ntb_purchases`,
  `get_campaigns` and `get_dsp_performance`.
- **AMC enabled on the account.** If the focus month returns no rows, stop and
  say so.
- Nothing else. No filesystem or internet needed.
- **Without the MCP:** works from an AMC new-to-brand-by-campaign export plus
  campaign spend from Campaign Manager and the DSP console.

## First run

Fill in a copy of `assets/account.example.md` saved as account.md beside the
skill. Every TrackIQ skill reads the same file, so an account already set up
for another TrackIQ report needs nothing added here.

If the runtime has no filesystem, print the same block and ask the user to
paste it into their project instructions once.

## Read first

- `assets/pulls.md` — one month per call, and the campaign-name join
- `assets/method.md` — recruiter, harvester, and cost per new customer
- `assets/checks.md` — what to verify before anything is sent
- `assets/report-template.html` — the report. Replace every `{{TOKEN}}`.

## Non-negotiables

1. **One month per `get_amc_ntb_purchases` call, and check the row count.** It
   truncates at `limit` without an error. If rows == limit, raise it and pull
   again.
2. **Never sum AMC rows across months.** Each month is its own cohort. Show
   months side by side and label every figure.
3. **AMC's `campaign_id` never joins to Sponsored Ads or DSP IDs.** They are
   different namespaces. Spend is matched by **exact campaign name** only;
   a campaign whose name does not match is listed without a cost, never
   guessed.
4. **Use AMC new-to-brand for every channel.** The DSP console's own NTB
   figure disagrees with AMC by 10–15%. Mixing them makes DSP look cheaper or
   dearer than it is.
5. **A harvester is not a bad campaign.** Brand and remarketing campaigns are
   meant to sell to existing customers. Judge recruiters on cost per new
   customer and harvesters on ROAS; never cut a harvester for a low
   new-to-brand share alone.
6. **Below 30 purchases in a month, a new-to-brand share is noise.** List the
   campaign, do not classify it.
7. **Never say a campaign caused a purchase.** AMC shows which campaign's ad
   the buyer saw, not which one did the work.
8. **Never print `account_id`.**

## What it pairs with

`trackiq-amazon-amc-media-mix` rolls this up by channel for the budget
conversation; `trackiq-amazon-amc-ntb-products` says which products new
customers start with, so the recruiting campaigns can feature them.

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

`trackiq-amazon-amc-ntb-campaigns` v1.1.1 (2026-10-06).

If the user asks whether this skill is current, fetch
`https://trackiq.com/skills/registry.json`, compare the `version` field for
`trackiq-amazon-amc-ntb-campaigns`, and if it is newer, give them the download link and
the one-line changelog. Do not fetch at any other time.
