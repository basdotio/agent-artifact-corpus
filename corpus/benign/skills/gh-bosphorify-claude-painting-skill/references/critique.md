# Critique: looking hard and repainting

Every render writes a review sheet beside it (`final_review.png`; `design_review.png` for the plan). Look at it as a painter steps back from the easel: first from across the room, then with the nose to the canvas. Write what you see in `notes.md` before changing code, so each round has a stated problem and a stated fix.

## Reading the review sheet

| Panel | What it answers |
|---|---|
| **Full view** (top left) | Composition, focal point, overall color. Does it look like the painter at a glance? |
| **Values** (5 levels of lightness, top right) | The value structure with color taken away: are there 3-5 clear masses, or confetti? Is the value pattern the one the dossier planned? |
| **Squint** (blurred, right) | How it reads from across the room: big masses, where the eye lands, warm against cool. Detail can't help a painting that fails here. |
| **1:1 crops** (bottom row) | Paint quality at full resolution: does it read as paint or as code? Your `focus` points come first, then the windows with the most local detail, then the center; each is labelled with its top-left corner. |

The automatic crops go to the busiest windows (flakes, scratches, rigging), which are rarely the focal point: in the Turner acceptance run they never once showed the boat. So pass the focal point as `focus` (`studio.save(final, path, focus=[(x, y)])`, or `python -m atelier.studio review final.png --focus x,y`) and look at it at 1:1 every round.

Two more things to look at: the **progress contact sheet** (did each layer do its job: values in the underpainting, masses in the block-in, lights in the details?) and **`design_review.png`**, the target value plan. Put the final's value map next to the design's: if they differ, either the painting drifted or the plan was wrong, and the dossier says which.

## Checklist, with what to change

Go in this order: a value problem can't be fixed with texture, and texture can't save a missing focal point. For each failure, change the thing at the level it lives: values and composition in the design map, direction in the fields, stroke character in brushes and passes, surface in `finish`.

**1. Values read when squinting.** The squint shows a few big light and dark masses, and the value map matches the plan.
- Muddy, everything mid-grey: widen the value range in the design (lighter lights with more `lead_white`, darker darks with `burnt_umber` + `ultramarine`); group values into 3-5 masses; glaze to pull down a whole area (`glaze` darkens lights, keeps darks); scumble to lift a dark area without repainting it.
- Confetti (values jump inside a mass): simplify the design, and lower `jitter` or raise `tolerance` so strokes stay inside their mass.
- Right values, wrong place: move the masses in the design, not with strokes on top.

**2. A clear focal point.** One place wins: the strongest value contrast, the hardest edge, the most saturated color and the most detail meet there.
- The eye wanders: quiet the competitors (glaze them toward their surroundings, soften their edges with `wet_in_wet`, lower their contrast in the design) rather than shouting louder at the focus.
- The focus is weak: put the darkest dark against the lightest light there, paint its accent by hand with the hardest edge, add `impasto` lights, lead to it with the fields (vortex, contour lines pointing in).

**3. Edge hierarchy.** Hard at the focus and where a form turns sharply into light; soft on turning forms and in atmosphere; lost where values match.
- Every edge equally hard (cut-out look): `wet_in_wet` along edges away from the focus, a glaze or scumble across them, a higher `blur` or `tolerance` in `paint_from_design`.
- Everything soft (no snap anywhere): hand strokes with `flat_bristle` or `rigger` along the few edges that matter, lower `tolerance` near the focus.

**4. Color temperature.** One light: if it's warm, shadows lean cool (and the other way round). Saturated color is rare and where the dossier puts it.
- Flat temperature: glaze the shadows cool (`ultramarine`) and the lights warm (`indian_yellow`, `raw_sienna`); mix a touch of the complement into large areas of the design.
- Candy colors: take pure pigments out of the design mixes (add white, the complement or an earth); keep the saturated accent for the focus.
- Wrong period feel: check the palette against the painter's time (pigment dates are in `atelier/pigments.py`).

**5. 1:1 crops read as paint, not code.** Crops should show bristle tracks, broken edges, varied strokes, underlayers peeking through and relief where the paint is thick.

| Looks like code | Change |
|---|---|
| strokes all the same length and width | wider `length` ranges, more passes with different sizes, varied `pressure`; hand strokes of different lengths |
| strokes all parallel, as if ruled | mix `fields.noise` into every field, `contour` fields that follow forms, a different field per region |
| perfectly straight lines (rain, masts, horizons) | 3+ control points with small offsets, varied width and opacity, broken into pieces |
| flat fills, smooth gradients | lower `density` so the underlayer shows, `jitter` 0.08-0.12, a scumble or dry-brush pass, a little noise in the design |
| identical marks in a grid (stipple, hatch, dabs) | vary `size`, spacing and colors; two sparser passes instead of one dense one; fewer, bigger marks |
| plastic surface, relief everywhere | fat over lean (`impasto` near 0 in lower layers), thick paint only in the lights, lower `varnish`; judge at full size |
| cut-out rectangles (knife slabs) | wider slabs in colors close to their surroundings, fewer of them, or `impasto` strokes instead |
| hard vector outlines in dry media | construction lines in `2H` at low weight, broken contours, pressure in `spline` / `vertex` |
| cut paper (watercolor): every wash one flat tone with the same crisp rim | vary `soft` and `edge` from wash to wash, lose some edges into their neighbours wet-in-wet (`soft` 10-40, `edge` 0), grade the big washes (`grade`) |
| snow (watercolor): a pale wash over everything | leave paper: reserve the whites first (`holes`), tone only the quiet areas (slack water, shadow planes), a few big darks against the paper |
| confetti (watercolor, and dabs in oil): many small scattered marks, stamps, commas | fewer, bigger strokes that are also the form; merge the small marks into one wash or one stroke |

