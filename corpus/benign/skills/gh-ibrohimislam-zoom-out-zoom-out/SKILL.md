---
name: zoom-out
description: >
  Before declaring any bug fix, root-cause diagnosis, or plan complete, force
  a Hypothesis Ledger that includes a mandatory zoom-out (non-local)
  hypothesis: is the thing you just handled one instance of something bigger?
  Use 5 Whys, systems thinking, and information-gain gates on every probe to
  separate real recurrence from speculation. Use whenever you're about to say
  a fix/plan/diagnosis is done, before shipping a config, alert, query, test,
  or script built from an investigation, whenever an explanation you found
  "fits" the symptom, or when the user says "zoom out", "think bigger", "is
  that the whole picture", "why only X", or otherwise pushes back on a narrow
  fix/plan.
---

Default is correction and rigor, not agreement or speed. A clean explanation
that fits the symptom is not a verified explanation of the full scope.

## Core

Evidence comes from instances: one call site, one host, one request, one
device. Conclusions and deliverables claim a scope: every place the cause
operates, everything a fix, config, alert, or test covers. This skill keeps
the claimed scope from silently differing from the verified scope.

Scope goes wrong in two directions:

- Too narrow: stopping at the instance while the class exists, or shipping a
  value that holds only where it was observed.
- Too wide: "maybe this is systemic" with no mechanism, or searching broadly
  for vibes.

Both have the same fix: name the recurrence signature, then enumerate.

Budget rule: spend little on the investigation, never on scope. The narrowing
rules below (information-gain gates, the hypothesis cap, search bounds,
dropping uninformative steps, proportionality) decide which probes to run and
how much ledger to write. They never shrink what a claim or deliverable
covers. The costs are not symmetric: a dropped probe can be rerun, but a
member dropped from coverage fails silently, because nothing reports a gap in
coverage. A request for focus, signal, or less noise in a deliverable is about
how precisely it detects, not how many members it covers.

## Primitives

Scope: the set of members a claim explains or a deliverable covers. Name it
explicitly: "all four hypervisors", "every caller of parseDate", "all
tenants on the v2 schema".

Recurrence signature: the mechanism that makes members alike, and so predicts
where else the defect appears:

- same generated source,
- same template,
- same shared utility,
- same schema or contract,
- same data path,
- same abstraction layer,
- same process gap,
- same missing guardrail.

In a deliverable, the signature becomes a role: the stable identifier that
picks out the same thing in every member (the pool's device-mapper name, not
the disk it happened to sit on in one host).

Enumeration: the cheapest check. List the members and check each one, rather
than reading the claim or deliverable and judging that it looks general. The
list is often already in earlier output (an orientation map, a grep, an
inventory, the config that defines the targets, a design doc), returned but
not acted on because it did not look relevant to the one spot being chased.
Re-read what you already have before querying again.

Ledger: the bookkeeping for the investigation. Hypotheses H1, H2, H3, the
probe for each, and a status for each:

proposed / tested / strengthened / weakened / eliminated / inconclusive /
survived.

Every step after the ledger references a hypothesis ID and updates its status.
A step that does neither is uninformative — drop it.

Informative = evidence that can change hypothesis ranking or the next action.
Uninformative = vague or duplicate hypotheses, broad searches, uncontrolled
tests, flaky observations, stock categories, plausible speculation.

## 1. Before concluding: generate, climb, write the ledger

Generate hypotheses before reaching a conclusion, never after. If hypotheses
only show up wrapped around an answer already picked, discard the frame and
restart from decomposition.

Climb from the instance to the system, one level at a time:

1. Instance: what exact defect was observed (symptom), and what directly
   produced it (proximate cause)?
2. Class: is this one member of a larger class? What recurrence signature
   identifies the class?
3. System: what allowed the proximate cause to exist or go unnoticed; what
   structure, workflow, missing test, contract, or ownership gap made that
   possible; and what incentive, assumption, feedback loop, or missing
   guardrail makes it recur?

For each step up, ask: what evidence links it to the level below, what
cheapest observation would confirm or weaken the link, and does fixing this
level prevent recurrence or only move the symptom? Do not jump to the system
level without a concrete class-level signature. Do not ask "why" mechanically;
stop when the next level has no discriminating evidence, is out of scope, or
has low expected information gain, and record where you stopped and why.

At the system level, ask:

- What shared code, schema, config, generator, template, policy, contract,
  dependency, or data path could carry the same mechanism elsewhere?
- What feedback loop hides the problem until it becomes visible?
- What missing guardrail would have caught this earlier?
- If only the local instance is fixed, can the system still produce the same
  defect? If yes, the narrow fix is not the full deliverable unless scope is
  explicitly reduced.

Then write the Hypothesis Ledger: at least three hypotheses, each with
mechanism, expected evidence, cheapest test, and assumption load. Admit a
hypothesis only if it has a concrete mechanism, a locus or layer where it
operates, an observable trace, and a cheapest discriminating probe.
Hypotheses must be mechanistically distinct; merge any two that differ only
in wording. Cap active hypotheses at three unless a fourth has unusually high
expected information gain.

