---
name: saas-demo-explainer
description: "SaaS and B2B product demos, onboarding walkthroughs, and explainers. Simulated screen recordings with human cursor physics, real-app logic, the readability law, and a mandatory asset-request protocol. Use for product demos, feature walkthroughs, onboarding, and software explainers."
---

# SaaS / B2B Demo & Explainer

> **THE LOOK IS CHOSEN, NOT MANDATED.** Pick it in the **Style Pass** — a motion
> style + a UI style (`MOTION-UI-STYLE-LIBRARY.md`) and a caption style
> (`CAPTION-STYLES.md`) — chosen for THIS job and recorded in CONCEPT.md. The
> **Apple Standard** (section 3) is the house default and a strong starting point
> for most product, UI and corporate work, but it is a **recommendation, not a
> rule**. If another style fits the brief better, recommend it with your reasoning
> and use it. **No style is deprecated.**


**Scope.** Product demos, feature walkthroughs, onboarding videos, software
explainers, docs-to-video. A demo is a SCREEN RECORDING, never abstract motion
graphics — the viewer must believe a person recorded their screen.

**Asset tier: 1–2.** Tier 1 = a public, login-free URL or screenshots (we
capture or faithfully recreate it). Tier 2 = behind a login → **the client must
supply** screen recordings or screenshots; we never log in. **Ask first.**

## STEP 0 — SOURCE GATE (mandatory, BEFORE the assets prompt)

**You cannot plan assets without the material.** Before writing
`ASSETS-PROMPT.md`, obtain at least ONE of:

1. **the video clip** — the footage to edit, or
2. **the voiceover / audio** — the narration track, or
3. **the transcript / script** — the words.

Ask for it up front. If the build is genuinely from-scratch graphics (no source
exists), say so and record it — the concept you write becomes the script.

**Then analyse the source and save the evidence** as `SOURCE-ANALYSIS.json`:

- **If a clip -> video analytics:** `ffprobe` (codec, size, fps, duration, audio
  channels); scene detection for cut times and ASL
  (`ffmpeg -i in.mp4 -filter:v "select='gt(scene,0.3)',showinfo" -f null -`);
  loudness (integrated LUFS + true peak); palette sample (quantise frames ->
  hex); beat/BPM if there is music.
- **If audio -> word-level transcription:** faster-whisper with
  `word_timestamps=True` -> a JSON of `{word, start, end}` per word, plus
  segments. This drives the Visual Narration Plan, the captions and the word
  sync. Recipe: decode to 16 kHz mono WAV with ffmpeg, pass a numpy array, run
  with `MKL_THREADING_LAYER=GNU OMP_NUM_THREADS=1` and `cpu_threads=1`, model
  `tiny` (base/small for accuracy).
- **If text only ->** the sentence list, mapped to the Sentence Law table.

**Only once the source is in hand and analysed** do you write
`ASSETS-PROMPT.md` — so every prompt reflects what the build actually needs.

## REFERENCE-LEARNED PATTERNS (from captured presets)

Real-world patterns measured from reference edits in this vertical. Apply
them; the matching preset locks the exact look (see `presets/INDEX.md`).

**From `presets/product/preset-003-saaswave-tactile-purple`** (a tactile 3D
product reel):
- **Tactile 3D objects** in a colour wash; **floating UI cards**; a **cursor that
  operates the UI**; **3D buttons** with glow feedback; a **morph-to-logo**.

**From `presets/product/preset-005-higgsfield-dark-ui`** (a dark-mode product demo):
- **Dark-mode UI floating in a void**; **2D -> 3D spatial** UI transforms;
  **cursor micro-interactions** (click / toggle / drag); a **neon accent** + a
  **monospace command line**; a **light-mode end card**.

## STEP 0.5 — A-ROLL PREP (matting first — mandatory when a person speaks)

If this piece has a **person speaking to camera** (talking-head, voiceover,
avatar, podcast), the **first job is the background**, before the concept.
Decide the path in `a-roll-matting`: **keep it / matte it / key it** — and by
default get the character **off the background** (or onto green). Matte FIRST
unlocks text-behind-subject, screen replacement, graphic backgrounds and floating
UI. Use `tools/matte.py` for the local matte (rembg + ffmpeg). Record the matte
as an asset in the manifest and check it at the QA gate (no holes, no baked-
caption artifacts, stable alpha). If the background is the message, keep it.

## STEP 1 — CONCEPT.md (write the plan before any prompt)

With the source analysed, write **CONCEPT.md** — the single plan the whole build
follows. **Everything is connected: every line here drives a later stage, and
every later stage writes its result back here.** Follow `THINKING-SYSTEM.md` — the
planning stack, the four lenses (EZRA), and (when you have only a script) the
only-a-script path.

- **Premise** — the video in one sentence + its emotional arc.
- **THINKING PASS (mandatory).** Work the stack **top-down** — goal -> audience ->
  angle -> concept -> script -> beats -> shots — and record:
  - the target **emotion** per section (EZRA: Emotion, Story, Rhythm, Action);
  - the **beat map** with the **two-column (said | shown)** filled for every row;
  - the **visual plan** table: beat -> viewer question -> visual evidence ->
    risk to review -> final asset;
  - the **retention check** — where the video is most likely to lose people, and
    the fix.
- **Style** — the named build style (this skill) and how it applies here.
- **STYLE PASS (mandatory).** Pick deliberately and record: the **motion style**
  and the **UI style** from `MOTION-UI-STYLE-LIBRARY.md`, and the **caption
  style** from `CAPTION-STYLES.md`. One primary + at most one garnish; name the
  chosen style's failure mode.
- **Segment plan** — the beat map with timings, taken from the analysis.
- **Sentence table** — one row per narration sentence: sentence -> visual concept
  -> lane (A speaker / B visual) -> the **stressed word** to land on -> timing ->
  element bindings -> **camera** (reason + target + zoom). (The Sentence Law.)
- **Camera-track plan** — the ordered camera entries
  (READ / EMPHASIZE / REVEAL / FOLLOW / BREATHE) with their word bindings.
  (The Camera Law.)
- **FEATURE MAP — the Feature Pass (mandatory).** Walk the **full catalogue** in
  `ADVANCED-FEATURE-USE-CASES.md` — camera & framing, motion & animation, speed &
  time, transitions, text, colour, compositing & VFX, audio, AI, stills & design,
  workflow — and record for **every** feature whether it applies and how:
  `feature -> applies? -> where (scene/timecode/sentence) -> how (implementation)
  -> why (the job it does)`. **Every group is visited; no group is skipped.** The
  concept is not finished until every applicable advanced feature has a row (a
  "yes" with no *how* is not a plan; every "no" is a deliberate choice).
- **Contact-sheet plan** — which sign-off variants will be built (V1 Classic Grid
  / V2 Storyboard Filmstrip / V3 Pro QC Sheet) and why. **The variant the user
  picks is written back here.**
- **Sync map** — the word-level timings that drive text and visuals.
- **Asset manifest** — what the build needs (fed by the feature map); this feeds
  STEP 2.

Then STEP 2 writes `ASSETS-PROMPT.md` from this plan.

### PIPELINE CONNECTIVITY LAW (mandatory)
Everything is connected — no stage is decided in isolation, and no stage is
skipped:

- **SOURCE** -> analysed into `SOURCE-ANALYSIS.json`, which feeds the concept.
- **CONCEPT** -> drives the thinking pass, the style pass, the asset manifest, the
  camera track, the sentence table and the feature map; it is the single source of
  truth for the build.
- **ASSETS-PROMPT** -> written from the concept's manifest; nothing unplanned
  appears in the build.
- **BUILD** -> follows the concept's sentence table, camera track and feature map
  exactly.
- **RENDER GATE** -> the contact-sheet variants visualise the concept's beat map;
  the variant the user picks is written **back into CONCEPT.md**.
- **QA GATE** -> `edit-qa-validator` / `tools/qa_check.py` re-check that every
  feature the map marked "yes" actually made it into the edit.
- **SIGN-OFF -> RENDER** -> the full render happens only after the variant AND
  the cut are finalised.
- **A new contact sheet means a new CONCEPT revision.** If the sheet reveals a
  change, the concept is updated FIRST, then the build follows. The record stays
  connected end to end: source -> concept -> assets -> build -> sheet -> sign-off
  -> render.

## ASSETS-PROMPT.md — MANDATORY (strict rule)

After the concept, produce ONE file — **`ASSETS-PROMPT.md`** — listing every
asset the build needs, **one executable brief per item**, addressed to **an AI
agent that has image generation, audio generation AND coding**. No prompt list,
no build.

1. **Images** — image briefs: subject · composition · style · palette (hex) ·
   lighting · aspect + background · negatives.
