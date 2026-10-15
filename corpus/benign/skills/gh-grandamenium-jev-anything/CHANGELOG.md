# jev-anything changelog

## Public distribution refresh (2026-09-24)

15. Added current TypeSafe direct API and official SDK access alongside the
    included OpenRouter clients.
16. Removed the stale direct-API waitlist language and added the official
    TypeSafe skill distinction.
17. Enforced the documented 2–10 Score-level range in the plan, references,
    Python client, and TypeScript client.
18. Added safe environment placeholders, public installation/configuration
    instructions, provenance, and MIT license metadata.

## Round 1 hardening (2026-09-22)

Built the skill, then eval-tested it: 5 Sonnet-5 agents each built a different app
(support triage, FAQ router, comment spam, resume grading, game chat) by following
the skill; their systems were then run live against the real Jev API. All 5 worked
(correct primitive, non-authoritative, real cost math). 11 gaps were surfaced and
applied. Snapshot of the pre-round-1 skill: ../jev-eval/skill-snapshot-round1/.
Findings detail: ../jev-eval/round1/FINDINGS.md.

Applied:
1. Interrogate now forces primitive disambiguation when a phrase fits noul or score.
2. Interrogate now asks the user's false-positive vs false-negative tolerance.
3. Interrogate now asks what happens to the non-selected / escalated pile.
4. Plan now requires reading exact criteria wording back to the user for sign-off.
5. Reference 03 now gives confidence-threshold ANCHORS by stakes (was invented blind).
6. Reference 02 now documents the escape-option pattern for `choice`.
7. Implement + reference 03 now cover call error/timeout handling (fail-open vs closed).
8. Reference 03 now gives a concrete real-time pattern (post-now, moderate-async).
9. Step 5 + reference 03 now cover the offline build-and-handover path (no key yet).
10. Educate + reference 03 now flag legally-regulated people decisions (hiring,
    credit, housing, moderation) with a get-counsel + human-review note.
11. Reference 02 now documents per-input-variable criteria (generic instructions,
    variable requirement in state).

## Round 2 (2026-09-22)

3 Sonnet-5 agents on NEW naive requests (live-chat anger flag, email-to-project
folders, loan auto-approval) with NO behavioral hints. Result: all 3 proactively
did what round-1 agents had to discover - primitive disambiguation, escape option,
non-selected-pile review, threshold anchoring, real-time async, error handling, and
the regulated-decision flag (the loan agent rewrote "auto-approve" into "one-click
human confirm" and raised fair-lending audit on its own). The hardening landed.

New improvement applied (2 of 3 agents flagged it independently):
12. Data privacy: skill now warns that the input `state` leaves the user's network
    to OpenRouter/TypeSafe, to flag PII / a data-processing review and to send only
    the fields the decision needs (Educate step + reference 03).

Round-2 deliverables: ../jev-eval/round2/. Snapshot pre-round-2 = the round-1
hardened skill (this file's prior section).

## Step 6: Measure and Optimize phase added (2026-09-22, James idea)

13. Added a post-run measure/optimize/re-measure loop, so the skill produces a
    TUNED classifier, not just a working one. New SKILL.md Step 6, new
    references/04-measure-and-optimize.md (evidence-based lever order: fix criteria
    first - published experiments moved 70% -> 96% by criteria alone - then state,
    primitive, escape option, examples, threshold last), and new
    scaffolding/evaluate.py (labeled-set accuracy + confusion + calibration + cost,
    stores versioned runs, prints per-question change vs the previous run).
    evaluate.py live-verified against the real Jev API.

## Step 6 labeling made human-reasonable + scientific (2026-09-22, James question)

14. The measurement loop no longer asks the user to hand-write JSON. New
    scaffolding/make_rating_sheet.py exports a BLIND CSV rating sheet (answer column
    blank, model guess hidden to avoid confirmation bias); the user fills one
    spreadsheet column (~10-20 min for 50 items, reused each round). evaluate.py
    gained load_labeled_csv, split (train/tuning vs held-out test so tuning does not
    overfit and the reported number is honest), a Wilson 95% confidence interval on
    accuracy (so a 40-50 item sample reads as "about 85%", not "85.0"), and errors()
    to dump misclassified tuning items for reading before tuning. reference 04 Step A/B
    and SKILL Step 6 rewritten around random/representative sampling, blind labeling,
    train/test split, and CI. All live/offline verified.
