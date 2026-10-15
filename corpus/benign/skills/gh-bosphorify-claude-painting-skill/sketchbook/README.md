# Sketchbook

What each painting taught, per painter, so the next painting of that painter starts where the last one left off instead of from zero. Read `<painter>.md` before writing a dossier, and append an entry after every painting, including the ones that didn't work: the failures and the parameter values are the useful part.

One file per painter, named by a lowercase slug (`turner.md`, `cezanne.md`, `hokusai.md`). Lessons about the kit itself rather than a painter (a tool that misbehaves, a workflow that saved time) go in `kit.md`. Add a row to the index when you create a file.

## Index

| Painter | File | Paintings |
|---|---|---|
| J. M. W. Turner | `turner.md` | turner-steamboat-snowstorm (oil) |
| John Singer Sargent | `sargent.md` | sargent-mountain-stream (watercolor) |
| Edvard Munch | `munch.md` | munch-moon-road (oil) |
| Pieter Claesz / Willem Claesz Heda | `claesz.md` | claesz-snuffed-candle (oil) |
| Vilhelm Hammershøi | `hammershoi.md` | hammershoi-farthest-room (oil) |
| Vincent van Gogh | `vangogh.md` | vangogh-open-gate (oil) |
| Claude Monet | `monet.md` | monet-ice-floes (oil) |
| Claude (its own manner) | `claude.md` | claude-self-portrait (oil) |
| (the kit itself) | `kit.md` | lessons about tools and traps |

## Entry format

Create the file with a `# <Painter>` title if it's missing, then append:

````markdown
## YYYY-MM-DD · <slug> · <oil | pencil | charcoal | watercolor | ...>

- **Subject and size:** what was painted, W×H, seed.
- **Worked:** what read as the painter, and the call that did it
  (e.g. "the constructive stroke: fill_strokes per patch with fields.constant(a), length=(30, 70) px, flat_bristle").
- **Failed:** what read as code or as another painter, and what the critique rounds could not fix.
- **Parameters that worked:** the values worth reusing, as code.
  ```python
  cv.ground("burnt_sienna", texture="linen", tone=0.5)
  passes = [brush("filbert", size=3.2 * S, impasto=0.04), brush("flat_bristle", size=1.2 * S, impasto=0.1),
            brush("round_bristle", size=0.6 * S)]
  cv.glaze(glow, "indian_yellow", strength=0.2)
  ```
- **Kit gaps:** tools that were missing or weak, and whether you extended the kit (preset or technique name).
- **Next time:** one or two concrete things to try first.
- **Files:** `paintings/<slug>/`, in the project where it was painted.
````

Keep entries short: a few lines each, and parameters only when they're worth reusing. When a file gets long, fold repeated lessons into a short "What works for <painter>" list at its top, and keep the dated entries below it.
