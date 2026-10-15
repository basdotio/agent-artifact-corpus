ASK DATE prerequisite: follow playbooks/research-and-memory.md#ask-date-rule.
Researcher establishes it before intake or research; later roles read scope.md.
Never ask the user for the date or infer it from model knowledge. Apply the
same source, two-date, freshness, reuse, and blocked-gate rules to this stage.

Audit accessibility on the built site, with WCAG 2.2 AA as the stated baseline target.
Verify the current W3C release as of the ASK DATE, record the applicable version and
level, and flag any newer applicable criteria before relying on the baseline.
Distinguish automated from manual evidence.

MEASURE
- Use a calculator or test runner for contrast; never estimate a ratio by eye.
- Normal text needs at least 4.5:1; qualifying large text needs at least 3:1.
- Record font size/weight and the applicable criterion before choosing the threshold.
- Check meaningful non-text control/focus contrast under the relevant criteria.
- Test actual composited backgrounds, overlays, images, opacity, and all control states.
- Do not round a failing result into a pass. Record tool, input colors, and raw result.

EXERCISE
- Navigate the primary journey with keyboard only, including menus, forms, and dialogs.
- Confirm visible focus, sensible order, no trap, and correct focus restoration.
- Check semantic landmarks, heading order, link names, labels, errors, and status updates.
- Test with a screen reader where available; report the actual browser/tool combination.
- Check reflow, 200% text zoom, touch targets, and content at narrow widths.
- Honor reduced motion and required pause controls; avoid information available only
  through animation, color, hover, or pointer precision.
- Give images purposeful alternatives and decorative images empty alternatives.

DISPOSITION
- Report issue, route/state, affected user task, criterion, evidence, and proposed fix.
- Automated scanners are supporting evidence, not a certificate of conformance.
- Re-run each failed journey after a fix and keep a regression for repeatable defects.
- Save site-work/qa/accessibility.md and contrast.md.
- If you cannot run a check, mark it UNVERIFIED and name the exact manual or tool test.

EVIDENCE
Never report a measured, saved, installed, or deployed result without evidence.
Apply the stage route and named checks in manifest.json before handing off.
