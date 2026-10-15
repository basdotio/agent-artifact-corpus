# Interactive lab page

One HTML page that makes the guide visible and playable — the main way the user
learns by doing in this skill. It is a local `.html` file the user opens in their
browser, not a published artifact, but it gets the same design care: load the
`artifact-design` skill before writing it, `dataviz` before any chart, and
`artifact-diagramming` before any diagram (when available). Follow their design
guidance (layout, type, color tokens, light and dark mode, phone width); skip
their publishing steps. If those skills aren't available, follow the Design
section below.

## Design (fallback when the design skills aren't available)
- **Colors as tokens** on `:root` (background, surface, text, muted text, border,
  accent, 3–5 series colors). Redefine them under
  `@media (prefers-color-scheme: dark)`. Give `body` an explicit background.
  Nothing is hard-coded to a color outside the tokens.
- **Type:** the system font stack (`system-ui, -apple-system, "Segoe UI",
  sans-serif`), 16px body, line height 1.5–1.6, text column max ~70 characters,
  3 heading sizes at most. Monospace only for numbers and code.
- **Space and layout:** content column (max ~960px) beside the navigation
  sidebar, 16px side padding on phones; spacing from one scale (4, 8, 16, 24, 32,
  48px). No horizontal scroll at phone width.
- **Figures:** each in a card (surface color, 1px border, 8–12px radius, padding)
  with title, "try this" text and § tag above, the figure, then "what to notice"
  below. Controls grouped in one row that wraps; labels next to each slider with
  the live value shown.
- **Charts and diagrams:** inline SVG or canvas sized with `viewBox` so they scale;
  labeled axes with units; direct labels over legends; colors from the series
  tokens; text in SVG uses the text tokens so it stays readable in dark mode.
- **Restraint:** one accent color, no gradients or shadows beyond a subtle one on
  cards, no decoration that isn't explaining something.

## The file
- One self-contained `.html` file: inline CSS and JS. External libraries only from
  a CDN with an exact version (e.g. `d3@7.9.0`), so the local copy also works when
  opened straight from disk.
- Built up part by part: each part adds its section; earlier sections stay.

## Layout
- One section per guide part, in the same order, with the part's § numbers.
- Each figure has: a title, short text on what to try and what to notice, and the
  guide section it belongs to.

## Navigation (always visible)
- **Desktop:** a sidebar fixed on the left (~240px), scrolling on its own if long.
  Parts as groups (number badge + title), their figures listed under each
  ("F5 · Calculator").
- **Phone** (below ~900px): a slim bar fixed at the top showing the current
  part; tapping it opens the full list as a panel; picking a link closes it.
- **Where you are:** the current part and figure are highlighted as the user
  scrolls (IntersectionObserver), with an accent bar on the left of the item. A
  thin reading-progress line along the top.
- **Clean, not raw:** no underlines or default blue; muted text that brightens on
  hover, small pill badges for numbers, generous spacing between groups.
- Smooth scrolling, with `scroll-margin-top` on headings so a jump never hides
  the heading under the top bar.

## Check before handing over
After writing or updating the lab, look at it, don't just load it:
1. Screenshot it in a headless browser (Playwright if installed, otherwise
   Chrome/Chromium `--headless=new --screenshot`) at desktop (~1280px) and phone
   (~390px) width, in light and dark mode, and look at the images. Without
   Playwright: headless Chrome won't go below ~500px wide, so for phone width
   screenshot a scratch page that loads the lab in a 390px-wide `<iframe>`
   (with `--allow-file-access-from-files`); for dark mode add
   `--blink-settings=preferredColorScheme=0`.
2. With Playwright, also move every control to its extremes and screenshot the
   figure again; labels that only collide at low or high values show up there.
3. Fix what you find: overlapping or clipped labels, text off the chart, controls
   that do nothing, console errors. Leave room for labels in chart margins, and
   move or hide a label that would collide instead of letting it overlap.
4. Report only what you couldn't fix or couldn't check.

## Kinds of figures (pick what fits each concept)
- **Interactive simulation** — sliders and buttons change parameters live; two
  speeds: step through slowly (Step / Next) or run quickly (Run 100×).
- **Animated diagram** — the core mechanism, stepping through its stages.
- **Chart** — comparisons, trade-offs, how a quantity changes with a parameter.
- **Worked example, playable** — the guide's hand-worked example, with inputs the
  user can change and every intermediate value shown.
- **Real-application explorer** — a card or small diagram per case study from
  Part 5: the setup, which concept it uses, and a link to the source.
- **Decision helper** — "should I use <topic> here?" for the "when not to use it"
  part.

Every key concept gets at least one figure. You choose which kind.

## Data
Use the guide's own worked examples and small simulations computed in the page.
Real-world numbers only when they come from a cited source.

## Where it goes
1. Write it to `<topic folder>/<TOPIC>_ESSENTIALS_LAB.html`.
2. Open it for them (`open <file>` on macOS, `xdg-open` on Linux) after Part 1;
   after later parts, tell them to reload the page.
3. Link the file from the guide's header and from `PROGRESS.md`.
