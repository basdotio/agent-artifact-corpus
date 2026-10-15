---
name: painting
description: This skill should be used when the user asks for a painting or drawing made in code, in a painter's style or a traditional medium - "paint X in the style of Turner / Cézanne / Monet", "make an oil painting of ...", "a pencil / charcoal / ink drawing of ...", "a watercolor of ...", "paint like the Opus 5.5 examples" - or in Turkish, "... tarzında resim yap", "yağlı boya resim yap", "karakalem çiz", "suluboya resim yap", "resim çiz". Every mark is computed by code, with a numpy oil engine (toned grounds, spectral paint mixing, bristle brushes, glaze, scumble, impasto, palette knife, raking-light finish), and p5.brush with a watercolor paper layer for pencil, charcoal, ink and watercolor. No image models, no reference images. Works like a painter - style dossier, thumbnails, layers with progress snapshots, critique of review sheets, a sketchbook of lessons. NOT for photo editing, AI image generation, charts or animation (use javascript-animation).
---

# Painting (every mark computed in code)

Paint the way a painter works: decide the look in words, plan the values, lay the picture down in layers from ground to varnish, look hard at the result and repaint. The oil engine (`oil/`, Python package `atelier`) and the dry-media page (`dry/`, p5.brush) do the marks; this file and `references/` are the method. `<skill>` below is the folder this file is in.

## Model

The critique loop reads PNG review sheets, so it needs image input. If the current model can't see images, say so and treat the critique as not done. Built and tested with Claude Opus 5.5; say so if a weaker model's result looks crude rather than calling it the best possible.

## Default flow: don't stop to ask

Run straight through with sensible defaults and state them at delivery. Ask first only when the request has neither a subject nor a painter or medium.

1. **Read the brief.** Painter or style, subject, medium, format. Default size 2048×1536 (portrait 1536×2048 when the subject is vertical). Slug: `painter-subject`, e.g. `monet-poplars`.
2. **Open the folder** `paintings/<slug>/` in the current project. Read `<skill>/sketchbook/<painter>.md` if it exists: it holds what worked last time.
3. **Find the idea** when the brief leaves it open (`references/method.md` §0). Write 8 one-line concepts across subject, medium, viewpoint, time of day, palette and mood, then pick the most surprising one the kit does well.
4. **Write `dossier.md`** from what you know about the painter (template in `references/method.md`): palette as named pigments, ground, stroke vocabulary mapped to kit calls, composition, values, edges, temperature, surface, layer plan.
5. **Thumbnails and a value study** at 512 px before any full-size work (`references/method.md`). Composition and values are cheap to change now and expensive later.
6. **Paint in layers** with a progress snapshot after each: oil from `templates/oil_starter.py`, dry media from `dry/template.html`. Iterate oil at 900 px wide and dry media at full size (the paper grain turns to noise below it); `references/techniques.md` maps painter's terms to calls.
7. **Critique** with `references/critique.md`: your own look at the review sheet every round, biggest problem first (values, then focal point, edges, color, paint quality). From round 2 judge the full-size render, with a 1:1 crop of the focal point (`--focus`). A fresh-eye critic, a subagent given only a dossier summary and the review sheets, scores a fixed rubric at two checkpoints by default: when the big forms read, and before the final. Choose between versions with a blind A/B sheet (`compare`). Stop when the scores stop rising or the top fix is a kit limit, and log that in `notes.md`.
8. **Final render** at full size, one more look at its review sheet, then `notes.md` (decisions, critique rounds, known flaws) and an entry in the sketchbook. Deliver `final.png`, its review sheet and the progress contact sheet; offer one or two alternatives in a line (another painter, medium or crop).

## Choosing the medium

| The request says | Medium | Start from |
|---|---|---|
| oil, painting, canvas, impasto, glaze, "yağlı boya", most "X tarzında resim" of oil painters | oil (`atelier`) | `templates/oil_starter.py` → `paintings/<slug>/paint.py` |
| pencil, graphite, charcoal, ink, pen, "karakalem", "çizim" | dry (p5.brush) | `dry/template.html` → `paintings/<slug>/sketch.html` |
| watercolor, wash, "suluboya" | dry: washes, strokes, dry brush and lifts with `dry/paper.js` on a paper grain; p5.brush for pencil and pen | `dry/template.html` |
| gouache, acrylic, tempera | oil engine: thinner paint (low `impasto`), flatter edges, less varnish | `templates/oil_starter.py` |

When the brief leaves the medium open, let the idea choose it. Code is at home with line, repetition and geometry, for example:
- a technical drawing with its construction left in;
- one mark repeated into a system;
- graphite or charcoal on toned paper with one accent;
- pen hatching on kraft.

Oil is one choice among these. When a painter worked in several media, pick the one the named work or period is known for. Watercolor washes go through `Paper.shape` and `Paper.stroke`, which reserve whites with `holes`: p5.brush's own fill folds long strokes into ribbons, is slow at 2048 px and can't leave whites.

