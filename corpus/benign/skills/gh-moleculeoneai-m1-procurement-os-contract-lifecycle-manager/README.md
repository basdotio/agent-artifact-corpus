# Contract Lifecycle Manager
**Molecule One Procurement OS — Contracts**

Review supplier contracts from the buyer's side, track obligations and key dates, and decide what to do at renewal.

## What it does
- Clause-by-clause review against your standard positions, with Green / Yellow / Red severity
- Ready-to-use redlines with rationale and fallback positions, grouped by negotiation tier
- Obligations and key-date extraction, including calculated notice deadlines and money-at-risk items
- Renewal, re-tender or exit recommendation backed by performance and market evidence

## Usage examples
```
"Review this MSA from our cloud vendor — we are the customer"
"What are our obligations and key dates under this contract?"
"When do we need to give notice to avoid the auto-renewal?"
"Should we renew the Accenture agreement or go to market?"
```

## Works with
`negotiation-playbook-generator` (Tier 1 and 2 items), `supplier-scorecard-engine` (renewal evidence), `supplier-management` (risk findings), `rfp-generator` (re-tender).

## Notes
Supports procurement and legal workflows. It does not give legal advice; qualified counsel should review RED items before signature. Adapted in part from Anthropic's `contract-review` skill (Apache License 2.0).
