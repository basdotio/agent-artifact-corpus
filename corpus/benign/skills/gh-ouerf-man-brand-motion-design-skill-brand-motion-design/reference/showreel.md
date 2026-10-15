# The showreel cut: the default register

Every film this skill makes is a **showreel cut** unless the user explicitly asks for a calm explainer: fast, 3D, a new picture on almost every beat, giant type, colour flips, one showpiece per scene, cut to a beat. Do not ask "calm or fast?". Fast is the answer. The brand decides how it looks; the showreel decides how it moves.

| | Showreel (default) | Explainer (only when asked for "calm", "tutorial", "walkthrough") |
|---|---|---|
| Length | 12 to 25 s (social), up to 40 s (launch) | 30 to 90 s |
| New picture | every 2 beats; a scene is 1 to 2 bars | every 2 to 4 bars |
| Tempo | 135 to 150 BPM trap for a young audience (`synth.py --style trap`), 120 to 128 punchy otherwise | the song's |
| 3D | at least half the scenes are Three.js, lit and bloomed | optional |
| Words | 1 to 3 giant words at a time, under 20 in the film | punchlines and captions |
| Backgrounds | a full-bleed colour flip on every scene, from the brand palette | the product's one background |
| Transitions | the transition is the show: floods, irises, blinds, whips, hard cuts on the downbeat | magic moves, fades |
| Chrome | a viewfinder HUD: corner brackets, chapter label `01 — NAME`, timecode | none |

A showreel still looks like the product. The difference is energy, not taste: every effect is made from something the brand owns (its mark, its colours, its type, its subject). A generic lens flare reads as a template; the brand's dot flooding the frame reads as the brand.

## Why a first pass comes out flat (and how the good ones differ)

Two films built from the same brand can look years apart. What separated a flat first cut from a showreel the owner loved was never the engine (HyperFrames and Remotion render the same pixels); it was these, in order of impact:

1. **Light.** Flat colour on flat colour looks like a slide. Lit, glossy objects with an environment map, a strong key light and bloom on one emissive highlight look like a render. This is the single biggest jump.
2. **Material.** Clearcoat plastic, glass, satin, soft metal: surfaces that catch highlights. `PF.three.mat("gloss" | "glass" | "satin" | "metal" | "glow", hex)`.
3. **Depth.** Fog towards the background colour, particles in front of and behind the subject, a camera that drifts on every shot.
4. **Scale contrast.** Giant words (250 to 300 px at 1080 wide, condensed, uppercase for Latin) against small precise HUD labels (22 px, tracked).
5. **Cadence.** A cut or hit on every beat, the camera re-framing every 2 beats, a half beat of silence before the drop.
6. **Brand constraints read as permission, not as a ceiling.** A brand book written for UI ("restraint, no blur, one highlight") is right for the app and wrong for a Reel. Treat the video as a **brand moment**: what bends is pace, light, depth and transitions; what never bends is the palette, the logo files, the fonts, the voice, the claims and correctness. Write that split in `BRAND.md` under "Brand moment" and tell the user in one line; ask only if the brand book explicitly forbids motion effects in video.

## The shape (about 20 s at 140 BPM, 12 bars)

This is the shape for a product that fixes a problem (a launch or a feature spotlight). Promos, teasers, events, social proof, before/afters and product showcases have their own chapters in [video-types.md](video-types.md); the pacing, the 3D recipe and the rules below apply to all of them.

