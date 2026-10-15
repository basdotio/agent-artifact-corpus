# AiPas kit

For the authors of `stagesA.tsx` … `stagesE.tsx`. Everything below is exported from `./kit`. Edit only your own
stages file; `kit.tsx`, `blob.ts` and `AiPas.tsx` are shared.

1920×1080, 30 fps, 5007 frames. Beat sheet: `OneTake/storage/jobs/ai-pas-kurz/beats.md`. Motion rules:
`references/motion.md`, `references/illustrated-animation.md`.

## How a beat is mounted

- `AiPas.tsx` mounts exactly one beat at a time: beat n from `B[n].start` until `B[n].until` (the next beat's
  start). It passes `fr`, the composition frame.
- A beat draws in **world coordinates**. Paint order is JSX order. Sprites and UI are HTML, code-drawn shapes go
  inside `<Draw>` (an SVG layer in world coordinates).
- Every beat draws `<Residents t={fr} />` so the world stays inhabited. `hide` the creature you animate and draw
  it yourself. Idle motion depends only on the frame, so a creature at home hands over between beats without a
  jump. Anything else that crosses a beat boundary inside one file should share one module-level object (see
  `need` in `stagesA.tsx`).
- The camera is fixed per beat (table below). To nudge it on an impact, return screen pixels from your file's
  `nudgeA` … `nudgeE`.
- Whatever sits in the sea below `SEA` is behind the front water and shows through dimmed.
- Keep action above screen row `SAFE_Y` (960); the caption pill is below. `view(SHOT[n]).safe` is that row in
  world y.
- No `Math.random`, no `Date`: use remotion's `random(seed)`.

## Time

| Export | Use |
|---|---|
| `FPS`, `DURATION`, `f(seconds)` | 30, 5007, seconds → frame |
| `at(beat, word, nth = 0)` | Frame a spoken word starts on. Case and punctuation ignored: `at(4, "GPU")`, `at(9, "empat", 1)`. Throws if the beat has no such word. Every event goes on one of these, never a typed number |
| `B[n]` | `{ start, end, mid, until }` frames of beat n (1–15) |
| `beatAt(fr)` | The beat mounted at a frame |
| `WORDS` | The voice timings (`para` is the beat minus 1) |

## Motion

Re-exported from `../../motion`: `POP`, `SOFT`, `stagger`, `exit`, `breathe`, `depart`.

| Export | Use |
|---|---|
| `ramp(fr, a, b, ease = inOut)` | 0 → 1 between two frames |
| `sp(fr, start, cfg = POP)` | Spring `{ v, vel }` from a frame: arrivals |
| `punch(fr, E, wind = 12, back = 0.08)` | A big event in one curve: wind-up to `-back`, `HIT`-frame hold, release on E, one overshoot past 1, settle |
| `settle(seconds)` | Step response with one overshoot of about 13% |
| `bounce(fr, E, v, freq, decay)`, `decay(fr, E, rate)` | Inertial bounce and fade after an impulse |
| `vel2(path, fr)`, `stretchBy(speed)` | Velocity of a path; a `squash` value that stretches an actor along its travel |
| `arrive`, `inOut`, `clamp`, `lerp`, `mixC`, `HIT` (4) | Easings and small helpers |

## Palette and type

`C`: `ground` #141400, `deep`, `card`, `line`, `mute`, `ink`, `gold`, `coral`, `cream`, `sky`, plus set tints.
`KIND.cerdas | spesialis | ringan | besar` → `{ name, color }`. `FONT` is Geist (500, 700), `MONO` is Geist Mono
(500). On-screen text stays under six words per element.

## Creatures

Shared props (`ActorProps`): `x`, `y`, `t` (frame), `scale`, `squash` (above 0 flattens, below 0 stretches,
area kept), `tilt` (degrees, clockwise on screen), `opacity`, `flip`, `seed` (idle phase), `idle` (0 freezes
breathing and blinks for a hit-pause).

