# Mode: Renewal, Extension or Exit

## Goal
Give the business owner a defensible renew, renegotiate, re-tender or exit recommendation with enough lead time to act on it.

## Step-by-Step

**Step 1 — Get the clock.** Run obligations-mode if no register entry exists. State the notice deadline and the number of days remaining. If less than 60 days remain, say so first and treat the timeline as the main constraint.

**Step 2 — Gather evidence.**
- **Performance:** latest `supplier-scorecard-engine` results, SLA data, incidents, credits claimed.
- **Commercial:** spend vs commitment, price vs market (`spend-analyzer` benchmark), indexation applied.
- **Strategic:** category strategy quadrant, business dependency, planned demand change.
- **Risk:** open findings from `supplier-management`, financial or security concerns.
- **Alternatives:** known suppliers, estimated switching cost and time (needed for a credible BATNA).

**Step 3 — Score the options.**

| Option | When it fits |
|---|---|
| Renew as is | Strong performance, price at or below market, low strategic change |
| Renew and renegotiate | Good service but price, term or SLA terms off-market |
| Short extension | Need time to run a competitive process |
| Re-tender | Weak performance, price drift, or a competitive market with a credible alternative |
| Exit | Persistent failure, unacceptable risk, or need gone |

Compare total cost over the next term, including switching costs and risk, not just unit price.

**Step 4 — Recommend.** State the recommended option, the two strongest reasons, the two biggest risks, and the date by which a decision must be made to protect the notice deadline.

**Step 5 — Plan the next steps.** If renegotiating or exiting: hand off to `negotiation-playbook-generator` with the leverage points found. If re-tendering: hand off to `rfp-generator`, noting the incumbent's contract end date. If exiting: list the exit and transition obligations from the contract.

## Output Rules
- Never recommend letting an auto-renewal pass silently. Make the decision explicit and dated.
- Mark any claim not backed by supplied data as an assumption.
