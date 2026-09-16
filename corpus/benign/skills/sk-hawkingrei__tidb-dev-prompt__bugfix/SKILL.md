---
name: bugfix
description: "Fix software bugs with root-cause analysis, minimal diffs, regression tests, and a mandatory self-check loop. Use for general bugfix work that is not covered by a more specific domain skill."
---

# Bugfix Skill

Fix bugs by proving the root cause first, then landing the smallest reviewable change that prevents the regression from returning.

Prefer a domain-specific skill when one exists. Use this skill for general bugfix work or as the shared bugfix workflow behind narrower skills.

## Required inputs

- A concrete symptom: failing test, error, log, issue link, or reproduction steps.
- Target repository, branch, and expected behavior.
- Any known constraints: compatibility baseline, public API boundaries, data format limits, performance limits, or test scope.

If an input is missing but the safe path is still clear, proceed with an explicit assumption. Ask only when the missing information can change the fix target or make the change risky.

## Workflow

1. Reproduce or pin down the symptom
   - Reduce the problem to the smallest failing command, test, request, or data shape.
   - If reproduction is expensive or unavailable, document the exact evidence used instead.
   - Record the expected behavior source: specification, compatibility baseline, previous release, user contract, or maintainer decision.

2. Localize ownership before changing code
   - Search existing code and tests with `rg`.
   - Find the narrowest module, helper, or state transition that owns the failing behavior.
   - Check nearby tests before creating new files or fixtures.

3. Build and verify root-cause hypotheses
   - List 1-3 plausible causes, ranked by likelihood.
   - Validate the most likely cause with targeted inspection, a failing test, or a small diagnostic.
   - If the evidence rejects it, update the hypothesis and continue before coding the fix.

4. Implement the smallest defensible fix
   - Change only logic on the proven root-cause path.
   - Preserve public APIs, data formats, and cross-service protocols unless the task explicitly requires changing them.
   - Avoid unrelated cleanup, naming churn, broad refactors, and speculative abstractions.
   - Prefer assertions and focused guards over debug logs.
   - Add short "why" comments only for non-obvious invariants or compatibility choices.

5. Add regression protection
   - Prefer extending an existing test suite over creating a new one.
   - Cover the exact failing shape and one nearby variant when that reduces overfitting risk.
   - Keep tests deterministic and behavior-focused.
   - Do not leave temporary logs, sleeps, or environment-specific assumptions in tests.

6. Mandatory self-check loop

```text
loop {
  ask: Is the fix minimal?
  answer: remove every line that is not required for the proven root cause.

  ask: Even if this is minimal, is it the best root-cause fix, and can the same root cause be fixed more systematically to cover more cases?
  answer: compare the local patch against the owning abstraction or invariant; keep the narrow fix only when the broader fix would widen risk or change unrelated behavior.

  ask: Is this a system design problem, and does the goal require correcting the system design instead of patching local behavior?
  answer: inspect whether the failure comes from a broken boundary, ownership model, invariant, lifecycle, or cross-module contract; if so, stop treating the local patch as complete and propose the smallest design correction that achieves the goal.

  ask: Is every added line reviewable and behavior-linked?
  answer: map each added line to a regression assertion, required invariant, or compatibility decision; remove anything without a clear mapping.

  ask: Is every claim backed by code evidence instead of memory or impression?
  answer: cite the concrete function, branch, test, trace, or data path that supports each root-cause and risk claim; if no code evidence exists, downgrade the claim to a hypothesis and verify it first.

  ask: Does the test prove the bug and avoid overfitting?
  answer: keep the exact reproduction, add one nearby variant when useful, and avoid asserting unrelated implementation details.

  verify:
    - old behavior is rejected or explained when pre-fix replay is infeasible
    - new behavior is accepted
    - targeted tests cover the changed path
    - nearby similar code was scanned for the same bug shape
    - conclusions are tied to code locations, not prior impressions

  if all checks pass: break
}
```

7. Validate and close
   - Run the smallest targeted test command that proves the fix.
   - Run formatting or linting required by the touched language when available.
   - If wider tests are too expensive, state the unverified surface explicitly.
   - Summarize the root cause, why the fix is minimal, and what remains out of scope.

## Risk gates

Stop and re-plan before making any change that:

- changes a public API, persistent format, database schema, or cross-service protocol
- rewrites large control flow without a failing test or strong evidence
- depends on data deletion, history rewriting, force push, or other hard-to-reverse operations
- trades correctness for performance without an explicit product or compatibility decision

## Reporting contract

When finishing, report:

1. Root cause and evidence.
2. Files changed and why each change is necessary.
3. Regression tests added or updated.
4. Exact verification commands run, plus anything not verified.
5. Remaining risks or follow-up work.
