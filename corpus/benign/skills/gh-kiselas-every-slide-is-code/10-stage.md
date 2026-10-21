# Stage: a world behind the slides

The stage is one canvas behind every slide. It is drawn every frame from the camera position, so it can make the deck feel like one continuous place instead of a stack of pages: paper that feeds past, a map that pans, a grid that recedes, light that shifts between chapters.

```js
Deck.stage({
  setup(ctx, { W, H, deck }) { /* once: build patterns, textures */ },
  draw(ctx, S) {
    // S = { W, H, T, rest, cam: {x, y, s}, i, from, to, p, slides: [{x, y, s}, …] }
  },
});
```

| Field | Meaning |
|---|---|
| `S.cam` | camera in world units (slide widths / heights): top-left `x, y` and scale `s` |
| `S.slides` | every slide's `data-pos`, to draw things at slide positions |
| `S.i` | current slide index; fractional during a transition |
| `S.T` | global clock; `S.rest` is true in exports. Reading it makes the stage animated (see the performance rule below); with `ambient: fps` on the stage spec it is rounded down to 1/fps |
| `S.p` | progress of the current transition, 1 when none is running |

During a `camera` transition, `cam` moves with the flight. During any other transition it sits at the destination, so the background does not slide under slides that are not moving.

## World to screen

```js
const k = 1 / S.cam.s;
const toScreen = (wx, wy) => [(wx - S.cam.x) * k * S.W, (wy - S.cam.y) * k * S.H];
```

A slide at `data-pos="0 1.12"` has its top-left at world `(0, 1.12)`. Draw what belongs to that slide at `toScreen(0, 1.12)` scaled by `k`.

## Recipes

**Paper grain that moves with the world.** Build a small seeded noise tile once, make it a pattern, and offset the pattern by the camera. Also give the tile to `--dk-card`, so opaque transitions (`tear`, `cover`) carry the same texture.

