# Craft rules

Sources: leo, "Make your product videos look expensive (Apple Framework)" (X, Sept 2026); 0xMovez, "How to build a
motion design studio with Opus 5.5" (X, Sept 2026); and a 62 s launch film built with this pipeline.

## Brand

- Three colors: background, accent, text. A lighter tint of the text color for secondary lines only.
- Two fonts: a clean sans for headlines, one expressive accent (an italic serif works) for the single magic phrase
  per headline. A wordmark font only for the logo.
- One background for every shot (gradient, sparse twinkling stars or a texture, fine grain). It never competes with
  the key object.
- Music with a chosen tempo: 60–80 BPM reads regal/cinematic, 90–110 smooth and effortless, 115–123 kinetic.

## Shots

- One shot, one idea. The key object sits in the center with room around it.
- Headlines sit in the same place every shot (top center works). Never put text on a subject's face; if the art is
  busy, frame it (a device, a card) and keep the headline on the background.
- Hook in the first 2 seconds, a visual payoff every 3–5 seconds, and the first frame must not be blank (autoplay
  thumbnails).
- Real product UI beats mock UI. Crop cards out of real captures and pop them out of the device. When a capture is
  stale, rebuild that component in HTML from the app's code (colors, radius, motion).
- Show range with a cascade: pop several options out around the device on sixteenth notes, pick one on the beat,
  dim the rest, dissolve them in place, fly the chosen one home.
- A trending device mockup can be the surprise (for example a foldable that unfolds into a book spread), but only
  where the product really supports that layout.

## Motion

- Closed-form springs only, so any frame renders alone. Presets: ui (tiny overshoot), default, heavy (no overshoot:
  big type, logos), playful (visible overshoot: stickers, pop-outs), camera (slow). A value with several targets
  gets one spring per change (`track()`).
- Type: per word, opacity + blur 14 → 0 px + rise 28 → 0 px on a heavy spring, 70 ms stagger. Exit: fade, blur 10 px,
  rise 20 px over ~0.45 s.
- No hard cuts. Hand an object or the camera to the next shot: text → particles → logo; photo → painted portrait
  → the same portrait in a UI tile; button → burst → the result; device folds shut before the next statement.
- Adaptive rhythm: slow open, faster middle (half-beat montages), slow emotional close.
- Motion blur on the final render (4 samples, 180° shutter) makes fast moves read as expensive.

## Sound

- Plan the score in timed sections (bars) that follow the edit, generate a few seeds, measure, pick, then move cuts
  onto the measured events. The track leads; the picture follows it.
- Voiceover: restrained. It says the headline in its own words, never over the product's own sounds (an in-app
  narrator reading, a sound effect that demonstrates a feature). Pick a voice that contrasts with any in-product
  voice (male ad voice over a female in-app narrator, or the reverse). Warm and calm beats "radio ad" energy for
  premium products.
- Place voice by measured word timings; anchor the word that matters to its beat.
- Sound effects only where they explain the product or mark a magic moment. Match every cue to a loudness target;
  duck the score under voices; normalize to −14 LUFS for social.

## Deliverables

Voiceover cut, alternate-voice cut, music-only cut, SRT captions, poster stills (the strongest product frame and
the end card), a contact sheet, and a README that lists sources, generated assets and open claims (for example a
platform that is not live yet).