2. **Transparent images (PNG/alpha)** — briefs ending "transparent background,
   PNG with alpha, no background".
3. **Logos** — a brief, or "client supplies".
4. **Music** — audio briefs: mood · genre · BPM · length · instrumentation.
5. **Sound effects** — audio briefs: type · character · duration.
6. **Code components** — CODING briefs for what code does best (glass cards,
   animated type, diagrams, count-ups, UI mockups, particles, shaders, 3D):
   exact values (hex, px, easing, durations), the motion, and the
   **nested-zip deliverable**: ONE master zip containing a zip per category and
   a zip per component kit (each kit unzips to `index.html`, `styles.css`,
   `README.md`, `assets/`, palette exposed as CSS variables).

**This file IS the prompt** — write it as a self-contained instruction you
hand straight to the agent, ending with the deliverable tree (one zip) and
acceptance checks. A full worked example: `EXAMPLE-ASSETS-PROMPT.md`.

**EXCLUDED — never in this file:** **voiceover** and **ALL video clips**
(A-roll and B-roll). The user supplies the A-roll — voice, primary footage, or a
transcription JSON — at the start. If the build needs any **B-roll clip**, ask
the user for it **separately**; clips are never listed in this prompt file.
(The agent can only generate images, audio and code — it cannot generate video.)

Full format, the kit shape, and a worked example: `ASSET-REQUEST-GUIDE.md`.

## 1. Intake — ask before you build
1. What does the product do, for whom, and what is the single most impressive
   workflow to show?
2. Is there a public login-free page I can study, or screenshots you can send?
   (If it is behind a login, I need your recording — I never log in.)
3. Demo (60–120s), onboarding (2–5 min), or explainer (60–90s)?
4. Brand kit, logo, colours, fonts? Any reference video?

Then emit **ASSET-REQUEST.md**:
```
# ASSET REQUEST — <product>
## Screen recordings (need N)
1. <workflow: e.g. "create project → invite teammate → export"> — 1080p+, no cursor lag
## Screenshots (clean, no personal data)
## Logo / brand kit / product name + exact labels
## Music & SFX — prompts in ASSETS-PROMPT.md (voiceover supplied separately)
```
Never log in, never accept credentials. Recreate the UI from research instead,
and disclose "UI recreation" in the description.

## 2. Research before recreate (2–5 min, time-boxed)
Never simulate a tool from memory. Study its real screens, colours, fonts,
exact labels, and workflow order. Use real product names and logos.

## 3. The demo engine
- **Cursor physics:** travel on a quadratic bezier on a **minimum-jerk profile**
  `s(t)=10t³−15t⁴+6t⁵` — never linear. Timing = Fitts's law
  `MT=0.07+0.15·log₂(D/W+1)`, clamp 0.08–2.5s. Overshoot 3–12% on long moves.
  Tremor ±1–2px while dwelling. Click anatomy: 50–200ms pre-click pause → press
  dip ~0.92 (2–3 frames) → hold 50–150ms → UI responds 100–150ms later. Typing
  60–120ms/char, one typo→backspace per 30–40 chars.
- **Real-app logic:** build the app as a state machine — screens → elements →
  states → valid transitions. A value shown twice never disagrees. Modals
  swallow clicks behind a scrim.
- **Containment:** every scroll region clips (`overflow:hidden`); content never
  crosses its border or the frame. Scroll offset clamped to
  `[0, contentHeight−viewportHeight]`.
- **No phantom clicks:** every click comes from a timeline entry; the renderer
  invents nothing.
- **The Readability Law:** text the viewer must read renders ≥4% of frame
  height (≥44px at 1080p). Zoom = `min(5, max(1.25, 0.04·frameH ÷ h))`. Hold
  ≥ chars÷13 s. Typical UI labels need 3–4× zoom.

## 4. The camera
One camera wrapper; every move has a reason (READ · EMPHASIZE · REVEAL ·
FOLLOW · BREATHE). Click-zoom 2× default, hold ≥1.2s. Return to rest before
cuts. Motion tracing runs GENTLE (drift ≤2–3%, one zoom event per 3–4s).

## 5. The edit — the explainer structure
hook (the pain or the outcome, 0–3s) → context (who this is for) → the demo in
3–5 steps (one workflow per step, one idea per shot) → the payoff (the result,
visibly) → CTA. In hybrid builds, cut to full-screen explain moments for
concepts — never burn subtitles.

## 6. Audio
Procedural UI ticks/clicks, soft whooshes, a calm pad. Music 90–115 BPM, well
under the voice. If narrated, the client's voice — we cannot generate voice.

## 7. Delivery
16:9 1080p/4K; 9:16 for social cuts. Chapters for long demos. −14 LUFS
(YouTube) / −16 (social).

## The look — THE APPLE STANDARD (mandatory; the only look)

**The house default.** The Apple Standard below is the pack's default look and
the right starting point for most product, UI and corporate work — verified
tokens, one accent, restrained motion. It is a **recommendation, not a mandate**:
choose the look in the **Style Pass** (`MOTION-UI-STYLE-LIBRARY.md`). If a
different style fits this brief better, recommend it with your reasoning and use
it. **No style is deprecated.**

- **Canvas:** alternating `#ffffff` / `#f5f5f7` bands — the colour change IS the
  divider (no borders, no rules). Dark variant `#0d0d0f` with glow
  `rgba(10,132,255,.25)`.
- **Text:** `#1d1d1f` primary · `#6e6e73` secondary · `#86868b` tertiary ·
  hairlines `#d2d2d7` on light, `#333` on dark.
- **The one blue — interactive only, never decoration:** filled action
  `#0071e3` · text links `#0066cc` on light · `#2997ff` on dark. Hover wash
  `#e8e8ed`. Icon gradient `#41A6FF -> #0A64E8` at 180°.
- **Type (Inter stands in for SF Pro):** hero 80px/600/-1.2px · display
  56px/600/-0.28px · section 40px/600 · **body 17px/400/25px/-0.374px** ·
  small 14px/-0.224px · caption 12px. **Negative tracking at EVERY size.** One
  accent word per headline, never whole lines.
- **Buttons:** pill radius **980px**, filled `#0071e3`, white text, 44px tall,
  11px 21px padding (compact 36px/14px); outline twin 1px `#0066cc`. **One CTA
  per scene, maximum.**
- **Shadow:** one light source. Cards `0 24px 60px rgba(0,0,0,.08)` + hairline
  `rgba(0,0,0,.055)`; icons `0 30px 70px rgba(10,100,232,.35)` + inner highlight
  `inset 0 2px 6px rgba(255,255,255,.45)`. Shadow on the focal element only.
- **Radii:** cards 28-32px · icons ~26% of size · pills 980px · inner UI
  12-16px · never below 10px. Spacing on the 8px grid; card padding 34-40px.
- **Frosted bar** (nav / chapter strip): `rgba(250,250,252,.8)` + backdrop blur,
  44px tall, 1px hairline `#d2d2d7` beneath.
- **Motion:** springs with 5-8% overshoot; every entrance = fade + rise +
  scale-settle (0.5->1) + deblur 12-18px->0; stagger 0.05-0.16s; exits scale to
  ~1.05 with blur 8; camera push-ins <=8% over 3-5s. **Never linear.**
- **Layout:** symmetric, centred, one focal point, >=30% whitespace, <=6
  elements per scene.

**Vertical application for this skill:** the recreated UI IS the picture; the Standard provides the chrome, the cards and the type, and the accent marks the one control being taught.


## Visual narration layer — full spec (mandatory wherever a person speaks)
The market-dominant format: the speaker carries the voice, the **visuals carry the
meaning**. Whoever is speaking — on camera, walking, or voiceover — the video
must SHOW what is being said.

### Three placements (choose per beat, alternate them)
1. **Full-screen cutaway** — visual takes the frame (icon, diagram, stat count-up,
   keyword card, B-roll). Voice continues (L-cut in, J-cut out). Best for concepts,
   numbers, lists, comparisons.
2. **Front overlay** — motion graphics over the speaker; face stays visible
   (labels, keyword pops, callouts, arrows, lower-thirds). Best for emphasis,
   naming, quick facts.
3. **Behind / around the subject** — speaker keyed/cut-out over graphic background
   or blurred plate, elements animating behind and beside. Best for intros, hero
   segments, brand pieces. Needs a clean cut-out or a clean plate (Tier 1–2 asset).

### Rules
- Every spoken concept gets a visual landing on the exact word (±100 ms).
- One visual event every 6–10 s; no talking frame static > ~8 s.
- Alternate placements; avoid 3 of the same in a row.
- **Captions are additive, never the layer** — remove them and the ideas must still show.
- One idea per visual. Motion: fade + rise + settle, eased, never linear (180–450 ms in, 250–350 ms out).
- Never hide the speaker's face when the face is the message.
- Zero-speech pieces: apply the same layer to on-screen kinetic text.

