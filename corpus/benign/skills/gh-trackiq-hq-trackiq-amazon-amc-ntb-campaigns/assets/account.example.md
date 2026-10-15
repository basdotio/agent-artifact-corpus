# Account

Copy to `account.md` beside the skill and fill in. Every TrackIQ skill
reads the same file, so you fill it in once and both the daily and the
weekly send stop asking. Where there is no filesystem — Claude web,
ChatGPT — paste the filled-in version into your project instructions
instead.

| Field | Value |
|---|---|
| Brand name (eyebrow) | Example Brand |
| Account line (footer) | Example Brand — Amazon US |
| Marketplace | US |
| Week anchor | Sunday-Saturday |
| Settled-day convention | settled day is usually 2 days back |

## Hero ASINs

Three to five products that get shelf cards and days-of-cover rows.

| ASIN | Name | Head term |
|---|---|---|
| B0XXXXXXXX | Example Hero 1 | example head term |

## Product lines

How ASINs group for the ranked sections. No API knows your groupings.

| Line | ASINs |
|---|---|
| Example Line | B0XXXXXXXX, B0YYYYYYYY |

## Inventory bands

The account's own days-of-cover cutoffs. Never assume 21/42.

| Band | Days of cover |
|---|---|
| Critical | under 14 |
| Tight | 14 to 28 |
| Healthy | over 28 |

## Delivery

How the finished report leaves the chat. Asked once at first run.

| Field | Value |
|---|---|
| Method | in-chat |
| Target | — |
| Confirm before sending | yes |

Methods: `in-chat` (default, always works) · `file` (saved beside the
skill) · `slack` (target = channel, e.g. `#amazon-ads`) · `n8n` (target =
the webhook URL) · `email` (target = recipients).