One hypothesis is always reserved for zoom-out: the instance in front of you
is one member of something bigger. What that "bigger" is isn't fixed in
advance; work it out from what is actually there, not from a stock category.
The zoom-out hypothesis must state concretely:

- the larger class,
- the recurrence signature,
- where recurrence would appear,
- the cheapest way to check.

Reject "maybe this is systemic", "maybe there are other cases", or "maybe the
architecture is wrong" unless translated into mechanism, locus, observable
trace, and recurrence signature.

Shapes this takes:

- A fix at the one call site reported, while the same helper is used the same
  way in six others.
- An alert pinned to the disk device that saturated on the host under
  investigation, while the job scrapes four hosts whose disk layouts differ.

## 2. Each probe: gate it

Before running any test, search, inspection, or probe, state which hypothesis
it targets, what result would strengthen it, what result would weaken or
eliminate it, and the verdict if the result is ambiguous. Do not run a probe
whose result would not change hypothesis ranking or the next action.

Where possible, use a baseline, one variable at a time, a known-good and
known-bad case, listed confounders, and a reproduction. Flaky, irreproducible,
or confounded evidence is uninformative: stabilize it or mark the hypothesis
inconclusive. Do not build systemic conclusions from one unstable signal.

Search only where the current mechanism predicts recurrence. Do not expand
scope unless the mechanism predicts where similar instances should appear.
Stop expanding when more search has low expected information gain.

Evidence rules:

- Eliminate a hypothesis only on a discriminating test or explicit
  contradiction, never on plausibility alone.
- A hypothesis explaining what was reported is not evidence it covers the full
  scope; that is the failure this skill exists to block.
- Weak or confounded evidence raises uncertainty; rank instead of pruning.
- Rank survivors by fewer assumptions, shorter causal chain, and greater
  testability, but evidence beats simplicity: a hypothesis that explains more
  and survives a check beats a simpler one that doesn't.

## 3. Converging: decide the scope, then check coverage

Converge only once a hypothesis survives an attempted falsification.

If the zoom-out hypothesis survives (the pattern really does recur), its scope
becomes the deliverable, not the original instance. The deliverable is one of:

1. Category fix: fix or diagnose the whole class.
2. Guardrail fix: add the missing test, constraint, lint, review gate,
   contract, schema rule, or observability that prevents recurrence.
3. Systemic recommendation: change the process, ownership, interface,
   incentive, or architecture that produces the class.
4. Explicit scoped exception: deliberately fix less than the class, stating
   exactly what is excluded and why before calling it done.

Never silently downgrade a systemic finding back into a local fix.

If the zoom-out hypothesis is eliminated, state which recurrence checks were
run and why stopping at the instance is justified. State residual uncertainty
rather than forcing closure.

Coverage check. A category or guardrail fix covers only what it reaches.
Before calling it done, enumerate the members the recurrence signature names
and confirm the deliverable reaches each one. Reaching a member means acting
on the same role or mechanism inside it, not just matching it in a selector.
Fix any member it misses, or name it in an explicit scoped exception.

A deliverable built for the same system after a zoom-out survived
(monitoring, alerts, tests, policy) is that class's guardrail fix, even when
the user asked for it as a separate task. Run the coverage check on it too. A
guardrail built at instance scope for a class-scope finding is a silent
downgrade: it looks like the systemic fix and covers one instance.

## 4. Building: every carried value is a scope claim

Writing a value from the evidence into a deliverable (a config, query, alert,
test, fix, or script) claims that the value holds across everything the
deliverable covers. For each identifier or threshold carried over, ask:

- What population does the deliverable claim to cover?
- Does this value hold across that population, or only in the instance where
  it was observed?

Enumerate the value across that population: a label's values across every
scrape target, a field across all rows, a path across all hosts. If it varies,
select by the role that picks out the same thing everywhere, or state the
narrower scope explicitly.

How strongly a value stood out in the incident (the busiest device, the
loudest error) is evidence about that instance, not evidence that it
generalizes.

These gaps produce no symptom: the deliverable runs and looks fine while
covering less than it claims. So run this check before shipping, even when
proportionality skips the full ledger. When a ledger exists, the enumeration
is the zoom-out probe for the deliverable: record it under a hypothesis ID.

## 5. Challenged: enumerate, don't argue

When the user asks "why only X", or you find yourself explaining why a
conclusion or deliverable covers this device, host, or case and not the
others, that is a claim about scope. Answer it with the enumeration, not with
arguments. If the enumeration shows members you did not cover, the scope was
wrong: fix it or state the exception.

## Proportionality

This is a discipline, not a report. For a real bug fix, root-cause claim, or
plan, the ledger can be one line per hypothesis.

Skip the full ledger only for genuinely single-instance, non-recurring work: a
typo, a one-off script with no siblings, a content-only change, or an isolated
manual operation. Even then, answer "nothing bigger here" fast by checking for
a recurrence signature, not by manufacturing ceremony.

Proportionality decides how much ledger to write, never what a deliverable
covers. Skipping the ledger does not skip the check in section 4.
