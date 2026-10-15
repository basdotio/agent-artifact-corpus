# Promote an exact, operable release

Date rule: [establish ASK DATE and revalidate claims](research-and-memory.md#ask-date-rule).
Source status: external facts and example commands are UNVERIFIED until checked for the chosen version and engagement.
Record opened URLs, source dates or unknown, actual access dates, and supporting evidence.

Question: can a cold reader release, verify, and recover this site from one document?

## Establish release authority and identity

Require the brief, user selection, current research, QA receipts, independent review,
and ROUND 1 dispositions with regressions on the final candidate.
Name target account, project, domain, operator, and authorized action.
Existing explicit authorization is sufficient within its scope.
If authority is missing, finish the reviewable candidate before asking at that boundary.
Do not infer permission to buy services, create accounts, change unrelated DNS, or rotate keys.

Record source revision, build environment, immutable artifact digest, and preview identity.
If review fixes changed the candidate, retain the reviewed predecessor, explained diff,
post-fix harness, and final digest. Unexplained changes invalidate affected evidence.
Identify a known-working rollback artifact and its documented restoration command.
An initial release needs an explicit safe recovery plan when no predecessor exists.

## Prepare and promote

Build cleanly using the documented command and locked dependencies where applicable.
Inspect the actual upload allowlist for research, private assets, credentials, and unrelated files.
Test the preview's routes and production configuration before promotion.
Promote the checked bytes rather than rebuilding from a moving source revision.
Record the command/action, actual response, deployment identifier, timestamp, and public URLs.
A successful command is evidence of a deploy operation, not a working public journey.

## Verify the live release

Check HTTPS, canonical hosts, redirects, intended routes, error paths, and assets.
Complete the primary journey, including validation, submission, and recovery.
Inspect actual CSP and other headers on all response classes.
Check canonical metadata, social images, sitemap, llms.txt, and intentional exclusions.
Inspect mobile and desktop behavior with production CSP enforced.
Separate social-bot origin responses from third-party preview-cache results.
Verify analytics at the intended property; loading a script does not prove receipt.
Record absent field observations as UNVERIFIED with a follow-up owner.

If a critical check fails, use the authorized recovery plan and verify the restored journey.
Record both the failure and recovery evidence; do not hide rollback under a release PASS.
Apply checklists/ship.md SH01 through SH10, including distinct pre-promotion and live phases.

## Write one complete operations document

Builder writes SITE_OPERATIONS.md in the authorized implementation root.
Use templates/site-operations.md and replace blank contract fields with actual evidence.
Keep these sections in order:

1. What and why: purpose, audience, primary action, and deployed identity.
2. Trigger: manual or scheduled content, build, and release events with owners.
3. Invocation chain: editing through validation, build, preview, promotion, and verification.
4. Dependencies: versions, host, integrations, credentials by mechanism only.
5. Reads: content, assets, tokens, environment names, and approved external resources.
6. Writes: generated output, deployed targets, logs, and runtime side effects.
7. The closed loop: watcher, expected signal, cadence, recipient, and response.
8. Failure modes: symptoms, diagnosis, recovery, and escalation owner.
9. Run-and-verify by hand: exact working commands, success evidence, and rollback.
10. Source of truth: source, deployed artifact, research/approval revisions, and maintenance owner.

Name what watches the site, including nothing. Silence is not a monitoring plan.
Include enough content-editing and recovery detail to avoid requiring a second document.
Every untested command or procedure says UNVERIFIED and names the settling test.
Never write secret values, authenticated URLs, or personal credentials into the document.

## Maintain the result

Record who adds content, approves brand changes, updates dependencies, and checks measurements.
Scheduled publication requires an actual trigger; date-dependent templates do not self-run.
Revalidate expired host, license, security, and search facts before later releases.
Re-run checks affected by changed content, resources, forms, or dependencies.
Keep rollback identities and retention limitations explicit.

## Failure modes and sources

- Artifact drift: deploying unreviewed files after a green harness.
- False live proof: command success replaces browser and response evidence.
- Missing loop: nobody receives an alert or knows how to run a manual check.
- Untested recovery: a rollback command is documented as verified without a run.

Open the selected host's current deployment, promotion, and recovery documentation.
Record version, plan restrictions, actual access evidence, and authorized runtime receipts.
No host procedure is assumed to work because this package describes it.
