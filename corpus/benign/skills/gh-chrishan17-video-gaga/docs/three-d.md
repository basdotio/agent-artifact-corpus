# 3D with three.js

Canvas 2D and three.js are two engines in the same composition. Choose one **for each shot**, by what that shot has to show, and say which one in the storyboard. Most videos are mostly Canvas; a few shots earn depth.

## Canvas or three.js: decide per shot

Ask what the shot must show. It is a three.js shot when it needs one of these:

1. **A form that changes with the view.** The viewer learns the shape by seeing it turn: a product, a device, a building, a molecule.
2. **A material read by light.** Chrome, ceramic, glass, fabric, where a glint or a reflection is the point.
3. **Real depth order.** Parts that separate in depth (an exploded view, stacked layers, inside and outside), or occlusion that changes as the camera moves.
4. **A space to travel through or around.** A globe, terrain, a room, a city, where the camera move is the explanation.
5. **A value as the third dimension.** A bar city, a surface, columns whose heights are the data.
6. **Volume and weight.** A character or object that lands on a floor, squashes and casts a contact shadow.

It is a Canvas shot when it is:

- **read**: type, a number, a quote, a list, a caption;
- **a chart or diagram whose positions and values must be exact** (perspective distorts them);
- **UI, a screen or a document**;
- **a flat look** (Swiss, riso, paper, ink, pixel, Saul Bass). Parallax layers (`draw.camera` with `depth`), card flips, isometric drawings and a slight tilt are faked well in 2D and don't need three.js;
- **a mechanism seen working under a fixed camera**: an isometric machine whose moving parts are the explanation, built with the anatomy kit and painted by `CV.iso` ([iso-figures.md](iso-figures.md)). Its row says `2D·iso`. It becomes three.js only when the viewer must see the form turn;
- **drawn**: a line drawing on, a hand-made texture, an illustration.

