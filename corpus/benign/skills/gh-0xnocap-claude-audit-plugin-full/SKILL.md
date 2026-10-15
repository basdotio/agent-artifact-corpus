---
description: Full pre-audit pass on this repo's own smart contracts. Runs the slither static pass first, then the multi-agent adversarial review with the slither triage as recon, and merges both into one ranked report. Use before a mainnet deploy or a professional audit handoff.
---

Run the full pre-audit suite on this repository's OWN smart contracts. Two passes, one report. Do NOT apply any fixes until the user reviews the report and confirms.

## 1. Static pass
Run `/audit:slither` exactly as that skill describes: compile, run slither, filter to the project's own contracts, triage every finding as real, false positive, or cosmetic. Keep the triage table. It is the recon for the next pass.

## 2. Adversarial pass
Run `/audit:adversarial` exactly as that skill describes, with two additions:
- Hand every specialist the slither triage table from step 1 so they start informed and do not re-derive what static analysis already settled.
- Any slither finding marked REAL in step 1 goes through the same adversarial verification as the specialists' own findings. A static hit is a lead, not a verdict.

## 3. One report
Merge both passes into a single ranked list, most severe first. For each finding: severity, title, source (slither, specialist, or both), concrete failure scenario, file:line, suggested fix. Then a short coverage section: what was checked and found safe, with reasoning, and which slither patterns were dismissed as known false positives and why.

If nothing survived either pass, say so plainly. Then STOP and let the user decide what to fix. For anything holding real funds, recommend a human professional audit as the final gate; this suite is pre-audit hardening, not a substitute.

$ARGUMENTS
