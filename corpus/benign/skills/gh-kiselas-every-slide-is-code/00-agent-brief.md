# Agent brief: presentations as code

Short rules. The details are in the neighbouring files.

## Architecture
1. One self-contained HTML file per deck. The runtime (`runtime/deck.js`, `runtime/deck.css`) is pasted inline. Fonts from Google Fonts, libraries only from a CDN, nothing else external. `export/deck.mjs bundle` makes it fully offline.
2. The deck is a pure function of `(slide, step, t)`. No animation state carried between frames, no `setTimeout` choreography, no CSS `transition`/`@keyframes` on content. Every visual value is computed from `st` in `frame(el, st)` or declared with `data-anim`. That is what makes jumping, the rest frames for PDF/PPTX and the video timeline possible.
3. Randomness is seeded (`Deck.rng(seed)`). `Math.random()` is banned in anything that draws.
4. Plan as data first: the storyline (one sentence per slide), the steps of each slide, the transitions and what each one means. Then code.
5. Slides are DOM and SVG at a fixed 1920×1080 canvas, scaled to the screen. Measure in pixels of that canvas, never in `vw`/`vh`.

## Story
6. One idea per slide. The title is that idea as a full sentence with a verb: "Costs flattened after the switch", not "Costs".
7. Read the titles alone, in order. If they do not tell the whole argument, fix the story before the slides.
8. Every chart answers one question, and the title states the answer. Highlight the part that proves it; grey the rest.
9. End on the decision or the ask, not on "Questions?".

## Visual
10. Derive the style from the subject: its materials, era, craft, where it lives. A food-waste pitch can be a receipt; a logistics plan can be a departure board. If no style is given, propose one and say why.
11. Avoid the default look: purple-to-blue gradient, glassmorphism cards, a row of three icon cards, emoji bullets, everything centred, a dark navy background with a neon accent. Legitimate only when chosen on purpose.
12. 4–6 colours with roles (background, ink, muted, rule, accent, second accent). The accent covers under 10% of a slide and carries meaning, the same meaning on every slide.
13. One bold decision per deck. Everything else is disciplined.

## Motion
14. Motion explains, it does not decorate. Builds reveal the argument in reading order; a transition says how two slides relate (06-transitions.md).
15. Nothing moves linearly except constant processes (flow along an edge, a ticker). Entrances on outExpo/outCubic, moves on inOutCubic, emphasis on a spring.
16. Stagger groups by 40–120 ms. Never animate more than one thing that matters at the same time.
17. Two or three transition types per deck, each tied to a meaning. A deck where every slide uses a different transition reads as a demo reel.

## Rest frames
18. Every step has a rest frame: the state when all its animations have finished. It must carry the full message without motion, because it is what PDF, PPTX, the overview and anyone who skims will see.
19. If the point only exists in the motion ("watch the line overtake"), add a label, an annotation or a highlight that makes it visible when still.

## Text
20. Body text at least 24 px on the 1080 canvas, labels at least 20 px. Titles 72–110 px. The runtime's `check` flags anything under 20 px.
21. Under 40 words on screen per step. What does not fit goes into speaker notes (`<aside class="notes">`).
22. Safe area: keep text at least 60 px from the edges (the check flags under 38 px).
23. Fonts are loaded before the first frame (`display=block`; the runtime lays every slide out once and awaits `document.fonts.ready`).

## Containment: nothing leaves its box
24. A box with text hugs its content: `min-height` and padding, never a fixed `height`. Fix the width, let the height follow.
25. Assume the font may not load. On a locked-down network the fallback font is wider, so leave 10–15% slack in every box and give titles `data-fit="2"` (shrink to at most two lines).
26. A value that changes (a counter, a read-out, a label that follows a moving point) must fit at its widest: the minus sign, the most digits, the longest unit. Size it for "−0.000 kg", not for "0.000 kg".
27. Text that sits on a shape (a node, a bar label inside the bar, a circle) must stay inside the shape; if the text is dynamic, check the longest case.
28. Before calling a deck done: `check --timeline` (mid-animation frames, where counters and moving labels spill out) and `check --no-webfonts` (fallback fonts).

## Navigation
29. Keep the on-screen controls on: bar with back/next, slide title, step dots and a scrubber, the first-run hint, click zones (left fifth back, the rest forward). Turn them off (`data-controls="off"`) only for kiosks and embeds.
30. Every slide has a real title (an h1–h3 or `data-title`): it is what the control bar, the scrubber tooltips, the overview captions and presenter view show.
31. Interactive elements inside a slide carry `data-no-advance`, so a click on them does not advance.

## Performance
32. Never read layout inside `frame` (`offsetHeight`, `getBoundingClientRect`, `getComputedStyle`): measure once in `setup` or an animation's `init`.
33. Motion driven by `st.since()` declares its length with `active: seconds` on the slide spec; `st.T` and `st.life()` are only for real ambient motion. Otherwise the slide never goes idle.
34. Animate transform and opacity; keep blur and filters small and one at a time; keep each slide under a few hundred DOM nodes (a canvas for dense marks).
35. `node export/deck.mjs perf` stays under 8 ms per frame; `?perf` shows "idle" on every still slide (13-performance.md).

## Check
36. After every version run `node export/deck.mjs check deck.html` and `sheet`, open the sheet, describe what you see, then fix by slide and step number.
37. Check at least one transition with `strip` when you add or change it.
38. Numbers in an invented deck are labelled as illustrative on the title slide. Never present made-up figures as real data.

## Long decks, code, effects
39. Long decks start as a `SCRIPT.md` table with a thesis, a spine, a through-line that reverses once, and a last slide that returns to the first image; check it with `scripts/plan.mjs` (`--check`, `--animatic`) before any slide code (03-story.md).
40. Code slides: 8-15 lines per state, 24 px minimum, states or line focus instead of scrolling; run `--code-cache` before `bundle` (14-code-slides.md).
41. Kinetic text (`chars`, `tracking`, `scramble`, `flip`) and the statement grammar (`data-say`: setup small, payoff large, at most 8 words) only where the wording carries the meaning. Grain and other ambient effects are optional, frozen in exports, and must not keep still slides from going idle (`Deck.fx`, 10-stage.md).
42. After runtime or transition changes run `npm test` and `npm run test:browser`: determinism, transition end frames, no `Math.random`, idle rendering.
43. Sketch plugin: sketched shapes are drawn once from a seed (never `Math.random`), line boil runs only while the slide is live, morphing shapes stay clean (15-sketch-and-morph.md).
44. Live annotation (`D` pen, `H` highlighter, `L` laser, `E` erase) exists only in live and presenter windows, never in exports; `data-annotate="off"` on `.deck` turns it off for kiosks (11-presenting.md).
45. Start a palette from `scripts/palette.mjs` when no style is given; `check` flags text under 3:1 as an error and under the norm as a warning, so fix warnings before handing over (04-slide-design.md).
