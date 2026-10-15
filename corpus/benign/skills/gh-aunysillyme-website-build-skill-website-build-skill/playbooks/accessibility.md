# Test whether people can complete the task

Date rule: [establish ASK DATE and revalidate claims](research-and-memory.md#ask-date-rule).
Source status: external facts and example commands are UNVERIFIED until checked for the chosen version and engagement.
Record opened URLs, source dates or unknown, actual access dates, and supporting evidence.

Question: can the site's primary journey work across input and perception needs?

## Establish the target

Start with the method's WCAG 2.2 AA baseline and verify the current W3C release,
applicable target level, and relevant criteria as of ASK DATE before relying on it.
Record a newer applicable release or erratum without silently changing an approved target.
Name each critical journey and its routes, controls, errors, and completion state.
Require manual evidence for every critical journey as well as automated checks.

## Use meaningful structure

Choose headings for hierarchy, landmarks for page regions, links for navigation,
and buttons for actions. Give controls names that make sense out of context.
Use native controls when they meet the need and test any custom control fully.
Expose expanded/selected/invalid state and relationships accurately.
Do not use an icon, color, or positional instruction as the only meaning.

## Exercise keyboard and focus

Navigate from entry through completion using keyboard only.
Test menus, dialogs, validation errors, dismissal, retry, and success.
Record visible focus, logical order, no trap, and restoration after closing overlays.
Confirm focused content is visible and not hidden behind sticky UI.
Test the escape path and focus destination when asynchronous content replaces a control.

## Compute contrast

Use a calculator or runner with actual foreground and background inputs.
For translucent layers, gradients, or images, compute the rendered composition and
inspect the relevant worst-case locations and control states.
Record font size/weight, criterion, threshold, unrounded ratio, method, and result.
The baseline text thresholds are 4.5:1 for normal text and 3:1 for qualifying large text;
verify the authoritative criteria and qualification rules before applying them.
Evaluate meaningful control boundaries and focus under their applicable criteria.
A color pair with no computed ratio is UNVERIFIED and cannot pass.
Never round a failure upward or silently change an approved brand role to claim success.

## Test communication and recovery

Associate labels and descriptions with inputs; preserve useful entered data on errors.
Explain each error, its location, and a practical way to recover.
Test status announcements with a named screen reader/browser combination.
Inspect image alternatives for their actual purpose, with empty alternatives for decoration.
Provide required media alternatives and usable controls.
Automated semantics checks supplement actual assistive-technology journeys.

## Check reflow and motion

The method proposes widths of 320, 390, 768, and 1280 CSS pixels for layout checks.
Test text zoom at 200% and reflow separately against the applicable criteria.
Record unintended horizontal scrolling, clipped controls, or hidden content.
Check target size and spacing against the verified criterion, not a remembered number.
Honor reduced motion and provide pause controls where required.
Do not make information available only through animation, hover, or precise pointing.
Inspect flashing hazards and preserve useful content without JavaScript.

## Work a small example

A dialog opens from an inquiry button, traps no user, names its purpose, and can close.
A missing required field exposes a linked error and preserves the other entries.
After closing, focus returns to the inquiry trigger.
Capture each transition and its result, not only the default dialog screenshot.

## Verify and remediate

Write site-work/qa/accessibility.md and site-work/qa/contrast.md.
For each result record route/state, candidate, tool/environment, criterion, inputs,
observed behavior, evidence, impact, owner, and retest result.
Apply checklists/accessibility.md AX01 through AX08.
Re-run failed journeys after fixes; keep meaningful regressions for repeatable failures.
Do not call an automated scanner a conformance certificate.
Unavailable checks remain UNVERIFIED with a precise test and capable runner handoff.

## Failure modes and source starting points

- Visual guess: a brand-colored button is called accessible without calculation.
- Mouse-only evidence: keyboard and error recovery remain untested.
- Scanner certificate: no violations is mistaken for complete conformance.
- Incomplete composition: opacity or image background is omitted from ratio inputs.

Open https://www.w3.org/TR/WCAG22/ and current W3C release information.
Open https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
for text contrast, with separate relevant criteria for controls and focus.
Record actual source access before adopting the baseline in a project.