Most 3D shots are really **both in one frame**: the three.js render composited over a 2D backdrop, primary type in 2D on top (crisp and caption-safe), labels riding projected points (`gl.project`), and Canvas painted onto 3D surfaces with `gl.texture` (a phone's screen, a card in space, a label on a box).

Tie-breakers:
- If a good Canvas version of the shot exists, use Canvas. It renders 2–4× faster, stays crisp, and is easier to keep readable.
- If the look stands on a flat reference, a 3D shot must belong to it (flat or toon shading, the same palette, an orthographic camera, the same grain) or stay 2D.
- Switch engines for a reason the viewer feels. A strong one is the turn of the story: the flat diagram lifts into depth when the viewer is let inside. Alternating every shot for variety reads as two films.

**One film, two engines.** The same palette hexes on both sides; the 3D backdrop is the same 2D paint as the Canvas scenes; light falls from the same side as any 2D shadows; one `overlay` (grain, vignette) over every scene; type is always 2D. Cuts across the seam carry something: a 3D object match-cuts to its flat icon at the same screen position (`gl.project` gives it), or the camera pushes into a 3D surface whose `gl.texture` is the next Canvas scene. Transitions between 2D and 3D scenes work like any other.

**Record it.** Each storyboard row names its engine (`2D`, `2D·iso`, `3D`, `3D+2D`) and the reason in a few words ([craft.md](craft.md), *The brief*). A 3D row also has its numbers in the brief (below). The choice is yours to make; it goes in *Calls made*, not into a question for the user.

## Why it fits the pipeline

- three is imported as an ES module from a pinned CDN (`three@0.186.1`). It works when `video.html` is opened from disk *and* in the headless renderer. There's no install and no build.
- Headless Chromium renders WebGL with SwiftShader. Frames are **pixel-identical across pages and render order** (the determinism test covers the 3D presets). Expect about 30 ms per 1080p frame for a simple lit scene, and 100–150 ms with shadows, physical materials and studio reflections.
- `CV.three()` shares one `WebGLRenderer` across all scenes, so a transition between two 3D scenes works and the WebGL context limit is never reached.

## The pattern

```html
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.min.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/"}}</script>
<script src="build/narration.js"></script>
<script src="video-gaga.js"></script>
<script type="module">
import * as THREE from 'three';
const { ease, clamp, lerp } = CV;
const W = 1920, H = 1080;
const gl = CV.three(THREE, { width: W, height: H, shadows: true, toneMapping: 'neutral', exposure: 0.9 });

// 1) Build the world ONCE: geometry, materials, lights, the environment.
//    The files come from the brief's environment and surfaces lines (Surfaces, below):
//      gaga asset <project> polyhaven:studio_small_09
//      gaga texture <project> --prompt "speckled stoneware, bone white" --name stoneware --seamless --neutral
const world = new THREE.Scene();
const cam = new THREE.PerspectiveCamera(30, W / H, 0.1, 100);
const ENV = 'assets/studio_small_09.hdr';
gl.hdri(ENV);                                    // starts loading; the renderer waits for it
const glaze = new THREE.MeshPhysicalMaterial({
  ...gl.pbr('assets/stoneware', { repeat: [6, 1], normalScale: 0.6 }),
  color: '#E6E0D4', roughness: 0.9, clearcoat: 0.55, clearcoatRoughness: 0.22,
});
const hero = new THREE.Mesh(new THREE.TorusKnotGeometry(1, 0.32, 240, 32), glaze);
world.add(hero);
const open = CV.spring({ ratio: 0.6, hz: 1.6 });

CV.create({
  width: W, height: H,
  scenes: [{
    id: 'hero',
    draw(ctx, s) {
      // 2) Every frame: set EVERY animated property from s.t (no deltas, no clocks)
      const p = ease.enter(clamp(s.t / 1.6));
      hero.rotation.set(0.3, lerp(-0.8, 0.4, p), 0);
      hero.scale.setScalar(lerp(0.9, 1, open(s.t - 0.4)));
      cam.position.set(0, 0.6, lerp(12, 9, p));
      cam.lookAt(0, 0, 0);
      world.environment = gl.hdri(ENV);
      // 3) Paint the 2D backdrop, composite the 3D, then draw 2D type on top
      ctx.fillStyle = '#E8E4DD'; ctx.fillRect(0, 0, W, H);
      gl.render(ctx, world, cam);
      ctx.font = '700 96px "Geist"'; ctx.fillStyle = '#111'; ctx.fillText('Orbit One', 160, 900);
    },
  }],
});
</script>
```

## Direct it in numbers

Adjectives get the default look: "premium, modern, cool" comes back as dark navy space, a glowing halo ring, bloom, particles and a spinning turntable. Every adjective replaced by a number is a decision taken back from the default. A 3D shot is directed by five lines, written into the brief before any code:

- **MODEL**, in real units (1 unit = 1 cm): the dimensions, the split lines, the bevels, the proportions that must not change. A character or a logo keeps its exact proportions (a pixel mascot is 14×10×8 voxels and stays so); that guardrail keeps it recognisable in 3D.
- **LOOK**: a material for every surface (table below) and, for a hero surface, its maps and where they come from (*Surfaces*), exact hexes, one accent on one part only, and the lights with colour, strength and position. The backdrop is the 2D paint behind it.
- **CAMERA**: the lens, where it starts and ends in azimuth, elevation and distance, and its one decisive move.
- **SHOTS**: what moves when, in seconds (or frames), with the spring or curve of each move.
- **BANNED**: the defaults, by name. After the first render, name the ones that appeared anyway and add them.

### Materials

| Surface | Material |
|---|---|
| satin ceramic, matte plastic | `MeshPhysicalMaterial` roughness 0.38, clearcoat 0.35, clearcoatRoughness 0.08 |
| toy plastic, voxels | roughness 0.45, clearcoat 0.3 |
| chrome, polished metal | metalness 1, roughness 0.05. It reflects the studio, so it needs dark and bright areas there, or it reads gray |
| brushed metal | metalness 1, roughness 0.3–0.4, `anisotropy` 0.5 |
| silicone, rubber | roughness 0.7–0.9, no clearcoat |
| a painted accent surface | roughness 0.7, `specularIntensity` 0.3, so grazing reflections don't wash the brand colour out |
| glass | `transmission` 1, roughness 0.05, ior 1.5, `thickness`. It costs an extra pass: probe its render time early |

These numbers set the overall material. On a hero surface the viewer is meant to touch, add maps over them (*Surfaces* below): the same glaze with speckles and pits in it reads as a real object, while the same glaze without maps reads as plastic.

### Light

A key, a fill and a rim, each with a role, plus the studio reflections:
- **Key**: warm (`#FFF4E8`, about 3), upper front, 28–45° high. Higher, and the top faces flood to white, so nothing on them (a glint, an edge) can read.
- **Fill**: cool (`#E8EEF5`, about 0.6), low on the other side. With the key off, the subject sits near 50% grey, so the key's arrival is felt.
- **Rim**: white (about 4), upper back on the side the camera sees, so it edges the silhouette.
- **Tone mapping**: `toneMapping: 'neutral'` keeps product and brand colours true. The default ACES darkens and shifts saturated colours (an orange reads salmon); keep it for filmic looks, and raise `exposure` when it renders dark.
- Contact shadow: a `ShadowMaterial` floor at opacity 0.2–0.55, or a baked soft ellipse.

### Camera

- Lens: 28–35° for a product, 35–50° for a scene, about 18° (telephoto) for a miniature or diorama, which flattens it into a toy.
- **It never parks.** Over a hold it drifts 10–30° in azimuth or creeps 2–4% in distance on the softest curve (`inOutSine`, `inOutCubic`).
- One decisive move per shot: a push-in on ease-out-expo (`ease.bezier(0.16, 1, 0.3, 1)`, about 0.8 s) on the beat it belongs to. Camera moves get the softest curves; objects get the snappier ones.
- A 3D camera move is the loudest motion on screen; keep 2D motion quiet while it moves.

### Banned in 3D, by name

A hero surface with no maps in a look that isn't flat (it reads as plastic), a hero lit only by `RoomEnvironment`, dark navy space, a glowing halo ring, bloom on everything, glow orbs, floating particles, neon, lens flares, a spinning turntable, a slow rotation as the only motion, a made-up tagline, purple or blue gradients. Bloom, when used, has a threshold of 1.0 and touches only emissive parts.

## A studio built in code: `gl.studio()`

Reflections are what make chrome read as chrome and ceramic as ceramic, and they come from the environment. A real HDRI (`gl.hdri`, *Surfaces* below) is the default; build a studio in code when the reflections themselves are directed: a glint that sweeps on the beat, a black flag that draws a band along a chrome edge. `RoomEnvironment` gives every object the same generic room. `gl.studio(spec)` builds a studio you direct: a dome (`sky` above the horizon, `ground` below) and panels placed in degrees around the subject: `az` 0 is the camera side, 90 the right, 180 behind; `el` 0 is the horizon, 90 overhead; `w × h` is the panel's size in degrees, with `intensity`, `color` and `tilt`. A black panel (intensity 0) is a flag: it puts a dark band on chrome. It returns a PMREM texture for `scene.environment` (or one material's `envMap`), built once and cached.

