---
name: adversarial-mr-review
description: "Runs a pull/merge request through repeated rounds of adversarial, architect-level code review — hunting for design flaws, edge cases, and regressions — fixing every finding immediately and starting the next round right away, until two consecutive rounds come back clean. Use whenever the user asks to review an MR/PR, wants an adversarial or architect-level review, asks to loop a review until it's clean, wants regressions checked before merging, or asks for a review-fix-repeat cycle — even without the words \"adversarial\" or \"loop\"."
---

# Adversarial MR Review Loop

Reviews a pull/merge request the way a skeptical, senior architect would: assume the change is guilty until proven innocent, actively look for reasons it's wrong, and don't stop at the first clean-looking pass. Fix everything found, then re-review from scratch, because a fix can introduce its own problems. Keep going until two rounds in a row turn up nothing.

## Why this shape

A single review pass tends to rubber-stamp — once you've read a diff once, your eyes skip over it the second time. Reviewing it fresh each round, adversarially, catches what a friendly first pass misses. Requiring *two* clean rounds, not one, guards against a lucky pass where you just didn't look hard enough. And running rounds back-to-back — never waiting on CI or a timer — is the point: the goal is to hand over a change that's already clean, not sit idle waiting for a pipeline to tell you what you could have found yourself.

## 1. Find the MR to review

Work out what's actually being reviewed before starting:

- If the user names a PR/MR number or pastes a URL, fetch it. Check which CLI is available (`which gh`, `which glab`) and use the one that matches — `gh pr diff <num>` / `gh pr view <num>` for GitHub, `glab mr diff <num>` for GitLab.
- If they say "this branch" / "my changes" / give no target, diff the current branch against its base (find the merge-base, then `git diff <base>...HEAD`). Work out the base from the branch's tracking info, or default to `main`/`master`, whichever exists.
- If none of this resolves to an actual diff (no repo, no reachable PR, ambiguous base), stop and ask rather than reviewing nothing or guessing at a target.

## 2. Run rounds, back to back

Repeat this cycle. Once a round's fixes are applied, the next round starts immediately — no waiting for CI, no scheduled check-in, no pause for confirmation unless something is genuinely blocking (e.g. you can't find the MR at all).

**Each round:**

1. **Re-read the diff fresh.** Don't reuse the previous round's read — include whatever was fixed last round, since a fix can introduce a new problem.
2. **Review adversarially**, looking specifically for:
   - Correctness bugs: edge cases, off-by-one, nil/empty/null handling, error paths that silently swallow failures
   - Regressions: does this change break an existing caller, test, public contract, or behavior that worked before — trace call sites of anything changed, don't just read the diff in isolation
   - Architecture: layering violations, logic living in the wrong place, coupling introduced where there wasn't any, leaky abstractions
   - Concurrency/shared-state issues, if the change touches shared state
   - Security issues, if the change touches auth, input handling, or secrets
   - Missing test coverage for the new or changed behavior
3. **Report the round's findings.** Use the `ReportFindings` tool if it's available in this session; otherwise list them plainly, most severe first, each with file, what's wrong, and the concrete failure scenario. If there's nothing to report, say so explicitly in one line — that's what counts as a clean pass.
4. **Fix every finding now**, in this same round, as real edits — not a list of things to do later.
5. **Move straight into the next round.**

**Stop condition:** two consecutive rounds with zero findings. Then summarize what was found and fixed across all rounds, and confirm the final diff is clean.

**Safety valve:** if you pass roughly 8-10 rounds without converging, stop and report what's still unresolved instead of looping indefinitely — that's a sign the change needs a human decision, not more automated passes.

## Round report format

Keep each round's report short and scannable:

```
Round N — <clean | N findings>
[if findings, one per line:]
- [severity] file:line — what's wrong → what was fixed
```

## Notes

- Don't count a fixed finding from a previous round as a new finding in the next round's report just because it's mentioned again — only unresolved or newly-introduced issues count toward the streak.
- Regression-checking means actually tracing usages, not just re-reading the new code in isolation — grep for callers of anything whose signature or behavior changed.
- If the repo has a test suite, run it as part of a round when that's fast enough not to stall the loop; treat a failing test as a finding like any other.