### The Visual Narration Plan (write BEFORE cutting)
A table with one row per spoken idea:
| Timecode | Spoken phrase (exact word to land on) | Concept | Placement 1/2/3 | Visual | Duration | Sound |
Rules for the plan: ≥ 1 row per 6–10 s; no more than two consecutive rows with the
same placement; every number gets a stat visual; every named thing gets a label
or cutaway; every list gets a build-in with one item per spoken item.

### Beat micro-timings
- Keyword pop lands 0–80 ms **before** the audible word onset (the eye leads the ear).
- Count-ups run 0.6–1.0 s and finish on the spoken number.
- Lower-third: in at first speech, on screen 4–5 s, out ≥ 0.3 s before the next cut.
- Cutaway length = the length of the spoken idea (usually 2–5 s); return to speaker on the sentence boundary.

## Industry benchmarks (working conventions)
- Product demo 60–120 s; onboarding clip 30–60 s; changelog 20–45 s. Lead with the outcome in the first 5 s, not the login screen.
- Cursor moves 0.4–0.8 s eased point-to-point, click ripple 150 ms, 1.2–1.5× zoom to the active UI region; one action per beat.
- Readability law: on-screen UI text must be ≥ ~18 px effective at final size — zoom or crop instead of shrinking.
- Blur or replace any real customer data/emails/keys in captures (privacy).

## Worked example
**Example — 75 s demo ("Invoice automation")**
| t | Beat | Visual |
|---|---|---|
| 0–5 | Outcome hook | "Invoices sent in 1 click" stat card → cut to dashboard |
| 5–20 | Problem | split-screen: spreadsheet chaos vs clean list |
| 20–50 | Walkthrough (3 steps) | zoom to each UI region, cursor path eased, step badges 1-2-3 |
| 50–65 | Result | invoice status flips to Paid, count-up "−6 hrs/week" (client figure) |
| 65–75 | CTA | one button, URL pill |

## Common mistakes to avoid
- Recording full-screen at 4K then showing it small and illegible.
- Dead cursor time / hunting for buttons; cut it, don't show it.
- Showing features in menu order instead of user-goal order.

## Signature techniques for this style (use these, with the recipes below)
- **Simulated screen recording** — build the UI in HTML/CSS and animate it (HyperFrames/Remotion) so text stays crisp at 4K; real captures only where authenticity is required (blur private data).
- **Cursor physics** — eased path 0.4–0.8 s point-to-point, slight overshoot, click ripple 150 ms, then a 1.2–1.5× punch-in on the active region (recipe 1).
- **Zoom-to-region** — crop-and-scale to the UI area being discussed; never shrink UI text below ~18 px effective.
- **Step badges + split-screen before/after** (recipe 10) for 'problem vs solution'.
- **Highlight rings / dim-the-rest** — darken everything except the active element with a masked overlay.
- **Click and typing SFX** — soft tick per click, keyboard texture while typing; silence on reading pauses.

## Modern editing toolkit (techniques editors use today + how to do them from the terminal)

### A. The technique catalogue — what top editors actually reach for
**Cutting & structure** — jump cut · J-cut / L-cut · match cut (shape, motion, colour) · smash cut · cutaway/insert · split edit · cut-on-beat montage · invisible cut hidden by a whip, zoom or object wipe · freeze frame · reverse · seamless loop · transcript-based rough cut · silence/filler removal · multicam switching.
**Motion & camera** — eased punch-in/push-in · slow digital push · pan/tilt on stills (Ken Burns) · 2.5D parallax from separated layers · camera shake on impacts · speed ramp / time remap · optical-flow slow-motion · stabilisation · whip pan · simulated dolly-zoom · motion blur on fast moves.
**Transitions** — hard cut is the default; then push/slide, whip, zoom-through, shape/mask reveal, luma wipe, light-leak/flash, glitch/RGB split, crossfade. Every transition has a matching sound. Never repeat the same transition twice in a row.
**Text & captions** — kinetic typography · word-by-word karaoke captions · one-accent-word highlight · animated lower-thirds · text tracked to a moving object · **text behind the subject** (matte) · typewriter/mask reveals · drawn-on callouts and arrows · count-up numbers.
**Compositing & depth** — subject cut-out/matting · background blur/replace · split-screen · picture-in-picture · chroma/luma key · screen replacement (UI on a device) · shadow + reflection under cut-outs · glow/bloom · overlays (grain, dust, light leaks) · blend modes (screen, add, multiply).
**Colour & look** — correct first (exposure, white balance), then log→Rec.709, LUT, contrast curve, secondary tweaks (skin, sky), split-tone/film emulation, halation/bloom, grain, vignette, letterbox (2.39:1), shot matching. Protect skin tones.
**Audio design** — dialogue chain (high-pass → denoise → de-ess → compress → loudnorm) · side-chain ducking · SFX layer (whoosh, impact, riser, tick, sub-drop) · ambience/room tone · music edited to phrases · a 0.2–0.4 s silence before the drop · stem separation for cleanup.
**Graphics & data** — animated charts with a single highlight colour · count-ups · map/route draws · diagrams that draw on the narration · UI demo with eased cursor + click ripple · stat "bento" grids · progress bars · timeline graphics.
**AI-assisted (2026)** — word-level transcription · filler/silence removal · scene detection · auto-chapters · face-tracked auto-reframe · matting/rotoscope · upscaling · frame interpolation · stem separation · beat detection · generative B-roll/imagery (disclose when real footage is implied).

### B. Terminal toolchain (pick the lightest tool that does the job)
| Tool | Use it for | Notes |
|---|---|---|
| **FFmpeg / ffprobe** | cuts, concat, scale/crop, zoom, xfade transitions, speed ramps, LUT/grade, grain/glow, overlays, captions (ASS), audio chain, loudness, export | The backbone. Chain edits in ONE `filter_complex` pass to avoid generation loss. |
| **auto-editor** | rough cut by removing silence/dead air via loudness/motion analysis | Signal analysis, not generative. |
| **faster-whisper / WhisperX** | transcription with word-level timestamps (captions, beat plans, filler cuts) | Needed for ±100 ms word sync. |
| **PySceneDetect / ffmpeg `select='gt(scene,0.3)'`** | find shot boundaries in source footage | |
| **librosa** (Python) | BPM + beat timestamps for cut-on-beat | |
| **HyperFrames (HeyGen, Apache-2.0)** | motion graphics as HTML/CSS/GSAP/Lottie/Three.js → deterministic MP4; CLI `init`, `preview`, `lint`, `render` | Agent-friendly: `npx hyperframes init my-video` → edit `index.html` → `npx hyperframes render`. |
| **Remotion** (React) | code-defined video compositions, data-driven templates | Check its licence terms for company/commercial use. |
| **MoviePy** (Python) | scripted clip assembly where FFmpeg graphs get unwieldy | Slower than raw FFmpeg. |
| **rembg / Robust Video Matting / SAM-family** | subject cut-out (alpha) for text-behind-subject and layered looks | Check each model's licence (some are non-commercial). Review edges/hair; rembg is per-frame (flicker risk), RVM is temporally consistent. |
| **MediaPipe** | face tracking for auto-reframe to 9:16 | |
| **Demucs** | separate vocals/music for cleanup | |
| **Blender (headless `blender -b -P script.py`)** | 3D titles, product/architecture renders, camera moves | Heavy; use only when 3D is the point. |
| **MLT/melt, GStreamer, OpenTimelineIO** | timeline-style assembly and interchange | Optional; not needed for most jobs. |
| **ImageMagick / Pillow** | stills, masks, cards, contact sheets | |
*Always check what is installed first and fall back to FFmpeg-only:* `for t in ffmpeg ffprobe python3 node npx auto-editor scenedetect melt blender; do command -v $t >/dev/null && echo "have $t" || echo "missing $t"; done`. If the network is off, do not plan on installing anything.

