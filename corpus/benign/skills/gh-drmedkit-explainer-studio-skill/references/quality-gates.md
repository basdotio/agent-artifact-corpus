# Quality gates

`node <kit>/gate.mjs <topic>` runs them all and prints a table (logs in `<topic>/out/gate/`, the table in
`out/gate.json`; exit 1 on any FAIL). `--quick` (text every 2 s, page at 1400 only) for iterating; `--skip-film` before
the full render. Each gate is a lesson from the seven hand-built explainers.

| gate | measures | typical fix |
|---|---|---|
| model | `node src/model.mjs` (topic.config `model.check`) exits 0: the self-checks close | fix the physics, not the check |
| audit | anatomy `node figure/build.mjs --audit` ends `audit passed` (clearances, supports, depth order, stand-in shapes, crowding, ...) | fix the geometry; `cover`/`allow` only for pairs you looked at in a close-up |
| lines | anatomy `scripts/lines.mjs` on the dark and light figure pages: 0 floating line ends | end every line on a stroke, dot or outline; `free` only for text rules and needle tips |
| film text | `checks/textcheck.js` every 0.5 s over the whole film: instrument labels clipped or overlapping, **a stroke through a label**, overlay boxes overlapping or off the frame | lay labels out from the font size; header bands for readouts; backings (`data-backing`) behind labels inside plots; clip traces to the plot |
| readouts | every spoken measurement ("eight point oh volts", "thirty g", "20 times") is printed on screen (readout, note, label, panel, figure readout; never the subtitles) between 0.5 s before the word and 2 s after its line | pose the model on the word; show the number in the readout or a note; `"readouts": false` on a line only when the number is rhetorical |
| contrast | sampled every 2 s (title/end cards excluded), bottom 22 % ignored: ink = share of pixels darker than 200/255. washed (ink < 1 % and darkest 5 % lighter than 205) fails; more than a quarter pale (< 2 %) fails | real material colours, darker structure, fog toward grey not white, the subject as the contrasty part |
| page 390 / page 1400 | the built page in muted Chrome: every tab, every step before and after answering, every lab range at min and max, every lab button; text check at each stop, console errors, sideways scroll | fix layout at phone width; `page.labPoses` in topic.config adds topic-specific lab states |
| voice | words.json is the real narration, not `--placeholder` timing | `node audio.mjs <topic> narrate` |
| 720p size | the web copy exists, is under 15 MB, and its duration matches the narration | `render.mjs --encode-only --crf720 30`, or tighten the film |

Contrast calibration (finished films sampled every 4 s): crumple-zone after its look pass ≥ 5.6 % ink everywhere;
generator ≥ 1.7 %; four-stroke and pendulum-clock fall to 0.0-0.4 % on the shots that read as white-on-white. Run
`node checks/contrast.mjs <film.mp4>` on any film.

Not automated, still required (do them by eye, write them in STATUS):
- look at the `--sheet` stills and the gate's `contrast-*.jpg` frames; zoom into instruments for lines through text
  the checker excuses (strokes painted under a backing);
- listen to the mix once at the end (levels, nothing clipped, sounds on their frames);
- anatomy 4× close-ups of every junction in both themes (anatomy `references/verify.md`).

## Lessons the kit enforces (from the reviews)

- Text-collision check over the whole film every 0.5 s and the page at 390 and 1400 px; also lines through text.
- On-screen readouts match the narration at that moment: pose the model on the spoken word.
- Light theme: real material colours and four-tone shading; focus dims toward grey, never toward white.
- Slow motion labelled "20× slower" (the scene derives it from the timeline's `rate`). Full-bleed 16:9
  (`frame({aspect})`), never a card in the frame.
- 720p web copy: crf 29, `-preset veryslow -tune animation`, 96 kbps AAC, must be < 15 MB for the artifact
  (`lib/ffmpeg.mjs` WEB). 1080p master crf 19 slow, 192 kbps.
- Headless Chrome always `--mute-audio` (`lib/chrome.mjs` refuses to launch without it); one browser per render worker
  (a background page gets no rAF); `--ranges` partial re-render.
- Event-placed sound effects (pushed on the frame), loops following the seen speed, the bed ducked under the voice;
  effects trimmed, normalised to one peak, faded in 10 ms, spaced at least 0.35 s (`audio/mix.py`).
- Narration through the shared voice cache (an edited line re-bills only that line); captions inline as VTT (artifacts
  do not serve .vtt files); chapters from the narration cues.
- Instruments: readouts in a header band, labels laid out from the font size, a placement solver or backings for chart
  labels (heat-pump `placeLabel`), traces clipped to the plot, values rounded for display (camera-lens showed
  49.99999999999999 mm).
- Send only changed settings to the figure (pendulum-clock: re-release on every slider move); snap settings in the film.
