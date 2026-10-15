---
name: debug
description: "Systematic debugging: reproduce first, write a failing test, classify the bug L1/L2/L3, find the root cause before changing code, apply the minimal fix and prove it with the same test. Use when something is broken, a test fails, or behaviour is unexpected."
---

# Debug

A green gate made green by hiding the bug is worse than the bug. When the honest fix is hard, do the hard thing or stop and say so.

## Honesty invariants
- **H1 Independent oracle.** Expected values come from an independent source (closed form, separate script, sympy, reference implementation) — never copied from the code under test's own output.
- **H2 Real API.** Convergence/order/slope tests call the real public entry point on coarse vs 2×-fine inputs; never an inline re-implementation of the kernel.
- **H3 Thresholds fixed before measuring.** Never widen a tolerance or bound to pass. A stale reference is regenerated from the oracle, not absorbed by the threshold.
- **H4 No unverified claims.** No asserted property, bound, order or citation in code, docs or comments unless verified — never to make something compile or pass.
- **H5 Explicit error over silently wrong.** A path that cannot be correct returns a typed error, even if an "approximation" label is tempting. A relabeled wrong path is still wrong.
- **H6 Loud preconditions.** If a test family can degenerate into a tautology (commuting operators, trivial input, constant collapsing the term under test), assert against it.
- **H7 Fail before, pass after.** Show the gate failing on the pre-fix code and passing after, with both outputs.
- **H8 Evidence.** "Fixed" requires: the failing and passing output, the named oracle, and the diff.

If an honest fix is infeasible (no independent oracle, unprovable property, unimplementable path), report that plainly. A truthful "could not fix this honestly" is acceptable; a dishonest green is not.

## Repair gate (every fix)
- **G1 Red first.** Before editing source, have a test that fails on the current code and isolates this bug. Run it and show the failure.
- **G2 Green twice.** After the fix, the same test passes and the relevant suite stays green. Show both.
- **G3 Root cause, not symptom.** State: "the underlying cause is …; this will not reopen because …". Clamping a value, widening a tolerance, swallowing an error, or guarding one call site of N is a symptom patch and will come back.
- **G4 Origin.** Name the commit that introduced the bug: `git blame -L <start>,<end> <file>`, then `git log -1 <sha>`. If it cannot be attributed, say why.

## Procedure

### 1. Context
- Extract from the report: symptom, stack trace, affected files, expected vs actual.
- Find or write the reproducing test (G1). No test framework nearby → a minimal script that exits non-zero on the bug.
- Read the implicated code around the failure point.
- `git log --since="7 days ago" --oneline -- <file>`; `git show <sha>` on suspicious recent changes.
- If logs/traces exist: follow the correlation/trace id, look at what happened just before the error, check for swallowed exceptions near it.
- Write a hypothesis: evidence → cause → confidence.

### 2. Localize
- Run the failing test with short tracebacks; parse the deepest frame in project code.
- Rank suspect locations: direct failure point first, then callers, then test setup.
- Read ~15 lines around each top suspect. Confirm or reject the hypothesis against the code, not intuition.

### 3. Classify
| Level | Signals | How to proceed |
|---|---|---|
| L1 simple | One file, clear stack trace, cause confirmed | Minimal patch directly |
| L2 medium | 2–4 files, no stack trace, or unclear cause | Hypothesis-driven: list candidate causes, design one experiment per cause (log, assertion, bisect), eliminate until one remains |
| L3 complex | 5+ files, complex logic, or cause spans components | Run in order: localization (which files/functions), analysis (why, step by step), fix (patch) — finish each before the next |

`git bisect run <test-cmd>` is the default tool when a known-good commit exists.

### 4. Patch
- Smallest change that removes the root cause; aim ≤10 changed lines for L1.
- Consider 2–3 candidate fixes; choose the one that closes the failure class, not the one site.
- No unrelated edits.

### 5. Validate
- Run the G1 test: must now pass.
- Run the full relevant suite before and after; any test that passed before and fails now is a regression → reject the patch.

### 6. All candidates fail → re-plan
After 3 rejected candidates, stop patching:
- All caused regressions → design flaw; the fix belongs at a different layer. Re-read the architecture (`arch.md` if present) and restate the problem.
- All failed the repro test → the hypothesis is wrong; return to step 1 with the new evidence.
- Never try candidate #4 of the same approach.

## Report
```
Root cause: <one sentence>
Why it won't reopen: <one sentence>
Introduced by: <sha|unknown: reason>
Repro: <command>  before: <fail output>  after: <pass output>
Suite: <counts before / after>
Diff: <files changed>
```
