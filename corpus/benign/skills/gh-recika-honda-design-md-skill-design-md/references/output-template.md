# DESIGN.md output template, token sourcing, and the completeness bar

Read by SKILL.md Step 5. Format follows the Google design.md spec (alpha):
https://github.com/google-labs-code/design.md (docs/spec.md). Front matter holds tokens,
the body holds prose and rules, `{group.key}` references a token. The linter rejects
duplicate headings and preserves unknown sections and token groups, which is what lets
this skill add `elevation`, `motion`, `breakpoints` groups and its own body sections.

Language: English body. The `Brief (Japanese)` section is the signed-off brief, verbatim.

## The completeness bar

Quality is measured by what the file lets a builder do, not by its length. A file passes
when every item below is present and filled with substance (no section one-lined, no
`<...>` left). Most complete files land between 200 and 700 lines; that range is a sanity
check, never a target. Under 200 usually means a section was one-lined; over 700 usually
means padding or components the site does not have.

The file must have:

- The full color role set derived from the chosen primary (brand, containers and on-colors,
  surfaces, text, borders, semantic, state variants, scrim, focus ring): roughly 24 roles.
- Type roles across display / headline / title / body / label: at least 9.
- A spacing scale of 8 steps plus `section`, `gutter`, `container`.
- Elevation levels 0 to 5 with CSS shadow values; motion durations (short / medium / long)
  and 3 easings; 4 breakpoints and a responsive table with one row per breakpoint.
  Exception: when a `take` or `said` line rules shadows or motion out, that group holds one
  token (`elevation.level0: none`, `motion.duration-short: 0ms`), and the `Elevation &
  Depth` or `Motion` body section (still present; no `##` section is deleted) says what
  carries depth and feedback instead (borders, surface tone, an instant color change). That
  token is `chosen: site N` when the picked option's patterns cover the group and the site
  itself shows none; otherwise `# defaulted: no shadows; for pick "<option text>", site N`
  (or `no motion`).
- Components that exist on THIS site: the ones the user picked, plus the ones the Page
  Structure actually uses. `nav`, `footer`, and `button-primary` are on almost every site;
  `button-secondary`, `text-input`, `card` and the rest appear only when Page Structure has
  them. Never write a component the site will not have. Interactive components carry
  hover, focus, active, disabled siblings.
- Interaction state matrix, Motion, Imagery & Iconography, Voice & Content, Accessibility,
  Do's and Don'ts, Known Gaps: none skipped or one-lined.
- Every chosen, derived and defaulted token traced (tier comment), every open token listed
  in Known Gaps with the question the owner must answer.

## Token sourcing: four tiers, never a fifth

Every token value carries its tier in a trailing comment. The tier belongs to the VALUE, not
to the attribute: the user may choose "a giant thin wordmark", but if the 96px comes from
this skill's defaults, the 96px is `defaulted`, and its comment names the pick.

| Tier | When | Comment form |
|---|---|---|
| chosen | the user picked the interview option that covers this token on a site (its path matches a `take N` line in picks.txt, or a `said N` line when the user answered in free text) and the value is that site's, read from one source in the SKILL.md Step 2 order (the rendered page at 1440px, else facts.txt; a screenshot read by eye never gives a number or hex), or the user typed the value | `# chosen: site 2 (airbnb.com)` or `# chosen: user` |
| derived | computed mechanically from chosen values by a public rule in sec.1-7 or sec.9 of `references/derivation-rules.md` | `# derived: <rule>, sec.N` e.g. `# derived: M3 tone T90, sec.1` |
| defaulted | this skill's own recommended value (sec.8 of `derivation-rules.md`), or an "unverified" row used as a stated choice, or a value the skill supplies to realize a pick that has no literal value on the site ("device fonts" written as `system-ui`); it yields to any chosen value or a reason in Intent | `# defaulted: <row>, sec.8` plus `; for pick "<pick>", site N` when a pick triggered it; a value supplied for a pick with no sec.8 row: `# defaulted: <what>; for pick "<option text>", site N`, the text copied exactly from a `take N` or `said N` line |
| open | no chosen input, no rule and no default can bridge the gap | in `colors` / `typography` / `spacing` / `rounded`: OMIT the key and leave a comment line `# <key>: open (TODO: decide), see Known Gaps` (the linter rejects a placeholder value); in body prose: the literal `TODO: decide` |

