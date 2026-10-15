---
name: joint-business-plan
description: 'Drafts a joint business plan with a strategic partner: shared goals, target accounts, investments from each side, metrics, and governance. Use when: joint business plan, JBP, strategic partner planning, annual partner plan, partner alignment, shared targets with a partner, alliance plan.'
---

# Joint Business Plan

Turn a strategic partnership into written commitments both sides sign and review.

## When to Use

- A partner reaches the Strategic tier
- Annual planning with an existing strategic partner
- Resetting a partnership that has activity but no shared targets
- Preparing for an executive sponsor meeting

## What You'll Need

**Critical inputs (ask if not provided):**

- The partner's name and the planning period
- Last period's results: sourced won, influenced won, joint customers
- Each side's top priority for the period

**Nice-to-have:**

- Output of `partner-eco score`, `overlap`, and `attribution` for this partner
- Last period's plan and what was delivered
- Integration roadmap items on either side

## Process

### Step 1: Establish the baseline

```bash
python -m partner_ecosystem score data/partners.csv --partner "Northwind Data"
python -m partner_ecosystem attribution data/opportunities.csv --partner "Northwind Data"
```

State where the partnership is today in numbers. Targets without a baseline cannot be judged later.

### Step 2: Agree two or three shared goals

Each goal needs a metric, a target, and a date. Prefer goals that both sides are measured on internally; those get resourced.

### Step 3: Pick the target accounts

```bash
python -m partner_ecosystem overlap data/our_accounts.csv data/partner_accounts.csv --partner "Northwind Data" --opportunities data/opportunities.csv
```

Choose ten to twenty named accounts with a play and an owner on each side. Fewer accounts with owners beat a long list without them.

### Step 4: List investments from each side

Write both columns. Typical items: integration work, enablement and certification, marketing funds, executive time, dedicated sellers. An empty column means it is not a joint plan.

### Step 5: Set governance

Name the executive sponsors, the working leads, the review cadence, and how a missed commitment is escalated.

### Step 6: Record risks and dependencies

Include roadmap dependencies, competing partnerships on either side, and organizational changes.

## Output Format

```markdown
# Joint Business Plan: [us] and [partner], [period]

## Where we are
| Metric | Last period |
|--------|-------------|

## Shared goals
| Goal | Metric | Baseline | Target | Date |
|------|--------|----------|--------|------|

## Target accounts
| Account | Play | Our owner | Their owner | Next step |
|---------|------|-----------|-------------|-----------|

## Investments
| We commit | They commit |
|-----------|-------------|

## Governance
- Executive sponsors:
- Working leads:
- Cadence: weekly pipeline, quarterly review

## Risks and dependencies
## Sign-off
```

## Guardrails

- Keep it to two pages. A plan nobody rereads is not a plan.
- Every target needs a baseline and an owner.
- Do not write commitments for the partner that they have not agreed to; mark them as proposed.
- Keep sourced and influenced targets separate.

## Related

- [Leading a partner ecosystem](https://github.com/varunk130/ai-ecosystem-partnerships/blob/main/playbooks/leading-a-partner-ecosystem.md): what the Strategic tier commits each side to
- [partner-qbr-brief](https://github.com/varunk130/ai-ecosystem-partnerships/blob/main/skills/partner-qbr-brief/SKILL.md): the quarterly review of this plan
