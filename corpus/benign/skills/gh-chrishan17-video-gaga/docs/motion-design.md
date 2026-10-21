# Motion design

Motion does two jobs: it tells the eye where to look and what changed, and it gives the piece life and a character of its own. The two don't conflict. A camera that reframes between two ideas has a job (it says "now look here"), and so does a word that slams up from a mask (it says "this one"). What has no job is motion added because a frame felt empty: wobbling text, random particles, everything pulsing to the beat. A frame that feels empty usually needs a better idea, not more movement.

Aim for motion that looks designed by a person with taste: a clear focal point, layers moving at different speeds, moves with weight and timing, cuts on action. The references the look stands on ([craft.md](craft.md), *The look has a name*) usually say how things move too: a stop-motion clay piece steps on twos, an ink painting soaks and settles, a Saul Bass title cuts hard between flat shapes. Move the way that reference moves, then push it further for this story.

## 1. A well-made scene

- **One idea, one focal point at a time.** At every moment the eye knows where to go; everything else is quieter (smaller, dimmer, slower).
- **Things arrive in the order the viewer needs them:** subject before detail, cause before effect, question before answer, axis before data.
- **Every animated property means something:** an arrival, an emphasis, a transformation, a relationship or a departure.
- **Hits land** on a spoken word (`s.when('word')`), a beat (`s.onBeat(i)`), or the end of the previous move.
- **It leaves on action.** Secondary elements are gone before the cut (`s.out()`, `exit:` on reveals) and the hero is carried by the transition. A scene that is only shoved off by the next one feels like a slideshow.

## 2. Easing: the hand of the video

| Intent | Runtime name | Feel |
|---|---|---|
| arrives and settles | `ease.enter` | fast in, long settle. The default for reveals |
| moves A → B | `ease.standard` | quick start, soft landing |
| leaves | `ease.exit` | accelerates away; exits are shorter than entrances |
| snap, push, cut on action | `ease.swift` | anticipation, then a snap |
| ambient drift, breathing light | `ease.gentle`, `inOutSine` | slow, low amplitude, never the main event |
| physical objects | `CV.spring(spring.presets.…)` | real weight and overshoot; `CV.springTrack` for a value that re-targets |
| mechanical things | `linear` | tickers, clocks, conveyor grids only |

The tables are vocabulary, not a menu. What matters is that the video has a consistent hand, the way one animator's work does: heavy things move slowly and settle long; light things snap. Overshoot belongs to objects and titles, not to numbers or data, which look wrong when they wobble.

## 3. Principles that make motion feel made