Every leaf value in `colors`, `typography`, `rounded`, `spacing`, `elevation`, `motion` and
`breakpoints` carries its own trailing comment, including repeated ones (a `fontFamily`
repeated in every role, `none: 0px`). Trailing comments add no lines, and the validator
(`scripts/check-design-md.sh`) checks each one.

Rules:
- Derivation is mandatory, not optional. If a chosen primary color exists, the full role set
  (containers, on-colors, surfaces, outlines, state overlays, dark scheme) is derived. A file
  that leaves derivable tokens as `TODO` fails the completeness bar.
- `derived` never cites sec.8. A value computed from a defaulted input (the two reading
  columns computed from the defaulted 1120 container) is `derived` and cites its own rule;
  the input it starts from keeps its own tier.
- Derivation never overrides a chosen value. A chosen hex stays as chosen even if the rule
  would compute a slightly different tone; the rule fills the roles around it. If the
  chosen hex fails WCAG contrast in a text role, keep it as a brand swatch and derive a
  passing tone for the text role, and say so in the Colors body.
- Rows marked "unverified" in derivation-rules.md are inputs the skill chooses and names as
  choices (`# defaulted: type ratio 1.25, unverified row`), never cited as rules.
- Two sites chosen for the same attribute: the user's free text decides; absent that, ask one
  question before writing. Never average or blend.
- Component tokens reference other tokens with `{colors.x}` syntax; a raw hex inside
  `components` is an error. The spec's normative component properties are
  `backgroundColor`, `textColor`, `typography`, `rounded`, `padding`, `size`, `height`,
  `width`; others (`borderColor`, `borderWidth`, `shadow`) are preserved with a lint
  warning, which is acceptable. States are sibling entries (`button-primary-hover`,
  `-active`, `-disabled`, `text-input-focus`), the pattern the richest public files use.
- `{ref}` syntax resolves only into the spec's groups (`colors`, `typography`, `spacing`,
  `rounded`). A reference into `elevation`, `motion`, or `breakpoints` is a lint ERROR
  inside `components`: write the literal value there with a comment naming the level
  (`# = elevation.level2`). In body prose the `{elevation.level2}` form is fine.
- A visually transparent component gets `backgroundColor: "{colors.surface}"` (its usual
  host surface), not `transparent`, so the linter's contrast check has a real pair.
- Expected lint warnings, accepted and listed in Known Gaps: disabled-state contrast
  (Material 38% / 12% is low by design), a decorative hero wordmark, the non-normative
  component properties, and the extra token groups. Errors are never accepted.
- Colors are lowercase hex in quotes. Font families are plain names in YAML with the fallback
  stack in the body prose.
- Lengths in `rounded` and `spacing` always carry a unit, zero included (`0px`): the Google
  linter silently drops a unitless length, and every `{rounded.none}` reference then breaks.
- The body never names a reference site in Overview through Accessibility. Attribution lives
  in `Sources` and `Intent`. The consuming AI should read the system as the user's own.

## Skeleton

Fill every `<...>`. Delete no `##` section; a `###` subsection marked "only if" is deleted
when the site does not have that thing. Where a section has no chosen input, it is still
written from derived values and says in one sentence that it is derived, not chosen.

