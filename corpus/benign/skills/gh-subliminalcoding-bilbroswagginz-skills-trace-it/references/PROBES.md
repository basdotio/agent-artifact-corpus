# Probe Recipes & Trap Craft

Companion to trace-it. Pick the cheapest probe class that can decide the
hypothesis; every recipe assumes the hard rules (minimal, structured, correlated,
prod-safe, decommissioned).

## Part 1: Probe classes (cheapest decisive one wins)

### Structured log line (default)

One line per probe point, fields not prose:

```
{"probe":"invoice-render-start","req":"<corr-id>","items_resolved":false,"items_count":0,"ts":"..."}
```

Rules: a stable `probe` name (greppable, removable), the correlation id, the
*values the hypothesis is about* (not "got here" but "got here WITH x=null"), and
machine timestamps. "Got here" breadcrumbs are only legal as a pair bracketing a
suspected non-return, and they still carry the id.

### Trace span

When the hypothesis is about *ordering, latency, or fan-out* ("B starts before A
finishes", "the retry storms"), a span with the correlation id as trace id beats
log archaeology: parent/child + timestamps answer interleaving questions logs
make you reconstruct by hand. Use the project's existing tracer if one exists;
a hand-rolled span = two structured log lines (start/end) sharing a span id.
Don't install an observability platform to catch one bug.

### Metric / counter

When the hypothesis is about *rate or proportion* ("some requests skip the cache")
and per-event capture would drown: a counter pair (hits/skips) or a histogram,
tagged with the smallest cardinality that decides the hypothesis. A metric locates
*that* it happens and how often; you'll usually follow with a sampled log probe on
the rare branch to see *why*. That's two passes, and that's fine.

### Crash/state capture

When the bad state is a corpse, not an event: enable core dumps for the target,
add an assertion that dumps state when the "impossible" invariant breaks (a
tripwire: it captures and continues or aborts per severity; it does NOT handle
the error and hide it), or attach a debugger (gdb-for-debugging if installed,
plain gdb/lldb otherwise) to the live hung process.
For kernel/syscall-shaped hypotheses on Linux, `strace`/`bpftrace` on the sampled
target is a probe too; zero code change is the cheapest probe there is.

### Differential trace

When one request works and its twin doesn't: capture the full probe set for a
known-good and a known-bad execution and diff them. Turns "read the trace" into
"read the divergence"; the first differing field is usually the located cause.

## Part 2: Correlation-id threading

- One id per unit of failure (request, job, message), generated at the boundary,
  passed through every hop the hypothesis crosses, including into queues and
  background workers, which is exactly where it's usually dropped and exactly
  where the interesting bugs hide.
- If the codebase has no id plumbing, thread it through ONLY the suspect path.
  This is a probe, not an observability initiative. (If the pass ends with "we
  should have this everywhere," that's a decision-inbox item, maybe a promotion.)
- The symptom's user-visible artifact should carry the id when possible (error id
  in the response/PDF/email) so a field report can be joined to its trace.

## Part 3: Traps and amplifiers

The probe watches; the trap makes the symptom walk past it.

- **Wait (prod, sampled):** arm and let real traffic trigger it. Set a trap window
  up front ("48h or first capture") so waiting is a decision, not a drift.
- **Replay:** captured real requests against a probed sandbox: the best of both
  when the symptom follows data, not load.
- **Amplify** (shared with test-max's flake-zero matrix): loop the operation
  100+×, run it under real parallelism, perturb timing (injected delays at
  awaits/IO, CPU load, clock skew/freeze). Which amplifier fires names the class:
  loop → inherent nondeterminism; parallelism → shared state; timing → race.
- **Starve/chaos:** for resource-shaped hypotheses, cap memory (e.g. via memguard
  profiles on a memory-constrained host), fill the disk to N%, drop/delay the
  dependency. Confirm the hypothesis by *making* the rare condition common.

## Part 4: Prod-safety checklist (before arming anything in prod)

- Sampled or rate-limited if on a hot path (1–5% decides most hypotheses;
  a per-user allowlist decides the "one user" ones at 100% for just them).
- No secrets, tokens, or raw PII in fields; hash or id-reference instead.
- Cost bounded: log volume estimated, cardinality of metric tags bounded.
- Behavior-neutral: no new failure modes (probe errors are swallowed AND counted),
  no lock taken, no await added inside a critical section.
- Removal path as easy as installation: one grep for the probe names, one revert.

## Part 5: Promote-vs-remove checklist (decommission gate)

Promote a probe only if ALL hold; otherwise remove:

1. It guards an invariant that actually broke (not "might be handy").
2. It's re-sited to the right place and named/leveled like the codebase's real
   telemetry, not like a debug session (`probe-tmp-2` does not get promoted).
3. Someone would act on it firing. Ideally it becomes an alert; a promoted probe
   nobody watches is removal with extra steps.
4. It passes the prod-safety checklist permanently, not just for the trap window.

Record the verdict table (probe → REMOVED/PROMOTED + one-line why) next to the
located cause. That table plus the capture is this skill's entire output.
