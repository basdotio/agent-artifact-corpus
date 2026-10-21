---
name: talwar-pm-issue-tree-skill
description: Decompose a fuzzy problem into a MECE (Mutually Exclusive, Collectively Exhaustive) tree of branches down to testable hypotheses. Use whenever the user has a big vague problem ("why is retention dropping," "why did the launch underperform") and needs to break it down systematically, says "help me structure this problem," or is about to start investigating without a clear map of what to rule in or out.
---

# Issue Tree

## Why this matters

Most problem investigations fail not from lack of data but from lack of structure — people chase the first
plausible hypothesis that comes to mind, find some supporting evidence (because you can always find some), and
stop looking. A classic McKinsey-style issue tree forces the alternative: state the core question, break it into
branches that are Mutually Exclusive and Collectively Exhaustive (MECE) so no possible cause is double-counted or
silently missing, and keep decomposing until each leaf is a testable hypothesis rather than another vague question.
The tree is the difference between "investigate why retention dropped" and a checklist you can actually falsify one
branch at a time.

## Gather inputs first

Before drafting, get (ask if not given, and make a reasonable assumption out loud if told to proceed without asking):

- **The core question**, stated precisely — "why is retention dropping" is vaguer than "why did 90-day retention
  for cohort X drop 8 points starting in March," and precision here determines whether the tree can be MECE at all
- **What's already known or ruled out** — don't rebuild branches the user has already tested
- **Available data sources** to test each hypothesis against, so the tree ends in testable leaves rather than
  further speculation
- **Time/depth constraint** — a tree for a 30-minute triage looks different from one for a quarter-long
  investigation

## Process

1. **State the core question at the top**, phrased so it has a definite answer in principle (a number moved, an
   outcome did or didn't happen) — not a philosophy question.
2. **Choose one consistent basis for the first split** and make it MECE. Common bases: a funnel/process stage
   (acquisition → activation → retention), a population segment (new vs. existing users), a causal category
   (product, market, execution), or a time-based before/after. Pick one basis per level — mixing bases within a
   level is the fastest way to break MECE.
3. **Check MECE at every level before going deeper**: do any two branches overlap (a user event could sit under two
   branches)? Is there an obvious category missing (often "external/market factors" gets silently dropped because
   nobody on the team owns it)? If either check fails, fix the split before decomposing further — errors compound
   downstream.
4. **Continue decomposing each branch until it's a testable hypothesis**, not another question. "Onboarding is
   broken" is still a question. "Users who don't complete step 3 of onboarding within 24 hours churn at 2x the
   rate" is a hypothesis — it has a specific test against data.
5. **Attach a test and an owner to each leaf hypothesis.** A tree that ends in untested hypotheses is just a fancy
   outline; the point is to prioritize which branches to actually go test.
6. **Prune ruthlessly.** Not every branch deserves equal depth — decompose furthest where the hypothesis is both
   plausible and cheap to test; leave low-plausibility branches at a shallower level with a one-line reason they're
   deprioritized, not deleted.

## Output template

```markdown
# Issue tree: [Core question]

**Core question:** [Precise, answerable-in-principle question]

## Branch 1: [Category — split basis: e.g. funnel stage / segment / causal type]
- **1.1 [Sub-branch]**
  - Hypothesis: [testable, specific statement]
  - Test: [data/experiment that would confirm or kill it]
  - Owner: [who checks this]
- **1.2 [Sub-branch]**
  - Hypothesis: [...]
  - Test: [...]

## Branch 2: [Category, same split basis as Branch 1]
- **2.1 [Sub-branch]**
  - Hypothesis: [...]
  - Test: [...]

## Branch 3: [Category, same split basis]
- [...]

## MECE check
- Overlap check: [any hypothesis that could sit under two branches — resolved how?]
- Completeness check: [what category almost got left out, and why it's included/excluded]

## Priority order to test
1. [Highest plausibility × lowest cost to test]
2. [...]
```

## Quality checklist

- [ ] Does every branch at a given level use the same split basis (no mixing funnel stage with causal category
      in one level)?
- [ ] Could any single piece of evidence belong under two different branches? If so, MECE is broken — fix it.
- [ ] Is there a branch for the category people usually forget (external/market factors, or "nothing is actually
      wrong, this is noise")?
- [ ] Does every leaf read as a testable hypothesis with a named test, not as a restated question?

## Related skills

- Turn the top hypothesis into a formal comparison of options: `talwar-pm-decision-framework-skill`
- Once a leaf points to a cause, size the fix as an initiative: `talwar-pm-initiative-canvas-skill`
- Use the tree's structure as the backbone of a narrative: `talwar-pm-executive-storyline-skill`
