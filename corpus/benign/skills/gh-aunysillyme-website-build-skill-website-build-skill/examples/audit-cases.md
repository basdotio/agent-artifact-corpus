# Synthetic audit cases

Date rule: [ASK DATE and evidence discipline](../playbooks/research-and-memory.md#ask-date-rule).
Everything in this example is invented. It is not a real organization, person, project,
source-opening receipt, measurement, approval, or deployment.
Do not import example state as evidence for a live engagement.

Use these invented cases to rehearse rejection behavior on a disposable candidate.
They are test data, not claims that measurements or browser tests have been run.

## Two accents doing one job

Input: primary actions use #DA6736 on the home page and #D85F30 on workshop cards.
Both claim the same action token and no state distinction or approved exception exists.
Expected finding: token drift with both exact values, roles and locations.
Reject with brand-and-mockups.md BM02 until source evidence resolves intentionality.
Do not merge them solely because they look similar.
Retest: inspect the approved action mapping on every route and in hover/focus states.

## A weak primary action

Input: the inquiry action is visually quiet and described as accessible without a ratio.
Expected finding: contrast is UNVERIFIED; appearance is insufficient evidence.
Reject with accessibility.md AX01 and brand-and-mockups.md BM03.
Record actual rendered foreground/background, opacity, font size/weight, criterion,
calculator or runner, unrounded ratio, and result before proposing a shade or role change.
No ratio is invented in this example.
Retest: compute again after the approved correction and complete the real inquiry journey.

## Empty provider identifier

Input: a published workshop record has an empty optional demonstration-provider ID.
Faulty output: a Watch demonstration link whose URL has an empty provider suffix.
Expected finding: dead control generated from absent optional data.
Reject with build.md B04, including whitespace-only and malformed-ID variants.
Correct behavior: keep the workshop content, omit the provider link and player,
record the omission, and emit no provider request before or after absent-control handling.
Required provider data would instead fail validation with record/field context.
Retest: inspect generated HTML, DOM and network requests; verify a valid ID still works.

## Stale metadata after a content change

Input: the workshop title changes in its visible record but the social title, sitemap
location, or llms.txt entry still comes from an independently maintained list.
Expected finding: source-to-output drift on the identified candidate.
Reject with performance-seo.md PS06 and build.md B03.
Correct behavior: derive the public surfaces from the same validated route/content registry.
Retest: change one synthetic record, rebuild, and inspect initial HTML and discovery output.
Verify intentional private or draft exclusions remain excluded.

## False completion labels

Input: no source was opened, but research is labeled complete.
Reject with research.md AD07; query plans do not satisfy current research.
Input: Builder reviews its own work and marks independent review complete.
Reject with ship.md SH01; record INTERNAL and independent gate NOT MET, ship BLOCKED.
Retest: require actual source-opening evidence or different-family review as applicable.
Changing the label cannot repair either missing capability.

## Capture a useful finding

Record case, candidate identity, location, preconditions, reproduction action, observed
result, user impact, confidence, smallest fix and the check proving the fix.
A pattern match is a lead. A defect claim requires reachable behavior and evidence.
Builder reproduces returned allegations before fixing or reporting them as confirmed.
Record ROUND 1 dispositions and before/after regression results without adding an audit loop.
