# Motion

These rules apply to every animated element in every mode: explainer scenes, title cards, captions,
illustrated scenes, and anything added later. The goal is motion that people find easy to watch:
energetic, but readable. Pace comes from frequent changes (SKILL.md, "Keep it exciting"); each
single motion stays clean. The code lives in `remotion/src/motion.ts`. The burned-in captions follow the same
rules in ASS (`scripts/captions.py`).

## Rules

1. **One thing starts moving at a time.** The start of a motion grabs the eye, and people
   track about 4 objects at once. Stagger related parts 4–5 frames apart (`stagger(i)`), for example
   kicker → title → emoji. Rest 15–30 frames between beats.
2. **Rig parts, never weld them.** Build a parent → child hierarchy, and give each child its own spring
   that starts a few frames after its parent's. A shadow lands 4 frames after its card; a number badge
   pops in 4 frames after its row. This follow-through makes motion feel physical instead of pasted on.
3. **Springs for arrivals, eased curves for everything else; never linear on anything organic.**
   - `POP` (damping 12, stiffness 170): one visible overshoot. Use it for things that arrive.
   - `SOFT` (damping 22, stiffness 120): no overshoot. Use it for large surfaces (backgrounds, panels,
     caption bars), where a bounce feels busy.
   - `spring()` settles in about 1 s whatever the stiffness. For moves over several seconds, use
     `interpolate` with `Easing.bezier`.
4. **Squash and stretch keeps the area.** Stretch along the direction of travel by the spring's
   velocity and shrink across it by the same factor: `squash(vel)` returns `[1+s, 1/(1+s)]`. Never
   scale both axes the same way during a squash.
5. **Exits accelerate away.** `exit(framesLeft)` eases out with `cubic-bezier(0.3,0,1,1)`, and can be
   paired with a small lift or shrink. A linear fade reads mechanical.
6. **Big events get anticipation, a hit-pause and an overshoot.** Wind up the opposite way first,
   freeze for about 4 frames, release, overshoot 8–15%, and settle in 2–3 oscillations. Save this for
   the moments that matter; on every small entrance it gets tiring.
7. **Calm budget.**
   - Idle motion is slow breathing (`breathe(t)`: a period of about 7 s, an amplitude of 1–3%), never a
     pulse on every beat. The explainer's corner blob breathes with a 1.5% beat accent instead of
     jumping 8% on every beat.
   - Secondary motion runs at about 30% of the hero motion's amplitude, ambient motion at about 5%.
   - Colour changes ease over a few frames instead of snapping.
8. **Text pops return to rest.** A highlighted word may overshoot (110%), but it settles back to 100%.
   In ASS, the opaque box is drawn per word, so a held scale leaves a step in it. Caption lines never
   overlap: a line ends when the next one starts.
9. **60 fps.** Elastic motion at 30 fps strobes.

## The rig: `remotion/src/motion.ts`

| Helper | Use |
|---|---|
| `rig(frame, fps, POP \| SOFT)` | Spring progress `v` and its velocity `vel` (progress per second) |
| `squash(vel)` | Area-preserving `[along, across]` scale factors from velocity |
| `stagger(i, gap = 5)` | Frame offset for the i-th related part |
| `exit(framesLeft, frames = 15)` | 1 → 0 over the last frames, accelerating away |
| `breathe(t, period, amp)` | Slow ambient scale around 1 |

Where it is applied:

| Element | Motion |
|---|---|
| Explainer scene | The panel settles on `SOFT`; kicker, title and emoji arrive staggered on `POP`; the title squashes along its travel; the scene exits with an eased fade and a 2% shrink |
| Explainer points | The row slides in with squash; the number badge trails 4 frames behind |
| Explainer corner blob | Slow breathing plus a faint beat accent |
| Title card | The card slides in with squash; the shadow lands 4 frames later; the subtitle rises 8 frames later; the card exits with an eased fade and a lift |
| Remotion captions | The line rises on `SOFT`; the active word's colour and scale ease in on `POP` and back out on `SOFT` |
| ASS captions | `\t` transforms: the colour eases in with a 110% pop that settles to 100% within 200 ms, the previous word's colour eases back over 150 ms, and the line fades in over 120 ms |

## Perception principles

The sources behind the rules.