### C. Tested FFmpeg recipe cookbook (verified on FFmpeg 6.1.1; confirm a filter exists with `ffmpeg -filters | grep <name>`)
Set `IN=input.mp4`. All outputs add `-c:v libx264 -pix_fmt yuv420p` (+ audio as needed).
```bash
# 1 Smooth punch-in (6%/s growth, centred). Prefer this over zoompan on VIDEO — zoompan can jitter.
-vf "scale=w='trunc(1920*(1+0.06*t)/2)*2':h='trunc(1080*(1+0.06*t)/2)*2':eval=frame:flags=bicubic,crop=1920:1080"
# 2 Transition + matching audio crossfade (offset = clip1_duration − transition_duration; clips need same size/fps/pixfmt)
-filter_complex "[0:v][1:v]xfade=transition=smoothleft:duration=0.5:offset=3.5[v];[0:a][1:a]acrossfade=d=0.5[a]" -map "[v]" -map "[a]"
#   other xfade names: fade fadeblack fadewhite wipeleft slideleft circleopen circleclose radial pixelize hlslice vuslice dissolve smoothup distance
# 3 Speed ramp (normal → slow-mo → fast) with split + setpts + concat
-filter_complex "[0:v]split=3[a][b][c];[a]trim=0:1,setpts=PTS-STARTPTS[v1];[b]trim=1:2,setpts=(PTS-STARTPTS)*2[v2];[c]trim=2:4,setpts=(PTS-STARTPTS)*0.5[v3];[v1][v2][v3]concat=n=3:v=1:a=0[v]" -map "[v]"
# 4 Premium look: glow/bloom + film grain + vignette
-vf "split[a][b];[b]gblur=sigma=30,eq=brightness=-0.05[g];[a][g]blend=all_mode=screen:all_opacity=0.25,noise=alls=10:allf=t,vignette=PI/5"
# 5 Colour: contrast curve + split-tone + saturation (add lut3d=file.cube first if you have a LUT)
-vf "curves=preset=medium_contrast,colorbalance=rs=-0.05:bs=0.08:rh=0.08:bh=-0.06,eq=saturation=1.08"
# 6 Camera shake for impacts (apply with enable='between(t,a,b)' on a crop wrapper, or to a short segment)
-vf "scale=2016:1134,crop=1920:1080:x='48+12*sin(t*40)':y='27+8*cos(t*47)'"
# 7 Whip-style blur around a cut at t=2.0 + slight push
-vf "boxblur=luma_radius=40:luma_power=1:enable='between(t,1.8,2.0)',scale=iw*1.1:ih*1.1,crop=1920:1080"
# 8 Cinematic 2.39:1 letterbox
-vf "crop=1920:804,pad=1920:1080:0:138:black"
# 9 Vertical 9:16 from 16:9 with blurred-fill background
-filter_complex "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
# 10 Split screen
-filter_complex "[0:v]scale=960:1080,setsar=1[l];[1:v]scale=960:1080,setsar=1[r];[l][r]hstack"
# 11 TEXT BEHIND SUBJECT: text on background, subject (alpha from matte) composited on top
-i bg.mp4 -loop 1 -i subject.png -loop 1 -i matte.png -filter_complex "[0:v]drawtext=text='PREMIUM':fontsize=420:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:fontfile=FONT.ttf[bg];[1:v][2:v]alphamerge[fg];[bg][fg]overlay=shortest=1"
#    for video: produce a per-frame matte (rembg/RVM) → ProRes 4444/WebM alpha subject clip → overlay it over the text layer.
# 12 Animated drawtext (fade + rise over 0.5 s)
-vf "drawtext=text='HELLO':fontsize=96:fontcolor=white:x=(w-text_w)/2:y='h/2+60*(1-min(t/0.5,1))':alpha='min(t/0.5,1)':fontfile=FONT.ttf"
# 13 Karaoke / word-pop captions: write an .ass file (per-word {\kf} timing from WhisperX, {\t(...)} scale pop) then burn
-vf "subtitles=captions.ass"
# 14 Progress bar
-vf "drawbox=x=0:y=ih-12:w='iw*t/DURATION':h=12:color=0xFFD700@0.9:t=fill"
# 15 Freeze-frame hold of 1 s at the end / reverse / interpolate to 60 fps
-vf "tpad=stop_mode=clone:stop_duration=1"   |   -vf reverse   |   -vf "minterpolate=fps=60:mi_mode=mci"
# 16 Stabilise (2-pass)
ffmpeg -i $IN -vf vidstabdetect=result=t.trf -f null -  &&  ffmpeg -i $IN -vf vidstabtransform=input=t.trf:smoothing=15 out.mp4
# 17 Dialogue chain + loudness (measure first, then apply the measured values for true two-pass)
-af "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-18dB:ratio=3:attack=15:release=200,loudnorm=I=-16:TP=-1:LRA=11"
ffmpeg -i $IN -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null -     # read input_i/input_tp/… then rerun with measured_* values
# 18 Music ducking under voice (voice = input 0 audio, music = input 1)
-filter_complex "[1:a][0:a]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=300[m];[0:a][m]amix=inputs=2:normalize=0[a]" -map 0:v -map "[a]"
# 19 Detect silence / scene changes (feed results into a cut list)
-af silencedetect=n=-35dB:d=0.3 -f null -      |      -vf "select='gt(scene,0.3)',showinfo" -f null -
# 20 Final export (H.264, tagged Rec.709, web-ready)
-c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -profile:v high -colorspace bt709 -color_primaries bt709 -color_trc bt709 -c:a aac -b:a 256k -ar 48000 -movflags +faststart
# 21 RGB split / chromatic aberration (glitch accent — apply to a 3–6 frame window only)
-filter_complex "split=3[r][g][b];[r]lutrgb=g=0:b=0,pad=iw+8:ih:8:0[r2];[g]lutrgb=r=0:b=0,pad=iw+8:ih:4:0[g2];[b]lutrgb=r=0:g=0,pad=iw+8:ih:0:0[b2];[r2][g2]blend=all_mode=addition[rg];[rg][b2]blend=all_mode=addition,crop=1920:1080:4:0"
```
**Rules that prevent bad renders:** conform every source to the same fps/size/pixel format before xfade/concat · work from proxies (720p) while iterating, render masters once · chain filters in one pass · never mix variable-frame-rate screen recordings (convert with `-vsync cfr -r 30`) · keep a 1.1–1.2× scale margin before any crop-based move to avoid black edges · use `-ss` before `-i` for fast seeking, after `-i` for frame accuracy.

### D. The production loop (every job)
1. **Probe** inputs (`ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,duration -of json`). 2. **Transcribe** with word timestamps. 3. **Plan**: write the cut list + Visual Narration Plan (timecode, phrase, placement, visual, sound) as a table or JSON. 4. **Rough cut** (silence/filler removal, scene boundaries). 5. **Motion graphics** rendered separately (HTML/HyperFrames/Remotion or FFmpeg drawtext/overlay) with alpha where they sit over footage. 6. **Composite + grade + sound design.** 7. **Loudness + export.** 8. **Verify like a viewer**: extract frames at key beats (`ffmpeg -ss T -i out.mp4 -frames:v 1 f_T.png`), make a contact sheet, check safe zones, check captions against the transcript, re-measure loudness. Fix and re-render; never ship unseen.

### E. What makes it feel premium (rules, not effects)
- **One system:** one palette, one type pair, one motion grammar, one transition vocabulary per video. Consistency reads as expensive.
- **Ease everything:** entrances `cubic-bezier(0.16,1,0.3,1)`, transforms `cubic-bezier(0.65,0,0.35,1)`, playful overshoot `cubic-bezier(0.34,1.56,0.64,1)`. Never linear.
- **Depth:** separate foreground / mid / background; add soft shadows, subtle parallax (≤ 3–6% travel), grain 5–12% and a gentle vignette.
- **Hierarchy:** one focal point per frame, ≥ 30% negative space, max ~6 elements.
- **Rhythm:** vary shot length; land graphics and cuts on beats/words; let important moments breathe.
- **Sound sells picture:** a sound for every cut and graphic land; the quiet before the hit.
- **Restraint:** effects serve the idea. If it doesn't clarify or emphasise, delete it.
- **Polish:** no audio pops, no jitter, no black edges, no text outside safe zones, no single-frame flashes.

## Hybrid premium style & advanced feature pack

### H1. What "hybrid" means (observed in six premium reference videos)
Text and graphics are treated as **objects inside the scene**, not captions laid on top. Footage, 3D/AI renders, UI cards and kinetic type share one visual system. Devices seen across the references:
1. **Hierarchy inside one line** — a small lead-in word and one huge keyword (e.g. "here's the branding secret" small → "no one tells you" large).
2. **Single accent colour** (red, gold, orange or brand blue) against a controlled base (white, black or one graded footage look) with soft shadows and glow for depth.
3. **Words appear on the spoken beat** with blur-in/rise-in; the key word gets the accent colour and the largest size.
4. **Text integrated with the subject** — text arcs/wraps around the speaker, sits behind them (matte), or tracks an object; accent glow or flash on impact words.
5. **UI-as-graphics** — stat cards (64%, $50k), badges, toggles, a search bar that types "Comment ___", cursor/hand pointer, app-icon orbit, mind-map nodes.
6. **Hero objects** — 3D or AI-generated renders (statue, badge, product, device mock) on clean backgrounds, slow push + soft shadow.
7. **Hidden cuts** — a whip, flash, starburst/ribbon sweep, zoom-through or object wipe covers the edit; the hard cut is invisible.
8. **Before/After or phone-frame framing** — split-screen labelled panels, or a phone-shaped inset over a blurred, enlarged copy of the same footage.
9. **Matched cinematic B-roll** graded to the same look as the talking head; the speaker may be cloned/multiplied for emphasis.
10. **Comment-keyword CTA** ("Comment 'folder'") and a brand end card with a soft focus-pull.
**Pace:** a new visual event every 1–2.5 s (measured cut ASL 2.3–3.2 s, but most changes were in-scene motion, not cuts). **Audio:** speech forward, bass-heavy bed, impact/whoosh hits on the key-word slams; delivered around −14 LUFS.

