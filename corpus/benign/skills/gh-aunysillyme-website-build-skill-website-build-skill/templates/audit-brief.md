# Independent audit brief

Date rule: [ASK DATE and evidence provenance](../playbooks/research-and-memory.md#ask-date-rule).
This is a blank artifact contract. Fill it from actual inputs and evidence at runtime.
Unresolved required fields keep the relevant gate BLOCKED; never prefill a PASS.

## Candidate and authority

Record exact immutable artifact/revision and source identity, intended release target,
authorized review scope, Builder's actual model family and evidence, and Reviewer's family.
Different model names within one family do not satisfy independence.
If independence is absent, record INTERNAL and independent gate NOT MET, shipment BLOCKED.
Reviewer owns no filesystem paths; Coordinator captures returned bodies unchanged.

## Runtime and reproduction

Name stack/runtime/version, host response classes, dependencies and build environment.
Provide exact clean-build, preview, test and reproduction commands with actual prior results.
State how a capable runner can use a disposable candidate without changing reviewed files.
Name tools or checks that remain unavailable as UNVERIFIED.

## Callers and threat model

Inventory public routes, endpoints, users, auth roles, integrations, forms, uploads,
content inputs, secret boundaries and data movement relevant to this candidate.
Identify attacker-controlled inputs and the permitted scope of negative testing.
Keep secrets and unrelated private content out of the packet.

## Design reasoning to challenge

| Decision | Requirement | Reasoning | Alternative | Evidence | Risk or limit |
| --- | --- | --- | --- | --- | --- |

Explain state computation, rendering contexts, URL rules, empty-ID handling,
resource permissions, cache behavior and any server/client trust boundaries.

## What was verified

Link current research/library and top-up revisions, source-opening receipts,
selected mockup, rights evidence, build/adverse cases, accessibility, performance,
metadata, enforced headers, scanner result and exact candidate digest.
Identify each remaining blocker or uncertainty explicitly.

## Review instructions

Read-only: inspect complete relevant flows and supporting source evidence.
Repeat AD01 through AD08 as independent AD09, including reuse and later-day freshness.
Challenge source assumptions against actual generated/live behavior.
For each finding return location, preconditions, reproducible steps/test, observed result,
impact, confidence, narrow fix guidance and inspected identity.
Separate reproduced defects, evidence-backed risks and unverified hypotheses.
If no findings are supported, return an explicit scoped no-findings result and limits.

## ROUND 1

| Finding | Reproduction evidence | Disposition | Fix identity | Fails before | Passes after | Final candidate |
| --- | --- | --- | --- | --- | --- | --- |

Use confirmed, not reproduced, accepted limitation, or unresolved with evidence.
Only confirmed fixes receive a defect claim; each gets a meaningful regression.
An accepted limitation does not waive a mandatory release gate.
Verify affected checks on the final artifact; do not start an automatic second audit round.
Coordinator records acceptance after inspecting original findings and Builder dispositions.
