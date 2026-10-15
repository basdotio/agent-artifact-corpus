ASK DATE prerequisite: follow playbooks/research-and-memory.md#ask-date-rule.
Researcher establishes it before intake or research; later roles read scope.md.
Never ask the user for the date or infer it from model knowledge. Apply the
same source, two-date, freshness, reuse, and blocked-gate rules to this stage.

Run one independent adversarial audit of this fixed release candidate.
The reviewer must be a different model family from the builder.
If that is unavailable, prepare the review packet and mark independence incomplete.

PREPARE THE AUDIT_BRIEF
- Identify runtime, exact revision or artifact digest, routes, callers, and trust boundaries.
- State threat model, authorized review scope, and what tests already passed.
- Explain design decisions and why they were made so the reasoning can be challenged.
- Include how to reproduce the build and which output is proposed for release.
- Exclude secrets and unrelated private content from the review packet.

REVIEWER INSTRUCTIONS
- Work read-only against the named source/artifact. Do not fix implementation files.
- Challenge untrusted input handling, script-bound JSON, attributes, URL schemes,
  empty IDs, state/date edges, resource permissions, public endpoints, and exposed secrets.
- Look for mismatches between source assumptions and generated or live behavior.
- Inspect relevant flows fully; a pattern match is a lead, not a confirmed vulnerability.
- For each finding, give location, preconditions, reproducible steps or a test,
  observed result, impact, and a narrowly described fix.
- Distinguish reproduced defects, evidence-backed risks, and unverified hypotheses.
- Return an explicit no-findings result if that is what the review supports.

BUILDER DISPOSITION
- Reproduce each finding before fixing or relaying it as fact.
- Record confirmed, not reproduced, accepted limitation, or unresolved, with evidence.
- For each confirmed fix, add a regression that fails before and passes after the fix.
- Re-run affected checks against the final artifact.
- Record ROUND 1 in the brief with finding, disposition, test, and final artifact identity.
- Use the harness to verify the fixes; do not start an automatic second audit round.
- Do not bury an unresolved material issue inside a claim that the review passed.

FINISH
Return the reviewed identity, reviewer family, findings, dispositions, regression results,
remaining limits, and whether the concrete release candidate meets the agreed gates.
This audit is evidence, not a guarantee that no other defects exist.

EVIDENCE
Never report a measured, saved, installed, or deployed result without evidence.
Apply the stage route and named checks in manifest.json before handing off.
