# Mode: Contract Review (Buyer Side)

## Goal
Read a supplier contract in full, compare each material clause to the organisation's standard position, classify the deviation, and produce prioritised redlines.

## Step-by-Step

**Step 1 — Load the playbook.** Use the standard positions from config or the user. If none exist, say so and label the review "based on general commercial standards, not your organisation's positions". Offer to create a playbook afterwards.

**Step 2 — Establish context.** Contract type (MSA, SOW, SaaS, licence, goods supply, framework), the user's side (default: customer/buyer), annual and total value, term, and whether personal data, IP creation or regulated activity is involved.

**Step 3 — Read the whole document first.** Clauses interact: an uncapped indemnity may be softened by a broad liability cap. Read definitions, schedules, order forms and any linked online terms before flagging anything. If linked terms (URLs, policies) are not provided, list them as "not reviewed".

**Step 4 — Analyse each clause.** Cover at minimum:

| Clause | Check |
|---|---|
| Fees, pricing, indexation | Price lock period, uplift caps, volume tiers, most-favoured-customer, unilateral price change rights |
| Payment terms | Net days vs baseline, late-payment interest, set-off, disputed invoices |
| Limitation of liability | Cap amount and basis, mutuality, carve-outs, consequential-loss exclusion |
| Indemnities | Scope, mutuality, cap relationship, defence control |
| IP | Pre-existing IP, deliverable ownership, licence scope, feedback clauses |
| Data protection and security | DPA, controller/processor role, sub-processors, breach notice timing, transfers, audit rights, deletion on exit |
| SLAs and service credits | Measurable targets, credit size, chronic-failure termination right, exclusive-remedy wording |
| Term, renewal, termination | Auto-renewal notice window, termination for convenience, cure periods, minimum commitments, exit fees |
| Exit and transition | Transition assistance, data return, step-in, escrow where relevant |
| Subcontracting and assignment | Consent rights, change of control |
| Insurance | Types and limits against exposure |
| Compliance | Anti-bribery, sanctions, modern slavery, code of conduct, audit rights |
| Governing law and disputes | Law, venue, arbitration, escalation steps |

**Step 5 — Classify each deviation.**
- **GREEN** — at or better than standard. Note only.
- **YELLOW** — outside standard but commonly negotiable. Give redline plus fallback.
- **RED** — outside acceptable range or triggers escalation (uncapped liability, assignment of pre-existing IP, no DPA with personal data, one-sided termination, conflict with regulation). Explain the exposure and recommend escalation to Legal.

**Step 6 — Draft redlines.** For each YELLOW and RED item:
```
Clause:            [section and name]
Current language:  "[exact quote]"
Proposed redline:  "[specific replacement language]"
Rationale:         [1-2 sentences, suitable to share with the supplier]
Priority:          [Must-have / Should-have / Nice-to-have]
Fallback:          [position if the ask is rejected]
```

**Step 7 — Present by negotiation tier.**
- **Tier 1 Must-haves:** inadequate liability protection, missing data protection for regulated data, loss of core IP, regulatory conflicts.
- **Tier 2 Should-haves:** cap adjustments, indemnity scope, termination flexibility, audit rights, SLA remedies.
- **Tier 3 Nice-to-haves:** governing-law preference, notice periods, definitional tidy-ups, insurance certificates — use as trade candidates.

Lead with Tier 1, trade Tier 3 for Tier 2. Never concede Tier 1 without escalation.

**Step 8 — Output.** A one-page summary (overall risk, counts by colour, top five issues, recommendation: sign / negotiate / escalate), then the clause table, then the redlines. Offer to hand Tier 1 and 2 items to `negotiation-playbook-generator`. Offer the obligations extract (`modes/obligations-mode.md`).

## Output Rules
- Quote the contract exactly when citing current language. Never paraphrase inside quotation marks.
- State explicitly what was not reviewed (missing schedules, linked terms, unreadable pages).
- Close with the legal-review reminder.
