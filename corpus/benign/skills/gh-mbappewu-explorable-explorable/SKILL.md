---
name: explorable
description: Turn any "how does X work?" question into an explorable explanation — a single self-contained HTML page with an essay and live, draggable figures that simulate the real mechanism (physics, algorithms, machines, biology, economics). Use when the user asks how something works, wants an interactive or visual explainer, an "explorable", or a Bret Victor / Distill-style article about a concept.
---

# explorable

Write one HTML file that teaches a mechanism by letting the reader play with it. The page is an essay with 4–7 interactive figures. Every figure is a small simulation of the real thing: drag, scrub or toggle, and the behavior comes from the actual rules of the system, not from a canned animation.

The bar: a curious adult who has never studied the topic reads it once, plays with each figure, and can then explain the mechanism to someone else, including the one non-obvious reason it works the way it does.

## Workflow

1. **Find the story before the figures.** Write down, in plain words:
   - the reader's question ("Why do noise-cancelling headphones still let voices through?")
   - the mechanism in one sentence
   - the one surprising insight the page builds towards
   - 4–7 steps from zero to that insight. Each step introduces exactly one new idea.
   Check the facts you will state. If you are unsure of a number, derive it, cite it in a code comment, or leave it out. Never invent statistics.

2. **Design one figure per step.** For each step choose the smallest interaction that makes the idea discoverable (see `references/craft.md`, "Figure patterns"). One or two controls per figure. The reader should be able to find the key moment on their own, and the caption tells them what to try.

3. **Build the model first, then draw it.** Write the simulation as plain functions (state → next state, parameters → result) before any drawing code. Put the real formula or rule in the code with a one-line comment saying what it is. Figures that disagree with the model are bugs.

4. **Start from `template.html`.** Copy it next to the output and fill it in. It already has the typography, light/dark color tokens, the figure markup, an English/Chinese switcher, and helpers for crisp canvases, visible-only animation, dragging, labels and audio. Keep everything in one file. The only allowed external request is the Google Fonts stylesheet in the template.
   - **Language.** Write in the user's language. For a bilingual page (the user asks, or the audience is mixed), keep the switcher, pair every text block as `lang="en"` / `lang="zh"`, wrap every string drawn on a canvas or written into a readout in `t(en, zh)`, and register redraws with `langHooks.push(draw)`. Otherwise delete the switcher and the second language.
   - **3D.** When depth is the point (gears, engines, molecules, orbits), use WebGL directly. Copy the matrix, extrusion and `stage()` helpers from `examples/planetary-gears.html`; no libraries.

5. **Write the prose around the figures.** Short paragraphs, concrete words, one idea each. Name things with the same color in the prose and in the figure (`<span class="c1">`). Explain what the reader just saw before moving on.

6. **Verify like a reader, not like a compiler.** Follow `references/verify.md`: run the static check, screenshot every figure (`scripts/shoot.py`, or your own browser tool), drive every interaction to its interesting state, check both color schemes, both languages if bilingual, and a 375px-wide viewport, and fix what you find. Do not report the page as done until it passes.

7. **Deliver.** Save as `<topic-slug>.html` (or where the user asked), open it if you can, and tell the user in two or three sentences what the page covers and which figure to try first.

## Non-negotiables

- **Real mechanism.** The figure's behavior comes from the model: the physics equation, the algorithm, the rule. A figure that only plays a pre-drawn animation is not acceptable.
- **The reader is in control.** Every figure responds to input within one frame. Sliders show their value. Anything that can get into a broken state has a reset.
- **One idea per figure.** If a figure needs a paragraph of instructions, split it.
- **Interesting at first sight.** Every figure's default state already shows the phenomenon (waves mid-cancel, the key half inserted). Never open on an empty stage that needs a click first.
- **Recognizable things.** Draw the real object so a reader would recognize it: a water molecule has an oxygen and two hydrogens at an angle, a lock has a plug, pins and springs. Abstract symbols only for abstract quantities.
- **Honest.** Simplifications and illustrative numbers are labeled as such, where the claim is made. Exaggerations for visibility are called out ("the error is exaggerated so you can see it"). Never call an approximation "exact" or a stylized drawing "real", and check at least one shown number against a published table or standard (see `references/verify.md` §3).
- **Readable everywhere.** Works in light and dark mode, at 375px wide, with mouse and touch. No labels overlapping each other or the drawing. No horizontal page scroll.
- **Light on the machine.** Animate only figures that are on screen (the template does this). No frameworks, no build step.

## Files

- `template.html` — the starting point. Copy it; don't rewrite the helpers.
- `references/craft.md` — figure patterns, color, layout and prose rules, with examples of what good looks like.
- `references/verify.md` — the verification protocol and the common bugs to look for.
- `scripts/check.mjs` — static check: `node scripts/check.mjs page.html`.
- `scripts/shoot.py` — screenshot every figure and report console errors and horizontal overflow (needs Python Playwright): `python3 scripts/shoot.py URL out/ [--dark] [--width 375] [--lang zh]`.
- `examples/` — three complete, bilingual reference pages: noise-cancelling headphones (waves, audio, an adaptive filter), pin tumbler locks (direct manipulation and a picking game) and planetary gears (WebGL 3D). Skim one before your first page to calibrate the level of polish.
