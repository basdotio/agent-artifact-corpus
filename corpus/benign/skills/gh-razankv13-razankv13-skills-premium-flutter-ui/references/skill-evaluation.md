# Skill Evaluation

Maintenance only. These authored scenarios test whether an agent applies this skill consistently; they are not evidence of a shipped app's quality. Use them after changes to routing, defaults, state contracts, or evidence rules. The bundled Dart tests exercise the reference component separately.

## Procedure

Give each scenario's Prompt and Input to a fresh agent with this skill. Keep the acceptance checks hidden until grading. Requests below are reviews of supplied evidence: no production edits or external actions. Save the response, mark every acceptance check pass/fail/unverified, and cite the response supporting each pass. A missing required observation is a failure; a stated lack of runtime evidence is expected. Fix guidance only when the miss exposes ambiguity or missing coverage, then repeat the failed scenario.

## Form: uncertain write and dismissal

**Prompt:** Review this Flutter edit-address sheet. Give prioritized findings and the smallest fixes. Do not implement changes or claim tests ran.

**Input:** The draft is owned by the sheet. Save sends a request; the server can commit before the client times out. Timeout shows “Save failed” and Retry repeats the write. There is no offline queue or known idempotency contract. `PopScope(canPop: !dirty)` surrounds the editor, but `showModalBottomSheet` uses default drag/barrier dismissal. The actions have no bottom safe-area or keyboard padding. No screenshots, test results, or native-access checks are supplied.

**Acceptance:**
- Flags uncertain completion and requires reconciliation/existing idempotency before another write; invents no offline queue.
- Covers drag, barrier, explicit close, and system-back draft protection; distinguishes these dismissal paths.
- Requires reachable actions under keyboard/system insets and identifies the missing rendered/access evidence.
- Uses findings with evidence and minimal fixes; makes no verified quality or test-pass claim.

## Search: reversed completion and numeric locale

**Prompt:** Review this search/filter behavior for implementation risks. Give prioritized findings, minimal fixes, and focused checks.

**Input:** Request A searches “tea”; request B then searches “teapot”. B succeeds first, then A fails and clears the results. The widget is disposed while a third request remains pending. The price filter offers a decimal keyboard but parses text using `double.parse` with no validation. A supported locale uses comma decimals. No render, semantics, native, or performance evidence is supplied.

**Acceptance:**
- Guards both stale success and stale error, preserving B's valid results; names a reversed-completion check.
- Separates widget disposal/mounted checks from request cancellation and state-owner lifetime.
- Treats keyboard type as an input aid; handles locale, pasted/temporary invalid text, finite values, and domain range/precision before commit.
- Names focused failure checks and leaves appearance, access, and performance unverified.

## Refinement: protect scope and meaning

**Prompt:** Review a proposed spacing-only change to an existing Flutter navigation bar. Recommend the smallest correction.

**Input:** The app intentionally uses purple, rounded shapes, and stock Material controls. Existing tokens and navigation behavior are consistent. The proposed diff changes label padding but also replaces the palette/font and adds a new navigation package. At the project's large-text test size, ellipsis makes two destination labels identical. Only before/after screenshots and this diff summary are supplied.

**Acceptance:**
- Preserves the deliberate brand, framework controls, and navigation behavior; removes unrelated redesign/dependency changes.
- Treats indistinguishable labels as a task/access defect, not an acceptable fixed-height shortcut; proposes shorter localized labels or adaptive layout while preserving full semantic names.
- Restricts validation to the affected layout/states, with runtime/access checks marked unverified.
- Does not award a precise full-screen score from screenshots; if asked for a score, follows `review-calibration.md` evidence ranges.