```md
---
version: alpha
name: <site name or working title from Step 0>
description: <one line: what the site is, for whom, primary goal>
colors:
  # Every leaf below carries its own tier comment. When primary was chosen, the derived
  # comments shown are the usual ones; a value the user chose instead gets `chosen: ...`.
  # brand
  primary: "<hex>"                    # chosen: site N (<domain>)
  on-primary: "<hex>"                 # derived: M3 tone T100, sec.1
  primary-container: "<hex>"          # derived: M3 tone T90, sec.1
  on-primary-container: "<hex>"       # derived: M3 tone T30, sec.1
  primary-hover: "<hex>"              # derived: state layer 8% on-color, sec.1
  primary-active: "<hex>"             # derived: state layer 12%, sec.1
  primary-disabled: "<hex>"           # derived: on-surface 12%, sec.1
  secondary: "<hex>"                  # derived: Tonal Spot secondary T40, sec.1
  on-secondary: "<hex>"               # derived: M3 tone T100, sec.1
  secondary-container: "<hex>"        # derived: M3 tone T90, sec.1
  on-secondary-container: "<hex>"     # derived: M3 tone T30, sec.1
  tertiary: "<hex>"                   # derived: Tonal Spot tertiary T40, sec.1
  on-tertiary: "<hex>"                # derived: M3 tone T100, sec.1
  # surfaces
  # neutral seed (derivation-rules sec.8 "Neutral palette seed"): append "; achromatic neutrals defaulted, sec.8" or "; neutral palette seeded from the chosen surface, sec.8"
  surface: "<hex>"                    # derived: neutral T98, sec.1
  surface-dim: "<hex>"                # derived: neutral T87, sec.1
  surface-bright: "<hex>"             # derived: neutral T98, sec.1
  surface-container-low: "<hex>"      # derived: neutral T96, sec.1
  surface-container: "<hex>"          # derived: neutral T94, sec.1
  surface-container-high: "<hex>"     # derived: neutral T92, sec.1
  on-surface: "<hex>"                 # derived: neutral T10, sec.1
  on-surface-variant: "<hex>"         # derived: neutral-variant T30, sec.1
  # borders
  outline: "<hex>"                    # derived: neutral-variant T50, sec.1
  outline-variant: "<hex>"            # derived: neutral-variant T80, sec.1
  # semantic
  error: "<hex>"                      # derived: M3 error T40, sec.1
  on-error: "<hex>"                   # derived: M3 tone T100, sec.1
  error-container: "<hex>"            # derived: M3 error-container T90, sec.1
  # success: open (TODO: decide), see Known Gaps   (no M3 rule; a chosen value replaces this line)
  # warning: open (TODO: decide), see Known Gaps
  # overlays
  scrim: "<hex>"                      # derived: M3 scrim neutral T0, sec.1; 50% opacity defaulted, sec.8
  focus-ring: "<hex>"                 # derived: >= 3:1 vs adjacent, sec.6
typography:
  # Every role is written in block form, one property per line, each with its own tier
  # comment; a flow map (`body-lg: {fontSize: 16px, ...}`) is rejected by the validator
  # because one comment cannot carry two tiers. Roles: display-lg, display-md, headline-lg,
  # headline-md, title-lg, title-md, body-lg, body-md, label-lg, label-md, caption.
  # No family chosen: omit fontFamily and write `# fontFamily: open (TODO: decide)` instead.
  display-lg:
    fontFamily: <heading family>       # chosen: site N (<domain>)
    fontSize: <px>                     # derived: M3 display-medium 45px, sec.2
    fontWeight: "<100-900>"            # derived: M3 regular 400, sec.2
    lineHeight: <unitless>             # derived: M3 display 1.12, sec.2
    letterSpacing: 0                   # derived: DADS display tracking 0, sec.9
  body-lg:
    fontFamily: <body family>          # chosen: site N (<domain>)
    fontSize: 16px                     # derived: M3 body-large, sec.2
    fontWeight: "400"                  # derived: M3 regular 400, sec.2
    lineHeight: <unitless>             # derived: M3 body-large 1.5, sec.2 | Japanese: derived: DADS Std-16 175%, sec.9
    letterSpacing: <em>                # derived: DADS step 0 / 0.01em / 0.02em, sec.9
  # label-md and caption: 14px minimum (Hard Baseline; DADS, sec.9)
rounded:
  none: 0px                            # derived: M3 shape none, sec.4
  sm: <px>                             # derived: M3 shape row, sec.4; feel-to-row mapping defaulted, sec.8
  md: <px>                             # derived: M3 shape row, sec.4
  lg: <px>                             # derived: M3 shape row, sec.4
  xl: <px>                             # derived: M3 shape row, sec.4
  full: 9999px                         # derived: M3 shape full, sec.4
spacing:
  base: 4px                            # derived: Tailwind --spacing, sec.3
  xxs: 2px                             # derived: half step of the 4px base, sec.3
  xs: 4px                              # derived: Tailwind step 1, sec.3
  sm: 8px                              # derived: Tailwind step 2, sec.3
  md: 12px                             # derived: Tailwind step 3, sec.3
  lg: 16px                             # derived: Tailwind step 4, sec.3
  xl: 24px                             # derived: Tailwind step 6, sec.3
  xxl: 32px                            # derived: Tailwind step 8, sec.3
  xxxl: 48px                           # derived: Tailwind step 12, sec.3
  section: <px>                        # defaulted: section padding by feel, sec.8; for feel "<answer>"
  gutter: 24px                         # defaulted: grid gutter, sec.8
  container: <px>                      # chosen: site N (a picked site's width) | defaulted: 1120px, sec.8
  page-margin: <value>                 # defaulted: container and side margins, sec.8 (clamp(24px, 6vw, 96px), with the default container) | defaulted: page margin beside a chosen container, sec.8 (24px) | chosen: site N (the site's measured side padding)
  content-wide: <px>                   # derived: DADS 8-col offset column in the container, sec.9 (740px at 1120); reading, FAQ, forms
  content-narrow: <px>                 # derived: DADS 6-col offset column, sec.9 (548px at 1120); single-column forms, short statements
