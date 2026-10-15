---
name: explainer-studio
description: Build a complete science explainer for one topic - a real quantitative model with self-checks, a crafted isometric anatomy-skill figure of a real object whose moving parts ARE the concept, a 6-8 step explainer that opens on catalog misconceptions, an open lab with real knobs, slow motion, live instruments and 3 challenges, and a directed full-bleed 16:9 explainer film (narration, camera moves, slow motion, events posed on the spoken word), shipped as one page + Cloudflare site + claude.ai artifact. Use it whenever the user wants an explainer video, an interactive explainer, an open lab or a simulation page for any physics, chemistry, biology or earth-space topic, a concept card for such a topic, a topic from the curriculum explained, or wants to scaffold, render, gate or ship an explainer-studio topic - even if they only name the topic.
---

# Explainer Studio

One topic = one real object on a bench, one model that drives everything, four ways in: **Watch** (a directed film),
**Explain** (steps that open on misconceptions), **Open lab** (every knob, slow motion, instruments, challenges), and
the figure itself. The kit grew out of seven hand-built explainers (a four-stroke engine, the photoelectric effect, a
generator, a heat pump, a crumple zone, a pendulum clock, a camera lens); the gates and the film rules are what their
reviews taught. If you have finished topics of your own, open their README and STATUS ("Fixes after review" lists what
was rejected) before the first topic of a session.

The shared toolchain is the **kit**: the folder this skill lives in (`<kit>/skill`; `<kit>` = where you cloned the
explainer-studio repo). A topic folder holds only what is specific to it; everything else is imported from the kit. Do
not copy kit files into topics.
The drawing craft is the third-party **anatomy** skill (`~/.claude/skills/anatomy`, MIT). Read it; never modify it.

## The one idea

**The object is the explanation, and the model is the truth.** A recognisable, detailed physical thing (a machine, an
instrument on a bench, a cabinet, a tray, a recorder) whose motion IS the concept: "X moves, and that motion means Y".
Every number on screen, in the narration and in the lab comes from one model with self-checks that close.

## Workflow (in this order)

1. **Concept card** (`references/concept-card.md`): id, concept in one sentence, archetype, object, what moves = what it
   means, model + real headline numbers (compute them), 3-6 catalog misconceptions, a 6-10 beat shot list, bundle, size,
   risks, fit. Curriculum data (optional): `references/curriculum.md`. Get the user's OK on the card for a new rig.
2. **Scaffold** a running skeleton (page opens, stub figure with the full API, stub model with self-checks, a short film
   that renders, gates that run):
   ```
   node <kit>/new-topic.mjs <slug> --archetype machine|bench|micro|field|chart|investigation --title "..." --port 528x
   ```
   It goes next to the kit (`<kit>/../<slug>`, or `--dir <parent>`), with `topic.config.json`, its own git repo, and a
   first commit. Ports: one per parallel topic, from the range you were given.
3. **Model** `src/model.mjs`: replace the stub, keep the interface (`QUANTITY`, `DEFAULTS`, `KNOBS`, `simulate`,
   `stateAt`, `selfCheck`; the CLI tail after `// @cli`). Real constants with sources, an energy/momentum/charge balance
   or a known limit as self-checks. `node src/model.mjs` must exit 0. Quote the headline numbers in the README.
4. **Figure** via the anatomy skill: read its `SKILL.md`, `references/craft.md` and the closest example FIRST. Replace
   `figure/subject.mjs` (and the plate if needed) with the real object: many small precise parts, real material colours
   (`materialCss`, light theme first), every part recorded for the audit, live slots for what moves. Honour the figure
   API contract (`references/figure-api.md`): set/get/play/pause/onChange/clock/advance, `view({region, zoom})`,
   `focus(region)` fogging toward grey (~0.45, never white), `frame({aspect})`. The kit's `figure/stage.js` (XFigure)
   gives you view/focus/frame/clock; you add posing (`time`, `pose`, ...). Audit to `audit passed`, line check to 0.
   Sizes: Figure 40-80 parts, Hero 80-150; an Epic needs the user's yes. A sub-agent may build the figure to a
   written contract; you integrate and check it.
5. **Explainer** `src/content.mjs`: 6-8 steps, each opening on a prediction whose wrong options are catalog
   misconceptions (`catalog` id), camera (`view`) + spotlight (`focus`) on the part that matters, `after` shows the answer.
6. **Open lab** (`src/app.mjs`, `src/lab.html`, `src/widgets.mjs`): the model's real knobs, real time to 20x slower (or
   step by hand), live instruments (header-band readouts, labels outside the plot or on backings, traces clipped), and 3
   challenges with checks on the live state.
7. **Shot list as code** `video/timeline.mjs` + `video/scene.mjs`: wide -> close-up -> slow motion -> pull back for each
   idea; the camera moves to what is said; key events POSED on the spoken word (`wordAt`, cues, `pw` model-time maps);
   readouts show the number being spoken. Rules: `references/film-direction.md`.