### H2. How much of it to use ("hybrid dial") — decide per job
**0** = none (clean, regulated, calm) · **1** = light (accent colour, hierarchy lines, subtle push) · **2** = medium (+ UI cards, stat count-ups, hidden-cut transitions) · **3** = full (+ behind-subject text, 3D/AI hero objects, glow/flash, phone-frame, tracked text). Ask the client which dial; default is given in "Hybrid dial for this skill" below. Higher dial = more assets required (see H4) and more render time.

### H3. Editor feature → terminal equivalent (NLE checklist)
| Editor feature | In the terminal |
|---|---|
| Cut / split / trim | `trim` + `setpts`, or `cutlist.py` clips (in/out) |
| **Ripple edit** (close the gap) | delete the clip from the cut list — concat closes the gap |
| **Slip** (change content, keep position/length) | shift `in` and `out` by the same amount |
| **Slide** (move a clip, neighbours keep length) | reorder/shift entries in the cut list |
| **Copy/paste attributes** | reuse the same `vf` string/preset for many clips (store presets in one file) |
| Speed / ramp / slow-mo | `setpts`, split+concat ramp (recipe 3), `minterpolate` |
| Colour correct / LUT / contrast / saturation | `eq`, `curves`, `colorbalance`, `lut3d` (recipe 5) |
| **Sharpen / blur** | `unsharp` (recipe 23), `gblur`, `boxblur` |
| Film grain / vignette / glow | recipe 4 |
| **Light leaks / lens flares** | generated gradient overlay + `blend=screen` (recipes 24–25) |
| Transitions (fade, whip, zoom, glitch, match) | `xfade`, recipes 2, 7, 21, 31 |
| Keyframes: zoom, pan, **opacity, position** | expressions in `scale`/`crop`/`overlay` with `t` (recipes 1, 26) |
| **Object tracking (text follows subject)** | `track_text.py` (OpenCV CSRT → ASS positions) |
| Subtitles / kinetic type | ASS from word timestamps (recipe 13), HTML/GSAP via HyperFrames |
| Lower thirds / callouts | drawtext / PNG overlay with eased entrance (recipes 12, 26) |
| **Emoji / sticker pop** | transparent PNG overlay with scale-pop timing (recipe 26); never rely on system emoji fonts in drawtext |
| Audio: music sync, SFX, denoise, EQ, ducking | recipes 17, 18, librosa beats |
| Jump cuts / silence removal | auto-editor or `silencedetect` (recipe 19) |
| Pattern interrupts / B-roll / loop ending | recipes 1, 3, 15, 27 |
| **Green screen (chroma key)** | `chromakey` + `despill` (recipe 22) |
| **Masking & reveal** | animated `alphamerge` mask (recipe 28) |
| **Depth blur / fake bokeh** | radial-mask blur (recipe 29) |
| Letterbox | recipe 8 |
| **Proxy editing** | recipe 36 |
| Multicam | cut list across several sources + audio-energy/transcript switching |
| Presets/templates | keep a presets folder (LUTs, ASS styles, `vf` strings, HTML templates) |
| Auto subtitles (AI) | faster-whisper / WhisperX → SRT + ASS |

### H4. Hybrid-style asset request (ASK THE CLIENT — never fabricate)
At dial 2–3, add these to ASSET-REQUEST.md and wait for them (or confirm the AI may generate/synthesize each):
- **Brand kit:** the accent colour, base colours, 1–2 fonts, logo (SVG/PNG with transparency), end-card wording and the comment-keyword CTA.
- **Script/transcript with the key word of each line** marked (the one word that gets the accent).
- **Subject files:** the speaker/product footage; for behind-subject or cut-out looks either a **green-screen shot**, a **clean background plate**, or permission to run a matting model (check its licence).
- **Hero objects:** 3D renders, AI images or product packshots **with transparent background** (PNG/WebM-alpha), or approval to use generated placeholders (disclosed).
- **UI assets:** real screenshots/screen recordings, logo/icon set, names and figures to show on cards (each with source/date).
- **Sound pack:** whoosh, impact, riser, click, pop, sub-drop (licensed) and the music bed.
- **References:** 1–3 videos whose look is wanted (we match the system, never copy the content).
If an asset is missing and cannot be generated honestly, **lower the dial**, say so, and list what unlocks the next level.

### H5. Tested recipes 22–36 (FFmpeg 6.1.1; all executed on synthetic sources)
```bash
# 22 Green screen: key + remove green spill, composite over a background
-i bg.mp4 -i green.mp4 -filter_complex "[1:v]chromakey=0x00ff00:0.12:0.08,despill=type=green[fg];[0:v][fg]overlay=(W-w)/2:(H-h)/2:shortest=1"
# 23 Sharpen (apply last, small amount; avoid on noisy footage)
-vf "unsharp=5:5:0.8:5:5:0.0"
# 24 Moving warm light leak (screen-blend a generated gradient that sweeps across)
-i in.mp4 -f lavfi -i "color=c=black:s=1920x1080:r=30:d=4,geq=r='255*exp(-pow((X-1920*(0.2+0.2*T))/500,2))':g='140*exp(-pow((X-1920*(0.2+0.2*T))/400,2))':b='40*exp(-pow((X-1920*(0.2+0.2*T))/300,2))'" -filter_complex "[0:v][1:v]blend=all_mode=screen:all_opacity=0.7"
# 25 Lens-flare hotspot (static or animate the centre with T)
-f lavfi -i "color=c=black:s=1920x1080:r=30:d=4,geq=r='255*exp(-hypot(X-1400,Y-300)/90)':g='220*exp(-hypot(X-1400,Y-300)/90)':b='160*exp(-hypot(X-1400,Y-300)/90)'"  (then blend=all_mode=screen:all_opacity=0.8 as in 24)
# 26 Pop-in card / sticker / emoji PNG: fade in + rise with ease-out (cubic) between t=0.3 and 0.8 s
-i video.mp4 -loop 1 -i card.png -filter_complex "[1:v]format=rgba,fade=t=in:st=0.3:d=0.4:alpha=1[c];[0:v][c]overlay=x=(W-w)/2:y='H-h-120+80*pow(1-min(max((t-0.3)/0.5,0),1),3)':shortest=1"
# 27 Loop ending: last 0.5 s cross-dissolves into the first 0.5 s (output = duration − 0.5)
-filter_complex "[0:v]split[m][h];[h]trim=0:0.5,setpts=PTS-STARTPTS[head];[m]trim=0.5:DUR,setpts=PTS-STARTPTS[body];[body][head]xfade=transition=fade:duration=0.5:offset=DUR-1.0[v]" -map "[v]"
# 28 Mask reveal (left→right wipe of clip B over A over 1.5 s; swap the geq for circles/shapes)
-i a.mp4 -i b.mp4 -filter_complex "color=c=white:s=1920x1080:r=30:d=4[w];[w]geq=lum='if(lt(X,1920*T/1.5),255,0)',format=gray[m];[1:v][m]alphamerge[fg];[0:v][fg]overlay=shortest=1"
# 29 Fake depth blur: sharp centre, blurred edges (radial mask made once with geq → radial.png)
ffmpeg -f lavfi -i "color=c=black:s=1920x1080,format=gray,geq=lum='clip((hypot(X-960,Y-540)-300)*0.6,0,255)'" -frames:v 1 radial.png
-i in.mp4 -loop 1 -i radial.png -filter_complex "[0:v]split[s][b];[b]gblur=sigma=18[bl];[bl][1:v]alphamerge[blm];[s][blm]overlay=shortest=1"
# 30 Accent glow text (draw text, blur a copy, screen-blend it back)
-vf "drawtext=text='WORD':fontsize=200:fontcolor=0xff2040:x=(w-text_w)/2:y=(h-text_h)/2:fontfile=FONT.ttf,split[a][b];[b]gblur=sigma=25[g];[a][g]blend=all_mode=screen:all_opacity=1"
# 31 Impact flash (brightness pulse at t=2.0) + barrel-distortion punch
-vf "eq=brightness='0.6*exp(-12*abs(t-2))':eval=frame"        |        -vf "lenscorrection=k1=-0.25:k2=-0.1"
# 32 Count-up that lands on the spoken number (here 0→64 % in 1 s)
-vf "drawtext=text='%{eif\:trunc(min(t/1.0\,1)*64)\:d}%':fontsize=300:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:fontfile=FONT.ttf"
# 33 Phone-frame inset over a blurred, darkened, enlarged copy of the same footage (rounded-corner mask)
-filter_complex "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.15[bg];[b]scale=-2:1500,crop=800:1500,format=yuva420p,geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='if(lt(hypot(max(abs(X-400)-340,0),max(abs(Y-750)-690,0)),60),255,0)'[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
# 34 Before/After labelled vertical split
-i after.mp4 -i before.mp4 -filter_complex "[0:v]scale=1080:-2,pad=1080:960:0:(960-ih)/2[t];[1:v]scale=1080:-2,pad=1080:960:0:(960-ih)/2[u];[t][u]vstack,drawtext=text='After':fontsize=44:fontcolor=white:box=1:boxcolor=0xff3366@0.9:boxborderw=14:x=30:y=30:fontfile=FONT.ttf,drawtext=text='Before':fontsize=44:fontcolor=white:box=1:boxcolor=0x333333@0.9:boxborderw=14:x=30:y=990:fontfile=FONT.ttf"
# 35 Cut list (ripple/slip/slide/speed/copy-attributes) → see cutlist.py below
# 36 Proxy workflow: edit on 360p proxies, then re-render the SAME cut list against the originals
ffmpeg -i original.mp4 -vf scale=-2:360 -c:v libx264 -preset ultrafast -crf 28 -an proxy.mp4
```
**Not testable with FFmpeg alone — build these in HTML/CSS/GSAP/Three.js (HyperFrames or Remotion) or request assets:** text arcing/wrapping around a subject in 3D, particle-dissolve text, 3D camera moves on hero objects, app-icon orbit, mind-map/UI motion, speaker cloning/"many arms", AI-generated hero renders. Render those layers with transparency, then composite with FFmpeg (overlay) and grade the whole. These approaches are documented but were not executed in this pack's test run — render a 2-second test and inspect frames before building the full video.

