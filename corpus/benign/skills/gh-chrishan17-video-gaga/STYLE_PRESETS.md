# Style presets

Thirteen worked examples of a named look. Each preset stands on references you can name (its **Stands on** line), and shows one way to build that look in code: a palette and type (`THEME`), drawing and motion helpers (`KIT`), transitions and a caption style. It never decides the content, the scene structure, the choreography, the pacing or the music; those come from the brief ([docs/craft.md](docs/craft.md)).

A preset is one option, not the starting point. The look of a video starts from the references this story calls for ([docs/craft.md](docs/craft.md), *Picture*): a work, a studio, a medium or an era you can name. When that is close to a preset, `gaga init <dir> --preset <slug>` copies its style and you change it; otherwise `gaga init <dir>` gives a blank project, and any preset's KIT can be borrowed into it. A reference the user gives outranks every preset.

Each preset also ships an example video in `presets/<slug>/video.html` (the `EXAMPLE` sections, scenes, narration and score). It shows the KIT in use. Treat it as documentation of the helpers, not as a template: your video should not resemble its structure.

| Mood | Presets to consider |
|---|---|
| premium, launch, impressive | Launch Keynote, Studio 3D, Swiss Kinetic |
| understand, learn, trust the numbers | Clear Explainer, Blueprint, Data Globe |
| story, history, essay, gravitas | Editorial, Ink Wash, Cinematic Film |
| calm, contemplative, Chinese culture | Ink Wash |
| hype, social, loud | Pop Collage, Neon Circuit, Swiss Kinetic |
| warm, friendly, human | Paper Sketch, Pop Collage, Clear Explainer |
| playful, nostalgic, game-like | Pixel Retro, Pop Collage |

Native formats: most are 16:9; Swiss Kinetic is 1:1; Neon Circuit and Pop Collage are 9:16. Any of them can be re-laid out for another ratio (below). Studio 3D and Data Globe use three.js ([docs/three-d.md](docs/three-d.md)). Any look can mix engines: the engine is chosen per shot, and a 3D shot in a flat look is shaded to belong to it.

---

## 1. Launch Keynote — `launch-keynote`

<img src="docs/media/launch-keynote.jpg" width="480" alt="Launch Keynote">

- **Stands on:** Apple's product reveal films (one object turning in the dark, light doing the reveal); change the object and the light for the story, or it reads as every launch video.
- **Look:** a dark stage, one hero object, light as the storyteller. Calm confidence.
- **Suits:** launches, feature reveals, teasers, openers. **Avoid:** playful content, dense data.
- **Palette:** `#050506` stage · `#F5F5F7` ink · `#86868B` dim · one accent `#4D7CFF` (swap for the brand)
- **Type:** Geist 600/800 display, tight tracking · Geist 400/500 for quiet labels in sentence case
- **Motion character:** slow, weighty arrivals out of the dark; light does the revealing (sweeps, glows, a hairline that opens); earlier items recede as new ones speak.
- **KIT:** `sweepFill` (a specular sweep across type) · `hairline`
- **Transitions:** `split`, `push`, `zoomBlur`, hard match cuts
- **Captions:** small, boxed, low contrast

## 2. Studio 3D — `studio-3d`

<img src="docs/media/studio-3d.jpg" width="480" alt="Studio 3D">

- **Stands on:** ManvsMachine and Buck product films, a photographer's seamless sweep.
- **Look:** a coloured seamless studio sweep, one hero object, soft key and rim light. Tactile and quiet.
- **Suits:** products and hardware, packaging, "what's inside", colour-ways. **Avoid:** topics without an object, dense data.
- **Palette:** `#C9D5E0` → `#97A9BA` slate-blue sweep (pick the sweep against the product: the accent should pop off it) · `#111720` ink · `#4E5B69` dim · one accent `#FF5A1F` (swap for the brand)
- **Type:** Bricolage Grotesque 800/700, 500 for labels in sentence case
- **Motion character:** the camera does the work (arrive-push, slow orbit); 2D stays quiet while it moves; callouts track projected 3D points.
- **KIT:** `lathe`, `shadowed` (building the object) · `poseStage` (every pose from time) · `project` (3D → 2D) · `sweep` (the backdrop) · `callout`
- **Transitions:** camera-continuous cuts, `zoomBlur`, `flash`
- **Captions:** pale box, ink text
- **Surfaces:** a real studio HDRI (`polyhaven:studio_small_09`), a generated speckled-stoneware glaze (`gaga texture --prompt … --neutral`, tinted per colourway) and a scanned knit (`polyhaven:jersey_melange`); see `assets/CREDITS.md`.
- **Render tip:** a 3D frame costs ~4× a 2D frame; draft with `--scale 0.5 --format jpeg`.