elevation:
  # shadows ruled out by a take or said line: this group is only `level0: none` (completeness bar exception)
  level0: none                         # derived: M3 level0, sec.4
  level1: "<css shadow>"               # derived: Tailwind shadow-xs, sec.4
  level2: "<css shadow>"               # derived: Tailwind shadow-sm, sec.4
  level3: "<css shadow>"               # derived: Tailwind shadow-md, sec.4
  level4: "<css shadow>"               # derived: Tailwind shadow-lg, sec.4
  level5: "<css shadow>"               # derived: Tailwind shadow-xl, sec.4
motion:
  # motion ruled out by a take or said line: this group is only `duration-short: 0ms` (completeness bar exception)
  duration-short: 200ms                # derived: M3 short4, sec.5
  duration-medium: 300ms               # derived: M3 medium2, sec.5
  duration-long: 500ms                 # derived: M3 long2, sec.5
  easing-standard: cubic-bezier(0.2, 0, 0, 1)   # derived: M3 standard, sec.5
  easing-enter: cubic-bezier(0, 0, 0, 1)        # derived: M3 standard-decelerate, sec.5
  easing-exit: cubic-bezier(0.3, 0, 1, 1)       # derived: M3 standard-accelerate, sec.5
breakpoints:
  sm: 640px                            # derived: Tailwind sm, sec.3 (or chosen: site N)
  md: 768px                            # derived: Tailwind md, sec.3
  lg: 1024px                           # derived: Tailwind lg, sec.3
  xl: 1280px                           # derived: Tailwind xl, sec.3
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.md}"
    padding: "{spacing.md} {spacing.xl}"
    height: <px>                       # >= 44px, sec.6
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
  button-primary-disabled:
    backgroundColor: "{colors.primary-disabled}"
    textColor: "{colors.on-surface-variant}"
  button-secondary: {...}
  button-secondary-hover: {...}
  text-input: {...}
  text-input-focus:
    borderColor: "{colors.focus-ring}"
    borderWidth: 2px
  text-input-error: {...}
  card: {...}
  card-hover: {...}
  nav: {...}
  footer: {...}
  <one entry per component the user picked, with its states>
---

## Agent Guide
<8-12 lines addressed to the AI that will build the site. Reading order: Hard Baseline
first, then Intent, then tokens, then Components, then Layout Heuristics. Priority when
rules conflict: Hard Baseline > Intent and the Do's and Don'ts that come from picks and
rejections > chosen tokens > derived tokens > Layout Heuristics, defaulted tokens and
`(skill heuristic)` Do's and Don'ts > body prose. How to treat `TODO: decide` (ask the
owner, never guess). Which token groups are chosen, derived, or defaulted, so the AI knows
what is sacred (chosen), what follows from it (derived), and what is only a recommendation
(defaulted). One line on the one thing to make memorable (Step 0).>