| Actor | Anchor (x, y) | Extra props | Notes |
|---|---|---|---|
| `Whale` | body centre | `swim` 0..1 | Art faces right; at home it is flipped to face the shore. `swim` rocks and stretches the body, which stands in for the tail |
| `Owl` | feet | | Faces the viewer. Head tilt is `tilt` |
| `Ant` | feet | `walk` 0..1 | Faces right. `walk` is a 4 Hz rock and hop in place of moving legs |
| `Eagle` | talons | `fly` 0..1, `flap` 0..1 | `fly` 0 perched sprite, 1 flying sprite, crossing over between 0.3 and 0.7: ramp it over 2–3 frames under a crouch-and-launch squash. `flap` (default `fly`) squashes the spread wings in a 3 Hz cycle; 0 glides |

All four blink. No wing, tail or leg is a separate part: flapping and stepping are whole-sprite cycles.

`HOME.ants[]`, `HOME.eagle`, `HOME.owl`, `HOME.whale` are the home poses (`<Owl {...HOME.owl} t={fr} />`).
`<Residents t hide? opacity? />` draws all four kinds at home.

## NeedBlob

```tsx
const need = blob({
  from: 0, to: B[3].start,          // frames simulated; held outside
  floor: GROUND,                    // optional: it flattens on this y
  path: (fr) => ({ x, y, r }),      // art-directed centre and radius; the jelly lags and overshoots it
  hits: [E],                        // optional: frozen for HIT frames before each
  kicks: [{ at, oval, lobe, angle }], // optional wobble impulses, px/s
  split: { at: E, wind: 28, axis: 0, gap: 1.25, to: [(fr, rest) => pt, (fr, rest) => pt] },
});
<NeedBlob sim={need} fr={fr} label="Laporan harian" />
```

- Call `blob` once at module level. The result is a pure function of frame.
- **Drop:** bring `path` down to `floor - r` on the event frame (`stagesA.tsx`). It squashes about a third,
  rebounds about 8% tall and is still within about 20 frames.
- **Roll:** move `path` along the ground and pass `spin` (degrees) to `NeedBlob`; the inner bubbles turn, the
  label stays upright.
- **Split:** `split.at` is the frame it becomes two. Before it: about 9 frames of squeeze the other way, `wind`
  frames of pinch, a `HIT`-frame hold. After it the halves spring to `gap` radii apart with one overshoot. `to`
  sends each half on from its resting place (left half first). Pass `label={[left, right]}` after the split
  (`stagesD.tsx`).
- `NeedBlob` props: `sim`, `fr`, `label`, `color`, `spin`, `opacity`, `glow`. Labels wrap to two lines.

## GPU

- `<GpuCube x y size? squash? glow? opacity? />`: one cube, anchored on its bottom corner.
- `<GpuPile x y count fr start? size? seed? glow? opacity? />`: a heap anchored at its base centre. With `start`
  the cubes drop in bottom row first and the whole pile lands within about 1.5 s; without it the pile is at rest.
  It draws at most `GPU_CAP` (120) cubes: for a mountain raise `size`, not `count`.
- `pileLayout(count, size, seed)` gives the cube positions, width and height, for draining or pouring a pile.

## People and UI

- `<Person who="rina" | "budi" | "dinda" x y t … happy? look? />`: anchor at the feet. Rina wears the gold scarf,
  Dinda is smaller. `happy` 0..1, `look` -1..1. `PersonHead` is the head alone.
- `<Card x y fr start? w? title sub? who? rows? tags? scale? opacity?>children</Card>`: anchor at the top centre.
  Springs open on `start`, shadow 4 frames behind; `rows` (`{ k, v, at? }`) and `tags` (`{ text, color?, at? }`)
  follow 5 frames apart or on their own `at` frame.
