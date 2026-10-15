# Ready-to-copy JEV Anything prompts

Install the `jev-anything` skill first, then paste one of these prompts into your
coding agent. Replace bracketed text with your own details. Do not include API
keys or sensitive production data in a prompt.

## 1. Discover the best JEV use case in an existing project

```text
Use $jev-anything. Inspect this project and identify the three strongest places
where a bounded JEV decision could replace a brittle rule, repeated manual label,
or expensive LLM classification. For each candidate, state the input, the JEV
primitive, the output, the action it would control, the likely failure mode, and
whether JEV is actually a good fit. Do not change code yet. Recommend one
candidate, then walk me through the skill's planning questions.
```

## 2. Route support requests

```text
Use $jev-anything to design a support-request router. The input is [ticket fields
and source]. It should choose among [billing, technical, account, sales, or human
triage]. Help me define mutually useful criteria, include an escape option, decide
what happens on low confidence or an API error, estimate cost at [volume] tickets
per month, and get my approval before implementing it in [language/framework].
```

## 3. Score code-change risk

```text
Use $jev-anything to add a risk score for pull requests. The state can include
[title, body, changed paths, diff statistics, test status, and selected diff
content]. Propose an ordered rubric that separates trivial, normal, sensitive,
and dangerous changes. JEV must never merge or reject a PR by itself. Design the
thresholds and human-review path, scaffold the integration in [Python/TypeScript],
and add an offline test using an injectable fake decision function.
```

## 4. Add a fast guardrail before an agent

```text
Use $jev-anything to design a non-authoritative guardrail before my AI agent. The
input is [user message plus only the context needed]. I need yes/no decisions for
[prompt injection, secret-seeking, or another bounded condition]. Explain whether
each question is suitable for JEV, design fail-open/fail-closed behavior for each
action, and make borderline cases go to [a second model/a human]. Do not claim the
guardrail is safe until we have measured it on labeled examples.
```

## 5. Triage leads or inbound email

```text
Use $jev-anything to classify inbound messages into [my fixed segments] and score
their urgency. Ask me which false decisions are most costly, define the state and
criteria with me, estimate monthly cost for [volume], then adapt the included
email-triage example. Return the full probability distribution and confidence so
my application can escalate uncertain messages.
```

## 6. Replace an expensive LLM classification step

```text
Use $jev-anything to evaluate whether JEV can replace the classification-only
part of this LLM workflow: [describe the current call]. Separate bounded decision
work from any generation or reasoning that still needs an LLM. Compare the
expected cost, latency, privacy implications, and failure behavior. If JEV fits,
produce the approved plan and a small integration; if it does not, stop and
explain why.
```

## 7. Measure and tune an existing JEV layer

```text
Use $jev-anything to evaluate this existing JEV decision layer against real data.
Create a blind rating sheet from [input file], help me define valid human labels,
split the labeled set into tuning and held-out test sets, and use the included
evaluation scaffolding to report accuracy with uncertainty, confusion patterns,
confidence calibration, and cost. Improve criteria wording before changing the
confidence threshold, and preserve timestamped results for every run.
```

## 8. Batch-classify a dataset safely

```text
Use $jev-anything to design a batch classifier for [dataset and decision]. Start
with a small sample, minimize the fields sent in state, define a retry and failure
queue, return answer/confidence/probabilities for every row, and estimate total
cost before running anything. Require my approval before any paid API call or
write to the source dataset.
```

## 9. Theoretical cortextOS PR-to-software-factory example

**This is a hypothetical content/demo scenario, not a claim that this system is
currently deployed.**

```text
Use $jev-anything to DESIGN—without deploying—a theoretical cortextOS system that
routes open pull requests from a repository into a software factory.

The state may include the PR title, body, labels, changed paths, diff statistics,
CI status, and a focused diff excerpt. Propose a JEV choice question with clear
criteria for these illustrative destinations:

- quick-fix lane: small, localized, low-risk correction
- feature lane: scoped product or capability work
- maintenance lane: refactor, dependency, tooling, or infrastructure work
- docs-and-tests lane: documentation or test-dominant change
- security-review lane: auth, permissions, secrets, cryptography, or trust boundary
- human-triage: ambiguous, cross-cutting, unsupported, or low-confidence work

Show how a coding agent would interrogate the use case, draft criteria, wire the
classifier, and return a typed route with confidence and probabilities. Keep all
execution, assignment, merging, and irreversible actions outside JEV. Include a
low-confidence and API-failure path. Produce a plan and illustrative pseudocode,
not a live GitHub integration and not a claim of measured accuracy.
```

## 10. Ask the agent for a reusable handoff

```text
Use $jev-anything to finish the approved decision layer, then hand back: the
completed plan, final criteria, integration code, offline tests, live-verification
status, cost assumptions, threshold rationale, known limitations, and the exact
steps for creating a blind labeled set and re-measuring after the data changes.
Clearly separate what was tested from what is still pending.
```