## 3. Clear Explainer — `clear-explainer`

<img src="docs/media/clear-explainer.jpg" width="480" alt="Clear Explainer">

- **Stands on:** Vox explainers and The Economist's animated charts: annotated, highlighted, built while the voice reasons.
- **Look:** a well-edited explainer channel. Clean white stock, ink type, functional colour, a real highlighter.
- **Suits:** knowledge and science, finance and data, how-it-works, training. **Avoid:** luxury and mood pieces.
- **Palette:** `#FCFCFB` paper · `#16213A` ink · `#677086` muted · cobalt `#1F4FFF` = the point · green `#0E9F6E` = the evidence · highlighter `#FFD84D` behind ink type
- **Type:** Noto Sans SC 900/700/500/400, labels and axes in the same family
- **Motion character:** everything appears on the word that introduces it; diagrams build in reading and causal order; the camera follows what is growing.
- **KIT:** `pill` (a highlighter pill behind a key term)
- **Transitions:** `push`, `iris`
- **Captions:** ink box, paper text

## 4. Blueprint — `blueprint`

<img src="docs/media/blueprint.jpg" width="480" alt="Blueprint">

- **Stands on:** patent drawings and cyanotype engineering sheets, Animagraffs cutaways.
- **Look:** a cyanotype engineering drawing that builds itself, then runs. Precise and quietly impressive.
- **Suits:** mechanisms, hardware, architecture, technical onboarding. **Avoid:** emotional or lifestyle stories.
- **Palette:** `#0D3A66` cyanotype field with a 24 px grid · `#EAF4FF` object lines · `#8EC9F2` construction and dimensions · one signal `#FF8A1F` for the moving parts and the point
- **Type:** Barlow Condensed 700/600 · JetBrains Mono for labels, dimensions and the title block
- **Motion character:** drawn in a draftsman's order (construction lines, then outlines, then hatching and callouts); real kinematics when something moves; the camera pushes and pulls inside one continuous drawing.
- **KIT:** `sheet` (the drafting sheet) · `hatchIn` · `arrowHead` · `callout` · `zoomAbout` · `poly`, `rectPts`, `kicker`
- **Transitions:** hard cuts on the beat inside one drawing, a `wipe` with a cyan `lineColor` to a new sheet
- **Captions:** Barlow Condensed on a deep-navy box

## 5. Data Globe — `data-globe`

<img src="docs/media/data-globe.jpg" width="480" alt="Data Globe">

- **Stands on:** the Bloomberg and Reuters graphics desks, NASA's Earth at night.
- **Look:** a night-time world in motion. Cartographic and calm; the data glows warm against a cool world.
- **Suits:** "where in the world" data, rankings across places, trade, travel, networks. **Avoid:** single-location stories, dense text.
- **Palette:** `#06101D` navy · `#0A1A2D` ocean · `#A7BEDA` land dots · `#2F4B70` graticule · amber `#FFB547` = the data, only
- **Type:** Noto Serif SC 900/700 · Noto Sans SC 500/700 · IBM Plex Mono
- **Motion character:** the globe turns to each place as it is named (shortest path, continuous across cuts); arcs draw on with a bright head; 2D labels ride projected 3D points.
- **KIT:** `setGlobe`, `project`, `viewLerp`, `track` (globe pose, projection and camera moves) · `isLand` (land mask) · `backdrop`, `kicker`
- **Surfaces:** flat on purpose: the globe is a dot matrix and the data is emissive light, so it has no maps and no environment; a photographic Earth would fight the graphics-desk look.
- **Transitions:** beat-snapped cuts while the camera keeps moving, dissolves into a data panel
- **Captions:** navy box, light text

## 6. Editorial — `editorial`

<img src="docs/media/editorial.jpg" width="480" alt="Editorial">

