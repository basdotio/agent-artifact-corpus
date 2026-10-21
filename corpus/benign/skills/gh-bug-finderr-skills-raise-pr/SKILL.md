---
name: raise-pr
description: Use when opening, pushing or updating a pull request, reviewing a branch before merge, writing PR text, handling review or bot comments on an open PR, or when the user asks for PR videos, screen recordings or demo clips, even if they only say "pr", "push", "open the PR", "review this", "resolve comments" or "update the PR".
---

# Raise a PR

Follow the project's rule files and recent merged PRs where they differ from this.

## Prove
- Start from latest main; check new migration numbers and file names against main and open PRs.
- Test the measures this change can regress, old against new. A smoke test proves it runs, not that it is as good.
  - Model or prompt swap: public data with human references (never self-made samples), silence and noise for invented output, latency, cost, the candidate's retirement date.
  - Access, auth, RLS: show the hole on the base first, then outsiders refused, every legitimate caller still served, speed at realistic row counts.
  - Refactor: old and new side by side, plus a planted change to prove the comparison can fail.
  - UI: phone and desktop, before and after.
- One bug found means search for the same pattern and fix every instance.
- Agent-written tests stay local; their results go in the description.

## Review
- Own checks green, then a clean Opus agent and gpt-6-astra (codex) in parallel on the full diff and the PR text.
- Lenses: correctness and prod safety (auth, data loss, release order, every caller of a changed contract, the same flaw elsewhere in the codebase); useless logic (impossible-state guards, unread data, helpers the repo already has); project and user rules.
- Refute each finding against the code before applying; keep anything uncertain on security. Re-review the fix commits.
- Keep the diff small: repeated lines become one helper, no copies of what git holds, no nice-to-haves.

## Describe
For a smart reader new to the codebase. Title says the effect. Open with what breaks without it. Then only what applies: change, how it was tested (before and after table, data source), prod safety, to make it live (steps and who; merging often changes nothing), known limits, videos. Facts checked this session only, else "configured but untested". No em dashes, no filler, no Co-Authored-By or "Generated with". Update the body whenever a fix changes a fact.

## Videos (user-facing flows only)
`scripts/vlib.mjs` with Node, not Bun; start from `scripts/example-flow.mjs`. Local dev, seeded accounts, passwords from the seed file, setup outside the recording, one caption per step, 20 to 60 s, under 10 MB, check with `scripts/sheet.mjs`, undo test data, re-record if the UI changes. Attach through the PR comment box in Chrome: upload with the long Windows path (`~1` names are refused), read the user-attachments links from the textarea, clear it, never submit.

## Comments until clean
Bots re-review every push, so loop: list unresolved threads, sort each against the code, batch fixes into one push, reply and resolve every thread, wait for the re-review.

| Comment | Action |
|---|---|
| Real defect | Fix it and every instance of the pattern; reply with the commit |
| Real but broader than claimed | Fix the whole class; say what went beyond the ask |
| Wording or docs | Apply if correct |
| Asks for tests | Decline; point to the results in the description |
| Over-protective or out of scope | Decline in one line |
| Repeat of a declined point | Point to the earlier answer |

Done when every PR has zero open threads, a passing AI review on the latest head and green CI. Never merge. Tell the user the links, what each fixes, what reviews caught or were declined, diff size, anything untested, and who does what after merge.