8. **Narration** `video/assets/data/narration.json` (ElevenLabs; the voice in `voices.narrator`, `{cue}` markers,
   `readouts` for numbers that must be on screen): `node <kit>/audio.mjs <topic> narrate --dry`, then without `--dry`
   (the voice cache makes unchanged lines free). Sounds: `sfx.json` (prompts; `"lib:<name>"` when your library has it),
   bed: `music A B` -> listen -> `--keep B --as <name>`, or `music --from-lib <bed>` from your library. Until the voice exists, `narrate --placeholder` gives timing so the film can be built.
9. **Sheets and stills, reviewed by eye**: `node <kit>/render.mjs <topic> --sheet 3,12,25,...` and LOOK at every frame
   (Read the JPGs): framing, full bleed, nothing white-on-white, labels clear, the subject the most contrasty thing.
10. **Full render**: `node <kit>/render.mjs <topic> --workers 3` (1080p master, 720p web copy crf 29 veryslow tune
    animation 96 kbps, poster). Fix spans with `--ranges a-b,c-d` instead of re-rendering everything.
11. **Gate**: `node <kit>/gate.mjs <topic>` until every row is PASS (`references/quality-gates.md`).
12. **Ship**: `node <kit>/ship.mjs <topic>` (page + site), then `--deploy` (Cloudflare Workers via wrangler,
    when the user approved deploying). Optionally publish `out/page/index.html` as a claude.ai Artifact: load the
    `artifact-design` skill first, icon one generic word, the 720p film and poster as files.
13. **README + STATUS** (what is done, URLs, film length, model numbers, gate table, known gaps; later "Fixes after
    review"), commit.

## The six archetypes

Detail, instruments and worked examples for each: `references/archetypes.md`.

| archetype | when | the figure must contain |
|---|---|---|
| machine | the device is the concept | the real machine cut open, its moving parts posed by the model (four-stroke, generator, heat-pump, pendulum-clock, crumple-zone) |
| bench | a classic experiment on a bench | the apparatus on an optical/lab bench with its real meters (photoelectric, camera-lens) |
| micro | the concept lives at particle level | a real container with a magnifier window where the particles move (the second-law marble cabinet) |
| field | invisible fields and space | a tray/table that makes the field visible: compass lattice, iron filings, rubber sheet |
| chart | math-heavy, graphs | a pen recorder/plotter drawing the graph as the system beside it moves |
| investigation | practices and engineering design | a workbench with the set-up, a stopwatch/meter and a logbook that fills trial by trial |

## Topic folder (what a topic holds)

```
topic.config.json   title, slug, worker, port, figure { api, id, name }, colours, film { chapters, units, end }, page
src/model.mjs  src/content.mjs  src/widgets.mjs  src/app.mjs  src/lab.html  [src/page.css]
figure/build.mjs  figure/subject.mjs (+ more modules)  figure/live.js      -> figure/<name>(-light)(.fragment).html
video/timeline.mjs  video/scene.mjs  video/assets/data/{narration,sfx,music,mix,project}.json
README.md  STATUS.md  .gitignore   (out/, video/out/ are build output)
```
Kit commands take the topic folder: `render.mjs`, `gate.mjs`, `ship.mjs`, `audio.mjs`, `checks/*.mjs`. Layout and
every flag: `references/kit.md`.

## Hard rules

- English (US) on screen and in narration; audience older students and adults unless the card says otherwise.
- Light theme film; full-bleed 16:9 via `frame({ aspect: 16/9 })`; never a card or a square figure inside the frame.
- Focus fogs the rest toward a mid grey; never toward white. Real material colours with four tones.
- Slow motion is labelled ("20x slower", from the timeline's `rate`). Posed events land on the spoken word.
- Headless Chrome ALWAYS `--mute-audio` (the kit enforces it; any script of your own must too). One browser per worker.
- Parallel work: one agent per topic, each in its own folder on its own port (`references/agent-rules.md`; the
  `explainer-round` workflow in `<kit>/.claude/workflows/` runs a whole round). Render with `--workers 3` when other
  topics render at the same time.
- Work only in your topic folder; never edit other topics, the anatomy skill or your audio library by hand (adding a
  new bed or sfx to the library through the tools is fine).
- Before deploy and publish, the gate table is all PASS (a WARN needs a sentence in STATUS).

## References

- `references/figure-api.md`: the figure API contract, regions, focus fog, live slots, what XFigure gives you.
- `references/film-direction.md`: the direction rules and how the timeline expresses them.
- `references/quality-gates.md`: every gate, what it measures, how to fix a failure, and the lessons behind them.
- `references/archetypes.md`: the six archetypes with objects, figure contents, instruments, worked examples.
- `references/concept-card.md`: the card format with an example.
- `references/curriculum.md`: optional curriculum data (topics, specs, misconception catalog) and how to use it.
- `references/agent-rules.md`: parallel rounds, ports, what a coordinator checks.
- `references/kit.md`: kit layout, commands and flags, the topic interfaces (model, APP, hooks, timeline).