- **Stands on:** The New York Times Magazine and The Pudding's scrolling stories.
- **Look:** a well-made magazine page that reads itself aloud. Measured, literate, quietly dramatic.
- **Suits:** history and documentary essays, journalism, culture and brand stories. **Avoid:** hype, dense dashboards.
- **Palette:** `#F8F8F6` white stock · `#111114` ink · `#676A73` muted · one ultramarine `#2436D9` (the key word, the mark, one full-bleed page) · tape `#E6E8EE`
- **Type:** Newsreader 800/600 + italic · IBM Plex Sans Condensed for datelines, labels and captions, in sentence case · Plex Mono only for the teletype
- **Motion character:** rules draw on, type is set by masked line reveals on the voice, images print in as halftone, a blue mark falls on the key word and the page turns blue once, at the turn; silence is part of the layout.
- **KIT:** `rule`, `label` (rules and datelines) · `set` (the type-setting ease) · `inkWash` (an ink-edged transition)
- **Transitions:** an ink-edged wipe (page turn), `inkWash`
- **Captions:** ink box, paper text

## 7. Paper Sketch — `paper-sketch`

<img src="docs/media/paper-sketch.jpg" width="480" alt="Paper Sketch">

- **Stands on:** RSA Animate whiteboard talks, a teacher's notebook drawn live.
- **Look:** someone drawing for you on paper. Warm, handmade, patient.
- **Suits:** education, habits, kids, onboarding, non-technical how-it-works. **Avoid:** premium tech, anything that must feel precise.
- **Palette:** `#F1E9D8` paper with fibres · `#2B2A28` pencil · marker `rgba(255,216,77,.75)` · watercolour red `#D1495B`, green `#4F8A4B`, blue `#3D6FB6`
- **Type:** ZCOOL KuaiLe titles · Long Cang handwriting · Caveat Latin notes · Noto Sans SC captions
- **Motion character:** strokes drawn in the order a hand draws them, lines that boil (animated on threes), washes after outlines, notes that clear the desk before the next page.
- **KIT:** `boil`, `pencil`, `line`, `circle`, `sketchCurve`, `wash` · `highlight`, `arrow`, `paper`, `handTimes` · `pageSlide`, `slide`, `clearDesk`
- **Transitions:** a custom page slide, one `ink` bloom, hard cuts on the same page
- **Captions:** cream paper box, ink text

## 8. Swiss Kinetic — `swiss-kinetic`

<img src="docs/media/swiss-kinetic.jpg" width="320" alt="Swiss Kinetic">

- **Stands on:** Josef Müller-Brockmann's Tonhalle concert posters, Experimental Jetset, Pentagram's kinetic identities.
- **Look:** International Typographic Style in motion. A grid, one red, type as image.
- **Suits:** quotes, manifestos, principles, titles, typographic stories (also long ones: see `examples/take-your-time`). **Avoid:** dense explanation.
- **Palette:** `#F2F0EB` paper · `#111111` ink · `#E62E2D` red, one red only
- **Type:** Archivo 900/700/500, huge display sizes, negative tracking, tracked-caps labels
- **Motion character:** snap easing `bezier(.7,0,.1,1)`; words slam up out of masks on the beat and drop back on the exit beat; hierarchy by subtraction (everything else recedes); match cuts between shapes; the music is the clock.
- **KIT:** `grid` (the 12-column grid) · `onB` (beat-snapped timing) · `label`
- **Transitions:** hard cuts on the beat, `blinds` along the grid's columns. No fades.
- **Captions:** none, or bottom-left in Archivo caps
- **Render tip:** `--motion-blur 5` for the snaps.

## 9. Neon Circuit — `neon-circuit`

<img src="docs/media/neon-circuit.jpg" width="220" alt="Neon Circuit">

- **Stands on:** Akira's Neo-Tokyo, Tron: Legacy's HUDs, an esports broadcast package.
- **Look:** night city, CRT and HUD. Energy with discipline.
- **Suits:** gaming, esports, dev tools, events, music drops, vertical social. **Avoid:** finance, healthcare, calm.
- **Palette:** `#07060D` violet-black · magenta `#FF2E88` = energy · cyan `#00E5FF` = information · `#EDEBFF` text · `#5B5875` dim
- **Type:** Chakra Petch 700/500 · ZCOOL QingKe HuangYou for Chinese display · Noto Sans SC 900 captions
- **Motion character:** hard and fast; RGB split fires only on a hit and decays within a few frames; neon tubes flicker on; the floor grid moves with the beat.
- **KIT:** `splitText` (RGB split) · `neon` · `city`, `skyline`, `floor` · `flicker`
- **Transitions:** short `glitch`, `whip`
- **Captions:** big, outlined, karaoke highlight in cyan, high enough to clear platform UI