**6. Repetition and grid artifacts.** Squint at the crops and the full view for patterns: the same stroke repeated, rows of dabs, a checkerboard from the `paint_from_design` cell grid, the same spiral arm over and over, noise that tiles.
- Break the rhythm: randomize counts and spacing, vary sizes, change `spacing` or `threshold` of the passes, raise the `scale` of `fields.noise`, add a second noise field with a different scale.

**7. Fidelity to the dossier.** Go through the dossier line by line: palette, ground showing where planned, stroke vocabulary, composition, values, edges, surface. Anything missing is a finding. If the painting found something better than the plan, change the dossier deliberately and say so in `notes.md`.

## The critique loop

Each round, name the one to three biggest problems in the order above, change the code for them, render, and compare the new review sheet with the last one. Changing an early call reshuffles the random stream, so expect small differences everywhere and judge whether the named problems got better.

**Your own look, every round.** It is quick and it knows the plan. Its weakness is habituation: after a few rounds you see the picture you meant to paint. The fresh-eye critic covers that.

**Scale and focus.** Iterate oil at 900 px, but from round 2, once the big forms read, render at the final size and critique that sheet with a 1:1 crop of the focal point. Tool flaws (knife slabs, scrapes down to the bare weave, stray dabs, crackle) and the real stroke scale don't show at 900 px. Dry media are worked at full size anyway (`method.md` §5).

**The fresh-eye critic.** A subagent started without this conversation's context, given only a dossier summary and the review sheets: no code, no notes, no earlier versions. That keeps it cheap (one short prompt and one or two images) and unbiased: it judges the picture rather than the intentions behind it, and it hasn't got used to it. It scores a fixed rubric, so checkpoints can be compared, and returns a short list of fixes. Two checkpoints by default:
1. when the big forms read at the final size (usually round 2 or 3), while problems are still cheap to fix;
2. before the final, to decide whether to stop.

Add a third when the scores are still rising and the top fix is one the kit can make. If you can't start a subagent, score the rubric yourself before rereading your notes, and treat the scores as rough.

**The readability check.** A painting whose subject no viewer can name has failed, however good the paint.
- **When:** once before the final, and once per option when the user picks between sketches.
- **How:** give a fresh subagent only the image, with no title and no text, and ask "What is this a picture of? One sentence." Run it on Sonnet.
- **Pass:** the answer names the subject.
- **On a fail:** change the one thing that misleads (a shape, a value, a missing cue) and ask a new reader once more.

The dossier summary is 5-10 lines in plain words: painter, period and the works in mind; subject; palette; key and the value pattern in one sentence; the focal point, where it is and what should make it win; edges; surface. Leave out the stroke-to-kit table, so the critic judges what it sees rather than the tools. The prompt, with the review sheet attached (focal point crop first):

```text
You are seeing this painting for the first time. It was made entirely in code, as a {painter} {oil painting |
watercolor | ...} of {subject}. The painter's plan in short:
{dossier summary}

Attached: its review sheet (full view, a 5-level value map, a blurred "squint" view, and 1:1 crops; the first crop
is the focal point).

Score each from 1 to 10, with one line of evidence (what you see, and where):
1. Value structure: a few big light and dark masses that read when squinting, in the planned pattern.
2. Focal point: one place wins, where the plan puts it.
3. Edge hierarchy: hardest at the focal point, soft or lost elsewhere.
4. Color temperature: one light, shadows the other way, saturated color only where it counts.
5. Paint quality at 1:1: reads as paint (varied, broken, layered marks), not as code (repeats, grids, ruled lines,
   flat fills).
6. Style fidelity: reads as {painter}, not as another painter or a filter.
7. The idea: one clear idea, and something a viewer would not expect. Name what looks generic.

Then at most three fixes, most important first: what is wrong, where, and what it should look like instead. Then name one thing that is unique here and must survive the next round.
Describe the picture, not code. Under 250 words in all.
```

**Blind A/B between versions.** To choose between two versions (before and after a risky change, or two candidates for the final), render both at the same size and put them on one sheet: `studio.compare(a, b, out)` or `python -m atelier.studio compare a.png b.png -o ab.png`. The sheet shows both unlabeled, with the same 1:1 crops, in a random order; which side is which goes to `ab_key.txt`, to open only after the verdict. Show the sheet to one fresh critic with the dossier summary. The reason: each critic scores on its own scale, so numbers from two critics can't be compared. In the Turner run one critic put round 13 at 65%, the next put round 14 at 55%, and a blind A/B then preferred round 15 over round 13. One critic looking at both side by side ranks them reliably.

```text
Two versions of one painting made in code, side by side: 1 (left) and 2 (right), the same size, with the same 1:1
crops under each. The painter's plan in short:
{dossier summary}

For each of these say which is better (1, 2 or even), with one line of evidence: value structure, focal point, edge
hierarchy, color temperature, paint quality at 1:1, style fidelity. Then say which one to keep, and the biggest
remaining problem of that one. Under 200 words.
```

**When to stop.** Stop when:
- the critic's scores stop rising between checkpoints (a point or so is noise between two critics; settle a close call with a blind A/B), or
- the top fix is something the kit can't do: write it in `notes.md` as a kit gap, and in the sketchbook, rather than spend rounds on workarounds, or
- the checklist passes and the dossier's key traits are visible.

For scale: the Turner acceptance painting took 15 rounds and 6 critics, and its last rounds moved it by a few points. Two checkpoints, a blind A/B for the final choice and an earlier stop would have reached nearly the same picture for a fraction of the cost.

Then render the final at full size and look at its review sheet once more. Record the rounds (problem → change → result), the critic's scores at each checkpoint and the remaining flaws in `notes.md`.