### H6. Scripts (tested)
**`cutlist.py` — NLE-style edits in one FFmpeg pass.**
```python
#!/usr/bin/env python3
"""Cut-list renderer: NLE-style edits (ripple, slip, slide, speed, per-clip filters) -> one FFmpeg run.
Usage: python3 cutlist.py edit.json out.mp4
edit.json = {"fps":30,"size":[1080,1920],"clips":[{"src":"a.mp4","in":0.0,"out":3.0,"speed":1.0,"vf":""}, ...]}
Ripple delete = remove a clip from the list (gap closes automatically).  Slip = change in/out by the same amount (length unchanged).
Slide = reorder/shift clips; neighbours' lengths are untouched. Copy attributes = reuse the same "vf" string."""
import json,subprocess,sys
e=json.load(open(sys.argv[1])); W,H=e["size"]; fps=e.get("fps",30)
inputs=[];parts=[];labels=[]
for i,c in enumerate(e["clips"]):
    if c["src"] not in inputs: inputs.append(c["src"])
    k=inputs.index(c["src"]); sp=c.get("speed",1.0); vf=c.get("vf","")
    chain=f"[{k}:v]trim={c['in']}:{c['out']},setpts=(PTS-STARTPTS)/{sp},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1,format=yuv420p"+(","+vf if vf else "")+f"[v{i}]"
    parts.append(chain); labels.append(f"[v{i}]")
fc=";".join(parts)+";"+"".join(labels)+f"concat=n={len(labels)}:v=1:a=0[v]"
cmd=["ffmpeg","-y","-loglevel","error"]
for s in inputs: cmd+=["-i",s]
cmd+=["-filter_complex",fc,"-map","[v]","-c:v","libx264","-pix_fmt","yuv420p",sys.argv[2]]
subprocess.run(cmd,check=True); print("rendered",sys.argv[2])
```
Example `edit.json`: three clips with one shared `vf` (copy-attributes), clip 2 at 0.5× and clip 3 at 2×. Ripple delete = remove an entry; slip = move `in`/`out` together; slide = reorder entries. Re-render in seconds.
**`track_text.py` — make text follow a moving object (OpenCV CSRT).** Requires `opencv-contrib-python`. Tracker can drift on fast motion/occlusion: review, re-seed the box, split into shots.
```python
#!/usr/bin/env python3
"""Make text follow a moving object. Usage: python3 track_text.py in.mp4 x y w h "LABEL" out.ass [dx dy]
(x,y,w,h = bounding box of the object on the FIRST frame, in pixels.) Then burn with: ffmpeg -i in.mp4 -vf subtitles=out.ass ...
Uses OpenCV CSRT tracker (opencv-contrib). Review the result; re-seed the box if the tracker drifts."""
import cv2,sys
src,x,y,w,h,label,out=sys.argv[1],*map(int,sys.argv[2:6]),sys.argv[6],sys.argv[7]
dx,dy=(int(sys.argv[8]),int(sys.argv[9])) if len(sys.argv)>9 else (0,-50)
cap=cv2.VideoCapture(src); fps=cap.get(cv2.CAP_PROP_FPS); W=int(cap.get(3)); H=int(cap.get(4))
ok,f=cap.read(); tr=cv2.TrackerCSRT_create(); tr.init(f,(x,y,w,h))
def ts(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
ev=[]; i=0
while ok:
    ok2,b=tr.update(f)
    if ok2:
        cx=int(b[0]+b[2]/2)+dx; cy=int(b[1])+dy
        ev.append(f"Dialogue: 0,{ts(i/fps)},{ts((i+1)/fps)},T,,0,0,0,,{{\\an5\\pos({cx},{cy})}}{label}")
    ok,f=cap.read(); i+=1
hdr=f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: T,DejaVu Sans,{max(24,H//14)},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,0,5,10,10,10,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
open(out,'w').write(hdr+"\n".join(ev)); print(len(ev),"tracked frames ->",out)
```

### H7. Motion rules for the hybrid look
- Entrance: blur 10–18 px → 0, rise 20–40 px, scale 0.9 → 1, over 0.25–0.45 s with ease-out (`cubic-bezier(0.16,1,0.3,1)`); exit faster (0.2–0.3 s).
- Key word: accent colour, 1.6–2.5× the lead-in size; land within ±100 ms of the spoken word (eye leads the ear by up to 80 ms).
- Impact words: 2-frame flash or glow pulse + low hit; never flash faster than 3 per second.
- Hidden cut recipe: start the whip/flash/sweep 3–5 frames before the cut and finish 3–5 frames after; put the whoosh on the first frame of motion.
- Depth: soft shadow under every card/object, background slightly desaturated or blurred, ≤ 6% parallax.
- Keep ≥ 30% negative space, ≤ 6 elements per frame, and keep text inside the platform text-safe zone.
- Do not copy a creator's specific artwork, brand or wording. Match the *system* (hierarchy, rhythm, motion), never the content.

### H8. Hybrid dial for this skill
**Default dial: 2 (UI-as-graphics, stat cards, cursor, phone-frame/split for before-after); skip glitch and behind-subject text.** Ask the client to confirm; if they have not supplied the H4 assets, drop one level and say what unlocks the next.

## WHICH LANE IS THE A-ROLL? (function, not source)

**A-roll = whatever carries the meaning. B-roll = whatever supports it.** The
lane is defined by FUNCTION, never by whether it came off a camera.

- In a **talking-head** piece the speaker is the A-roll; graphics and footage
  are B-roll.
- In a **graphics-led** piece — the motion graphics carrying the argument, the
  footage used as cutaways — **the motion graphics ARE the A-roll and the
  footage becomes B-roll.** This inversion is normal and correct; it is the
  hybrid format.
- So when the visual narration carries the meaning, treat the graphics as the
  spine: plan them first, bind them to the words, and let the footage serve them.

## ADVANCED FEATURE USE-CASES (mandatory — the professional toolset)

**"Mandatory" means: if the concept needs it, you use it.** These are the
features that separate a professional edit from an amateur one. Reading
"mandatory" is the prompt to reach for the feature; using the feature is what
makes the video hold up. Full guide + terminal recipes:
`ADVANCED-FEATURE-USE-CASES.md`.

