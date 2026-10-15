---
name: capacitylab-compare-results
description: "Compare a CapacityLab Result with its baseline or another comparable Result: comparability reasons, requirement changes, measured deltas, regression or improvement, and marking a Baseline Result. Use when the user asks to compare load test runs, check for a performance regression or verify that a fix helped."
metadata:
  source: capacitylab://knowledge/workflows/compare-to-baseline
---

Use the tools of the CapacityLab MCP server (`capacitylab`). If they are not available, ask the user to connect it from the AI agents page of CapacityLab Console; do not call the API another way. This skill is generated from the resource capacitylab://knowledge/workflows/compare-to-baseline; when the server serves a newer text, follow that.

# Compare a Result with its baseline

1. Read the Result with `capacitylab.results.get`. Its `comparisons` hold the latest previous, the previous comparable and the Baseline Result of its series. With an explicit `baselineResultId`, read that Result too and check that both belong to the same series with `capacitylab.results.series.get`.
2. Compare only comparable experiments. Two Results are comparable when their comparable experiments are equal; otherwise the read lists every differing part as a reason. Show incomparable numbers only with that flag and never draw a regression or improvement from them. Equal secret bindings mean the same Account secret names in the same placements, never equal values or application state.
3. Name `requirementChanges` separately: a changed SLO, assertion or knob changes what was judged, not what was measured. Workload and Load Spec revisions are provenance, not the comparison key.
4. Report the deltas as observed facts with both Results' `howItWasEvaluated`. Keep hypotheses (for example a deploy between the two Load Runs) separate, each with one concrete falsifier, and state what the evidence does not show.
5. To mark a Baseline Result, a member with `test_design:edit` asks for it explicitly; call `capacitylab.results.baseline.set` or `capacitylab.results.baseline.clear`. A mark changes what the next No Regression Load Spec pins; it never rewrites an already resolved Load Spec or a published Result.
6. No Regression replays the Baseline Result: No Regression replays its Baseline Result, allows p95 to grow by 15% and errors to reach 2 × the baseline, each above the rule's floors. A No Regression p95 may exceed the baseline by its tolerance or 20 ms, and its error ratio the baseline ratio by that ratio or 0.5%. It runs in its baseline's zone. To test one hypothesis, change exactly one variable against the baseline and state its falsifier before resolving the new Load Spec.
7. Comparison never resolves, compiles or confirms. A new Load Run needs a separate member request and explicit approval of that exact Load Plan digest and US-dollar price before `capacitylab.runs.confirm`.
