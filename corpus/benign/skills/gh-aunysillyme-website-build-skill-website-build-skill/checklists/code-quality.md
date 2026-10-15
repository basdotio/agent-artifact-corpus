# Code quality gate

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
| CQ01: current coding standards | Coding starts without saved, current standards for the selected stack, or acted-on claims lack opened sources. | Reopen site-work/coding-standards.md and Builder's learning receipt. Verify the ASK DATE opener, exact versions or dated targets, source URLs/access dates, feature support, and freshness rechecks against the accepted library. |
| CQ02: versions and supported patterns | Code or configuration drifts from pinned versions, uses listed deprecated APIs, or relies on unsupported features without the recorded fallback. | Compare source, manifests, lockfile, runtime/compiler configuration, and rendered behavior with the standards file. Record inspected paths and tests of required fallbacks. |
| CQ03: executed quality commands | Applicable tests, lint, format checks, or type-checks fail, are unrun, or lack recorded output. | Run the standards file's unit, integration, end-to-end, lint, format-check, and type-check commands on the candidate. Save commands, environment, exit codes, full output, and artifact identity; give inapplicable checks a scope-specific reason. |
| CQ04: dependency hygiene | A dependency lacks a requirement, versions or lockfile permit unexplained drift, or advisory findings lack disposition. | Compare the dependency inventory with the policy; verify pinned versions, lockfile, reproducible install, and audit command output. Record applicable findings, remediation or evidenced disposition, owners, and recheck dates. |
| CQ05: secure coding | Templates, scripts, URL handling, or secret boundaries violate the stack's secure-coding rules. | Inspect source and rendered output; run synthetic escaping, script-terminator, unsafe-URL, and invalid-input cases. Record results and a secret-boundary check without recording secret values. |
| CQ06: review evidence | The candidate lacks a code-review receipt against its standards, or material findings remain unresolved. | Builder records inspected revision, organization/pattern checks, findings, and dispositions before handoff. Include design-token drift (hard-coded values bypassing tokens) and repeated copy-paste implementation shortcuts among the pattern checks, and verify each finding in source before recording it. Reviewer challenges this checklist against the same standards and candidate at Challenge; retain the independent receipt and confirmed-fix regressions for shipment. |

## Gate receipt

List the standards revision, source and candidate identities, command output paths,
dependency dispositions, secure-coding evidence, review receipt, and unresolved limits.
Builder completes these checks before review dispatch; independent Challenge and ship
gates still require their own receipts.