```js
const STUDIO = { sky: '#1e1d1c', ground: '#5a5753', panels: [
  { az: -40, el: 35, w: 40, h: 30, intensity: 4.5, color: '#FFF4E8' },  // key softbox, upper front left
  { az: 0, el: 90, w: 60, h: 60, intensity: 0.9 },                       // overhead
  { az: 140, el: 25, w: 12, h: 40, intensity: 2 },                       // rim strip, upper back right
  { az: 70, el: 5, w: 18, h: 50, intensity: 0, color: '#000' },          // black flag: a dark band on chrome
  { az: 180, el: 15, w: 140, h: 50, intensity: 1 },                      // white cyc behind, -10° to 40°
  { az: 0, el: -6, w: 160, h: 1.5, intensity: 1.5 },                     // horizon line on the camera side
] };
world.environment = gl.studio(STUDIO);   // or chrome.envMap = gl.studio(STUDIO) beside an HDRI
```

- Start dark: a dim dome (about `#202020`), so unlit sides fall off and chrome shows dark and bright bands. A bright dome turns everything into white plastic; a dark dome alone turns chrome black. Give chrome something to reflect: a `ground` lighter than the `sky` (the floor below its horizon), softboxes, a white cyc behind the subject for its edges (about 140° wide, 10° below the horizon to 40° up) and a thin horizon line on the camera side, because faces that look at the camera reflect the camera side.
- **A glint is a strip that sweeps.** Give the studio a narrow strip (2–5° wide, intensity 12–24) and move it as a function of `s.t`: calling `gl.studio({ ...STUDIO, panels: [...STUDIO.panels, strip], key: 'studio' })` every frame rebuilds it while the strip moves and reuses it while it doesn't. Assign the result to `scene.environment` every frame.
- **Aim it with `gl.mirror(normal, camera, point)`.** It returns the `{ az, el }` a panel must sit at for a surface with that normal to reflect it into the camera. A glint on a lid's top sits behind the subject at the camera's height; sweep the strip ±40° around that point.
- A strip that crosses the mirror direction of a big flat face floods the whole face (the glint becomes a light switch). Keep it narrow, raise it so only curved edges catch it, or end it short of the face.
- Cost: each rebuilt frame adds about 0.3 s at 1080p in SwiftShader, and `--motion-blur n` rebuilds it for every subframe (n×). Keep sweeps short (0.3–0.8 s), and render the rest of the shot with the studio cached.

