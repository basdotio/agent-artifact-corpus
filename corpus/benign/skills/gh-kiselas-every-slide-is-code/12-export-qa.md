# Export and checking

## Formats

The HTML deck is the source. Every other format is a view of it:

| Format | Command | Contents |
|---|---|---|
| PDF | `node deck.mjs pdf deck.html` | vector, selectable text, one page per slide at its final step; `--steps` for every step, `--raster` for image pages |
| PPTX | `node deck.mjs pptx deck.html` | one full-bleed image per slide plus speaker notes; static and not editable as shapes |
| PNG | `node deck.mjs png deck.html frames/` | the rest frame of every step; `--last` final steps only; `--jpg --width 960` for small previews |
| single states | `node deck.mjs still deck.html 6.2 6.2@0.4 --out stills` | exactly the named frames as PNG (see "Look at one state") |
| GIF | `node deck.mjs gif deck.html teaser.gif --hold 1.1 --to 30` | the video timeline; frame-differenced, so holds cost almost nothing; parallel, `--draft` for previews |
| MP4 | `node deck.mjs mp4 deck.html film.mp4` | the timeline at 30 fps; needs ffmpeg; parallel, `--draft` for previews |
| narrated MP4 | `node deck.mjs mp4 deck.html talk.mp4 --timings t.json --voice v.wav` | the voice-over drives the step holds; audio muxed, `--loudnorm`, `--captions talk.srt` (see "Narrated video") |
| reference report | `node deck.mjs analyze reference.pdf` | palette and roles, accent share, words, text sizes, layout regularity of someone else's deck (see "Analyse a reference") |
| offline HTML | `node deck.mjs bundle deck.html deck.offline.html` | Google Fonts, CDN scripts and remote images inlined, plus metric-matched fallback fonts |

Setup once: `cd export && npm install`. Needs Node 18+ and Google Chrome (another Chromium via `CHROME_PATH`).

PDF and PPTX are static on purpose: PDF viewers do not play animation outside Acrobat, and PowerPoint cannot run the deck's builds. The rest-frame rule (00-agent-brief.md, 18) is what makes them good.

**The video timeline.** Each step holds for `data-hold` seconds (per slide, per step, or `--hold` for all), transitions play in between, step-0 builds start during the incoming transition. `--from` and `--to` cut a range.

## Checking

### 1. `check`: automatic lint on every rest frame

```bash
node deck.mjs check deck.html
```

| Finding | Meaning |
|---|---|
| `tiny-text` | rendered text under 20 px (SVG text is measured after scaling) |
| `safe-area` | text within 38 px of an edge (skip with `data-bleed`) |
| `overlap` | two text boxes overlap (glyph bands, not font boxes) |
| `overflow` | a box with `overflow: hidden` clips its content |
| `escapes-box` | text sticks out of the box it sits in (an element with a background or border), or out of the SVG rect/circle it is centred on; the message says by how many pixels |
| `off-canvas` | a box extends past the slide edge (mark intended bleeds with `data-bleed`) |
| `low-contrast` | text colour against the real backdrop under 4.5:1 (WCAG 2), or under 3:1 for text of 40 px and above: a warning between 3:1 and that norm, an error under 3:1; deliberately dimmed text (effective opacity under 0.9) is skipped; the message adds APCA Lc for information (see below) |
| `contrast-unknown` | the backdrop is an image, video, gradient or a non-uniform canvas, so the contrast cannot be measured (warning) |
| `density` | over 60 words on screen (warning) |
| `notes` | a slide without speaker notes (warning) |
| page errors | console errors and exceptions while rendering |

The exit code is 1 when there are errors, so it can run in CI. Text that is part of an illustration (a receipt, a code sample) can opt out with `data-lint-skip`.

Two flags widen the net. Run both before calling a deck done:

```bash
node deck.mjs check deck.html --timeline       # also every 0.15 s of every step while it animates
node deck.mjs check deck.html --no-webfonts    # with Google Fonts blocked, as on a locked-down network
```

Rest frames hide transient problems: in the demo, the scale read-out passed at rest but its minus sign stuck 29 px out of its box for half a second while it settled. Only `--timeline` catches that.

