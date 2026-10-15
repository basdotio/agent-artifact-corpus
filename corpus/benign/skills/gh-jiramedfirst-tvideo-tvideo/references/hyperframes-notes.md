# Hyperframes notes (what build.mjs already respects)

You rarely need to touch the generated HTML. If you extend `build.mjs`, keep these
rules — each one is a real failure the template already avoids:

- **One paused GSAP timeline** registered as `window.__timelines['main']`; the
  root `data-duration` is the render length.
- **Never nest a timed `<video>` inside a timed element.** The footage stage
  (`#stage-wrap`) is untimed and shown/hidden with opacity tweens; only the
  `<video>`/`<img>` clips carry `data-start`/`data-duration`.
- **Same source, many windows**: each step is its own `<video>` with
  `data-media-start`; holds are PNG stills extracted by ffmpeg.
- **Every `<audio>` needs an `id` and a real `data-duration`.** Without the
  duration, lint treats each SFX as playing to the end and flags hundreds of
  overlaps (`duplicate_audio_track`).
- **Fonts need a local `@font-face`**; system fonts may not exist at render time.
- **Footage should be all-intra** (`import.mjs` encodes with `-g 1`) so the preview
  can seek between many short windows without stutter. Renders are frame-exact
  either way.
- Validate with `npx hyperframes check` (lint + runtime + layout + contrast).
  Snapshots: `npx hyperframes snapshot --at t1,t2 --no-end` → `snapshots/`.
- Renders: `--quality draft` for review, `--quality delivery` for the final file.
- Remaining warnings that are expected: `nested_structure_needs_subcomposition`
  (single-file composition by design), `timeline_track_too_dense`, and
  `container_overflow #zoom inside #stage` during a zoom (the stage clips the
  scaled footage on purpose).

For anything beyond this, load the `hyperframes-core` skill.