| Bars | Part | What happens |
|---|---|---|
| 1 to 2 | **Cold open + hook** | Something already moving in frame 1 (a lit curve racing through space, the brand's mark landing). Two giant words slam on beats 1 and 2 of bar 2 over a wide shot. |
| 3 to 4 | **The problem, as a picture** | The user's material in 3D (a sheet of work, a UI card, a dashboard) under a moving camera; the flaw gets the brand's highlight. Headline over the wide shot, then a close shot on the flaw. |
| 5 to 6 | **The drop: what the product does** | The showpiece: a generative 3D moment built from the subject (a field of columns, particles forming the product's chart). The highlight rises, bloom hits, one shake. Everything the viewer must remember is here. |
| 7 to 8 | **The fix / the result** | The same material, corrected; a check lands; a sticker slams. Colour flips to the other half of the palette. |
| 9 to 10 | **The payoff** | The outcome as a feeling: a curve rising, stickers from the brand pack, a second language if the brand speaks one. |
| 11 to 12 + 1 s | **The lockup** | Particles or the highlight converge into the logo, the official build plays, the tagline holds 1.5 s or more. |

Say the product loop plainly across those parts in three short statements (see [story.md](story.md)).

## The 3D recipe (what made the rich version rich)

```js
// setup(): one stage, one scene per chapter
st = PF.three.stage($("#three"), { width: W, height: H, fov: 50, env: true,
  bloom: { strength: 0.9, radius: 0.6, threshold: 1.0 }, exposure: 0.95 });
const s = st.newScene();
s.background = new st.THREE.Color(BRAND.bg);
s.fog = new st.THREE.Fog(BRAND.bg, 7, 30);      // depth, towards the background colour
s.environmentIntensity = 0.55;                   // reflections without washing out
PF.three.lights(st, { scene: s, key: 1.6, fill: 0.5, keyPos: [-4, 8, 6] });
const curve = PF.three.tube(st, points, { radius: 0.14, material: PF.three.mat("gloss", "#FFFFFF"), scene: s });
const point = new st.THREE.Mesh(new st.THREE.SphereGeometry(0.26, 48, 32), PF.three.mat("glow", BRAND.accent));
const dust = PF.three.particles(st, 700, { scene: s, size: 0.06, pos: (i, t, o) => { /* from t */ } });
// draw(t)
st.use(s); curve.draw(p); dust.update(t);
PF.three.shots(st.camera, t, [
  { at: b(1, 1), azimuth: -30, elevation: 12, radius: 9, target: [0, 1, 0], drift: { azimuth: 10, radius: -1 } },
  { at: b(1, 3), azimuth: 20, elevation: 8, radius: 4, target: head, drift: { azimuth: -6 } },
]);
st.render();
```

- **Bloom only on the highlight.** Threshold 1.0 or more, and only the `glow` material (emissive above 1) crosses it. A threshold under 1 blooms the whole bright scene into milk.
- **Environment, not more lights.** `env: true` gives glossy surfaces something to reflect; keep `environmentIntensity` around 0.5 and exposure just under 1, or every colour drifts to pastel.
- **Exact brand colours stay exact.** Anything that must read as the brand swatch (a sheet of paper, a sticker, a UI card) is unlit: `MeshBasicMaterial` with `toneMapped = false`, or `PF.three.card(st, tex, w)` (unlit by default). Lit materials are for the objects that should shine.
- **Colour ramps inside the palette.** `PF.three.ramp([darkest, main, lightest])(u)` (three brand hexes) for fields and particles, so depth reads without inventing colours.
- **9:16 is narrow.** A 50 degree vertical fov gives about 30 degrees across. Scale the subject in x or pull the camera back, then check a still. A camera that looks "away" from the subject in a still means the target is behind the drawn part: put the camera ahead of the draw head, looking back.
- **Camera: cuts, not one long orbit.** A new shot every 2 beats (`PF.three.shots`), each with a small drift, reads as an edit and costs nothing.
- **Headlines only over wide shots.** A giant word over a close shot of detailed material is two things fighting. Slam the words over a wide shot (subject low in frame, clean colour on top), then cut to the close shot when the words leave. If the subject must sit under words, put a gradient scrim of the background colour behind the headline band (`data-layout-ignore`).
- **Words and stickers in the DOM, over the canvas.** Crisp at any size, measurable by `check`. 3D stickers (`PF.three.sticker`) only for stickers that must turn with the camera.
- **Every scene has a showpiece with internal motion:** a tube drawing itself, columns settling onto a function, a ball riding a curve, particles converging. A static object under a moving camera is a slideshow.
- **Make the 3D mean something.** The field of columns settles into the product's own function; the particles become the logo. 3D that turns into the subject is the showpiece; 3D that only decorates is noise.
- **Deterministic:** everything from `t`, `PF.random(seed)` for scatter, pixel ratio 1, render with `st.render()` inside `draw(t)`. Keep instances in the low thousands; no shadows; no effects that need previous frames (no TAA, no afterimage).

## Techniques (`kit/fx.js`, `kit/three.js`)

| Move | How | Notes |
|---|---|---|
| Flood | `PF.flood(el, p, "up")`, or an `inset()` clip from a line outward | Wipe the next scene's colour in from an element (the line the dot became) |
| Iris | `PF.iris(el, p, x, y, W, H)` | Through the brand's mark: the dot, a logo counter, a check |
| Blinds | `PF.blinds(bands, t, start)` | 6 to 10 bands of the next colour, staggered 30 ms |
| Whip | two scenes stacked, translate by a frame on `PF.bezier(0.75, 0, 0.15, 1)` in 0.35 to 0.4 s | Motion blur in the final render sells it |
| Slam | `PF.slam(t, at)` + `PF.slamStyle` | From 1.2 to 1.7x, blurred to sharp, in about 0.22 s; a thud on the frame |
| Shockwave | `PF.ring(t, at)` | One per landing, never looping |
| Shake | `PF.shake(t, hits)` on a camera wrapper | 8 to 20 px; the HUD does not shake |
| Word wall | `PF.wordWall(parent, word)` | Outline text at 10 to 15% contrast behind the hook |
| Particles | `PF.three.particles` (3D) or `PF.swarm` (2D canvas) | Targets from `PF.three.samplePoints(paint, n)`: draw the logo or chart into a canvas, sample it, converge |
| Real 3D | `PF.three.stage/newScene/use/shots/tube/field/card/sticker/particles/mat/ramp` | See the recipe above |
| Viewfinder | `PF.hud(parent, {...})` + `PF.timecode(t)` | Chapter label per scene; colour follows the background (`hud.color`) |
| Grain, vignette | `PF.grain(canvas, t, { alpha })`, `PF.vignette()` | Strength is the element's opacity |
| Motion blur | `render.mjs --blur 4` (240 fps master) | Free realism on every slam, whip and camera cut |

## Less text

Say it with a picture first. The highlight landing on the broken step beats "here is the problem"; a check beats "verified"; the price tag flipping to the offer beats "now cheaper" (then keep the one word if it lands harder). One to three words on screen at a time, under twenty in the whole cut, and still readable: a word holds at least 3 beats.

## Pacing rules

- A new picture at least every bar, a new element on every beat, a camera re-frame every 2 beats inside 3D scenes. The drop is the busiest frame of the film.
- Alternate light and dark scenes; never two scenes in a row on the same colour.
- One breath: half a beat of silence (`--gaps`) before the drop.
- A Reel loops: end on the downbeat after the last bar, so the loop lands on the beat.
- Keep all words inside the platform's safe zone even when the picture bleeds.

## Review

- `hyperframes check` reports decorative layers (HUD, word wall, grain, scrims) as overlapping or low-contrast text: mark them `data-layout-ignore`; mark the full-bleed 3D canvas `data-layout-allow-overflow`; mark intentionally stacked headline lines (tight leading) `data-layout-allow-overlap`. Everything else it reports is real: fix it.
- Stills at every scene's wide shot and close shot: the headline must sit on clean colour, the close shot must frame the whole line or object it is about.
- The draft contact sheet should show a different picture in almost every tile, and at most one long hold, at the end.
- Stickers sit above the HUD's bottom row, never under it: the HUD is drawn on top and its labels cut through a sticker.
- Stickers use the brand's pack phrases whole; a truncated phrase can turn into a claim ("100% natural" cut from "100% natural ingredients, no additives" still reads fine; "100% results" cut from "100% results-focused coaching" reads as a guarantee).
- A "resolved" mark (a check, a tick) goes on the corrected result, not on the line that was wrong, or the film says the mistake was right.
