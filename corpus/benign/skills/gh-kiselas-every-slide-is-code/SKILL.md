---
name: deck-kit
description: Presentation decks as code — pitch decks, product launches, idea pitches, board and quarterly reviews, tech talks. One self-contained HTML file with animated charts, diagrams, builds and cinematic transitions (camera moves, morph, zoom, iris, tear, dissolve), a presenter view, and static PDF/PPTX exports. Use whenever someone wants to present an idea, product, plan or result as slides, or asks for a deck, keynote, pitch or presentation that should look designed rather than templated.
---

# deck-kit

1. Read `00-agent-brief.md` in full. These rules are mandatory.
2. Read the files that fit the task:
   - any deck: `01-runtime.md`, `03-story.md`, `04-slide-design.md`, `12-export-qa.md`;
   - the brief is vague or you are writing a prompt: `02-prompting.md`;
   - animation and builds: `05-motion.md`;
   - transitions between slides: `06-transitions.md`;
   - numbers and charts: `07-charts.md`;
   - flows, architecture, timelines, matrices: `08-diagrams.md`;
   - titles, big numbers, text treatment: `09-typography.md`;
   - a background world that lives behind all slides: `10-stage.md`;
   - rehearsal, presenter view, the room: `11-presenting.md`;
   - smoothness, battery, heavy slides: `13-performance.md`;
   - technical talks, code on slides (magic move, line focus, diffs, terminal, file tree): `14-code-slides.md` (optional plugin `runtime/code.js`);
   - hand-drawn SVG (`data-sketch`) and path morph (`data-morph-to`, the `morph` transition with shapes): `15-sketch-and-morph.md` (optional plugin `runtime/sketch.js`);
   - a palette from one accent colour: `node scripts/palette.mjs --accent "#hex"`; a reference deck to learn from: `node export/deck.mjs analyze ref.pdf`; a talk as narrated video: `mp4 --voice --timings` (12-export-qa.md).
3. Start every deck from `template/deck.html` (`node scripts/sync-runtime.mjs --new my-deck.html`), or copy the template and paste `runtime/deck.css` and `runtime/deck.js` into its two marked slots.
4. Show the plan as data first: the storyline (one sentence per slide), the style, and which slides carry a chart, a diagram or a transition with a meaning. Then write code. For a talk of 8+ minutes, write `SCRIPT.md` (`template/SCRIPT.md`) first, run `node scripts/plan.mjs SCRIPT.md --check` and `--animatic`, wait for approval, then `--new deck.html` (03-story.md).
5. After every version run `node export/deck.mjs check` and `node export/deck.mjs sheet`, look at the sheet yourself and fix by slide and step number (`4.1`, not "the chart slide"). Before handing over, also run `check --timeline`, `check --no-webfonts` and `perf`. To look at the exact frame a finding names, use `still 6.2@0.45`; `mp4`/`gif` take `--draft` and `--workers N`; `fonts --write` adds metric-matched fallback fonts (12-export-qa.md).