## Hard Baseline
Floors that hold for this site whatever the style says: accessibility and safety, from
WCAG 2.2 and the hard rows of the Digital Agency Design System (DADS,
https://design.digital.go.jp/dads/), plus one legibility rule for Japanese headings that
the skill owner promoted here. A style rule that breaks one of these loses.
### Layout Safety
- Fluid layout at every width; a needed horizontal scrollbar is never hidden; the page keeps
  a side margin at the narrowest width; reflow at 320 CSS px and 200% zoom lose nothing.
  (DADS layout; WCAG 1.4.4, 1.4.10)
- Visual order equals reading order at every breakpoint. (DADS layout)
### Readable Text
- Body and UI text 16px or larger; 14px only in the footer or constrained UI; nothing
  readable below 14px. Body line-height at least 1.5 (this file: `{typography.body-lg}`),
  and the layout survives the WCAG 1.4.12 text-spacing overrides. One h1 per page; heading
  level and size are independent. (DADS typography, heading; WCAG 1.4.12)
- Japanese headings wrap at phrase boundaries with balanced lines (`word-break:
  auto-phrase; text-wrap: balance`); no heading ends in a one- or two-character orphan such
  as a lone final kana and period at any width. Where a narrow card cannot avoid it, the
  heading steps down one type role on phones. (owner-promoted legibility rule, sec.8)
### Color and Contrast
- Text 4.5:1 against its background, always; non-text UI and borders 3:1; a drop shadow
  never counts as contrast. Meaning is never carried by color alone: links are underlined
  or otherwise marked, states are shown by text or icon as well. (DADS color, link-text,
  elevation; WCAG 1.4.3, 1.4.11)
### Interaction Safety
- Every interactive element shows a visible focus indicator at 3:1 or better
  (`:focus-visible`, never `outline: none` without a replacement); targets are 44 x 44 CSS
  px minimum with no overlap. Decorative motion stops under `prefers-reduced-motion`.
  (DADS button accessibility; WCAG 2.4.7, 2.5.8)
### Form Safety
- Visible label above every field; a placeholder is never the label; required and optional
  are marked in words. Errors are static text that states the cause and the fix, tied with
  `aria-describedby`. No `maxlength`, no copy or paste bans, no split email fields, no
  disabled or readonly fields. (DADS input-text)
- FAQ and similar disclosures are built on `<details>` and `<summary>`, header = the
  question, nothing important hidden inside, no nesting. (DADS accordion, disclosure)
### Conformance Target
- JIS X 8341-3:2016 / WCAG 2.2 level AA. (DADS webaccessibility)

## Layout Heuristics
Recommendations that apply only where the user's picks and Intent are silent. Each one
yields to a chosen value (a picked site's width, alignment, or section proportions) or to a
reason written in Intent; when one yields, Intent says which and why. Sources: the layout
rows of DADS and this skill's defaults (derivation-rules sec.8).
### Grid and Container
- Content sits on a 12-column grid inside `{spacing.container}`, centered, with
  `{spacing.page-margin}` kept on each side, so cards and headings never sit near the
  screen edge; grids reduce column counts at breakpoints. (DADS layout; sec.8)
- Reading blocks (statements, long copy, FAQ, forms, articles) sit in a centered column of
  `{spacing.content-wide}` or `{spacing.content-narrow}`; their rules, dividers, and fields
  end at that column's edge. Display-size lines are not reading blocks: they use the full
  container so a one-line statement stays on one line. (DADS layout; sec.8)
### Section Rhythm
- The size of each section sets the reader's rhythm: equal sizes read as a steady march, a
  deliberate change in size reads as a pause or an emphasis. Page Structure states the
  rhythm this site uses and why; section sizes are decided, never left to whatever content
  each band happens to hold. (sec.8)
- One alignment axis per section: grid sections align to the container's left edge,
  reading sections put heading and content in the reading column; a section never mixes
  the two. A lone sentence (a statement, a call to action line) opens or closes a
  neighboring section instead of forming its own. (sec.8)
### Spacing and Type Conventions
- One modular spacing scale of 3 to 5 working steps; the same kind of element always gets
  the same gap; more important elements get larger gaps. Letter-spacing 0, 0.01em, or
  0.02em for running text; no italic for Japanese. (DADS spacing, typography)
### Control Conventions
- Button heights from 56 / 48 / 36 / 28; one primary per screen; confirm on the right,
  cancel on the left on desktop; disabled buttons avoided. Field width matches the expected
  input; required marks written `※必須` / `※任意`; error text begins with `＊`; radio for
  single choice up to five options; checkbox left of its label. Hover raises elevation one
  level; dialogs sit at least two levels up. (DADS button, input-text, radio, checkbox,
  elevation)

## Overview
<5-8 sentences. What the site is for, who visits, the mood in everyday words, how the page
should feel at first glance and after a minute, the one thing a visitor should remember.
No site names.>
**Key Characteristics:**
- <5-7 bullets, one trait each: e.g. one accent color per screen; flat surfaces, one shadow
  tier; airy section bands over dense card grids; sentence-case copy; no decorative motion>

## Colors
### Brand & Accent
<role of primary / secondary / tertiary; where each appears; how much of the page is
accent (a percentage or "one element per screen")>
### Surfaces
<background strategy: flat white, layered greys, dark bands; which surface-container role
goes where (page, card, sheet, modal)>
### Text
<on-surface for body, on-surface-variant for secondary, when inverse text appears>
### Borders & Dividers
<outline vs outline-variant usage; hairline weight; when borders are replaced by spacing>
### Semantic
<error / success / warning usage; never color alone (pair with icon or text)>
### States
<hover 8%, focus 12%, pressed 12%, disabled 38%/12% as applied; cite sec.1>
### Dark Scheme
<either the derived dark roles (M3 dark column) in a short table, or "Light only by
decision; dark scheme derivable on request" if the user chose light only>
### Contrast Verification
<a table: pair, ratio, pass/fail for every on-X/X pair and for focus-ring vs surface>

## Typography
### Families
<heading family, body family, why they fit the mood; fallback stacks; loading source if
Google Fonts; one or two families only>
### Hierarchy
<table: role, size, line-height, weight, tracking, where used>
### Principles
<line length under 80 chars; sentence case; no accented single words in headlines; serif
body gets more line-height; what gets bold and what never does>
### Substitutes
<if the chosen family is proprietary (SF Pro, Airbnb Cereal), the closest open family and
the metric differences to expect>

## Layout
### Spacing System
<base unit; the scale; what each step is for (card padding, gutters, section bands); how
sections are separated (whitespace, dividers, or a background change), as observed on the
picked sites or stated as a default>
### Grid & Container
<container width; column counts per breakpoint; gutter; any asymmetric layout (sidebar,
sticky rail)>
### Page Structure
<numbered list, top to bottom, one line per section: name, layout (columns, alignment),
relative size (its share of the rhythm), background surface, the component it uses, the
chosen source if any. Close with one sentence naming the rhythm and why it serves the goal>
### Whitespace Philosophy
<2-4 sentences: where the page breathes and where it is dense, and why that contrast
serves the goal from Step 0>

## Elevation & Depth
<how many shadow tiers exist and which elements use each; borders vs shadows; dark scheme
uses surface tone instead of shadow; modal scrim value>

## Shapes
<radius per element class: buttons, inputs, cards, images, chips, modals; whether radii are
uniform or deliberately mixed; `{rounded.*}` references>

## Components
### Buttons
<primary / secondary / tertiary: size, padding, radius, label style, every state in one
line each, where each variant is used>
### Inputs & Forms
<only if Page Structure has a form; otherwise delete this subsection. text input at rest / focus / error / disabled; label placement; helper text; validation
tone>
### Cards
<only if Page Structure has cards; otherwise delete this subsection. padding, radius, border or shadow, image ratio, hover behavior, text hierarchy inside>
### Navigation
<height, sticky or not, logo placement, link style, active state, mobile collapse pattern>
### Footer
<columns, background, link style, legal band>
### <Picked component 1, e.g. Hero>
<what it is, layout, tokens by reference, behavior; which site inspired it (number only)>
### <Picked component 2...>

## Interaction States
<a matrix table: component x state (rest, hover, focus-visible, active, disabled, loading,
error) with the token or rule in each cell; one line on cursor and transition for each>

## Motion
<what animates (transform and opacity only); durations per class (feedback short,
transitions medium, page or hero long); easings; the one orchestrated moment, if any;
`prefers-reduced-motion` behavior: remove decorative motion, keep feedback; never
`transition: all`>

## Responsive Behavior
| Name | Width | Key Changes |
|---|---|---|
| Mobile | < {breakpoints.sm} | <nav collapse, column counts, hero crop, CTA placement> |
| Tablet | ... | ... |
| Desktop | ... | ... |
| Wide | > {breakpoints.xl} | <content cap, gutters absorb> |
### Collapsing Strategy
<grids reduce columns never reflow rows; what becomes a sheet or bottom bar; sticky rail
behavior; the narrow-width nav rule (what leaves the bar below N px); mobile sizes for
display-lg and display-md (clamp() ranges) and mobile padding for bands and cards>
### Touch Targets
<44 x 44 CSS px minimum for every target, no overlap (Hard Baseline); spacing between adjacent targets; how small inline links meet it>

## Imagery & Iconography
<photo style (people vs product, color treatment, crop ratios), illustration policy, icon
set (one set only, stroke weight, size steps), logo clear space; what is forbidden (stock
cliches, mixed icon sets)>

## Voice & Content
<tone in three adjectives; sentence case; active voice; CTA wording rule (specific verbs);
error message shape (cause + fix); microcopy length limits; language and formality level
for the audience from Step 0>

## Accessibility
<contrast minimums applied (4.5 / 3 / 3); focus ring spec; target sizes; reflow at 320px;
200% zoom; text-spacing survival; reduced motion; color never the sole signal; alt text
policy; heading order>

## Do's and Don'ts
### Do:
- **Do** <rule derived from a chosen attribute>
- **Do** <...> (4-8 lines)
### Don't:
- **Don't** <rule from the user's "would not imitate" answers>
- **Don't** <generic-AI-look bans from derivation-rules sec.7 that apply to this mood and that nothing the user picked or said contradicts, tagged `(skill heuristic)`>
- **Don't** <...> (4-8 lines)

## Intent
<English, 8-15 lines. Industry, goal, audience from Step 0. For each bundle: what the user
chose to take and from which source number, what they explicitly rejected, what stays
open. Which token groups are chosen, derived, or defaulted, and which heuristics a pick overrode. This section is why the file exists; write
it so an AI with no other context could rebuild the choices.>

## Sources
1. <domain of site 1> : taken: <one line> ; rejected: <one line or "nothing"> ; measured: <rendered page at 1440px | static CSS (facts.txt)>
2. <domain of site 2> : ... ; measured: <rendered page at 1440px | static CSS (facts.txt)>
3. <domain of site 3> : ... ; measured: <rendered page at 1440px | static CSS (facts.txt)>
Rules cited for derived values: `references/derivation-rules.md` of the design-md skill
(Material 3 color and type roles, WCAG 2.2, Tailwind scales, Anthropic frontend-design).

## Iteration Guide
<6-10 lines for the owner and the AI: which token to change for which effect (warmer: shift
`primary` hue and re-derive; calmer: raise `spacing.section` one step and drop one accent
use; denser: step spacing down, keep `rounded`); what must be re-derived after a change
(on-colors and the contrast table after any color change; line-heights after any size
change); what never changes without a new interview (the Intent section)>

## Known Gaps
<bullet list of what this file does not cover and why: states not observable, dark scheme
not chosen, components the site will need that no reference showed, every site read from
static CSS only ("values read from static CSS; runtime theme not observed"), every
`TODO: decide` with the question the owner must answer>

## Brief (Japanese)
<the signed-off brief, verbatim, including its title line>
```

## Filling order

0. The Hard Baseline section is copied from the skeleton verbatim (it is not
   style-dependent); only the token references inside it are resolved. Then check every
   later section against it: a style choice that breaks a Hard Baseline rule is rewritten,
   not kept. Derived and defaulted values are snapped to it here (readable sizes to 14px or
   more, body line-height to 1.5 or more, FAQ written as `<details>` / `<summary>`), because
   builders follow a style section over a baseline when the two disagree.
   The Layout Heuristics section is copied too, then edited: every heuristic that a pick or
   Intent overrides is rewritten to the chosen behavior (and Intent says so), not left
   standing next to its contradiction (a pick that rules out shadows removes "Hover raises
   elevation one level; dialogs sit at least two levels up" from Control Conventions).
   Derived values follow the heuristics only where no
   chosen value disagrees (M3 tracking snapped to 0 / 0.01em / 0.02em unless the user chose
   a tracked display face).
1. Chosen tokens first, from the interview picks; each value read from one source in the
   SKILL.md Step 2 order (the rendered page at 1440px, else `facts.txt`), never mixed or
   averaged.
2. Derived tokens, group by group, following the recipe at the end of
   `references/derivation-rules.md` (palettes, roles, contrast check, states, type scale,
   spacing, radii, elevation, breakpoints, motion).
3. Layout and Page Structure from the WebFetch section list plus picks.
4. Components: the ones Page Structure uses, then every picked one, each with states.
5. Interaction States matrix, Motion, Responsive, Imagery, Voice, Accessibility.
6. Do's and Don'ts from picks and rejections first, then the sec.7 bans that fit and that
   nothing the user picked or said contradicts, each tagged `(skill heuristic)`. The Step 0 "memorable thing" is the one place boldness is spent.
7. Agent Guide and Overview last, so they summarize rather than promise.
8. Intent, Sources, Iteration Guide, Known Gaps, Brief.

## Consistency self-check (cross-section invariants)

Each pair below is a contradiction that can live between two sections that are
individually fine. Check every pair below before writing; a builder follows the
priority order (Hard Baseline > Intent and the Do's and Don'ts that come from picks and
rejections > chosen tokens > derived tokens > Layout Heuristics, defaulted tokens and
`(skill heuristic)` Do's and Don'ts > body prose) and will silently pick one side.

- Nav width budget: at 320px, logo + primary CTA (label at label-lg plus 2 x 24px padding)
  + menu button + gaps must fit inside 320 - 2 x gutter. If not, write the narrow-width rule
  yourself (CTA moves into the sheet below N px, or a shorter mobile label).
- "Once per page" rules vs semantic and state uses: if the accent may appear once, say
  where success, selected, and highlighted states go instead, or exempt them explicitly.
- Elevation prose vs Interaction States matrix: every level named in the matrix is a level
  the Elevation section says is in use, and vice versa.
- Page Structure heading sizes vs Hierarchy table: a section title size named in Page
  Structure matches the Hierarchy row for section titles, or the exception is stated.
- Rhythm vs band sizes: the rhythm sentence closing Page Structure matches the relative
  sizes listed for each section; a band said to "pause" is visibly different in size.
- Box arithmetic: for every component with a fixed height, height >= 2 x vertical padding
  + line-height x font-size. Inputs with body-lg at 1.75 need 52px or 8px padding.
- Focus treatment per class: buttons and links get the ring + offset; inputs get the
  border change; say which, so the Accessibility sentence and the component rules agree.
  Also state what happens when a field is both invalid and focused.
- Hover motion wording: "no hover animation" bans transform; say whether a shadow or
  color change on hover is allowed (it usually is) so card-hover and the Don't agree.
- One trigger per behavior: the nav hairline, the sheet breakpoint, and the collapse rule
  each appear once, or every mention uses the same value.
- Mobile rules for every display size and every padded band: display-md and display-lg
  get a clamp() or a mobile size; accent bands and cards get a mobile padding; section
  padding has a mobile value.
- Whole-card links: a card that "is the link" contains no second interactive element, or
  the inner button is the only link and the card is its hit area.
- Rails: enough items that the last one is cut at the widest breakpoint (compute it from the
  container and the card width actually written), and a stated destination for each item
  or an explicit "cards are not links".
- Single-page sites: say how the active nav state is driven (scroll position) or drop it.

## Self-check before writing the file

Mechanical checks first: run `scripts/check-design-md.sh <draft> <workdir>/picks.txt` (SKILL.md
Step 5). It fails on a token without a tier comment, a `chosen: site N` token whose path
matches no `take N` or `said N` line in picks.txt (naming the declined option when it
matches a `decline` line instead), a `for pick "<option text>"` that quotes no `take` or
`said` line, a `derived` token citing sec.8, a hex inside `components`, a defaulted fluid
`spacing.page-margin` (`vw` or `%`) beside a chosen `spacing.container`, a numbered `Sources`
item without `measured:`, a `colors` value whose comment says `achromatic` but that is not
a pure gray hex, a unitless length in `rounded` or `spacing`, and a missing or duplicated
required heading. Fix every FAIL line, rerun until it exits 0.

Then the judgment checks the script cannot make:
- Completeness bar met; no section one-lined; no component the site will not have.
- Hard Baseline present verbatim; no later section contradicts it (no text under 14px,
  placeholders never labels, contrast floors met).
- Layout Heuristics edited where a pick overrides one, with the reason in Intent.
- For each `decline` line in picks.txt: its content is absent from the Brief, Page
  Structure, Components, and Imagery, unless a `said` line asks for it.
- No value is `chosen` unless the user picked the option that covers it AND the value came
  from the site or the user; a pick realized with a skill number is `defaulted`. A declined
  option, or a value the user approved only as a proposal in the brief, is never `chosen`.
- Every `reject` line in picks.txt appears in `Do's and Don'ts` and in `Sources`.
- No `(skill heuristic)` line bans something a `take` or `said` line, a chosen token, or the
  Brief asks for.
- A pick that rules out shadows or motion: no shadow other than `none`, no duration above
  0ms, and nothing in Components, Interaction States or Motion adds one.
- Contrast table present, every text pair >= 4.5:1 or explicitly noted as large text 3:1.
- No reference site named outside `Sources` and `Intent`.
- No copied sentence, image URL, or logo from any site.
- The Brief section is byte-identical to the text the user said OK to.