## Running things

```bash
uv run --project <skill>/oil python paintings/<slug>/paint.py paintings/<slug> [--width 900]   # oil: final.png + final_review.png + progress/
node <skill>/dry/render.mjs paintings/<slug>/sketch.html paintings/<slug>/final.png --progress paintings/<slug>/progress
uv run --project <skill>/oil python -m atelier.studio review some.png [--focus x,y]  # review sheet; --focus crops that point at 1:1 first
uv run --project <skill>/oil python -m atelier.studio compare a.png b.png -o ab.png   # blind A/B sheet; which is which goes to ab_key.txt
uv run --project <skill>/oil python -m atelier.studio contact <dir>       # contact sheet of NN_label.png frames
```

The starter runs in about 10 s at 900 px and 30 s at 2048 px. The dry render takes a few seconds and writes the review sheet itself. First run on a new machine: `uv` builds the oil environment on its own; for dry media run `npm install --prefix <skill>/dry` if `dry/node_modules` is missing (Chrome or Playwright's Chromium must be installed).

A painting folder ends up with: `dossier.md`, `paint.py` or `sketch.html`, `design.png` (the value study), `progress/` with `contact_sheet.png`, `final.png`, `final_review.png`, `final_stats.json` (strokes and painting time, from `studio.save(..., canvas=cv)`), `notes.md`.

## Defaults that matter

- **No reference images.** Work from knowledge of the painter, as the Opus 5.5 paintings did: it keeps the work a reading of the style rather than a trace of a picture, and it needs no network.
- **Your own picture, in their manner.** Work from what you know of the painter, never from images of their work, and don't try to reproduce or redraw an existing painting: the point is a new picture, not a copy (and a living artist's compositions are their copyrighted work). Beyond that the choice is yours: subject, story, motif and mood, including the kinds of scene the painter loved.
- **The design map is a plan, not the painting.** Big shapes with the right values; the texture comes from the strokes. Put small crisp things (a mast, a highlight, an eye) in by hand in the details layer.
- **Fat over lean.** Thin lower layers (`impasto` near 0), thick paint only in the top layer and the lights. Relief everywhere reads as plastic under the raking light of `finish()`.
- **Everything relative to the canvas.** Write positions as fractions of `W, H` and sizes times `S = W / 2048`, so thumbnails, studies and the final are the same picture.
- **Seeded and repeatable.** Same script and seed, same pixels. Changing an early call shifts the random stream for everything after it, so compare rounds by what changed on purpose.

## Budget

- About 400k tokens and 90 minutes for a painting; about 600k and 2 hours for a pair of panels. When the budget is spent, stop, deliver the best version and list what is left in `notes.md`.
- Every check gets a cap. After a failed check, make one targeted fix and check once more. If it still fails, record it and move on.
- Run the fresh-eye critic on Opus, one per checkpoint. Run the readability reader (`references/critique.md`) on Sonnet. Never use Haiku.
- Write your rough tokens and minutes into `notes.md`.

## Extending the kit

Use the existing tools first. When a painter needs a mark the kit lacks, add it to the kit rather than to one painting, so the next painting has it too:
- **A brush:** a JSON preset in `oil/atelier/presets/` (fields in `oil/atelier/brushes.py`), a row in `oil/sheets/stroke_sheet.py`, a look at the regenerated `oil/out/stroke_sheet_review.png`, and an entry in `references/techniques.md`.
- **A technique:** a function in `oil/atelier/techniques.py` that draws its randomness from `cv.rng`, registered as a `Canvas` method in `oil/atelier/canvas.py`, a panel in `oil/sheets/technique_sheet.py`, a test in `oil/tests/`, and an entry in `references/techniques.md`. Run `uv run pytest` in `<skill>/oil`.

Scene code for one painting (its design map, its helpers) stays in `paint.py`. Code the next painting could reuse, such as an interior ray caster or a captioned sketch sheet, belongs in the kit. Details are at the end of `references/techniques.md`.

## Files

- `references/method.md`: style dossier template, thumbnails and value study, the design map in code, the layer sequence for oil and its dry-media equivalent.
- `references/techniques.md`: painter's vocabulary → API, every preset and technique with parameters and snippets, conventions (colors, masks, angles), p5.brush notes.
- `references/critique.md`: reading the review sheet, the checklist with fixes, the critique loop: the fresh-eye critic's prompt and rubric, blind A/B, when to stop.
- `sketchbook/`: per-painter lessons (format in `sketchbook/README.md`).
- `templates/oil_starter.py`: the layered method end to end, runnable (`<out_dir> [--width] [--seed]`).
- `oil/`: the `atelier` engine, its test sheets (`oil/sheets/`, output in `oil/out/`) and tests. `dry/`: `template.html`, `paper.js` (with the paper presets and light media), `lettering.js`, `print.js`, `render.mjs`, `sheets/` (`dry_sheet.html`, `papers_sheet.html`, `lettering_sheet.html`, `print_sheet.html`) and `test/`.