## Surfaces: maps, real studios and models

**Every three.js shot has an environment, and every hero surface has a source.** Both are written in the brief's 3D line before any code (`environment {…} · surfaces {…}`, [craft.md](craft.md), *The brief*) and fetched or generated first, for any video and any look; a flat look writes `surfaces {flat on purpose}` and still says why.

Light alone gives every surface the same colour, the same relief and the same gloss from edge to edge, and that evenness is what reads as "a render". A real surface varies at a small scale: speckles in a glaze, the rows of a knit, the grain of wood, a worn edge that is smoother than the recess beside it. That variation comes from maps, and a hero object that is meant to be touched needs them.

| A surface that is… | Where it comes from |
|---|---|
| wood, stone, concrete, metal, leather, fabric, read close up | a **scanned** PBR set: `gaga asset find walnut` for an id, `gaga asset <project> polyhaven:<id>` (Poly Haven, CC0) → `gl.pbr('assets/<id>')` |
| one of a kind: a glaze, a print, paper, plaster, a hand-made or stylised finish | a **generated** albedo: `gaga texture <project> --prompt "<the surface>" --name <name> --seamless` (Codex CLI generates it, the maps are derived) → `gl.pbr('assets/<name>')` |
| a stylised look (clay, toon, lacquer, a flat reference) with no lighting to manage | a **matcap**: `gaga texture <project> --prompt "<the material>" --name <name> --matcap` → `new THREE.MeshMatcapMaterial({ matcap: gl.map('assets/<name>.png') })` |
| a label, a screen, a printed card | `gl.texture()` painted with the 2D API (type stays crisp), or a generated picture through `gl.map()` |
| flat on purpose (Swiss, toon) | numbers only, as in the table above |

Reflections come from the environment: `gl.hdri('assets/<id>.hdr')` puts a real photographed place around the object (`gaga asset find studio --type hdris`; `studio_small_09` is a soft, neutral product studio; an outdoor or interior HDRI when the object lives somewhere); `gl.studio()` is the one to use when you need to place a glint yourself. Both can be in one shot: the HDRI as `scene.environment`, the directed studio as the `envMap` of the chrome part. `scene.environmentRotation.y` turns the HDRI until its biggest softbox sits on the shoulder you want lit.

```js
gl.hdri('assets/studio_small_09.hdr');                 // starts the download; returns null until it is in
const glaze = new THREE.MeshPhysicalMaterial({
  ...gl.pbr('assets/stoneware', { repeat: [8, 2], normalScale: 0.6 }), // map, normalMap, roughnessMap, aoMap
  roughness: 0.9, clearcoat: 0.55, clearcoatRoughness: 0.22,          // a satin glaze over a rough body
});
const lamp = gl.model('assets/desk_lamp/desk_lamp.gltf', { shadows: true }); // a Group, filled before frame 1
world.add(lamp);
// in draw (or the pose function): world.environment = gl.hdri('assets/studio_small_09.hdr');
```

