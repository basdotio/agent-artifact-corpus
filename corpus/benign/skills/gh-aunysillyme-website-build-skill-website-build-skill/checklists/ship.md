# Ship gate

Date rule: [ASK DATE, source evidence, and revalidation](../playbooks/research-and-memory.md#ask-date-rule).

## Record evidence before accepting a gate

- Status: PASS, FAIL, BLOCKED, or NOT APPLICABLE for each check; default BLOCKED.
- Required fields: check ID, artifact revision/digest, role and model family, method,
  environment, actual run/access time, input or claim IDs, observed result, evidence path,
  limitations, owner, and next action. NOT APPLICABLE needs a scope-specific reason.
- Passing evidence: reopen the artifact and the result; a checked box is not proof.
- Failure: any required FAIL or BLOCKED stops the dependent stage.
- Claims: UNVERIFIED describes missing proof and cannot count as a passing result.
- Spelling: treat PASSED, complete, or equivalent success labels as attempted PASS.
- Honesty: never report a measured, saved, installed, or deployed result without evidence.
- Ownership: the producer writes its receipt; Coordinator records acceptance in status.md.
- Change: revised inputs, expired sources, or a different artifact invalidate affected receipts.

## Blockers first

| Check | Reject condition | Method and required evidence |
| --- | --- | --- |
| SH01: independent family and read-only review | Review is INTERNAL, self-review, same-family, unspecified-family, or Reviewer changed the candidate. | Compare actual Builder and Reviewer family evidence, fixed inspected identity, tool constraints and unchanged candidate bytes. Different model names or roles do not prove different families. Independent gate is NOT MET and shipment BLOCKED for internal review. |
| SH02: independent ASK DATE rejection | Any acted-on library claim or top-up lacks source/access evidence, predates ASK DATE, has a false source date, expired window, or fresh stamp over unrevalidated content. | Reviewer applies research.md AD09, repeating AD01 through AD08 against scope, actual claim IDs, openings, original-access/revalidation history, all fourteen windows and later-day checks. Return read-only findings with locations and evidence. |
| SH03: reproduced dispositions | A review allegation is treated as confirmed without reproduction, a material issue is unresolved, or a confirmed fix lacks regression evidence. | Read original findings and ROUND 1 dispositions. Require before-fix failure and after-fix pass for confirmed fixes, explicit inconclusive/not-reproduced results, and post-fix affected-check results. One independent round; harness verifies corrections. |
| SH04: final artifact continuity | Promoted bytes differ from the reviewed/fixed candidate without an explained, checked change. | Compare reviewed predecessor, bounded fix diff, final harness artifact digest, upload manifest, and preview identity. No moving-branch rebuild substitutes for checked bytes. |
| SH05: prerequisite gates and approvals | Research, rights, brand selection, build, accessibility, performance/discovery, security, or required review evidence remains incomplete. | Reopen every applicable receipt and artifact. Researcher corrects library claims; owning roles correct top-ups; Coordinator accepts verified revisions without editing producer evidence. |
| SH06: concrete release authority | Target, account, project, domain, action, operator, or rollback authority falls outside recorded authorization. | Read the user's existing scope and exact prepared release plan. If missing, request authorization only after the candidate is concrete and reviewable. No implied purchases, account creation, unrelated DNS or key rotation. |
| SH07: public payload and recovery | Private work files or secrets enter deployment, or rollback/safe recovery lacks an identified target and procedure. | Inspect the final allowlist and exact artifact. Name known-working recovery identity, operator, commands, limits and verification; initial releases need an explicit safe recovery plan. |
| SH08: live routes and journey | Deployment command success substitutes for actual HTTPS, route, asset, error, or primary-action checks. | After authorized promotion, record public URLs, deployment identity/time, GET responses, mobile/desktop browser results, production CSP and complete primary journey. Critical failure triggers the authorized recovery procedure and verification. |
| SH09: live discovery and honest measurement | Canonical/schema/sitemap/llms data drift, or social caches, field results or analytics receipt are asserted without evidence. | Inspect live origin responses and discovery parity. Keep actual third-party cache/property/field observations separate; name UNVERIFIED follow-ups and measurement owner. |
| SH10: complete operations and handoff | SITE_OPERATIONS.md cannot guide a cold reader or omits what watches the site and who handles failure. | Read the one document end to end: purpose, trigger, invocation chain, dependencies, reads, writes, closed loop, failure modes, manual run/verify/recovery, source of truth. Verify tested commands; mark untested procedures UNVERIFIED. |

## Apply the two release phases

Pre-promotion requires SH01 through SH07 plus the completed operations preparation.
Record SH08 and SH09 as pending live verification, never already PASS.
Only then can Coordinator authorize Builder's release handoff within existing user authority.
After promotion, complete SH08 through SH10 against the actual public release.
The ship checklist is complete only when every required phase has evidence.
An INTERNAL review always prevents completion, even if a deployment already exists.

## Independent freshness findings

AD09 findings include confident claims without URL/access, unsupported publication dates,
misstated date provenance, mismatched openers, expired facts, and unrevalidated top-ups.
Check both source dates and access events; a regex cannot prove a page was opened.
A derived-floor receipt repeats the limitation and blocks decisions needing an exact day.
Coordinator captures findings unchanged. Researcher corrects canonical evidence;
owners correct their top-ups. Repeat failed checks and normal fix verification without
starting a second independent audit round. Keep dependent acceptance BLOCKED until resolved.

## Final release receipt

Record reviewed identity, final identity, actual families, dispositions, authorization,
deployment receipt, live verification, recovery outcome, operations path, limitations,
and next owner. PASS means the named checks completed on the named artifact.
A review-ready draft can remain useful while shipment is BLOCKED.