- `<Tag text color? size? x? y? fr? start? />`: a chip; inline, or centred on x, y. Pops on `start`.
- `<Label text x y color? size? align? fr? start? />`: small mono upper-case label.
- `<SpeechBubble x y text fr start? side? size? color? />`: x, y is the tail tip.
- `<Burst fr E seed n x y colors speed? size? life? arc? />` particles, `<Flash fr E x y r color? amp? />` light.
- `<Draw>` wraps your own SVG in world coordinates.

## World and anchors

One landscape, left to right, small to large. Land surface `GROUND` = 1000, waterline `SEA` = 1040, bank floor
`DESK_FLOOR` = 3900. The bank is a dark room below the landscape; the camera travels down to it.

| Anchor | World x, y | What is there |
|---|---|---|
| `P.trail0`, `P.trail1` | 220, 1000 · 1500, 1000 | Anthill and the end of the dotted trail |
| `P.ants` | 770, 1000 | Middle of the ant column (ants at x 440, 660, 880, 1100) |
| `P.perch` | 1750, 800 | Top of the eagle's perch |
| `P.branch` | 3000, 740 | Top of the owl's branch; trunk at x ≈ 3170 |
| `P.shore` | 3750, 1000 | Home shore; the server rack stands here. Land ends at x 4130 |
| `P.sea` | 5100, 1040 | The whale's home on the waterline |
| `P.far` | 5750, 380 | Sky across the sea: abroad |
| `P.wide` | 2950, -400 | Centre of the sky in the wide shot |
| `P.desk`, `P.rina` | 2450, 3900 · 2130, 3900 | Desk centre and Bu Rina's feet on the bank floor |
| `P.card`, `P.card2` | 3060, 3250 · 3720, 3250 | Top centres of the two cards |

Depth layers: stars and horizon glow, far hills, near hills, the playfield, foreground motes.

## Camera

`fit(x0, x1, floor, floorAt)` frames world x0..x1 with `floor` on a screen row. `SHOT[n]` is each beat's default.
`view(cam)` returns the world rectangle shown; `toScreen(cam, p)` maps a world point. The track is in
`AiPas.tsx` (`camAt`); each hold pushes in 3%.

| Beat | Shows world x | Zoom | Move into it |
|---|---|---|---|
| 1 | 3250–4650 (shore) | 1.37 | from frame 0 |
| 2 | 3350–5750 (shore and sea) | 0.80 | starts 4 frames before the beat, done 6 frames after "menyewa" |
| 3 | 100–5800 (everything) | 0.34 | starts on "bukan" in beat 2, done 14 frames into beat 3 |
| 4 | 40–1560, then 420–1940 | 1.26 | 34 frames from the beat's start; follows the column right from "semut" to "aturan" |
| 5 | 1200–2820 (perch) | 1.19 | −4 to +32 frames around the beat's start |
| 6 | 1210–2810 | 1.20 | 30 frames from the beat's start |
| 7 | 2150–3850 (branch) | 1.13 | −4 to +30 |
| 8 | 3600–6000 (sea) | 0.80 | −6 to +34 |
| 9 | 100–5800 | 0.34 | −6 to +30 |
| 10 | 1900–3700 (bank) | 1.07 | −4 to +40 |
| 11 | 1900–3700, then 1850–4130 | 0.84 | widens from "kasnya" to 4 frames before "Dinda" |
| 12, 13 | 100–5800 | 0.34 | starts 4 frames before beat 12, done 10 frames after "layar" |
| 14 | 3300–6000 (shore, sea, far sky) | 0.71 | −4 to +36 |
| 15 | 2970–4530 (shore) | 1.23 | starts 16 frames after "Indonesia", done 6 frames into beat 15 |

In the wide shot one screen pixel is about 3 world pixels: size text and props for it (a 28 px chip needs
`size={84}`).

## Checking your work

Stills only on this laptop, one at a time:

```
systemd-run --user --scope -p MemoryMax=4G -p MemorySwapMax=0 --quiet bash -c \
  'cd remotion && npx remotion still src/index.ts AiPas out.png --frame=N --scale=0.5'
```

Read motion from strips: every 2nd frame around each event.
