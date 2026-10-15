# Review — the loop that turns a draft into a film

You cannot watch or listen. You can look at frames, measure audio, and ask a model to watch with a proof
question. Do all three, every pass, and fix what they find before anyone else sees it.

## The loop (at least two full passes)
1. **Stills per section while building**: hero frames + both transitions + 3–5 moments in between
   (`node tools/render.js --stills ... --dir renders/stills/sNN`, tile with `tools/sheet.py`). Read each still
   at full size for the one or two that matter (text crispness, alignment).
2. **Preview**: `npm run preview` (half-res, no blur). Mux with the current mix:
   `ffmpeg -i renders/preview.mkv -i audio/out/mix.wav -map 0:v -map 1:a -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac -shortest renders/preview.mp4`
   (the project's ffmpeg is `node_modules/ffmpeg-static/ffmpeg`).
3. **Contact sheet, one frame per second**: `python tools/sheet.py --video renders/preview.mkv --every 1 renders/sheet.png`
   — read it like a stranger: does every second say something? any empty, cluttered or repeated frames?
4. **Strips through every transition** (0.2 s steps): `python tools/strip.py renders/preview.mkv renders/strip 4.2:5.8 …`
   — motion problems hide between seconds: overlaps, ghosted cross-fades, a window passing through a title,
   a blank card mid-morph, content popping instead of growing.
5. **AI watcher with proof**: `python review/watch.py renders/preview.mp4 "What company name is typed?"`.
6. **AI listener on the mix alone**: `python review/listen.py audio/out/mix.wav`.
7. **Objective numbers**: frames and duration (`tools/assemble.py` prints them), LUFS / true peak / clicks
   (`audio/analyze.py`), stem balance in 3 s windows, frame-to-frame difference across any splice.
8. **Score the rubric**, write the fix list into `docs/PLAN.md`, fix, re-render the affected range, re-check.

## Rubric (score each section 1–5; ship only when every section is ≥ 4)
| | 5 means |
|---|---|
| Clarity | a first-time viewer knows what happened and why, without the voice |
| Composition | one focal point, clean bands, nothing clipped or crowded, works paused |
| Motion craft | purposeful, one hero motion per beat, right curves, blur where fast, no pops |
| Fidelity | real UI/copy/flow, tokens exact, nothing invented or implied |
| Sync | events land on beats/words (±60 ms), transitions on bar lines |
| Sound | bed audible and fitting, every effect caused and quiet, voice clear, −14 LUFS |
| Legibility | key text ≥ 24 px on screen, contrast ≥ 4.5:1, holds long enough to read |

## Picture checklist
Text clipped? text under captions/tracker? stray elements from other scenes? a window edge in a close-up?
ghosting in a cross-fade? a scene ending before the wipe that covers it? a cursor covering what is typed?
z-order flips? an element posed from a previous frame (works in preview, fails in a worker)? fonts fallen
back? emoji rendered? numbers jittering in count-ups (use tabular figures)? last frame clean?

## The AI-critic protocol
- **Proof first.** Ask a question only someone who watched/listened can answer (typed text, a spoken
  sentence, the second a sound plays). Once, an uploaded file was never processed and the model invented a
  complete, confident review; another time it said "as an AI I cannot listen" halfway through. If the proof is
  wrong, discard the review.
- **Known blind spots**: video sampled at ~1 fps (slides become "hard cuts", growing rows "pop in"), quiet
  effects and beds under-heard in video mode (it claimed "no music" on a mix it praised in audio-only mode).
  Verify every motion note with strips and every sound note with `listen.py` and measurements.
- **Good uses**: sync disagreements ("the visual leads the VO at 0:19"), clarity for non-experts, clutter,
  readability, what a viewer would misunderstand, story gaps (an unused call-to-action in frame).
- Read its suggestions against the product's truth: "redesign the modal for the video" is wrong if the modal
  is the real product — dim, spotlight and zoom instead.

## Objective checks before delivery
`tools/assemble.py` must print the expected frame count (duration × fps) and duration; loudness −14 ± 0.5 LUFS;
true peak ≤ −1.0 dBTP; zero clicks in `analyze.py`; captions file present for narrated films; cover frame clean.
