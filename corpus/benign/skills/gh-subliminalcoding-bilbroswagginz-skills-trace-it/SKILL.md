---
name: trace-it
description: >-
  Make an un-reproducible symptom observable BEFORE anyone touches a fix: install
  the minimal structured logging/tracing/metrics that turns "it sometimes does X"
  into a located cause, gate on the instrumentation actually capturing the bad
  state, then remove or promote every probe deliberately. Use when a bug can't be
  reproduced on demand, "it only happens in prod / sometimes / for one user", a
  heisenbug, a symptom with no failing test, or before handing a vague defect to
  no-slop-bug-hunter.
---

# Trace It

no-slop-bug-hunter's contract opens with "the bug is reproduced — if it can't be
reproduced, it hasn't been found." This skill is what you run when you can't satisfy
that line. It fixes nothing. Its entire job is to convert a vague symptom into
evidence: a captured trace showing the bad state, and a one-sentence located cause
you can hand downstream. It sits upstream of no-slop-bug-hunter and bug-zero the way
hotspot-scout sits upstream of optimize-proof: the finder half, kept strictly apart
from the fixer half.

> **Core Insight:** The gate is that **the instrumentation reproduces the
> hypothesis**: a probe you installed captures the bad state (the wrong value, the
> impossible interleaving, the call that never came) before any product code
> changes. Until you hold that capture, you have a theory, and fixes built on
> theories are guesses that sometimes compile. The discipline cuts both ways:
> no fixing before the capture, and no probe left behind after. Instrumentation is
> scaffolding, and scaffolding left up becomes the "fix" nobody can explain in six
> months.

## The contract

Before installing any probe, the following must be written down:

1. **The symptom, as an observation.** "3 users/week get a blank invoice PDF."
   Not "PDF generation is broken"; that's already a theory wearing the symptom's
   clothes.
2. **One falsifiable hypothesis.** A sentence a probe could confirm or deny: "the
   render starts before the line-items query resolves." If no probe could deny it,
   it isn't a hypothesis, it's a vibe.
3. **The minimal probe set that decides it.** Which values, at which points, with
   which correlation id. If the probe list reads "add logging to the module," start
   over: you're instrumenting the codebase, not the hypothesis.
4. **A fix freeze.** No product-code change other than instrumentation until the
   gate passes. The urge to "just fix the likely thing while we wait" is the urge
   this skill exists to kill.

## Hard rules while probing

- **Instrument the hypothesis, not the codebase.** A handful of probes per pass.
  Carpet-logging produces a haystack and calls it observability.
- **Structured, correlated, or it didn't happen.** Every probe emits fields (not
  prose) and carries the request/job/session id end to end. An uncorrelated log
  line from a concurrent system is gossip. Recipes in
  [references/PROBES.md](references/PROBES.md).
- **Probes must be prod-safe by construction:** sampled, rate-limited, no secrets
  or PII in fields, no behavior change beyond negligible cost. A probe that changes
  timing enough to hide the bug is evidence in itself (see anti-patterns).
- **One hypothesis per probe set.** Probes for a dead hypothesis come OUT before
  the next goes in. Accumulated zombie probes are how carpet-logging happens one
  reasonable step at a time.
- **Logging is never the fix** (no-slop rule, inherited verbatim). The capture is
  the end of THIS skill, not the end of the bug.

## The pass structure (capped)

**Per pass:**

1. **HYPOTHESIZE:** one falsifiable sentence, ranked from the symptom's shape
   (per-user → state/data; intermittent under load → race; time-of-day → clock,
   cache expiry, cron; one host → environment).
2. **PROBE:** install the minimal set; deploy to where the symptom lives.
3. **TRAP:** arm it and make the symptom come to you: wait on real traffic, replay
   captured requests, or amplify (loop, parallelism, clock skew: the same
   amplification matrix flake-zero uses; see PROBES.md Part 3).
4. **READ:** did the capture confirm, deny, or miss?
   - **Confirmed** → GATE PASSED. Write the located cause in one sentence with the
     capture attached. Hand to no-slop-bug-hunter (or the bug-zero pipeline).
     Then decommission (below).
   - **Denied** → the hypothesis is dead, which is progress. Pull its probes,
     next hypothesis.
   - **Missed** (symptom fired, probes saw nothing) → the probes are in the wrong
     place; the miss narrows where the cause ISN'T. Re-site, same hypothesis, one
     more trap.

**Cap: three dead hypotheses without a capture → stop.** The next move is not a
fourth guess. Widen the trap (more traffic, longer window, heavier amplification),
take a fundamentally different probe class (a crash-state capture instead of logs,
a differential trace of a good vs bad request), or run problem-breakthrough on the
framing. Escalate to the operator if the widening has real cost (prod sampling rate,
retention).

## Decommission (the second gate: the pass isn't over at the capture)

Every probe installed gets an explicit verdict, recorded next to the located cause:

- **REMOVED:** the default. Scaffolding comes down.
- **PROMOTED:** deliberately kept as permanent observability: named, leveled,
  documented, added at the *right* place (which is often not where the debug probe
  sat), and justified in one line ("this invariant broke once in prod; this line
  is the alarm"). Promotion is a decision, never inertia.

A probe with no verdict is a leak. `git diff` against the pre-pass checkpoint must
show only promoted probes when this skill exits.

## Stopping condition

Done = a captured trace showing the bad state **and** the capture repeats (re-arm
the trap once; a capture you can't get twice is an anecdote) **and** the cause fits
in one sentence a fixer can act on. Not "we added good logging." That's the
consolation prize, and it's claimed via promotion, explicitly, or not at all.

## Anti-patterns that look like progress

- **Fix-on-theory:** shipping the "likely fix" with the probes still armed "to
  confirm." If it was confirmable, confirm first; if the fix works you've learned
  nothing and left probes behind.
- **Carpet logging:** instrumenting the whole module because the hypothesis is
  weak. Weak hypothesis → sharpen the hypothesis, not the coverage.
- **The vanishing act as victory:** the probe changed timing and the bug stopped.
  That's not fixed, that's a race with a flashlight in its eyes: hand the evidence
  to deadlock-finder-and-fixer (if installed; otherwise switch to a timing-free
  probe class such as a crash/state capture).
- **Leaving debug probes in as the outcome:** "at least we'll see it next time"
  without the promotion decision. Next time is exactly when the uncorrelated,
  unleveled probe will mislead someone.
- **Uncorrelated probes:** five log lines that can't be joined to one request
  prove nothing in any system with concurrency, i.e. every system.
- **Probing without the written symptom/hypothesis:** you'll read whatever the
  logs show as confirmation of whatever you already believed.

## THE EXACT PROMPT

```
/trace-it
Target:  <project path>
Symptom: <the observation, verbatim — what happens, to whom, how often>
Lives:   <where the symptom occurs: prod / staging / CI / one host>
Budget:  <hypothesis cap per run; default 3>
```

## References

- [PROBES.md](references/PROBES.md): probe recipes (structured logs, spans,
  metrics, crash-state capture), correlation-id threading, prod-safe sampling,
  trap amplifiers, and the promote-vs-remove checklist
