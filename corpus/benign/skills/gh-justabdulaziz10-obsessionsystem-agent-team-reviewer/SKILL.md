---
name: agent-team-reviewer
description: Reviews a change against its original requirement on two separate axes, Spec and Standards/Risk, and returns classified findings with a SHIP or NO-SHIP verdict. Use when risky or substantial work is about to be integrated, or when a worker or lead reports a change as done.
---

# Agent team reviewer

Review read-only: edit no files, return findings. Scale depth to risk: a mechanical change gets a Spec check; auth, payments, privacy, secrets, schema/migrations, concurrency, or production config get the full Standards/Risk pass from `agent-risk-reviewer`.

Routing: `agent-review-route "<task>"` recommends at most three reviewers per change: one general reviewer, one Opus risk reviewer (`agent-risk-reviewer`), and at most one specialist. Each applies this protocol within its slot; do not add reviewers it did not recommend.

## 1. Input contract

Required:

- the artifact: diff, commit range, branch, or file list;
- the original requirement and acceptance criteria, verbatim.

When the requirement is missing, ask the lead for it; if none exists, report Spec as "not reviewed: no requirement". When the input includes a success claim, test summary, or the author's reasoning, set it aside until your findings are formed, then check each claim against what you ran.

Inspect actual state for the whole change, committed and uncommitted (the route's `scope` field names the base or range): `git status`, `git diff <base>...<head>`, `git log <base>..<head>`, the changed files and their callers, and the tests. Run fast checks (tests, lint, analyze) when available and label results measured.

Done when you hold the diff and the requirement and have read every changed hunk.

## 2. Review two axes separately

Spec, quoting the requirement line for each finding:

- missing or partial requirement;
- scope creep: behaviour nobody asked for;
- wrong behaviour compared with the requirement.

Standards/Risk:

- correctness and edge cases; error handling that hides failures;
- security, auth, privacy, secrets;
- data loss, migrations, schema compatibility;
- concurrency, races, ordering;
- performance regressions;
- tests missing for changed behaviour, or asserting the wrong thing;
- conventions documented in the repo's AGENTS.md, CLAUDE.md, or CONTRIBUTING.

Report the axes under separate headings. Keep each axis's ranking within that axis.

Done when every changed hunk has been considered on both axes.

## 3. Write findings

```
[BLOCKER|IMPORTANT|NIT] <Spec|Standards> <file>:<line> - <title>
Evidence: <quoted code, command output, or requirement line>
Failure scenario: <concrete input or sequence -> wrong result>
Fix direction: <one line>
```

- BLOCKER: breaks a requirement, loses or exposes data, or fails a check.
- IMPORTANT: a likely bug or real risk; fix before merge unless the lead records an accepted trade-off.
- NIT: clarity or style; never blocks.

Keep only findings with a concrete failure scenario.

Done when every finding has file:line, evidence, and a failure scenario.

## 4. Verdict

SHIP when there are zero BLOCKERs and every IMPORTANT is fixed or accepted in writing by the lead; otherwise NO-SHIP. End with per-axis counts, the worst finding per axis, and the checks you ran (measured) versus could not run (inconclusive).

## 5. Review-fix cycles

The lead passes the cycle number and the previous findings with each re-review.

- Re-review only a changed artifact.
- At most 3 review-fix cycles per change. After the third NO-SHIP, the lead escalates to the user with the open findings.
- Doubt-theatre alarm: start the report with `DOUBT-THEATRE:` and recommend escalation when 2 or more cycles ended with zero findings accepted (fixed or acknowledged), or when every finding on a substantial change is a NIT.

Source: two-axis review adapted from mattpocock/skills `code-review`; cycle bound and doubt-theatre alarm from addyosmani/agent-skills `doubt-driven-development` (both MIT).
