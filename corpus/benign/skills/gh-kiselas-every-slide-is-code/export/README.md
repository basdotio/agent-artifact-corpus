# export

The HTML deck is the source; this turns it into everything else, and checks it.

## Setup

Node 18+ and Google Chrome.

```bash
npm install
```

Chrome elsewhere: `CHROME_PATH=/path/to/chrome node deck.mjs ...`. MP4 also needs `ffmpeg` in PATH; GIF does not.

## Commands

```bash
node deck.mjs pdf    deck.html [out.pdf]     # vector, final step per slide; --steps, --raster
node deck.mjs pptx   deck.html [out.pptx]    # static slides + speaker notes; --steps
node deck.mjs png    deck.html [dir]         # every rest frame; --last, --jpg --width 960
node deck.mjs sheet  deck.html [sheet.png]   # contact sheet of all rest frames; --cols 5
node deck.mjs strip  deck.html [strip.png]   # one transition: --slide N --frames 8
node deck.mjs still  deck.html 6.2 6.2@0.4 6.2@rest 7 --out dir [--width 960]   # exactly these states as PNG
node deck.mjs gif    deck.html [out.gif]     # video timeline; --from --to --fps 12 --width 960 --hold 1.2
node deck.mjs mp4    deck.html [out.mp4]     # video timeline via ffmpeg; --fps 30 --hold
node deck.mjs mp4 deck.html talk.mp4 --timings timings.json --voice narration.wav [--loudnorm] [--captions talk.srt]   # narrated video
node deck.mjs timings deck.html --from-notes [timings.json]   # starter timings from the speaker notes' word count
node deck.mjs timings deck.html --check timings.json          # what holds a timings file gives; what does not fit
node deck.mjs analyze REF... [--out dir]     # reference (PDF, images, deck.html) -> report.md, analysis.json, contact-sheet.png
node deck.mjs check  deck.html               # lint; exit code 1 on errors; --timeline, --no-webfonts
node deck.mjs perf   deck.html               # frame cost per step and transition; exit code 1 over 16 ms
node deck.mjs fonts  deck.html [out.html]    # metric-matched fallback fonts; --write inserts them
node deck.mjs bundle deck.html [out.html]    # inline fonts, CDN scripts, remote images (+ fallback fonts)
node ../scripts/palette.mjs --accent "#dd4428" [--bg light|dark|HEX] [--second auto|HEX] [--html out.html]   # palette from one accent
```

