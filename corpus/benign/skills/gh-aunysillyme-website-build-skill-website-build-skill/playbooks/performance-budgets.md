# Measure the experience against explicit budgets

Date rule: [establish ASK DATE and revalidate claims](research-and-memory.md#ask-date-rule).
Source status: external facts and example commands are UNVERIFIED until checked for the chosen version and engagement.
Record opened URLs, source dates or unknown, actual access dates, and supporting evidence.

Question: is the site fast enough for its visitors' routes, devices, and primary tasks?

## Set route budgets before implementation

Select representative routes: the main entry, a repeated content page, and the heaviest journey.
Record viewport, device/CPU/network profile, cache state, tool version, and route state.
Choose transfer, script, image, and third-party budgets from actual content and audience needs.
Name the owner, rationale, method, and exception process for each budget.
Do not invent a universal byte allowance or silently enlarge a missed target.

## Separate proposed targets from evidence

The method proposes a Lighthouse mobile performance median of at least 90 per route.
The field baseline to revalidate is p75 LCP at most 2.5 seconds, INP at most 200 ms,
and CLS at most 0.1, assessed separately by device class and reporting window.
These numeric baselines are UNVERIFIED for the current engagement until the authoritative
source is opened and its source date, access date, release, and applicability are recorded.
Do not cite this playbook as proof of current external thresholds.

Lab scores diagnose a controlled run. They do not establish real-user p75 or interaction quality.
A new site can lack sufficient field observations; record UNVERIFIED, the follow-up owner,
when to check again, and the intended data source. Do not invent a field PASS.

## Run a repeatable lab series

1. Build the identified candidate and serve its production output.
2. Fix the environment, route state, and cold-cache conditions for the series.
3. Run three comparable mobile Lighthouse measurements for each representative route.
4. Retain every raw report, run timestamp, environment, and command.
5. Use a calculator or runner to compute the median; retain its inputs and result.
6. Compare the result to the recorded budget and investigate the causes of misses.

Discard a run only for an evidenced invalid measurement, preserve it with the reason,
and rerun under the same conditions. Never select only the best report.
Budget exceptions need a named decision, remaining impact, and evidence, not a disguised PASS.

## Diagnose and improve

Use the trace to identify hero discovery delays, blocking resources, image overfetch,
font swaps, third-party work, and unnecessary JavaScript.
Test a bounded change and compare the same route under the same conditions.
Use image-pipeline.md, self-hosted-fonts.md, and embed-facades.md for focused corrections.
Keep animation optional, honor reduced motion, and suspend decorative work in hidden tabs.
Check useful initial content and the primary navigation with JavaScript disabled.

## Work a small example

A route loads its local poster immediately but delays the third-party player until activation.
Compare cold traces before and after the facade change.
Inspect the pre-click request log and test keyboard activation before accepting the gain.
A smaller transfer with a broken player fails the journey gate.

## Save the evidence

Write site-work/qa/build/performance.md with artifact identity, route budget table,
raw report paths, computed medians, field-data status, failures, and follow-up owners.
Apply checklists/performance-seo.md PS01 through PS04.
Unknown tool access leaves measurement UNVERIFIED with commands for a capable runner.

## Failure modes and source starting points

- Lab/field substitution: a single score is called real-user performance.
- Cherry picking: the best of several runs replaces the recorded series.
- Budget drift: limits change after a failure without a reviewable decision.
- Optimized screenshot: interactivity, reduced motion, and hidden-tab work go unchecked.

Open https://web.dev/articles/defining-core-web-vitals-thresholds for field definitions.
Open https://developer.chrome.com/docs/lighthouse/performance/performance-scoring
for the chosen Lighthouse version and score interpretation.
Keep source-opening receipts separate from site measurement reports.
