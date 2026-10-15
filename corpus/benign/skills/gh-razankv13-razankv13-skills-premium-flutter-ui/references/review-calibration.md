# Review Calibration

Use for every numerical screen/flow rating. This evaluates UI, not this skill's documentation. The craft checks live in `craft-rubric.md`; this file owns scoring and severity.

## Evidence and scope

Name the surface, product goal, applicable states, and supplied evidence before scoring. Distinguish inspected code, rendered output, widget/semantics tests, assistive-technology checks, and physical-device profiling. A screenshot alone cannot prove recovery, activation, or performance. Mark missing evidence **unverified**, and give a score range instead of silently passing it. Never infer a tested behavior from an illustrative example.

## Five dimensions: 0–2 each

| Dimension | 0 | 1 | 2 |
|-|-|-|-|
| Hierarchy and task clarity | Main task or essential information is obscured | Task is clear but a competing element or weak grouping slows it | Primary job, information order and action priority are clear with representative content |
| Product coherence | Inconsistent tokens/assets or decoration undermines meaning | Mostly coherent with a localized inconsistency | Tokens, type, imagery and controls form a consistent system grounded in the brief; no novelty quota |
| States and recovery | A required state loses input, misleads or blocks recovery | Required paths work but a minor feedback or recovery detail is weak | Loading, empty, error, success and repeated/cancelled actions satisfy the surface's state contract |
| Accessibility and localization | A required access path fails | Essential access works with a minor non-blocking improvement remaining | Applicable semantics, keyboard, contrast, targets, scale, RTL, localization and reduced-motion checks pass |
| Layout and runtime resilience | Constraints, media or workload break the surface | Layout works but a minor stability or measured performance issue remains | Representative widths, insets, keyboard and media are resilient; measured performance evidence supports claims where motion/workload creates risk |

For an unverified dimension, show its supported lower bound through 2 (use 0–2 if no bound is supported). Sum bounds for the overall range. Do not renormalize away a relevant missing check. A static surface without network or motion may earn full marks for its actual states; record why other branches are not applicable.

Scores: 0–3 broken; 4–6 substantial defects; 7–8 solid with localized gaps; 9–10 polished and verified. Use whole points and cite one observation for each deduction. Taste alone never costs points. Any P0/P1 defect makes completion **FAIL** and caps the score at 6, even if the arithmetic sum is higher. A cap is a safety gate, not an extra deduction per issue.

## Severity

- **P0:** task can cause data loss, an unintended irreversible action, or a security/privacy failure.
- **P1:** a core task or supported access path fails: inaccessible activation, unreadable essential text, clipped commit control, or no recovery from a normal error.
- **P2:** localized friction or craft inconsistency with the task and essential access intact.

## Worked example: saved-address form

This is an authored calibration scenario, not a real app audit or an executed benchmark. Assume supplied evidence includes rendered narrow-phone light/dark and 2x/RTL views, semantics/activation tests, and native focus/announcement checks. Network tests confirm save, server error and retry preserve input; no decorative animation or heavy workload warrants a performance claim.

| Dimension | Observation | Score |
|-|-|-|
| Hierarchy | Address fields lead to one visible Save address action; helper text supports entry | 2 |
| Coherence | The same field, spacing and typography tokens are used throughout | 2 |
| States | Save blocks repeat submission, preserves input on failure and confirms completion; the recoverable server-error copy lacks a useful next step beyond Retry | 1 |
| Accessibility/localization | Evidence confirms one localized button announcement, keyboard access, contrast/targets, long strings, 2x scaling and RTL | 2 |
| Resilience | Save remains reachable above the keyboard; validation messages grow the layout without clipping | 2 |

**9/10, P2:** improve the recoverable server-error guidance. A different palette or default platform control would not lower this score.

Counterexamples using the same screen:
- If Save instead exposes duplicate text but remains operable, record a P2 announcement defect and reassess the accessibility dimension; repeated text alone is not automatically P1.
- If Save lacks a semantics tap action, accessibility is 0 and the P1 gate caps the result at **6/10, FAIL** until fixed.
- If only an idle screenshot is supplied, states and accessibility are unverified and runtime claims stay unverified. Report a range and the exact missing evidence, not 9/10.