Each `--timeline` finding is one line per element, at its worst frame, and ends with a ready-to-copy state for `still`:

```
ERR   3.0   number  escapes-box (while animating, +1.20s): "re-entering data we already have" spills out of <div> by 36px   [still 3.0@1.2]
```

The summary line ends with the worst overflow in pixels, so a before/after comparison of a fix is one number.

**Contrast.** `low-contrast` composites what is painted under each text line (element backgrounds, SVG shapes, opacity; a canvas such as a stage counts when the pixels under the line are uniform) and computes the WCAG 2 ratio of the text colour against it. The gate is 4.5:1, or 3:1 for text of 40 px and above on the 1080 canvas (04-slide-design.md). The message also shows APCA Lc (SAPC 0.0.98G-4g, the constants of Myndex's apca-w3) as information: Lc 60 is a common floor for body text, 75 is comfortable. It never fails the check. Findings are grouped by text colour with a count and examples, and printed once per slide, again only when a later step adds texts. A dimmed or faded state that is intended (the previous point of a build, an unlit indicator on an illustration) is reported too; mark it `data-lint-skip`. `--timeline` does not check contrast.

With the severity policy above (a warning from 3:1 to the norm, an error under 3:1; dimmed builds are skipped) the demo deck had 45 warnings and no errors: 44 `low-contrast` and one `contrast-unknown`. The first version of the check reported 46 errors, all true positives by the rule as written: the muted colour `#857f72` on the paper (3.4:1, worst 3.38 on the grained stage) for every kicker, axis label and caption at 22 to 26 px; the accent `#dd4428` used as text on paper (3.6:1) and on the red tint under the margin gap (3.03:1), at 24 to 30 px; the green `#2b7a4b` (4.47:1, a hair under); the white step numbers on the accent discs (4.05:1). The unknown is the highlighter behind "$249 a month" (a gradient). The fix belongs in the deck's palette, not in the checker.

**The demo fix, measured.** `--muted` `#857f72` to `#6e685c` (3.4 to 4.6:1 on the paper); small accent text (24 to 30 px labels, bar values, the "16-point gap" note) in a new `--waste-text` `#ba2100` (4.5:1 on the red tint, 6.0:1 for the slip-coloured numbers on the discs, which now use it as their fill), small green (`■` swatches, the "less made" label, the "590" value) in `--saved-text` `#277648` (4.6:1); the big numbers (`$3,900`, `10%`, `86%`, `-41%`, `84`), bars, lines and fills keep `--waste` and `--saved`. Result: `check` goes from 45 warnings (44 `low-contrast`, 1 `contrast-unknown`) to 1 (the unknown highlighter), no errors. The before and after sheets read as the same deck; the small red labels are a shade deeper than the big red numbers next to them, which is the cost of legible 24 px text. A new deck starts from `scripts/palette.mjs` (04-slide-design.md) and does not have to find this out by lint.

### Look at one state: `still`

```bash
node deck.mjs still deck.html 6.2 6.2@0.4 6.2@rest 7 --out stills --width 960
```

Renders exactly the named states as PNG and prints the paths. `S.T` is slide S, step T (1-based slide, the numbers `check` prints); a bare `S` is the slide's last step. `@t` is seconds into that step's animation, the same clock `check --timeline` prints, so pasting its `[still 6.2@0.45]` shows the frame with the problem; `@rest` or no suffix is the rest frame. For step 0 of a slide after the first, the clock starts with the incoming transition. `--width` scales the output; the default is the full canvas.

### Narrated video: `--timings`, `--voice`, `--captions`

For a talk that should play by itself (a recorded pitch, a product launch video) the voice-over drives the holds:

```bash
node deck.mjs timings deck.html --from-notes timings.json --wpm 150      # starter file from the speaker notes
node deck.mjs timings deck.html --check timings.json --voice talk.wav    # dry run: every state's start, transition, hold; warnings
node deck.mjs mp4 deck.html talk.mp4 --timings timings.json --voice talk.wav --loudnorm --captions talk.srt
```

`timings.json` maps states to the second the voice-over reaches them: `{"1.0": 0, "2.0": 9.8, "2.1": 14.2, "3": 21, "end": 93.5}` (`slide.step` as in `check` and `still`; a bare `3` is `3.0`; keys starting with `_` are comments). A number is when the state starts: for step 0 of a slide after the first, when the transition into it begins; for the other steps, when the step's builds begin. The hold is what remains until the next start minus the transition into it. States you leave out share the gap in proportion to their `data-hold`, so slide starts alone are enough. `end` is the video's length (default: the voice plus `--tail 0.6` s). A state that gets less than 0.25 s after its transition is warned about; a state or key that does not exist, a state twice, or starts that do not increase, are errors. Full format in export/README.md.

`--voice` is cut, padded with silence and trimmed to exactly the video's length, and muxed as AAC in the call that joins the video chunks; `--loudnorm` normalises to -14 LUFS with a -3 dB limiter and the command prints the level it measured. `--captions` spreads each slide's speaker notes over the slide's window as SRT cues (placement, not recognition). `timings --from-notes` sizes each slide by its notes' word count at `--wpm` plus `--pause`, and writes every state: correct the numbers against the real narration. TTS route: synthesise each slide's notes to a file, concatenate with silence, and write the start of each slide into the file.

Measured on the demo deck (40 states, timings from `--from-notes` at 150 wpm: 102.7 s; a 110 s 220 Hz sine as the voice; 1080p, 30 fps, 4 workers, PNG frames):

- `ffprobe`: video H.264, 3081 frames, 102.700 s; audio AAC, 48 kHz, 2 channels, 102.700 s; container 102.700 s. The 110 s voice was trimmed to the video. A 45 s cut of the same file (`--to 45`): 1350 frames, video 45.000 s, audio 45.000 s.
- Step boundaries land on the timing. Independent check: the video frame at a state's start plus `t` was compared with `still S.T@t` (rendered from the deck's own animation clock) and with the video frames one to three before and after it, at 21 points spread over the whole film (up to 97 s, so no drift). The 14 transitions checked (into slides 2 to 15, in the first render also 2.0@0.3 and 2.0@0.7) matched at offset 0 with sharp minima: mean pixel difference 0.4 to 1.2 levels at offset 0, 1.9 to 33 levels one to three frames off. The steps checked (2.1, 5.1, 6.1, 8.1, 13.1, 3.1) are slow builds whose neighbouring frames differ by less than one level: five best at offset 0, one (3.1) tied with -1, so they are resolved to about one frame. The first frame that visibly changes after a start is 0 to 2 frames later for immediate steps and 2 frames later for transitions (the easing starts slowly); a build with its own `data-delay` shows later, as in the deck itself.
- 152.9 s wall time for the full film with `--loudnorm` (about 27 fps rendered); loudness measured on the result: -13.9 LUFS integrated (target -14) for the sine; use your real voice to judge the limiter.