1. **One focal mover; the start of a motion captures attention; people track at most about 4
   objects.** (Abrams & Christ 2003; Pylyshyn & Storm 1988; Mayer's coherence principle)
2. **Ease organic motion; linear reads mechanical.** (Flash & Hogan 1985; Viviani & Flash 1995)
3. **Squash and stretch with conserved area, anticipation, follow-through.** (Lasseter 1987)
4. **Round shapes read friendly, sharp shapes read as threat.** The effect is modest. (Bar & Neta 2006)
5. **Visual change lands on the word that names it.** (Mayer: temporal contiguity)
6. **Palette of 3–5 hues:** a calm ground, a lighter figure, one warm accent, saturation saved for the
   climax. (Schloss & Palmer 2011; Valdez & Mehrabian 1994)
7. **Low-clutter background, high-contrast subject.** (Reber, Schwarz & Winkielman 2004; Rosenholtz
   et al. 2007)
8. **Build tension, then one clean payoff; parts that move together read as one thing.** (Cheung et
   al. 2019; Wagemans et al. 2012)

Game-feel craft: Jonasson & Purho, *Juice It or Lose It* (2012); Nijman, *The Art of Screenshake*.
Inertial bounce for porting from After Effects (Dan Ebberts, motionscript.com):
`offset = v * sin(t*w) / exp(decay*t) / w`, `w = freq*2π`, with freq 3 and decay 5.

## Verify motion

You cannot watch the video, so read motion from frames.

- **Frame strips** around every entrance, exit and event: every 2nd–4th frame for 20–40 frames. Check
  that one thing starts at a time, children trail their parent, overshoot settles, and exits ease.
  `scripts/frames.py VIDEO OUT_DIR 240 780:820:2` extracts frames and builds the contact sheet.
- Extract frames by index (`-vf "select=eq(n\,N)"`) and composite them afterwards. With an alpha MOV,
  combining `-ss` with an `overlay` against a `color` source can emit a background-only frame, which
  looks like a broken render.
- Extract from the final encoded file too, not only from Remotion stills.
- **Checklist:**
  - one motion onset at a time
  - no welded children
  - no linear motion on organic or text elements
  - area kept in every squash
  - exits ease
  - idle motion slow and small
  - colours ease
  - text pops return to rest
  - caption lines don't overlap

## Pitfalls

- `interpolate` needs a strictly increasing input range. To count down, map `[0, n]` to `[1, 0]`; never
  pass `[n, 0]`.
- Anything that renders fractional frames (`CameraMotionBlur`) breaks code that indexes per-frame data
  by integer frame. Interpolate between neighbouring frames first.

## Motion blur

`CameraMotionBlur` from `@remotion/motion-blur`, shutter 180°, 6 samples. At about 720 px/s the streaks
reach about 6 px: film-like, not smeary. A 20 s 1080p60 scene took 157 s with blur against about 60 s
without. Helpers in `remotion/src/illustrated/shared.ts`: `sampleAt` blends per-frame data at fractional
frames, `trailingShift(shutter, samples)` gives the time offset below.

- **Blur only the moving layer.** The blur sums N copies at 1/N opacity in 8-bit, so faint gradients
  and low-alpha CSS-blurred layers band into rings. Render background, foreground, text and flashes
  once, outside the blur wrapper. This is also faster.
- **Keep light changes out of the shutter.** A flash or saturation spike that starts mid-shutter is
  averaged down to half on its payoff frame. Drive light effects from the frame's own time.
- **Trailing shutter.** Samples fall after the frame by default. Shift time back by
  `1 - shutter/360/samples` so the newest sample is the frame itself: hit-pauses stay perfectly still,
  and movers lead at their unblurred position.
- **Unique SVG ids per sample.** All samples render in one page, so `clipPath`, `filter` and gradient
  ids collide and every copy uses the first sample's shape.
- Slow moves (under about 350 px/s) show almost no blur at 180°. That is correct; widen the shutter
  only around chosen events, and only as an artistic choice.

## Sound

Motion lands harder with a sound on it. Score every event, even when the audio comes last.

`sfx.py` and `mix.py --sfx` implement the points below; `cuecheck.py` verifies placement (SKILL.md,
"Sound effects").

- Mix with ffmpeg after rendering, not with `<Audio>` in Remotion: a remix takes seconds instead of a
  re-render, and loudness needs a limiter and `loudnorm`.
- Put each SFX's loudest point on its event frame. Measure the peak (10 ms RMS) *after* pitch-shifting
  and filtering, and compensate limiter delay (`alimiter` shifts 5 ms by default; set `latency=true`).
- Tune tonal SFX (chimes, ticks, accents) to the music's key. Duck the music 3–5 dB under big hits.
  Measured as a cue's loudest 10 ms over the speech/music RMS, big hits sit at +9 to +11 dB, light ones
  at +4 to +6 dB.
- Sources: Freesound CC0 first (confirm the licence on each sound's own page), CC BY with credit. Keep a
  manifest of URL, licence and credit per file. Refuse sounds from deleted accounts: their licence can
  no longer be checked.
- Two-pass `loudnorm` silently switches to slow automatic gain when a plain gain change would break the
  peak ceiling, which lifts the fade-in. Check that pass 2 reports `linear`; if not, put a lookahead
  limiter in front. Target −16…−14 LUFS integrated, true peak ≤ −1 dBTP.
- ffmpeg 8 `loudnorm` also refuses linear mode when the measured loudness range exceeds its target.
  Raise the target to the measured range; in linear mode it is one gain, so nothing gets compressed.
- `alimiter` limits sample peaks. Run it 4× oversampled, or the true peak overshoots by about 0.75 dB.
- AAC encoding adds 0.2–0.4 dB of true peak; aim about −2 dBTP before encoding to stay under −1.5 after.
- You cannot listen. Say so, and hand the mood, timbres and balance to a human.

## Safe rendering on a laptop

- Never delete files in the same command as a render, and never use `rm -rf`. Write every round to new
  versioned folders (`build-v5`, `out/stills-v5`).
- Run every bundle and render inside a memory cap:
  `systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 --quiet bash -c '...'`. Use 6G and
  `--concurrency=3` for full renders, and run one render at a time. A stills round peaked at about
  0.8 GB. A 6 s 720p60 explainer plus a 3 s title card took about 50 s.
