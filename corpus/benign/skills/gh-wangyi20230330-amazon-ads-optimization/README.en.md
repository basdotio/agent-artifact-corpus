# Amazon Ads Optimization — An Agent Skill for Amazon PPC

> An **executable** Amazon advertising optimization methodology, packaged as an Agent Skill (`SKILL.md`).
> No vague strategy talk — **every conclusion must land as "change what, change to what, why".**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![No API Key](https://img.shields.io/badge/API%20Key-not%20required-green)](https://github.com)

[中文说明](README.md) · English

---

## What this is

A **decision layer** for Amazon advertising, not a scraper or bot. It sits on top of your data source (official Ads API or Seller Central report exports) and produces a **concrete action list**: which term to change, to what value, and on what evidence.

```
Pull data → Diagnose → Decide → Execute → Review
```

**For**: Amazon sellers, PPC specialists, agencies, anyone who wants to systemize ad optimization.
**Not for**: people wanting a "one-click auto-bid bot" — by default this project **proposes, it does not apply**.

---

## Highlights

### Start from bid arithmetic, not from strategy

Everything anchors on **break-even ACoS**, with reproducible formulas:

```
Break-even ACoS = contribution before ads ÷ selling price
Affordable CPC  = price × conversion rate × target ACoS
Dynamic click threshold = 1 ÷ conversion rate
```

```bash
node scripts/ads_opt.mjs calc \
  --price 39.99 --cost 8 --fba 7.5 --first-leg 3 \
  --commission-rate 15 --return-rate 5 --target-margin 15 --cvr 8
```

### Turn reports into an action list

```bash
node scripts/ads_opt.mjs diagnose --file examples/sample-search-term-report.csv \
  --target-acos 25 --break-even-acos 40
node scripts/ads_opt.mjs diagnose --file examples/sample-placement-report.csv \
  --mode placement --target-acos 25
node scripts/ads_opt.mjs sqp --file examples/sample-sqp-report.csv
node scripts/ads_opt.mjs keywords --seed "portable blender" --site us
```

Output is graded **P0 (stop the bleeding) / P1 (improve) / P2 (scale)**.

### Every threshold traces to evidence

`references/verification.md` documents **6 rounds of cross-verification** against
11 independent open-source implementations, 32 Chinese public sources, and 2 official Amazon sources —
each theory is tagged with its sources, whether it reached the ≥5-corroboration bar, and which ones are merely "starting points".

**Verification overturned 3 of our own rules**:

| Original rule | Why it was wrong | Now |
|---|---|---|
| Low Product Pages ACoS → raise PP modifier | Independent source: *There is no "Product Pages boost" in any sensible ruleset* | Judge by ACoS relative to break-even; PP has no raising tier |
| Harvest if orders ≥2 **and ACoS ≤ target** | A steady converter with poor ACoS most needs its own campaign | Switch to **conversion-velocity** gating; ACoS sets the bid only |
| Pause ads in low-converting hours | Pausing breaks continuity and lowers ad weight / quality score | Lower budget and bids — **do not pause** |

### Official vs empirical, clearly separated

**Authority order**: Amazon official guides / API docs > Amazon Ads Academy > overseas mainstream sources > Chinese public media.

Our break-even / target ACoS framework **matches the official one**; we simply itemize deductions more strictly (adding first-leg freight and return losses).

---

## Quick start

### As an Agent Skill

Place this directory in your agent's skills folder (`SKILL.md` must stay at the root):

```bash
git clone https://github.com/<owner>/amazon-ads-optimization.git \
  ~/.agents/skills/amazon-ads-optimization
```

### As documentation

Read in this order:

```
SKILL.md                    → the 5-minute overview of the whole flow
references/metrics.md       → formulas and definitions
references/diagnosis.md     → the diagnostic rule tables (most used)
references/playbooks.md     → 8 scenario playbooks
references/actions.md       → action library, rate limits, rollback
```

### Requirements

- **Node.js ≥ 18** (only for `scripts/ads_opt.mjs`; the Markdown part has zero dependencies)
- No API keys, no third-party packages

---

## The 9-layer diagnostic framework

The order is fixed — **an upper-layer problem masks lower ones; skipping layers is redecorating a broken foundation.**

```
Layer 0  Share funnel (SQP)     → locate the weak link: impression / click / add-to-cart / purchase
Layer 1  Account               → TACoS trend, ad share, organic cannibalization
Layer 2  Campaigns             → budget cap-out, ACoS vs target, impression share
Layer 3  Ad groups / keywords  → structure mixing, match-type conflicts
Layer 4  Search terms          → harvest / negate / migrate
Layer 5  Placements            → Top of Search / Rest of Search / Product Pages
Layer 6  Dayparting            → budget pacing and bids
Layer 7  Peak-event metrics    → CTR↓ + CVR↑ is normal, not a decline
Layer 8  New-demand analysis   → new vs historical converting terms
```

**Why layer 0 matters**: it prevents treating a *conversion* problem as a *bidding* problem — the most expensive mistake in PPC.
> Wherever the share cliff is, money should go to fixing that link — not to ads.

---

## Guardrails

| Guardrail | Rule |
|---|---|
| **Propose by default** | Read/diagnose freely; **every bid/budget/state change needs explicit confirmation** |
| **Batch size ≤ 20%** | Rate limit to avoid wrecking an account |
| **Always record the prior value** | No prior value = no rollback = don't execute |
| **Don't touch during learning** | < 3 days after launch/major change (conservative default: 7 days) |
| **No spend increase when low on stock** | Stop all scaling actions below 30 days of cover |
| **No structural decisions during peak events** | Event data isn't comparable to baseline |
| **No scraping platform pages** | Official API and report exports only |

---

## FAQ

**Do I need Brand Registry?**
Only for Layer 0 (SQP share funnel). Without it, skip Layer 0 — but you lose some ability to separate conversion problems from bidding problems.

**Can I use it without API access?**
Yes. Export the Search Term / Placement reports from Seller Central and feed the CSV to `diagnose`. Column conventions are in `references/data-integration.md`.

**Will the script change my ads?**
**No.** It performs local arithmetic and two public read-only endpoint calls. There are no write operations.

**Will these thresholds fit my category?**
Thresholds are **starting points, not doctrine**. Each one is tagged as multi-source-verified or merely empirical in `references/verification.md`. Calibrate with your own data.

---

## Contributing

Contributions **with evidence** are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
Especially welcome: adding sources for items marked "empirical / single-source", and sharing category-calibrated thresholds (please anonymize).

## Changelog · License · Sources

- [CHANGELOG.md](CHANGELOG.md)
- [LICENSE](LICENSE) (MIT, for original content)
- [NOTICE.md](NOTICE.md) (third-party sources and attribution)
- [SECURITY.md](SECURITY.md)

> Not affiliated with or endorsed by Amazon.com, Inc. Amazon and related marks belong to their respective owners.
