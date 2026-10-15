# Troubleshooting — failures already seen, and their real cause

| Symptom | Real cause | Fix |
|---|---|---|
| Zoom/ring lands on a different page than the button | The page changed after the click but the control was still in the DOM 2 s later, so `holdFirst` wasn't inferred | `holdFirst: true` on that step |
| Captions / stills consistently a fraction of a second early or late (footage–timeline drift) | Recorder times count from the test body, the video from page creation; `import.mjs` corrects it with the sync flash | Check the import printed `sync offset … ms`. "sync flash not found" → the clip didn't start with `createTimeline` + `tl.step`, or the take was a rehearsal; re-record |
| Ring is a few px off the control | A layout shift between the cursor arriving and the still (late-loading content) | Add a `hold()` / `expect` for the content before the `tap`; or give `ring {x,y,w,h}` by hand |
| A hold still shows the next step's screen (dialog already open) | Next step's click landed exactly on the boundary | Build samples `end − 0.2 s`; if still wrong, add a `hold()` at the end of the previous step in the spec and re-record |
| Clip videos from an earlier run disappeared | Playwright wipes `outputDir` at run start; two configs sharing one `outputDir` wipe each other | Import/copy right after each take; give each config its own `outputDir` |
| "Day N is disabled" in the date picker | Real booking window vs hardcoded date | `relativeDay()` |
| Validation error on submit that tests never hit | Real environment config (breaks, capacity, cut-off, required fields) | Read the error on the failure screenshot; choose valid values dynamically |
| Preview stutters / audio choppy | Studio seeks across many windows of one long-GOP file | `import.mjs` makes footage all-intra; judge timing from a draft render |
| `duplicate_audio_track` × hundreds | `<audio>` without `data-duration` | Template sets it; keep it if you add sounds |
| `check` reports contrast < 3:1 on a caption badge at one timestamp | Sampled during the caption's 0.4 s fade-in | Expected; confirm a mid-step snapshot is readable |
| `stdout` JSON truncated at 64 KB in a node script | `process.exit()` before the pipe drained | `process.stdout.write(data, () => process.exit(0))` |
| TTS "free voice-generation time left" error | Quota exhausted | See narration.md → Quota; keep existing voice files |
| A narrated word is mispronounced | Script form of the term | Latin script for English terms; local spelling for local brand names; regenerate only that line |
| Dev-server badge ("N") in the corner of every frame | Next.js dev tools overlay | `createTimeline` hides it; re-record |
| "Saved session expired" before the clips run | The cookies in `.auth/state.json` timed out, so the app redirects to login | Delete `.auth/state.json` and log in again, or rerun `npx playwright codegen --save-storage=.auth/state.json <url>` |
| Tofu boxes / missing glyphs in captions | The bundled font (IBM Plex Sans Thai) only covers Thai and Latin; the render can't use system fonts | Add a local font for that script under `font.files` in `tvideo.config.json` (see editing.md → Fonts) |
| Login works locally but `auth.setup` times out on staging | Different form selectors / SSO / 2FA | Set `TV_*_SELECTOR`, or log in inside the clip with an OTP pause |