```js
setup(ctx, { deck }) {
  const n = 220, cv = document.createElement('canvas'); cv.width = cv.height = n;
  const g = cv.getContext('2d'), img = g.createImageData(n, n), r = Deck.rng(42);
  for (let i = 0; i < n * n; i++) { const v = r(); img.data[i * 4 + 3] = v > .97 ? 16 : v > .75 ? 6 : 0; }
  g.putImageData(img, 0, 0);
  grain = ctx.createPattern(cv, 'repeat');
  deck.style.setProperty('--dk-card', `#f2eee5 url(${cv.toDataURL()})`);
},
draw(ctx, { W, H, cam }) {
  ctx.fillStyle = '#f2eee5'; ctx.fillRect(0, 0, W, H);
  ctx.save(); ctx.translate(-(cam.x * W / cam.s) % 220, -(cam.y * H / cam.s) % 220);
  ctx.fillStyle = grain; ctx.fillRect(-220, -220, W + 440, H + 440); ctx.restore();
}
```

**Marks between slides.** Draw something in the gap between slide positions (a dashed cut line, a chapter label, a fold). It is off-screen at rest and passes through the frame during a camera flight, which is what makes the flight read as travel. The demo draws a cut line under each slide and a small ticket number in the left margin.

**Parallax.** Draw a far layer offset by `cam * 0.3` and a near one by `cam * 1.4`: a grid, contour lines, a skyline. Keep it low-contrast; it must never compete with the slide.

**Chapter light.** Interpolate the background colour or a large soft gradient by `S.i`, so each chapter has its own tone and the change happens during the transition.

**Grain, vignette, chapter light with `Deck.fx`.** `Deck.fx` is a set of opt-in helpers (01-runtime.md lists them); none of it runs until you call it. This is the stage of the showcase deck:

```js
const grain = Deck.fx.grain({ fps: 18 });                    // 12..24 tiles per second, pre-rendered from a seed
const CHAPTER = ['#e8b04a', '#ff5a1f', /* one colour per slide */];
let live = [], base;
Deck.stage({
  ambient: grain.fps,                                        // redraw at most 18 times a second, with T rounded to that grid
  setup(ctx, { W, H, deck }) {
    live = [...deck.querySelectorAll('.slide')].map(s => s.dataset.grain === 'live');
    grain.warm();                                            // build the tiles now, not on the first transition frame
    base = document.createElement('canvas'); base.width = W; base.height = H;
    const b = base.getContext('2d'); b.fillStyle = '#15130f'; b.fillRect(0, 0, W, H);
    Deck.fx.vignette(b, { W, H }, { strength: .34, inner: .45 });   // colour and corners never change: bake them once
  },
  draw(ctx, S) {
    ctx.drawImage(base, 0, 0, S.W, S.H);
    const i0 = Math.floor(S.i);                              // chapter light: cross-fade to the next colour while the camera moves
    Deck.fx.glow(ctx, S.W * .84, S.H * .12, 700, CHAPTER[i0], { a: .16, core: .5, to: CHAPTER[Math.min(CHAPTER.length - 1, i0 + 1)], t: S.i - i0 });
    grain.draw(ctx, S, .09, S.p < 1 || live[Math.round(S.i)]);   // alive in transitions and on data-grain="live" slides, frozen elsewhere
  },
});
```

- **Grain** is tiles of black and white specks with random alpha, so it works on dark and light backgrounds; it is drawn with `drawImage` (a pattern fill of the whole canvas costs 5-10x more in a software canvas). `S.rest` (every export: PDF, PPTX, the sheet) gets the frozen first tile, so exports are canonical; the video timeline gets the tile of each frame's time, so a video is exact. It sits behind the slides, so it tints the background, not the content.
- **Vignette** is one small gradient stretched over the canvas; bake it with the background as above, or call `fx.vignette(ctx, S)` per frame.
- **Glow** is a sprite cached by look, never by time. Colours are quantized to 16 levels per channel for the cache key, so an animated tint cannot flood the cache; cross-fade two colours with `to` and `t` instead. Draw a hundred of them if you want; nothing is blurred per call.
- **Line boil on a diagram**: in the slide's `frame`, jitter the points with `Deck.fx.boil.pts(points, seed, T, amp, fps)` (new jitter 10 times a second; with `T = st.rest ? 0 : st.T` it is frozen in exports) and set `ambient: 10` on the slide spec, so it is redrawn 10 times a second and not 60. Try amplitude 2-4 px on a 1920 canvas; more looks like a fault, not a hand.
- **Noise** (`Deck.fx.noise(seed)`: `n`, `fbm`) for the rest: jitter that varies smoothly, clouds, a wobbly baseline.

**The performance rule.** If the stage reads `S.T`, the deck redraws the stage every frame. `ambient: fps` caps that (the stage sees `T` rounded down to 1/fps), and the slide and the stage idle independently: a still slide is not re-rendered while grain ticks. But an animated background costs a full-canvas draw 18 times a second for as long as it is visible, on a battery. So grain must be optional, and the deck must be able to be still:

- keep it frozen (`live = false`) on ordinary slides and let it move during transitions and on one or two slides that want tension, as above; then every other slide goes idle (`?perf` shows "idle", drawn 0/s);
- `?nograin` (or `grain.enabled = false`) removes it altogether, and a slide with no other ambient motion is idle;
- with the grain frozen `grain.draw` does not read `S.T`, which is what lets the deck idle; do not read `S.T` elsewhere in the stage for decoration;
- measure with `node export/deck.mjs perf`: in a software canvas (headless) a full-canvas overlay costs several milliseconds; 2-3 full-canvas draws per frame is the most a stage should do.

## Rules

- The stage is atmosphere. At rest, it should be nearly invisible behind the content.
- No information on the stage that the slide needs: `check` does not see canvas text, and exports treat it as a picture.
- Deterministic: seeded noise, no `Math.random()`, ambient motion only from `S.T` and frozen when `S.rest`.
- Performance: a full-screen fill with a pattern and a few paths is cheap. Per-pixel work belongs in a pre-rendered tile or a WebGL shader.

## WebGL stage

For a shader background (flowing noise, a light field), create a WebGL canvas in `setup`, render it in `draw`, then `ctx.drawImage(glCanvas, 0, 0)` into the stage. Create the context with `preserveDrawingBuffer: true` so the PDF export can capture it.