`analyze` needs `scripts/analyze-reference.mjs` (and `palette.mjs`) next to this folder; a PDF needs `pdfjs-dist`, which `npm install` fetches (it runs inside Chrome only; its Node engine field is stricter than this package's, so `npm install` on Node 18 may warn).

### Speed: `--workers`, `--draft`, `--profile`

`gif`, `mp4`, `check`, `png`, `sheet`, `strip` and `still` capture frames with CDP `Page.captureScreenshot` (`optimizeForSpeed`) and run on a pool of browsers: one worker thread with its own Chrome each.

- `--workers N` (default `min(4, max(1, floor(cpus / 4)))`). The browsers share one GPU, so more than about a quarter of the cores does not help; measure once on your machine.
- Chunking depends only on the frame range, never on `--workers`: any worker count gives the same frames in the same order (pixels can differ by 1 to 2 levels between runs: GPU rounding). `--signatures a.txt` writes a 16x9 luma signature per captured frame and `node deck.mjs sigdiff a.txt b.txt` compares two runs (`--workers 1` vs `--workers 4`).
- `--draft` (gif, mp4): half size, half the frame rate (mp4 15 fps, gif 8 fps, unless `--fps` is given), JPEG frames, x264 `veryfast` at crf 26, a 63-colour GIF palette. For iterating on timing; render the final cut without it.
- `check` without `--timeline` uses one browser by default (it is two seconds of work; extra browsers cost more to start than they save); `check --timeline` uses the pool.
- `--profile` (gif, mp4): the 10 slowest frames by timecode (with the slide and step they belong to) and the mean frame cost for every second of the timeline.
- Each chunk of a GIF starts with a full frame, so a parallel GIF is a little larger than one written in a single pass (a few KB per chunk).

### Narrated video: `--timings`, `--voice`, `--captions`

The voice-over drives the step holds. Slides' transitions still play between the holds; only the time each state stays on screen changes.

```bash
node deck.mjs timings deck.html --from-notes timings.json --wpm 150     # 1. a starter file from the notes
#    ... record or synthesise the narration, then edit the numbers to where each state begins in it ...
node deck.mjs timings deck.html --check timings.json --voice narration.wav   # 2. dry run: holds, warnings, lengths
node deck.mjs mp4 deck.html talk.mp4 --timings timings.json --voice narration.wav --loudnorm --captions talk.srt
```

**`timings.json`** maps states to the second the voice-over reaches them (seconds from the start of the audio, which is also the start of the video):

```json
{ "_comment": "keys starting with _ are ignored", "1.0": 0, "2.0": 9.8, "2.1": 14.2, "3": 21, "end": 93.5 }
```

- Keys are `slide.step`, the numbers `check` and `still` print (slide 1-based, step 0 is the slide before its first build); `"3"` means `"3.0"`. Numbers are the state's start.
- "Start" means: for step 0 of a slide after the first, the moment the transition into it begins; for the other steps, the moment the step's builds begin. So the new slide's title is on screen about half a transition later, and a build with its own `data-delay` shows its first pixel that much after the number. The video frame at `start` is the first frame of the state's animation (checked against `still S.T@t`: identical to the frame).
- A state's hold is what remains until the next start, minus the transition into it (`data-hold` is ignored for the states you give). States you leave out share the gap between the states around them in proportion to their own `data-hold`, so a file with only slide starts (`"2": 9.8, "3": 21`) is enough to start with.
- `"end"` is the video's length. Without it the video ends at the voice's length plus `--tail` (default 0.6 s), or, with no voice, after the last state's own hold. `"1.0"` must be 0 (or absent): the video starts on the first slide. A state closer to the next one than its transition plus 0.25 s gets 0.25 s and a warning; the next given state then comes late by the missing time (the warning says so), and later ones recover.
- Errors (exit 1): a key that is not a state of this deck (`2.7` on a slide with steps 0-1), a state given twice (`2` and `2.0`), starts that do not increase, a negative or non-numeric value.

**`--voice v.wav`** (mp4 only; any format ffmpeg reads) is cut at `--from`, resampled to 48 kHz stereo, padded with silence and trimmed to exactly the video's length, and muxed as AAC 192 kbit/s in the same ffmpeg call that joins the video chunks (the video is not re-encoded). `--voice` without `--timings` puts the audio on the deck's own timeline. Needs `ffprobe` (ships with ffmpeg). **`--loudnorm`** runs single-pass `loudnorm` (I=-14, TP=-1.5, LRA=11) and a limiter at -3 dB (the same chain as the sister project's `render.mjs`); the command prints the loudness it measured on the result (EBU R128 integrated and true peak). `--timings` also works for `gif`.

**`--captions talk.srt`** writes subtitles from the speaker notes: each slide's notes are split into sentences (at most 84 characters a cue, cut at commas or spaces, two lines of at most about 42), and spread over the slide's window (from its state 0 start to the next slide's) in proportion to their length. It is a placement, not speech recognition: if your narration departs from the notes, the cues drift inside the slide but never cross a slide boundary. `--from` shifts the cues. Works with or without `--timings`, and with `timings --check` to write subtitles without rendering.

**`timings --from-notes`** counts the words of each slide's notes and gives the slide `words / (wpm / 60) + pause` seconds (`--wpm 150`, `--pause 0.5`), never less than its transitions plus 1 s a step (a slide without notes keeps the deck's own holds). Steps split the slide's time by their `data-hold`. It writes every state with its start rounded to 0.1 s and prints a table; it is a starting point for a person or a TTS run to correct, not a schedule. `timings --check` resolves a file the same way the renderer does and prints, for every state, its start, transition and hold.

The renderer rewrites the segments of the timeline that the page returns from `window.__deck.timeline()` in place before the first frame (every worker resolves the same file against the same natural timeline). `__draw` must read that object, which `runtime/deck.js` does.

### `analyze`: read a reference before designing

```bash
node deck.mjs analyze reference.pdf                 # -> reference-analysis/{report.md,analysis.json,contact-sheet.png}
node deck.mjs analyze shots/ --out ref              # a folder of images (natural order), or: a.png b.png c.png
node deck.mjs analyze ../examples/demo/deck.html    # a deck: the last step of each slide
```

For a PDF, the pages are rendered by pdf.js (`pdfjs-dist`, an export dependency that only ever runs inside the Chrome the exporter already drives, onto a canvas: no native library) at 1920 px wide, and the text layer gives words and sizes. Images are decoded by the same Chrome (PNG, JPEG, WebP, AVIF, GIF). A `deck.html` is rendered as the exporter renders it and its words and sizes come from the DOM (speaker notes excluded). The report has:

- **Palette**: per slide and for the deck, clustered in OKLab (colours closer than about a just-noticeable step are one colour; leader clustering on a 5-bit histogram of the full-resolution pixels), with area shares, on how many slides each colour appears, contrast on the background, and role guesses: background (largest area), ink (best contrast, neutral, on at least 20% of slides), accent (the most extensive chromatic colour, chroma from 0.06), second accent, muted (a mid-tone neutral), rule/panel. They are guesses: check them against the contact sheet.
- **Accent share per slide** (median, maximum, slides over the kit's 10%) and the **share of each slide that is not background** (ink coverage).
- **Words per slide** (median, maximum, slides over 40 and 60), **text sizes** normalised to a 1080 px canvas (by size class, the sizes that carry the most words, the smallest) and the **title's place**: where it sits on each slide, how many slides keep it at the modal left and top, which do not. For images there is no text layer: words and sizes are skipped and the report says so; the title's place is estimated from the first band of non-background pixels.
- **Estimated density** (from words, or from ink coverage alone), the slide count and a short list of what to write down: palette and roles, type, grid, density, rhythm, devices that repeat, what not to copy. Read the contact sheet, write the style grammar, borrow structure, not look.

The analysis code is `scripts/analyze-reference.mjs` (also runnable on its own); the colour maths is shared with `scripts/palette.mjs`.

### `still`: look at exactly one state

```bash
node deck.mjs still deck.html 6.2 6.2@0.4 6.2@rest 7 --out stills --width 960
```

`S.T` is slide S, step T (1-based slide, as in `check` output); a bare `S` is the slide's last step. `@t` is seconds into that step's animation, the number `check --timeline` prints next to a finding (`[still 6.2@0.45]`); `@rest` or no suffix is the rest frame. For step 0 of a slide after the first, the animation clock starts with the incoming transition, so `@t` below the transition length lands inside the transition. The command prints the path of every PNG. `--width` scales the output (default: full canvas).

### `check`: new in this version

- `low-contrast` (warning from 3:1 to the norm, error under 3:1; deliberately dimmed text is skipped): WCAG 2 contrast of the text colour against the real backdrop, norm 4.5:1, or 3:1 for text of 40 px and above. The backdrop is composited from what is painted under the text (backgrounds, SVG shapes, opacity); a canvas is measured when the pixels under the line are uniform. The message also shows APCA Lc as information. Findings are grouped by text colour, with the count and examples.
- `contrast-unknown` (warning): the backdrop is an image, video, gradient or a non-uniform canvas.
- `data-lint-skip` on an element (or an ancestor) skips both.
- `escapes-box`, `overflow` and `off-canvas` now say by how many pixels; the summary line ends with the worst one.
- `--timeline` findings end with `[still 6.2@0.45]`, ready to paste into `still`, and the run ends with one `still ...` command listing them all.

### `fonts`: fallbacks that keep the layout when Google Fonts is blocked

```bash
node deck.mjs fonts deck.html                 # print the CSS block and what --write would change
node deck.mjs fonts deck.html --write         # insert the block and extend the font stacks in place
node deck.mjs fonts deck.html out.html --write
```

For every family requested from Google Fonts (or declared with `@font-face`), the metrics come from `@capsizecss/metrics`, and a `@font-face` named `<Family> Fallback` on a local system font (Arial, Times New Roman or Courier New, chosen by the family's category) is computed with `size-adjust`, `ascent-override`, `descent-override` and `line-gap-override`. `--write` puts the block in a `<style id="dk-font-fallbacks">` and adds `'<Family> Fallback'` right after the family in every font stack it finds (CSS, custom properties, SVG and canvas font strings). It is idempotent. A family capsize does not know is reported and skipped. `bundle` does the same automatically.

## Page contract

The page is opened with `?render` and must expose:

```js
window.__deck = { W, H, slides, states(which), show(i, step), buildPrint(list), timeline() };
window.__meta = { W, H, FPS, DURATION };
window.__draw = T => {};   // timeline frame
window.__ready = true;     // after fonts and images
```

Decks built on `runtime/deck.js` provide all of it. Details in [../01-runtime.md](../01-runtime.md) and [../12-export-qa.md](../12-export-qa.md).

`gif`, `mp4`, `check` and `still` jump between arbitrary times, so `__draw(T)` must be a pure function of `T` (the runtime guarantees it). Every worker loads the deck in its own browser and renders its own chunks.
