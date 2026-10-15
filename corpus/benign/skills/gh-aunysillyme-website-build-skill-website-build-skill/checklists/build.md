# Build gate

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
| B01: authorized inputs and stack | Code begins before accepted research and named mockup selection, or a dependency has no requirement. | Read brief, selection, current library/top-ups, ownership.yaml, and stack.md alternatives. Verify exact implementation root and chosen version/API evidence. |
| B02: validation before rendering | Malformed required data reaches output or errors lack record/field context. | Run synthetic invalid/duplicate slugs, malformed dates, missing required content, and broken relationships. Preserve failing build output and corrected rerun. |
| B03: data-only next item | A repeated item requires copying pages or separately editing discovery lists. | Add a representative synthetic record on a disposable candidate; inspect generated route, navigation, title, canonical, social data, sitemap, and llms.txt. |
| B04: empty identifier rejection | Any link, CTA, player, or iframe renders against an empty, whitespace-only, malformed, or absent required identifier. | Render empty and whitespace optional IDs and inspect HTML/DOM for absent controls and provider requests. Require omission report. Malformed required IDs fail validation; no empty href, dead fragment, or empty URL suffix is permitted. |
| B05: context-safe output | Quotes escape attributes, hostile text becomes markup, script terminators escape JSON, or unsafe URL schemes survive. | Render quotes, ampersands, angle brackets, a script terminator plus markup, and a javascript-scheme URL. Parse actual output; require inert text, valid script-safe JSON, and rejected unsafe actions. |
| B06: state and clock parity | Page, badge, control, feed, and discovery state disagree or dates use an implicit timezone. | Test before/at/after boundaries with an explicit clock and timezone. Verify one shared state decision and a documented rebuild trigger or manual owner. |
| B07: deterministic clean artifact | The build needs undocumented state, output changes without explained inputs, or generated output was hand edited. | Run the documented clean build, record tool/dependency versions and result, compare repeat output, and preserve artifact identity plus output allowlist. |
| B08: integration and design fidelity | Integrated assets/discovery drift from approved revisions or selected mockup. | Read source handoffs and compare rendered mobile/desktop output; preserve producer files and identify copied revisions. Replay the selected layout defaults (brand-and-mockups.md BM05) against the built page at the recorded mobile and desktop viewports, and log any mismatch or approved brand-decision exception. |
| B09: critical journeys and states | The main action, validation, empty/error/loading/success state, or no-JavaScript content fails. | Exercise each applicable state on the exact candidate and retain route, environment, screenshots, and functional outcomes. Apply accessibility and performance/discovery gates. |
| B10: truthful handoff | Unrun tests are called passed or output lacks reproduction commands. | Open build receipts, QA reports, limitations, artifact digest, next owners, and the audit packet. BLOCKED checks remain visible. |
| B11: code quality | Any required code-quality check is FAIL or BLOCKED. | Apply [checklists/code-quality.md](code-quality.md) CQ01-CQ06 to the exact candidate and coding-standards.md revision; reopen the standards, command output, dependency/security evidence, and Builder's review receipt before handoff. |

## Gate receipt

List source and output identities, clean command results, adverse-case evidence,
next-item proof, state/route parity, selected-design checks, and unresolved limits.
The build gate prepares QA and independent review; it does not authorize deployment.