- **The API.** `gl.map(src, { color, repeat })` loads one image (colour maps are sRGB, data maps pass `color: false`). `gl.pbr(dir, { repeat, normalScale, metalness, ao })` loads a folder of `albedo.jpg normal.jpg roughness.jpg ao.jpg` (+ `metalness.jpg`) and returns the props to spread into a material; a roughness or metalness map multiplies the material's own value. `gl.hdri(src)` returns a PMREM environment. `gl.model(src)` returns a Group and fills it with the glTF; its clips are in `group.userData.animations`, played with `mixer.setTime(s.t)`, never `update(dt)`. The renderer waits for all of them, and a file that fails stops `gaga render` with its path, because a missing map renders as a plain surface without any error.
- **Generating an albedo.** Ask for the surface, not a picture of it: *"albedo (base colour) map of …, flat orthographic top-down view filling the frame, perfectly even diffuse lighting, no shadows, no highlights, no reflections, no vignette, no perspective, seamless tileable"*. `gaga texture <project> --prompt "<the surface>"` wraps your words in that request, has Codex CLI generate the picture (about a minute; its `image_generation` feature), keeps it in `build/generated/`, derives the maps into `assets/<name>/` and writes the prompt into `assets/CREDITS.md`. Without Codex, generate the same request with any image model (or photograph the real surface square-on in shade and add `--delight`) and run `gaga texture <image> --out <project>/assets/<name>`. Generation happens once, while building, and never at render time. Generation is never part of rendering. Then `gaga texture <image> --seamless` (the seams cross-fade away) and `--delight` when the picture still has shading baked in. Check the albedo before you use it: a highlight or a shadow in it will fight the scene's light.
- **Colourways.** A map multiplies `material.color`. `gaga texture --neutral` makes the albedo grey with a mean of 0.82, so the colour you set is the colour you see; `--only albedo --out <the set's folder>` does it to a scanned set's colour and keeps its scanned relief. After a swap, compare the lit product with its 2D swatch: a map plus a dimmer environment can darken it.
- **Scale and UVs.** Keep texels square: a lathe's U goes around (2πr long) and its V along the profile, so a body of radius 1 and profile 1.4 wants about `repeat: [8, 2]`. Look at the texture at video size: a knit or a grain that is finer than about 3 px turns into noise. Spheres and lathes pinch the map at their poles; keep a pole out of the hero angle, or cover it with a part (a cap, a button).
- **Strength.** Relief is the first thing to overdo. Start with `normalScale` 0.5–1 and `gaga texture --strength 2`, compare probe frames with the maps on and off, and stop at the setting where the surface reads as a material and not as sandpaper.
- **Cost.** 1k maps are right for a hero at 1080p (2k only when the object fills the frame), and a 1k HDRI is enough for reflections. Measured on Studio 3D (27 s at 1080p, 6 workers): a 1k HDRI plus two 1k PBR sets took the render from 227 s to 250 s (+10 % wall time, +26 % CPU). That is a small price for the look; shadows and transmission cost more (see *Why it fits the pipeline*).
- **What goes into git.** Every `gaga asset` and `gaga texture` run is recorded in `assets/assets.json` (the Poly Haven id, or the picture in `assets/src/` and the `gaga texture` flags, and the prompt). `assets/.gitignore` keeps only that file, `CREDITS.md` and `src/` (the pictures that can't be fetched again, a few hundred KB) and leaves out everything they rebuild. `gaga asset restore <project>` rebuilds it byte for byte, and `render`, `still` and `moodboard` restore what is missing before they start, so a fresh clone renders after one download (cached in `~/.cache/video-gaga/assets` for every project). A picture you add by hand goes through `gaga texture` too, or into the manifest yourself, or it won't survive a clone.
- **Preview.** `gaga still` and `gaga render` read assets from disk. A browser that opens `video.html` by double-click can't load them into WebGL; serve the folder instead (`python3 -m http.server`) to use the live preview.

## Animation principles on a 3D object, in numbers

Every principle can be written as sizes and frames (30 fps here):

- **Anticipation**: a small move against the main one, held briefly. A lid presses 1.5° shut while the case squashes 2%, holds 2–3 frames, then springs open. A character crouches for about 0.2 s to 1.2 × 0.75 before it jumps.
- **Squash and stretch, keeping the volume** (x × y × z ≈ 1): stretch to 0.85 × 1.28 at take-off, squash to 1.25 × 0.7 on landing, spring back at ratio 0.55. Shape changes; volume doesn't.
- **Overlapping action**: attached parts lag the body. Arms 2 frames, legs 3; the second of a pair starts 2 frames after the first and floats 2 frames behind it.
- **Follow-through**: attached parts settle on a looser spring than the hero (hero at ratio 0.7, the parts at 0.5; arms that must read as settling, 2.2 Hz at 0.22).
- **Arcs**: jumps, flips and pours travel along a curve, never a straight line.
- **Contact**: a part seats with a 0.05 magnetic dip and settles; a lid shuts on the beat, bounces 3° and is still 0.3 s later; the body recoils 1.5%.
- **Hierarchy**: one hero move at a time. Secondary moves travel 50–70% as far and start 0.1–0.2 s after it; ambient motion stays under 5% of the hero's travel, on a slow sine.
- **Exaggeration**: the feed shrinks everything, so push key poses 10–30% further than feels right.

**Springs by damping ratio.** `CV.spring({ ratio, hz })` takes the one number every library translates to: 1.0 never bounces (text, UI), 0.7–0.85 premium product motion, 0.4–0.6 playful and characters, under 0.3 a cartoon. Position, rotation and scale may bounce; opacity and colour never do. A spring that starts on the beat frame still shows the rest pose on that frame; start it half a frame early when the beat frame should already be moving.

## Checking a 3D shot

- **Probe early.** Light is the first thing that goes wrong; one `gaga still --at` frame tells you before the whole shot is built.
- **Strips around every state change.** 3–5 close probes (`--at 0.93,0.97,1.0,1.03,1.07`) around each hit, cut and handoff catch what a contact sheet hides: a bump that pops onto a shape in one frame (grow it in from below zero instead), letters that vanish before what replaces them exists, one extra held frame on a beat.
- **Surfaces on and off.** Probe one hero frame with its maps and once without (comment out the `...gl.pbr()`): the maps should make the surface read as its material at video size and on a phone, with no sandpaper, no visible tiling and no pinch in view, and its colour should still match the 2D swatches and palette.
- **Measure an effect by toggling it.** Render the same frame with the strip, light or effect on and off, and count the pixels that change. A few hundred means it doesn't read; most of a face means it floods.
- **Audit the numbers, not just the picture.** Every pose is a pure function of time, so the storyboard's numbers can be checked. Expose the pose (`window.audit = (t) => ({ lid: hinge.rotation.x, feet: foot.position.y })`), evaluate it at the pinned times in the page, and compare: the lid reaches 100° by 1.4 s, the feet touch the pad on the landing frame, each label lights on its frame.

## Rules

1. **Pure.** Set every animated property (positions, rotations, scales, material colours and opacities, light intensities, the studio, the camera) from `s.t` in every `draw`. Never accumulate (`mesh.rotation.y += 0.01`). Frames render out of order in parallel pages.
2. **Build once, animate by assignment.** Create geometries and materials at load time. If a scene needs many objects, create them all and toggle `visible`.
3. **No `Math.random()` and no `THREE.MathUtils.seededRandom` with global state.** Use `CV.rand(seed)` at build time.
4. **Text in 3D:** use `gl.texture(key, w, h, paint)` with the 2D API, so the video's webfonts are used and repainted once loaded. Keep primary type in 2D on top of the render. For extruded letters, `TextGeometry` (an add-on, with a typeface JSON from `examples/fonts`) takes **`depth`** in r186: a missing `depth` silently becomes 50, so letters meant to be 0.12 deep come out 50 deep. Older builds (r160) read `height` instead; whatever the version, name the parameter that version reads.
5. **Transparent by default.** The renderer clears to transparent, so paint the 2D background (gradients, paper, grid) first and composite the 3D on top. Set `world.background` only for full-bleed 3D. A pale backdrop gradient bands: keep the `overlay` grain on.
6. **Shadows cost.** `shadows: true` with a `2048` map is fine for one key light. Prefer a `ShadowMaterial` floor or a baked contact-shadow gradient over many shadow casters.
7. **Add-ons** (`RoomEnvironment`, `RoundedBoxGeometry`, `TextGeometry`, loaders, …) need the second import-map entry, `"three/addons/"`, as in the pattern above. `gl.hdri` and `gl.model` import their loaders through it. Load files through `gl.map`/`gl.pbr`/`gl.hdri`/`gl.model`, not a loader of your own: three's loaders `fetch()`, which can't read the `file://` pages the renderer opens, and the renderer doesn't know to wait for them.
8. **Layered transparency: set `renderOrder`.** three sorts transparent objects by bounding-sphere centre, which flips with orientation (an ocean shell can paint over point-cloud land that doesn't write depth). Give every transparent layer an explicit `renderOrder`.
9. **Glows on a transparent renderer: no `AdditiveBlending`.** It writes alpha = 1 and shows as a black halo over the 2D backdrop. Use premultiplied one/one `CustomBlending` with a shader that outputs `vec4(color * i, i)`.
10. **Budget render time.** A lit, shadowed hero scene with studio reflections costs about 2–4× a 2D scene. Draft at `--scale 0.5 --format jpeg`.

## Good uses

| Content | 3D device |
|---|---|
| Product / feature launch | hero object on a seamless sweep, a glint across it, anticipation and a spring on the opening, an arrive-push, an exploded view |
| Where in the world | globe with points and great-circle arcs, rotating to each place as it is named |
| Composition / architecture | stacked layers that separate on the word, each labelled in 2D |
| Comparisons at scale | bar city or columns whose heights grow from the data |
| A process with a character | a small figure hopping across a set that is the diagram, landing on each step |
| Abstract concept | one simple form transforming (sphere → many) as the idea changes |

The **Studio 3D** (`studio-3d`) and **Data Globe** (`data-globe`) presets are working references.
