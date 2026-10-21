# Isometric figures (anatomy)

An isometric figure is a real, well-made machine drawn as solid parts under one fixed isometric camera, whose working *is* the idea: a pin-tumbler lock for a cache key, a gantry plotter for one GPU context serving many canvases, a dial gauge for a reading. It comes from the [anatomy](https://github.com/wheresryan22/anatomy) skill (MIT), whose geometry kit builds the parts as SVG path strings; `CV.iso` paints them onto the frame. It is a **Canvas** shot, not a third engine: the storyboard row says `2D·iso` ([three-d.md](three-d.md), *Canvas or three.js*).

[examples/iso-dial](../examples/iso-dial/video.html) is the anatomy kit's dial indicator rebuilt for video: a carriage slides gauge blocks under a plunger, the needle turns by the plunger's travel, the reading on screen comes from the same model, and the camera pushes in on the dial. 378 frames at 1080p render in about 9 s.

## When it is the right shot

Use it when **the explanation is a mechanism and the viewer should watch it work**:

- **The subject is a physical mechanism.** A watch escapement, a lock, a valve, a printer head, an engine stand. Show the real thing; this is the strongest case and needs no mapping.
- **An abstract system has a machine that maps one-to-one onto it** and stays true in the part that matters: a cache as a lock whose pins must all match, a rate limiter as a turnstile with a token hopper, a hash map's collisions as a rack of pigeonholes, a queue as a chute. Say in one sentence what moves and what that motion means. If the machine would have to be explained away at the turn, it is the wrong machine ([craft.md](craft.md), *When the video explains*: a metaphor only when it makes the idea more accurate).
- **The turn is "change one variable and watch what follows".** A knob turns, a block swaps, a load rises, and a needle, a counter or a part answers. That is exactly the shape of an explainer's turn, and the machine makes cause and effect visible.
- **The machine can be the video's one visual idea.** Built once, it carries 3–6 shots: established whole, the camera closes on the mechanism, the turn runs, an explode shows what is inside, and the landing returns to the wide shot read correctly. That is what pays for the build.
- **The tone is precise, technical, calm**: developer and engineering explainers, docs and product launches for technical tools, "how it works" pieces. It stands on nameable references: technical manuals and patent drawings, Linear-style product illustration, Teenage Engineering manuals.

Don't use it for:

- **Shots that are read or charted.** Type, quotes, lists, and charts whose positions must be exact (isometric foreshortens one axis): Canvas 2D.
- **A form the viewer learns by seeing it turn, a material read by light, a camera that travels through space**: three.js. The isometric camera never moves in depth; pushes, pans and an explode are what it does. Anatomy's own 3D mode is beta and slow, so leave turning to three.js.
- **Stories about people, feelings, places.** A machine at the centre of a personal story turns it into a manual.
- **A look it clashes with.** It is quiet, monochrome, hairline. Inside pop collage, ink wash or pixel art it reads as a second film. Blueprint is the neighbour: an orthographic line drawing that builds itself; the isometric figure is a solid object that works.
- **A one-shot cameo.** A Figure (40–80 parts) is 30–90 minutes of building. For one shot, a simpler Canvas drawing usually serves better.

## Scope

Size it the way anatomy does and record it in *Calls made*:

- **One machine per video**, Figure-sized (one mechanism, 40–80 parts). Build it once and shoot it many times; vary the framing and the state, not the object.
- **A Hero** (80–150 parts, pipes and round parts from `lathe.mjs` and `tube.mjs`) only when the machine is the whole video. Say so in the brief.
- **Never an Epic** (a whole vehicle or plant) inside a video.

## How to build one

Read the installed skill first (`~/.claude/skills/anatomy`, or `npx skills add wheresryan22/anatomy -g`): `SKILL.md` for the idea and the workflow, `references/craft.md` for the parts vocabulary, tones and painter's order, `references/kit.md` for the API, and the closest of its examples. Then follow its workflow through step 8 (truth first, invent the object, a parts list before geometry, plan the world, build geometry once, paint back to front) and replace step 9 with the video's motion below.

```html
<script src="video-gaga.js"></script>
<script type="module">
import * as k from 'https://cdn.jsdelivr.net/gh/wheresryan22/anatomy@dbf697a527bbf7d358668e1557cb1e35ff725d46/kit/iso-kit.mjs';
const iso = CV.iso({ paper: T.bg, ink: T.ink, lit: T.accent, weight: 1.4 });

// geometry ONCE, at the size the figure fills on screen
const P = k.fitProjection([...k.boxCorners(PLATE, -17, 0), [x, y, top]], 1500, 860, { pad: 30, azimuth: 42 });
const BASE = [
  (ctx) => iso.halo(ctx, k.haloOf(PLATE, -17, 12, P), { blur: 14, dy: 5 }),
  (ctx) => iso.solid(ctx, k.slabOf(PLATE, -12, 12, P, 8, 1.6), { tone: 'mid' }),
  (ctx) => iso.line(ctx, k.planOutline(k.insetPlan(PLATE, 5), 0, P), { tone: 'lo' }),
];
const PLUNGER = [(ctx) => iso.solid(ctx, k.cylinder(58, 0, 2.6, 0, 50, P, 20), { tone: 'hi', lit: true })];

CV.create({ /* … */ scenes: [{ id: 'bench', draw(ctx, s) {
  ctx.translate(OX, OY);
  BASE.forEach((f) => f(ctx));
  const [dx, dy] = k.axisVector(P, [0, 0, tipAt(s.t)]);   // a moving part: translate its prebuilt paths
  ctx.save(); ctx.translate(dx, dy); PLUNGER.forEach((f) => f(ctx)); ctx.restore();
  iso.line(ctx, needleAt(turnAt(s.t)), { tone: 'lit', width: 2.2 }); // a part that changes shape: rebuilt from t
} }] });
</script>
```

- **Import the kit from the pinned CDN**, like three.js (it works from `file://` and in the renderer). `lathe.mjs` and `tube.mjs` sit next to `iso-kit.mjs` at the same pin. Only the geometry modules are used; anatomy's page scripts, live loop and audit stay out of the composition.
- **Each part is a list of paint calls**, built once, so the list order is the painter's order. Repeated parts are sorted with `k.depthOf`; anything that wraps another part is split into a back half and a front half, exactly as in anatomy.
- **Moving parts are prebuilt at rest and translated** by `k.axisVector(P, move)`. A part whose shape changes (a needle turning, a coil compressing) is rebuilt from `t` every frame; one solid costs well under 0.1 ms.
- **The palette is the film's.** `CV.iso({ paper, ink, lit })` derives the kit's tones (`hi`, `mid`, `lo`, `faint`, the four side shades, the top, the halo) from the film's paper and ink; `lit` is the one part the viewer watches, so give it the film's accent. Override any tone with `tones: { … }`.
- **Lines keep their width on screen** however far the camera pushes in (`weight` in design px: 1.4–2 at 1080p), so a push to 3–4× shows more detail rather than thicker lines. Check it at phone size: the kit's hairline look on a dark ground loses contrast fast, so on a 9:16 social cut raise `weight` and the `lo`/`faint` tones, or use a light paper.

`CV.iso` returns `solid(ctx, paths, { tone, crease, halo, lit, flat, alpha })`, `line(ctx, d, { tone, dotted, dashed, width, alpha })`, `dots(ctx, points, { size, tone })`, `wire(ctx, from, to, { via, tone, ends })`, `halo(ctx, d, { blur, dy })`, `faded(ctx, [[d, alpha], …], style)` for `ribsOf`/`dotsOf` with `fade`, `tube(ctx, piece, { tone })` for a piece from `tubePieces`, and `tones` ([runtime-api.md](runtime-api.md)).

## Motion: anatomy's feel, the video's clock

Anatomy's figures step springs per frame, tour on a timer and wait for the pointer. A composition is a pure function of time, so the same feel is written differently:

- **Springs in closed form.** A part re-targeted at known moments is `CV.springTrack(t, [[t0, v0], [t1, v1], …], { ratio, hz })`. Anatomy's constants map over: its plunger (stiffness 420, damping 26) is about `{ ratio: 0.63, hz: 3.3 }`; its explode springs (64, 14.2) about `{ ratio: 0.89, hz: 1.3 }`.
- **A value that follows another moving part** (the plunger rides whatever block is under it) gets its targets by sampling the leader once at load, finding the moments the target changes, and springing through those keys (`examples/iso-dial`, `TIP_KEYS`). Never integrate across frames.
- **The idle tour becomes choreography.** The machine moves when the voice says so: `s.when('the second block')`, a step per beat with `s.onBeat(i)`. Keep it calm: one change at a time, then a hold long enough to read the result.
- **An explode** keeps anatomy's rules (one spring per assembly, staggered 35 ms in an order that lets nothing pass through anything, reversed on the way back), each spring a closed-form function of the scene's time.
- **One-shot events** (a click, a flash, a shake) use anatomy's envelopes on the event's age: `smooth(0, rise, age) · exp(−(age − rise) / fall)`. Its WebGL shaders don't come along; a glow or a spark is a 2D gradient registered to the same projection, or a three.js shot.

## Words around the figure

Anatomy keeps words out of the drawing, and so does the video: no labels, leader lines or balloons inside the figure. Readouts, terms and numbers are the film's 2D type beside or below it, computed from the same model that moves the parts, so the number on screen is the number the needle shows. Every such number goes into `SOURCES.md`. Anatomy's card (`Fig 1`, title, hint, readout) is a web convention: keep its readout as the video's anchor, drop the hint (nobody can hover a video), and use the title only when the look calls for a manual page.

## How you know it worked

- `gaga still --sheet` and `--phone`: the figure reads as one real machine at a glance, the subject and the one lit part are clear at 390 px wide, and the readout is large enough.
- The `repeat:` line is identical. A figure that drifts between pages has state between frames (a spring stepped per frame, a cache that changes the drawing).
- `gaga still --at` during each push and at full zoom, read like anatomy's 4× check: every line ends on something, no bare face or empty corner in what the camera now shows, and depth order is right where parts cross.
- Muted, the motion alone shows cause and effect: the control moves, then the result answers.