**Timeline & structure** — **multi-track timeline** (layer video/audio/effects,
never a flat single track) · **multi-camera editing** (sync angles, cut on
speaker/action) · **proxy editing** (cut proxies, re-render the same cut list on
the originals) · **batch export** (every ratio from one master) · project
collaboration.

**Motion & animation** — **keyframing** (position, scale, opacity, rotation,
blur on an eased curve) · **motion tracking** (bind text/effects to a moving
object; lowpass the track first) · **masking & rotoscoping** (frame-by-frame
isolation) · **speed ramping / time remapping** (speed curves across a beat) ·
**stabilisation** (2-pass warp) · **frame blending / optical flow** (smooth slow
motion).

**Colour** — **colour correction** (exposure, white balance, contrast FIRST) ·
**colour grading** (the look: LUT, film emulation, split-tone, SECOND) ·
**scopes** (waveform, vectorscope, histogram, RGB parade — grade by the numbers)
· **HDR grading** (only on request; tone-map to SDR for delivery).

**Compositing & effects** — **chroma key** (green/blue removal with spill
suppression and a clean edge) · **compositing / VFX** (combine layers into one
scene) · **3D camera tracking** (solve the move, place 3D in real footage) ·
**advanced transitions & effects** (blur, glow, glitch, light leaks, grain,
chromatic aberration — each timed to a cut or beat).

**Audio** — **noise reduction** (hiss, hum, room tone) · **EQ** (high-pass
dialogue, de-mud, carve space for music) · **audio syncing** (by waveform or
timecode) · **multi-track mixing** (dialogue/music/SFX; duck music 12–18 dB under
voice) · surround/spatial only where the delivery needs it.

**AI & smart** — **auto subtitles** (word-level timing drives captions AND the
narration plan) · **AI background removal** (matte without a green screen) ·
**auto reframing** (re-frame for 9:16 / 1:1 / 4:5 keeping the subject safe) ·
**scene detection & auto cutting** (cut list from scene changes) · **AI
colour/exposure correction** (first pass, then grade by hand).

**Assets & stills** (for every generated image/graphic) — layer-based editing,
layer masks, blending modes · frequency separation (skin retouch) · dodge & burn ·
content-aware fill / object removal · perspective correction · RAW processing ·
tone curves · HDR merge · panorama stitch · AI-assisted selection ·
non-destructive workflow · vector editing (bezier) · gradient mesh · typography
controls (kerning, tracking, leading) · symbol/asset libraries · artboards · grid
systems · multi-format export.

### The Camera Law (mandatory wherever there is a camera)
1. **One camera wrapper only** — all zooms/pans from a single master camera;
   never local ad-hoc transforms on nested elements.
2. **One camera move at a time** — never stack camera transforms.
3. **Every zoom has a reason** — READ / EMPHASIZE / REVEAL / FOLLOW / BREATHE.
   Constant zoom = no zoom.
4. **Do not cut while zoomed** — return to rest or hold the scene.
5. **Motion blur only during fast motion** — `blur = clamp(v*k, 0, max)`, zero at
   rest (start k ≈ 0.012, max ≈ 24 px). **Anchor zoom** sets the origin on the
   target; **follow** keeps the subject in a safe zone with a damped spring.

**The test:** walk the timeline. For each feature the concept needed, ask "is it
there, and is it doing a job?" A missing needed feature — a flat single track, an
ungraded image, a jittery tracked label — means the edit is not finished.

**For this skill:** screen compositing, motion tracking of the cursor, readability zoom, chroma key for a presenter, and multi-track audio are mandatory on every build.

## MANDATORY FEATURE USE-CASES (the modern standard)

These are not optional extras. Each has a job; if the job is missing, the edit
reads as amateur. Apply what the concept needs — the items marked **★** apply to
almost every build.

**Camera & motion**
- **★ Zoom in (anchor zoom)** — bring a detail to readable size; origin on the
  target; return to rest before the next cut.
- **★ Zoom out (reveal)** — pull back for context after a detail; wide <-> detail
  rhythm is the pacing engine.
- **★ Motion tracing / follow camera** — the camera follows the cursor or the
  action (safe-zone follow, spring-damped); never leave motion under a static
  frame.
- **Slow push** — <=8% over 3-5s for tension.
- **Camera shake on impact** — a brief 2-4 frame shake on a hit.
- **Speed ramp** — slow->fast or fast->slow across a key beat.
- **Motion blur (velocity)** — blur only while fast; exactly 0 at rest.

**Keyframing & animation**
- **★ Keyframe everything** — position, scale, opacity, rotation, blur; nothing
  moves without keyframes and a curve.
- **★ Easing curves (bezier)** — every move eased, never linear; curve the PATH
  (bezier), not just the timing.
- **Mask / wipe reveal** — draw-on reveals, mask transitions, trim-path draws.
- **Parallax / 2.5D depth** — layers move at different rates (<=3-6% travel).
- **Freeze frame / hold** — stop on the moment that matters.

**Text & data**
- **★ Kinetic text / word-pop** — words appear on the beat; one accent keyword
  per line.
- **★ Count-up numbers** — every stat animates to its value on the spoken word.
- **Text tracked to an object** / **text behind the subject** — for hybrid pieces.
- **Callouts & arrows** — draw-on annotations pointing at the thing.

**UI & product (mandatory for ANY demo)**
- **★ Readability zoom** — any UI text the viewer must read renders >=4% of frame
  height (>=44px at 1080p).
- **★ Micro-interactions** — hover, press, ripple, toggle, focus; the UI answers
  the cursor.
- **★ Screen transitions** — push/pull navigation, modal rise + scrim, sheet slide.
- **★ Cursor physics** — bezier path, minimum-jerk timing, overshoot, click anatomy.
- **Comparison split / PiP** — two states side by side.
- **Screen replacement** — UI on a device.

**Edit & finish**
- **★ Cut-on-beat / cut-on-action** — cuts land on the beat or mid-movement.
- **★ A sound for every cut** — whoosh/impact/tick; silence before the biggest hit.
- **★ Correct then grade** — exposure and white balance first, then the look.
- **Seamless loop** — for social/web loops (end state = start state).

**The test:** open the finished timeline and ask, for each ★, "did this build use
it where the concept needed it?" If a needed ★ is missing, the edit is not
finished.

## CAPTION & TEXT SYSTEM (mandatory)

**The Text Law.** On-screen text maps the visual — it is never generic subtitles.
A plain SRT ships separately as an optional accessibility file; it is NOT the
on-screen text. Every build declares ONE caption style and holds it.

### The three caption modes (choose per build; a build may use all three)
1. **Styled text captions** — designed, on-brand and animated: a declared style
   (font, weight, size, tracking, leading, case, fill, stroke/box, accent colour,
   entrance/exit) held consistently, keywords accented, text timed to the word.
   Never the OS default font, never a plain white box.
2. **Transparent-background captions (alpha)** — captions with **no background**,
   delivered as transparent PNGs (or an alpha clip: WebM VP9 alpha / ProRes 4444),
   so the type sits over or behind the picture: outline-only text, sticker/karaoke
   text, cut-out words, and **text-behind-subject**. Clean, premultiplied alpha.
3. **Chroma-key text & subject** — text or a subject shot on a flat green/blue
   screen and keyed so it floats over the graphic layer; or the subject keyed so
   text can pass behind them.

### Styled-caption spec (write it into CONCEPT.md)
- **Style sheet** — font · size (>=4% frame height for anything the viewer must
  read) · weight · tracking · leading · case · fill · stroke/shadow · box (none /
  subtle / solid) · accent colour · safe-zone position.
- **Timing** — word-level (from the transcription JSON); the caption lands on the
  spoken word (+/-100 ms); <=2 lines; <=17 characters/second; minimum cue ~0.84 s.
- **Motion** — entrance/exit eased (fade + rise, or a word-pop scale), never
  linear; one accent keyword per line.
- **Placement** — inside the text-safe zone (Platform standards); never under the
  platform UI.

### Transparent-caption spec
- Deliver as **PNG with alpha, no background** (or an alpha clip for animated
  type). Clean the edge: 1-2 px feather, no dark/light halo, premultiplied.
- **Text-behind-subject** — composite a text layer UNDER the subject's alpha
  matte (matte from chroma key or an AI matte). The subject needs a clean cut-out;
  where the cut is rough, choke the matte.
- Never a white box behind a "transparent" caption.