### Analyse a reference: `analyze`

Before designing in the style of a deck you liked, take it apart:

```bash
node deck.mjs analyze reference.pdf                    # or a folder / list of images, or a deck.html
node deck.mjs analyze ../examples/demo/deck.html --out demo-analysis
```

Writes `report.md`, `analysis.json` and `contact-sheet.png` (every slide numbered, with its words, accent share and a palette strip; the deck's role colours on top). The report has the palette per deck with role guesses (background, ink, accent, second accent, muted, rule) clustered in OKLab, the accent's share of every slide, words per slide and text sizes on a 1080 px canvas (PDF text layer or DOM; images have none and the report says so), where the title sits on each slide and how many keep it at the same place, an estimate of density, and a list of what to write down (palette and roles, type, grid, density, rhythm, repeating devices, what not to copy). Borrow the structure, not the look: the report is for writing a style grammar, and the sheet is for reading it against.

PDF pages are rasterised by pdf.js (`pdfjs-dist`) inside the Chrome the exporter already drives, so there is no native dependency; Measured on the demo deck (15 slides, a machine busy with other work, so read them as orders of magnitude): the HTML in 7 to 14 s wall, its PDF (made with `node deck.mjs pdf`) in 5 to 12 s, the 15 last-step PNGs in 2 to 6 s; most of it is starting Chrome and, for the HTML, loading the deck. All three find the same palette (background `#f0ece4`, ink `#1c1b18`, muted `#868176` for `#857f72`, green and red accents, rule `#d5cab8`), the same accent share (median 0.1%, at most 8.7% on the "$3,900" slide) and the same words per slide (median 40; the busiest slide has 79 words in the DOM and 80 in the PDF text layer, after joining the per-glyph items of letter-spaced kickers: without that join the PDF read 105). The title stays in place on 9 of 15 slides (HTML), 10 (PDF) and 12 (images, a pixel estimate of the first band of ink); the exceptions are the title, big-number and closing slides. Roles are guesses by area and contrast: here it calls the green the accent and the red the second accent, because green covers more area, while the deck means red. Read the sheet before believing them.

### Fallback fonts: `fonts`

The brief (rules 25 and 28) says a deck must survive blocked Google Fonts. `check --no-webfonts` tells you whether it does; `fonts` makes it more likely.

```bash
node deck.mjs fonts deck.html            # print the CSS and what would change
node deck.mjs fonts deck.html --write    # insert it into the deck; idempotent
```

For every requested family, `@capsizecss/metrics` gives the font's average glyph width and vertical metrics, and a `@font-face` called `<Family> Fallback` on a local system font (Arial, Times New Roman or Courier New by category) is computed with `size-adjust`, `ascent-override`, `descent-override` and `line-gap-override`, so the fallback takes the same space. `--write` puts the block in `<style id="dk-font-fallbacks">` and adds the fallback name right after the family in every font stack it finds (CSS, custom properties, SVG and canvas font strings). `bundle` does it automatically. A family that capsize does not know is listed and skipped; the metrics are those of the regular weight, so a heavy display face stays an approximation.

Measured on the demo deck with Google Fonts blocked, over all 666 text boxes of the 40 rest frames, against the same deck with the fonts loaded:

| | mean width error | worst width error | boxes more than 2 px off |
|---|---|---|---|
| fonts blocked, no fallback block | 8.2% (20.9 px) | 569 px | 576 |
| fonts blocked, with `fonts --write` | 1.8% (9.1 px) | 213 px | 110 |

`check --no-webfonts` finds nothing on the demo either way (0 containment findings, worst overflow 0 px; the demo already leaves the slack the brief asks for), so the fallback block does not change that result there; it shrinks the layout shift (a title that wraps to a different line, a label that moves) that the check cannot see. Decks with tight boxes are where the two checks part ways: run `check --no-webfonts` before and after.

### Rendering fast: `--workers`, `--draft`, `--profile`

`gif`, `mp4`, `check`, `png`, `sheet`, `strip` and `still` capture with CDP `Page.captureScreenshot` and run on a pool of browsers, one worker thread with its own Chrome each. The timeline is cut into chunks whose size depends only on the frame range, so any `--workers` gives the same chunks and the same frames in the same order; MP4 chunks are encoded separately and joined without re-encoding, GIF chunks are joined by concatenation (each starts with a full frame). `__draw(T)` must be a pure function of `T`; renders of the same `T` differ by at most 2 levels in a few dozen pixels (GPU rounding), which is why the debug flag compares signatures, not hashes.

```bash
node deck.mjs mp4 deck.html film.mp4 --workers 4       # default min(4, cpus/4)
node deck.mjs mp4 deck.html preview.mp4 --draft        # half size, 15 fps, JPEG frames, x264 veryfast crf 26
node deck.mjs gif deck.html teaser.gif --draft         # half width, 8 fps, JPEG frames, 63 colours
node deck.mjs mp4 deck.html part.mp4 --from 30 --to 40 --profile
node deck.mjs mp4 deck.html a.mp4 --to 4 --workers 1 --signatures a.txt   # debug: prove the order
node deck.mjs mp4 deck.html b.mp4 --to 4 --workers 4 --signatures b.txt
node deck.mjs sigdiff a.txt b.txt
```

`--profile` prints the ten slowest frames by timecode (with the slide and step) and the mean cost of a frame for each second of the timeline, split into the draw call, the capture and, for GIF, the encode. The capture is where heavy filters show up.

Measured on the demo deck (seconds 0 to 10 of the timeline, 1080p, 20 logical CPUs, headless Chrome, best of three runs on a machine that was 60 to 90% busy with other work, so read the ratios, not the seconds):

| Command | before (one process, `page.screenshot`) | 1 worker | 4 workers (default) | `--draft`, 4 workers | `--draft`, 1 worker |
|---|---|---|---|---|---|
| `mp4` (300 frames) | 56.7 s | 40.5 s | 15.8 s | 5.4 s | 7.0 s |
| `gif` (120 frames) | 15.1 s | 10.7 s | 6.4 s | 4.4 s | 4.5 s |

`--draft` is 6.1x faster than the default for MP4 with one worker and 2.9x with four (10x faster than the old default); for GIF 2.4x and 1.5x (3.4x faster than the old default). What stops it at four workers is the fixed cost of starting four browsers and loading the deck in each (about 3 s), which a 10 second range cannot hide; on a whole film the ratio grows. Other commands, same setup: `png` (40 frames) 7.9 s to 4.6 s, `sheet` 6.6 s to 5.4 s. `check` is not faster on a deck this small: 1.6 s to 2.5 s for rest frames (the contrast pass), 3.4 s to 4.7 s with `--timeline` (four browsers start for about 40 frames of work); the pool pays off on decks of dozens of slides.

Working loop: iterate on a 5 to 10 second range with `--draft`, look at `still` frames and the sheet, render the whole film at full quality once. Numbers and caveats in 13-performance.md.

### Performance

```bash
node deck.mjs perf deck.html
```

Frame cost per step and per transition, DOM size and live filters; budget 8 ms. See 13-performance.md.

### 2. `sheet`: the contact sheet

```bash
node deck.mjs sheet deck.html sheet.png --cols 5
```

Every rest frame on one image, labelled `slide.step · id`. This is the main review tool. Look at it after every version and describe what you see before changing anything:

- Read the titles in order: is it an argument?
- Is there one focal point per frame?
- Do kicker, title and footer sit in the same place on every slide?
- Is the accent used for one meaning only?
- Do step 0 frames make sense on their own (they are what the audience sees while the speaker starts talking)?

### 3. `strip`: one transition, frame by frame

```bash
node deck.mjs strip deck.html strip.png --slide 6 --frames 8
```

Look for frames where both slides are unreadable at once, text crossing text, the background moving while slides do not, and a jump between the last transition frame and the rest frame.

### 4. Live pass

Open the deck, press through it once with presenter view open, and time it.

## Checklist

**Story**
- [ ] Titles alone tell the argument
- [ ] Every chart title states its answer
- [ ] The deck ends on the decision or the ask
- [ ] Invented numbers are labelled as illustrative

**Slides**
- [ ] `check` passes with no errors (contrast included: no `low-contrast`, every `contrast-unknown` looked at)
- [ ] Under 40 words per step; the rest in notes
- [ ] One focal point per step
- [ ] The accent has one meaning
- [ ] Every final step reads without motion

**Motion**
- [ ] Two or three transition types, each with a meaning
- [ ] No linear motion except constant processes
- [ ] Groups staggered; nothing important animates at the same time as something else important
- [ ] Nothing that matters takes longer than two seconds

**Containment**
- [ ] `check --timeline` and `check --no-webfonts` pass; `fonts --write` (or `bundle`) added the fallback block
- [ ] Boxes with text have no fixed height
- [ ] Changing numbers fit at their widest value

**Technical**
- [ ] No `Math.random()`, no CSS transitions or keyframes on content
- [ ] `perf` under 8 ms; `?perf` shows idle on still slides
- [ ] Every slide has a title for the control bar and overview
- [ ] Opens offline after `bundle`
- [ ] PDF pages match the sheet's final steps
- [ ] Presenter view shows notes for every slide

## Common first-draft problems

- Topic titles ("Market", "Team") instead of claims.
- Every slide in a different layout; the title jumps around.
- A different transition on every slide.
- Charts with four colours and a legend instead of one highlighted series and a label on the mark.
- The point only visible mid-animation; the PDF page is ambiguous.
- Labels overlapping lines or bars (the demo had two until `check` caught them).
- SVG `fill`/`font-size` attributes silently overridden by the stylesheet (01-runtime.md, Gotchas).
- A background that slides under a static slide during a transition.
- A box with a fixed height that holds only as long as the webfont loads.
- A counter or read-out sized for its final value, not its widest one.