## 10. Pop Collage — `pop-collage`

<img src="docs/media/pop-collage.jpg" width="220" alt="Pop Collage">

- **Stands on:** Matisse's cut-outs, Saul Bass's paper shapes, a zine pasted up by hand.
- **Look:** cut paper on flat primary colour. Loud, playful and still tidy.
- **Suits:** social shorts, tips, listicles, consumer brands, community. **Avoid:** luxury, serious or sensitive topics.
- **Palette:** `#FFC93C` yellow · `#FF5A36` red · `#2D5BFF` blue · `#FFF6E9` cream · `#1A1A1A` ink; each scene can own one field colour
- **Type:** ZCOOL KuaiLe · Noto Sans SC 900 · Unbounded 900 for numerals and Latin
- **Motion character:** every shape is a sticker (ink outline, hard offset shadow) that lands with a snappy spring; words land as they are said, never bouncy.
- **KIT:** `sticker`, `land` · shapes `circle`, `box`, `star`, `crescent`, `bookmark` · `squiggle`, `halftone`
- **Transitions:** palette `stripes`, `whip`
- **Captions:** big cream text with an ink stroke, karaoke highlight in yellow

## 11. Pixel Retro — `pixel-retro`

<img src="docs/media/pixel-retro.jpg" width="480" alt="Pixel Retro">

- **Stands on:** Super Famicom RPGs (Final Fantasy VI, Mother 2), Celeste.
- **Look:** an 8-bit console game played straight. Nostalgic, a little heroic, and able to carry a real feeling.
- **Suits:** milestones and year-in-review, games and indie dev, playful onboarding, kids, personal stories told as a quest. **Avoid:** luxury, finance, fine detail.
- **Palette:** 12 colours and nothing else: `#16122B` night · `#2C2554` shade · `#4B3F86` dusk · `#8C85BD` dim · `#FFF3D6` ink · `#5FA8E8` sky · `#57C98A` mint · `#2E8A5C` leaf · gold `#FFC93C` · coral `#F25F5C` · `#A3473A` rust · `#E8B07A` sand
- **Type:** Press Start 2P on its 8 px grid · Noto Sans SC 700 thresholded to 1-bit for Chinese
- **The device:** `pixelFrame` paints each scene on a low-resolution buffer, snaps it to the palette (optionally dithered) and scales it up, so anything drawn with the normal canvas API comes out as pixel art. Colour can tell the story: `mono` drains the frame, `keep` lets one colour survive, `reveal` + `inCircle` flood colour back, `zoom` punches the cells bigger.
- **Motion character:** whole cells and quantised steps, never eased glides; sprites animated on eighth notes; impacts on twos.
- **KIT:** `pixelFrame`, `reveal`, `inCircle` · `pixelText`, `blockText`, `wrapCells` · `sprite`, `cycle` (keep sprites big: 16×24 at scale 2–4) · `win`, `meter`, `prompt`, `dialogue`, `bubble`, `dots` · `steps`, `jump`, `hop`, `jolt`, `debris` · `tileWipe`
- **Transitions:** `tileWipe`, the runtime's `pixelate`, hard cuts on the beat
- **Captions:** Noto Sans SC on a square night box, like a game's text box
- **Render tip:** keep the grid size (`T.px`) a divisor of both sides. GIFs want 16 colours and no extra dithering.

## 12. Ink Wash — `ink-wash`

<img src="docs/media/ink-wash.jpg" width="480" alt="Ink Wash">