- **Anticipation and follow-through.** A small move against the direction before a big one; a settle, a lag or a secondary wobble after it. This is the difference between an object and a rectangle.
- **Overlap and cascade.** Related elements arrive staggered, with parts of one object trailing the lead part. A cascade of three layers reads as one rich moment; three separate events read as clutter. Stagger tightly (tens of milliseconds) so they belong together.
- **Contrast of speed.** Fast against slow is what gives rhythm: a quick hit, then a long drift; a burst of three cuts, then a held shot. Constant speed is flat.
- **Arcs.** Natural motion travels on curves. Straight-line moves read as UI.
- **Depth.** Build shots from layers (background, supporting shapes, the hero, small accents) that move at different rates, so even a hold has parallax.
- **Holds are alive, not frozen, and not all alike.** During a hold light moves, texture breathes, a background layer drifts, each scene in its own way. The same slow push on every scene reads as a filter, not a camera. Stillness is a tool too: a beat where everything stops dead makes the hit after it land, and the final poster frame sits perfectly still.
- **Still while it is read.** When the viewer has to read a line, a label or a number, the words and the camera hold still until it has been read (§4 has the reading speed); the camera reframes between ideas, not during them. What keeps the hold alive is something the eye is not reading. `gaga render` reports such a hold as a `read:` line, not a dead one, unless it lasts well past the time its words take to read.
- **Objects live across scenes.** What the viewer has already learned stays on screen and changes instead of being replaced: a dot becomes a node, a label becomes an axis, the number from the last scene becomes the first bar of the next chart. Each transformation is one step of the explanation, and the viewer never has to re-find what they were looking at. [runtime-api.md](runtime-api.md#an-object-that-lives-across-scenes) shows how to draw one object through several scenes.
- **No twins.** Parts that share the same numbers move identically and look mechanical: a row of bars rising in lockstep, two arms swinging as one. Offset them by a few frames, vary the amount, let one side lead. Strong key poses read as good stills before any motion is added.
- **A rank for every move.** One hero move at a time. Secondary moves travel 50–70% as far and start 0.1–0.2 s after it; ambient motion stays under 5% of the hero's travel. In a cascade the next element starts when the previous one is 30–50% done; exits are 40–50% shorter than entrances.
- **Notes in numbers.** A note about motion becomes a number before it becomes code. "Make it pop": scale 1 → 1.08 → 1 over 6 frames, peaking on the beat. "Premium": ease-out-expo entrances, springs at damping ratio 0.8 (`CV.spring({ ratio: 0.8 })`), no overshoot on text. "It drags": shorten each hold by one beat, so cuts stay on the grid. "Too busy": one hero move at a time, the rest later and shorter. "Looks generated": name each default it used and ban it by name.
- **Signature moves.** Give each video a few moves that are its own and that explain something: the camera following the head of a growing line, an iris opening out of the key number, a match cut where one shape becomes the next, the visual device ([craft.md](craft.md), *Picture*) transforming. These are what people remember.

## 4. Readability

Motion is wasted if the viewer can't read what lands.
- Something meaningful is visible or moving within the first ~0.3 s; vertical social video needs the hook in the first second.
- Hold every information beat at least ~1 s after it lands (longer for numbers and charts) before anything competes with it. Use `tail` so the last beat isn't cut off.
- On-screen text that isn't spoken needs reading time: roughly 4–5 CJK characters or 3 English words per second.
- Nothing smaller than what a phone can show: a phone held upright shows the frame about 390 px wide, and text under ~6 px tall there is unreadable. That is ~24 px type on a 1080-wide frame (9:16, 1:1) and ~40 px on a 1920-wide one, so a 16:9 video has fewer, bigger words. `gaga still` points at smaller text, and `--phone` shows the probes at that size.
- Text is at least 4.5:1 against what is behind it (3:1 for large type); colour is never the only thing that marks the one that matters (it also changes weight, size or position). Text deliberately dimmed so it is *not* read (a list's other items while one is discussed) is the exception, and it is never the only place a fact lives. `gaga still` measures the contrast on every probe.
- Keep critical content inside the title-safe 90%: the subject and every word to be read sit whole inside it at every moment the viewer is meant to read them (a slam may enter from off frame, but it lands whole), and clear of the caption zone (bottom ~12% at 16:9; the lower 18% and right 12% at 9:16 for platform UI).

## 5. Camera

A virtual camera (`CV.draw.camera`) turns a layout into a shot. Keep camera motion slower than content motion, but keep it moving.

- A camera has a manner. It **chases** (lags behind the subject, catches up, overshoots a little: alive, urgent) or it **follows** (locked to the subject: calm, certain). The manner is part of the film's character, so it changes only when the story does.
- Change shot size for real (wide to close, close to extreme close). A 2% drift on every shot is invisible; one decisive push is felt.
- Push in or pull out, then keep going or cut. Zooming in and straight back out reads as indecision.
- Layers sit at depths and move from one camera (`depth` in `CV.draw.camera`), the near ones faster, so the world has space to travel through. A far texture or lattice gives the camera something to slide against.
- Key the camera with `CV.draw.cameraAt`: zoom moves evenly in log space, so a long push doesn't speed up as it closes in.
- Shake once, on a landing: low frequency, a little rotation, quickly damped. Hand-held float stops during a held moment.

| Move | Says |
|---|---|
| push-in over a hold | importance, intimacy, "look closer" |
| arrive-push on entry | the hero appears |
| pan / track | the next item is related, in the same space |
| pull-out | context, the bigger picture |
| parallax drift | depth and life |
| match cut | continuity: shape A becomes shape B |
| a short, damped shake | a literal impact, once |

## 6. Cuts and transitions

A cut on the beat almost always works. Every other transition says something, so choose it for what it says; a film reads as made by one hand when its transitions come from a small family that belongs to its look, and the biggest change can get a move of its own. The full list is in [runtime-api.md](runtime-api.md#transitions), and the best transitions are often not on it.

What makes a seam feel made is what crosses it. Something survives the cut: the shape that becomes the next shape, the colour that floods the next frame, the line that keeps travelling. The strongest transitions are built inside the shots on either side rather than laid over them: the camera pushes into an object until it becomes the next world, a word grows until its counter is the next frame. Pause on the midpoint of a transition: it should be a frame worth looking at. Match the motion across a hard cut (same direction, similar speed, a zoom keeps its direction) and the cut disappears; the incoming shot is already moving the way the outgoing one left. Don't end two shots in a row the same way.

| Transition | Says |
|---|---|
| `cut` | the default: energy, continuity, anything on a beat |
| `fade` / dissolve | time passes, a mood shifts, the ending |
| `dip` to black or colour | a chapter break, a reveal after a hook |
| `push`, `whip` | next, in sequence (whip: with energy) |
| `wipe`, `stripes`, `blinds` | graphic and editorial energy, a grid |
| `iris` | a focus point grows into the next scene (once) |
| `ink`, dissolve | memory, an idea spreading |
| `zoom`, `zoomBlur` | going into something |
| `split` | the frame opens onto a reveal |
| `flash` light leak | warmth, a premium reveal |
| `glitch`, `pixelate` | digital worlds only, short |
| custom (a paper slide, a morph, a handscroll) | the style's own physical metaphor |

With music on, each transition plays its natural sound at its midpoint, which lands on the beat.

## 7. Type in motion

- Animate lines or words for anything longer than a title; per-character reveals are for a hero word.
- Mask reveals (`fx.lineReveal`), scale and blur arrivals, tracking that closes in on one word, a highlighter or underline that draws on: these look designed. A plain opacity fade looks default; a word that lands rises a few pixels and settles in scale with a spring.
- A line of type has a life: it enters, locks still while it is read, takes its emphasis (one word changes weight, colour or size), and leaves or becomes part of the next shot. Spoken lines that matter get a frame of their own instead of competing with the picture.
- Reveal words as they are spoken (`fx.wordReveal({ sync: s })`). Numbers count up (`fx.countUp`, `fx.roll`) and then hold, with the unit arriving with or after the number.
- CJK: wrap with `CV.text.wrap` (kinsoku-aware), don't letter-space body text, and prefer short lines with a deliberate break.

## 8. Sound and picture

- The voice sets the clock. Visual hits are pinned to their words; a visual may lead the word slightly (the eye is faster than the ear) but should not trail it.
- The music sets the pulse. Cuts and the first syllable of every line land on the grid; music-only moves follow the beats. Let the energy of the motion follow the score's energy.
- Beat accents are seasoning: a dot, a glow or a cursor may pulse; whole layouts and text never do.
- Sound effects mark what matters: a transition, a counted item, the one big reveal. Not every element.

## 9. What holds on every probe

This is the floor, not the bar: it rules out broken output. Whether the video is good is described in [craft.md](craft.md). `gaga still` measures the text items on its probes (edges, caption band, size on a phone, contrast) and draws a few probes again in a fresh page to prove they repeat, and `gaga check` the motion and flashing over every frame; both only point at moments, and the eye decides.
- [ ] One clear focal point in every probe frame; nothing overlaps by accident; no text in the caption zone.
- [ ] Every word on screen is readable at the probe's size and holds long enough to read.
- [ ] At 390 px wide (`gaga still --phone`) the subject and every word to be read are whole inside the frame; only supporting shapes run off the edge.
- [ ] Visual hits land on their spoken words (check the `when()` targets).
- [ ] Nothing internal on screen: no "Scene 1", "Option A", preset names, placeholders or file names.
- [ ] Secondary elements leave before the cut; nothing pops off abruptly.
- [ ] The middle probe of each scene shows motion in progress.
- [ ] The last frame is a resolved still held ≥ 1 s.
- [ ] Fonts loaded (no fallback warning); CJK line breaks are clean.
- [ ] No more than 3 flashes per second and no big full-screen luminance flicker (photosensitivity).