### Chroma-key spec
- Key on a **flat, evenly lit green (#00B140) or blue**; avoid green clothing,
  props and spill on hair/shoulders.
- Key, then: **despill** the edges · **choke** the matte 1-2 px · add a **light
  wrap** so the subject belongs to the new background · a **garbage matte** to
  remove rigs.
- Composite over the graphic layer with matched grain and colour; grade the
  subject and background together so the seam disappears.

### Pick the style from CAPTION-STYLES.md
Choose ONE named caption style — **Apple-Clean · Vox-Highlighter · Sticker-Pop ·
Outline-Alpha · Karaoke-Word** — and declare it in CONCEPT.md.

### Request these in ASSETS-PROMPT.md
The transparent caption PNGs / alpha clips go under **transparent images
(PNG/alpha)** (category 2); the styled-caption font/style and any animated
caption engine go under **code components** (category 6).

### Surprise pack — make the text move (use where the concept needs it)
- **Kinetic typography** — word-by-word reveal, anchor repositioning before each
  word, one accent word per line.
- **Word-pop / karaoke captions** — per-word scale pop from word-level timing.
- **Animated underline / highlight / hand-drawn circle** — draw-on accents on the
  key word.
- **Text-behind-subject / rotoscoped text** — type passing behind a keyed subject.
- **Alpha overlays** — lower-thirds, sticker captions, floating labels as PNG/alpha.

## RENDER GATE — the contact sheet (mandatory before the full render)

**Never render the full video without sign-off.** Before the final render,
extract one frame per second and build a **contact sheet** for approval:

`ffmpeg -i build.mp4 -vf fps=1 sheet/f%04d.jpg`

Then **offer the user a choice of contact-sheet variants** — build 2-3 and let
them pick. The sheet is the cheapest place to catch pacing, composition,
safe-zone and continuity problems; a variant lets the reviewer read the edit the
way that suits them.

### The contact-sheet variants (build at least TWO; label them V1 / V2 / V3)
- **V1 — Classic Grid.** A uniform grid of 1 FPS frames in time order (left to
  right, top to bottom), each frame labelled with its **timestamp**. The baseline
  read of the whole edit at a glance.
- **V2 — Storyboard Filmstrip.** Larger frames laid in horizontal rows over a
  **time ruler**, with **scene-cut ticks** marked on the ruler and a one-line
  **caption** under each frame (what happens in that second). Reads like a
  storyboard; best for reviewing pacing, flow and the beat map.
- **V3 — Pro QC Sheet.** A dense technical sheet: each thumbnail carries its
  **timecode**, a **scene-cut flag**, a **motion/velocity indicator**, and a
  **safe-zone overlay**; a **colour-swatch strip** (the sampled palette) and a
  **summary header** run across the top (duration, shot count, ASL, loudness
  LUFS + true-peak, palette). Best for technical sign-off and continuity.

Build them at whatever aspect suits the cut (grid for a horizontal piece, a
vertical column for 9:16). Keep the Apple Standard chrome and the brand accent.

### The ask (mandatory)
Present the variants and ask the user directly:

> "Here are the contact-sheet variants — V1, V2, V3. **Did you like any of
> these, or shall I generate more variants so you can choose?**"

Then wait. If they want more, generate additional variants. **Render the full
video only after they finalise** — both the variant they prefer and the cut.

## QA GATE — validate before delivery (mandatory)

Before the full render and again before delivery, run the **`edit-qa-validator`**
skill. It does three passes:

1. **AUDIT** — walk the MASTER CHECKLIST (every mandatory list in the pack: the
   advanced toolset, the modern-standard features, the Camera Law, the Sentence
   Law, the Caption & Text System, the visual narration layer, the render gate,
   ethics and platform) and mark each item OK / WEAK / MISSING / N/A.
2. **AI RE-THINK** — for every WEAK or MISSING item, propose the concrete fix:
   what to add, where (scene / timecode / sentence), how (the exact move or kit),
   why it improves the video, and the expected gain.
3. **REVALIDATE** — re-audit after the fixes and produce the diff; PASS only when
   no star-mandatory item is MISSING and the caption system, Camera Law and
   Sentence Law are clean.

Write the report as `EDIT-QA.md`. **The edit is not finished until the QA gate
passes.**

## Platform & delivery standards (self-contained reference)
Platform UI and specs change; values are working standards (2026). Where sources disagreed the more conservative value is used. Re-verify before a paid campaign.

### 1. Vertical safe zones (1080×1920)
Safe zones are a *margin*, not a pixel-exact map; they differ per app and Reels
can additionally crop the feed preview to 4:5.
| Zone | Rule |
|---|---|
| **Universal action-safe** | keep faces/products/key action inside the centre ≈ **900×1330** |
| **Universal text-safe** | keep captions, prices, CTAs, legal text inside the centre ≈ **860×1100**, biased slightly above centre |
| **Shorts (measured)** | top ≈ 240px · bottom ≈ 380px (title/Subscribe) · right ≈ 200px (action column) · left ≈ 60px |
| **TikTok / Reels** | bottom caption tray is deep; right button column ≈ 120–200px; Reels feed preview can crop top/bottom ≈ 285px |
| **Rule of thumb** | design for the most restrictive app (Instagram bottom UI); then it works everywhere |
Always preview in the platform's own safe-zone checker/template.

### 2. Audio loudness (ITU-R BS.1770 integrated)
| Destination | Integrated | True peak ceiling |
|---|---|---|
| YouTube long-form, music, web | **−14 LUFS** | **−1 dBTP** (−2 if heavy codec risk) |
| Social vertical (Reels/TikTok/Shorts), mobile | **−16 to −14 LUFS** | −1 dBTP |
| Podcast (stereo) | **−16 LUFS** (−19 mono) | −1 dBTP |
| Broadcast TV | −23 LUFS (EBU R128) / −24 LKFS (ATSC A/85) | −1 to −2 dBTP |
| Streaming/VOD drama spec | −24 to −27 | −2 dBTP |
Use a **true-peak-aware limiter**, not a sample-peak limiter. Dialogue sits
~6–10 dB above music beds; duck music 12–18 dB under voice. Platforms only turn
loud files *down*, so do not chase loudness past the target.

### 3. Picture
- **Frame rate:** keep source rate. 24 = cinematic; 25 = PAL regions; 30 = web/social/talking-head; 50/60 = gaming, sports, screen capture, slow-mo source. Never mix rates without conforming. 180° shutter for live action (shutter ≈ 2× fps).
- **Colour:** Rec.709 / sRGB delivery. Tag colour metadata (`-colorspace bt709 -color_primaries bt709 -color_trc bt709`) so players don't shift gamma. HDR only on explicit request.
- **Resolution:** 1080p minimum, 4K master where source allows. 1080×1920 vertical.
- **Export (H.264):** `-c:v libx264 -preset slow -crf 16-18 -pix_fmt yuv420p -profile:v high -movflags +faststart`, AAC 48 kHz 192–320 kbps. Constant frame rate (variable-rate screen recordings must be conformed first).

### 4. Captions & accessibility
- Always deliver a sidecar **SRT/VTT** (accessibility, SEO, translation). Burn captions in only for social-first formats.
- Burned captions: ≤2 lines, ≤ ~42 characters/line, ≤17 chars/sec, minimum cue ≈ 0.84s, high contrast (stroke or box), inside text-safe zone.
- Never rely on colour alone to carry meaning; keep contrast ≥ 4.5:1 for text.
- Flash safety: no more than 3 flashes per second (photosensitivity).

### 5. Pacing benchmarks (average shot length, ASL)
| Style | Typical ASL | Notes |
|---|---|---|
| Short-form retention | 1–3 s | visual change every 2–4 s |
| Esports / kinetic hype | 0.4–1.5 s | cut on the beat/drop |
| E-commerce / DTC ad | 1.5–3 s | hook ≤ 1 s |
| Talking-head / creator | 3–8 s | visual event every 6–10 s |
| Podcast multicam | 4–10 s | cut on speaker change; reaction shots 1–2 s |
| SaaS demo | 3–6 s | one action per beat |
| Corporate / brand film | 3–6 s (interview 6–20 s) | B-roll 2–5 s |
| Real-estate flagship | 4–8 s | slow, held, gimbal |
| Wedding / event highlight | 2–5 s | emotional beats held longer |
| Luxury / minimalist | 5–12 s | stillness is the point |

### 6. Delivery checklist (every skill)
Hook/first frame verified · loudness + true peak measured, not guessed · safe
zones checked in platform overlay · captions file delivered · colour tags set ·
CFR confirmed · file plays on a phone in sound-off AND sound-on.

## 8. QA
Probe every scene. Verify: cursor bezier + minimum-jerk (never linear) ·
hover states fire · clicks precede UI by 100–150ms · typing variance + typo ·
scroll decelerates · no phantom clicks · no content crossing a border · every
read-moment ≥4% frame height and passes the phone test (350px downscale reads).

## 9. Hard limits
No logins, credentials, or CAPTCHAs — ever. No voice generation. No invented
features or metrics. Recreated UI disclosed. One deliverable: the video.