- **Stands on:** 上海美影的水墨动画（《小蝌蚪找妈妈》《山水情》）, 齐白石's shrimp, 八大山人's empty paper.
- **Look:** a Chinese ink painting (水墨) that paints itself on rice paper. Still, spacious, literate; empty paper is part of the picture.
- **Suits:** Chinese culture, poetry and philosophy, craft, festivals, reflective essays. **Avoid:** dense data, tech launches, hype.
- **Palette:** `#EEE7D7` rice paper · one cool ink `#141419` used at tones from 淡墨 to 浓墨 · `#F4EFE4` mist · one cinnabar `#B5342A` for the single thing that matters most
- **Type:** Ma Shan Zheng brush display in vertical columns, right to left · Noto Serif SC for labels and captions
- **Motion character:** ink seeps, blooms and soaks in; strokes press, run and lift into dry brush (飞白) and land on the beat; washes, mist and the camera move slowly and settle without overshoot; things leave by dissolving into mist.
- **KIT:** `xuan` (paper) · `seep`, `bloom`, `brush`, `wash`, `ridgeLine` · `mist` · `inkText` (calligraphy that soaks in) · `seal` · `penBrush` (a painted brush) · `scrollPan` (handscroll transition) · `spokenAt`, `startOf` (one painting growing across many scenes)
- **Transitions:** the handscroll pan, the runtime `ink` bloom, hard cuts when only the words change
- **Captions:** Noto Serif SC with a paper outline, low; or `captions: 'file'` when the line is already on screen as calligraphy

## 13. Cinematic Film — `cinematic-film`

<img src="docs/media/cinematic-film.jpg" width="480" alt="Cinematic Film">

- **Stands on:** Ken Burns documentaries, 16 mm home movies, Christopher Doyle's warm grades.
- **Look:** a documentary shot on film and projected in a dark room. Patient, warm, a little nostalgic.
- **Suits:** brand films, memoir and documentary, places and people, anniversaries, title sequences. **Avoid:** dense data, UI, anything that must feel crisp and digital.
- **Palette:** `#0B0A08` film black lifted to `#121A1B` teal · `#F1E6D0` cream titles · warm accent `#E3A257` · `#8A7F70` dim · a warm grade with red-orange halation
- **Type:** Noto Serif SC 500/600 · Cormorant Garamond in wide-tracked caps · Courier Prime for timecodes
- **Motion character:** every shot dollies slowly, never snaps; titles fade up out of focus and keep tracking open; rack focus; the film gate (weave, halation, flicker, dust, grain) over every frame.
- **KIT:** `filmGate`, `letterbox` (2.39:1 via `T.aspect`) · `dolly`, `zoomAt` (a push that keeps its point on screen) · `trackTitle`, `lowerThird`, `leader` · `frameAdvance`, `filmBurn`
- **Transitions:** long dissolves, `dip` to black, `frameAdvance`, one `filmBurn` for the turn. No pushes, wipes or whips.
- **Captions:** in the lower letterbox bar like a film print's subtitles
- **Render tip:** the gate touches every pixel, so draft with `--scale 0.5`.

---

## Custom styles

Most videos deserve a look of their own. Start by naming what it stands on: one or two specific references (上海美影《山水情》, a 1930s Shanghai calendar poster, Saul Bass's *Vertigo* titles, a two-drum riso zine, a PC-98 adventure game, Cartoon Saloon's *Wolfwalkers*). A name carries a whole set of rules at once (palette, line, texture, composition, how things move) that a list of adjectives never reaches. Then say what this video takes from them and what this story changes, and give it a visual thesis in one sentence ("a museum wall label that comes alive").

The name is where the look starts, not where it stops. Say what the reference is made of (cut paper and glue, ink soaking into rice paper, a riso print in two drums, light on a black stage) and how that material behaves: what comes first, what can't be undone, where it is imperfect, what it does when it moves. Then the craft follows from the medium, and so does what it is not: a riso print has no gradients, a pencil can't fade in. Take the reference's grammar, never its content, characters or logos.

A famous name can be the default in disguise: "Apple keynote" is near-black with one accent, "Kurzgesagt" is flat vector on navy, and every agent reaches for them. The more specific the reference (one film, one designer's period, one print process), the more the video looks like someone chose it. Direction ideas that differ only in colour are one idea; real alternatives stand on different references and differ in at least three of ground and light, type voice, where the motif comes from, camera language, transition vocabulary and rhythm.

## Another aspect ratio

`gaga init <dir> --preset <slug> --ratio 9:16` rewrites the size; re-lay out with `s.W`, `s.H` and `s.u`. Going vertical, stack rows, bring content toward the middle, raise type sizes relative to width and keep the lower 18% clear. Going square, use fewer items and bigger type. For the 3D presets also set the camera aspect and re-frame the hero.
