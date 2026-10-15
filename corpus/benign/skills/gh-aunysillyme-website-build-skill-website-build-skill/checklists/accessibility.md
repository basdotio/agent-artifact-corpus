# Accessibility gate

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
| AX01: computed contrast | Contrast is asserted without a computed ratio, raw inputs, applicable threshold, or actual rendered composition. | Calculate each text/control/focus pair with tool or runner; record actual colors, opacity/background, route/state, font size/weight, criterion, unrounded ratio and result. Never round a failure into PASS. Missing calculator access is BLOCKED, not visual approval. |
| AX02: current target and semantics | Standard/level has no current source record or controls/headings/landmarks misrepresent purpose. | Read ASK DATE research and source claims, inspect semantic structure and accessible names on each representative route. Record current version and applicable criteria. |
| AX03: keyboard and focus | Primary journey traps focus, hides focused content, or fails to restore focus after a dialog. | Complete keyboard-only navigation, menus, dialogs, submission, dismissal, and recovery. Record steps, environment, focus order/visibility, and actual outcomes. |
| AX04: forms and announcements | Inputs lack associated labels/errors, status is silent, or entered data is lost without reason. | Trigger invalid/loading/error/success states; use a named screen reader/browser pair to inspect labels, descriptions, status and recovery. Retain manual results. |
| AX05: reflow and targets | Narrow widths or zoom clip essential content, create unintended scrolling, or leave unusable controls. | Test declared widths, text zoom, reflow, long content and applicable target criteria. Preserve screenshots, computed sizes, and target/source evidence. |
| AX06: motion and media | Meaning depends only on motion/color/hover, required alternatives or pause controls are absent, or flashing is unchecked. | Test reduced motion, keyboard/pointer alternatives, media alternatives, pause behavior, decorative image semantics, and content without JavaScript. |
| AX07: manual journey coverage | A scanner result substitutes for manual checks or an untested tool combination is claimed. | Map each critical journey to a recorded human/runner interaction and actual assistive setup; retain automated output separately. State unavailable checks as UNVERIFIED with a settling test. |
| AX08: remediation and retest | A reported fix has no repeated failed journey or unresolved critical issue is hidden by a score. | Link finding, changed artifact, repeated scenario, evidence, and useful regression. Inspect the final candidate rather than the pre-fix screenshot. |

## Gate receipt

Save qa/accessibility.md and qa/contrast.md under site-work with all required fields.
Brand-stage contrast uses the same AX01 calculation contract.
Automated tools support evidence; they do not establish full conformance by themselves.
No blanket accessibility claim is allowed beyond the inspected scope and results.

