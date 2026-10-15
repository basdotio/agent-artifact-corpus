---
name: logo-intro
description: Build an animated WebGL logo intro from a brand's SVG logo. The mark arrives from a lens-warped, colour-fringed close-up, the wordmark pulls out of it, a gradient bloom grows, a lock-in beat (a badge pops, two parts snap together, inner layers rise, or the mark spins) sends out a ring, and a shimmer sweeps the logo. Outputs a single HTML file, an embeddable site splash, or an MP4/WebM video. Use when someone asks for a logo animation, brand intro, opening/splash animation for a website, an intro video like ElevenLabs', or to animate a specific company's logo.
---

# Logo intro

This folder is both the skill and the engine. Paths below are relative to it.

- `src/logo-intro.js`: the engine, one dependency-free ES module (`mountLogoIntro`).
- `src/controls.js`: preview playback bar.
- `scripts/build-html.mjs`: writes brand JSON to a single self-contained HTML page.
- `scripts/export-video.mjs`: renders frames in headless Chromium and encodes MP4/WebM with ffmpeg.
- `brands/*.json`: example brand configs. `references/brand-schema.md` documents every field.

## Workflow

### 1. Get the logo as SVG
Look in this order:
1. The site header's inline `<svg>` (for example `document.querySelector('a[href="/"] svg').outerHTML`) or `<img src="*.svg">`.
2. `/favicon.svg`.
3. The brand's press kit.
4. The largest PNG you can find: the header logo, a footer logo, the apple-touch icon, or a social profile avatar when the brand has no website.

Prefer the horizontal lockup, meaning the mark and the wordmark in one SVG. Read the file's text instead of downloading binaries. Fetch it in the page context (for example `fetch('/logo.svg').then(r => r.text())`).

**PNG-only logos.** Many sites ship only a PNG. Trace it:
1. Render the PNG large, at least 2000 px wide.
2. Classify each pixel to its nearest palette colour: the background, the letter colour, and each mark colour.
3. Run `potrace -b svg` on each colour mask.
4. Convert potrace's relative, flipped coordinates to absolute ones. The `<g>` has `translate(0,H) scale(0.1,-0.1)`, and the commands are `M m c l z`.

Rebuild simple geometry (circles, rings) analytically instead of tracing it. For layered fills inside a shape, extend each layer under the outer shape and let `mark.clip` cut the edge; traced edges leave hairline seams.

### 2. Split mark and letters
The brand config needs the symbol's paths and, for a path wordmark, one entry per letter.

- **Split subpaths at absolute `M` commands.** Once a path uses relative `m` after `z`, splitting changes its meaning. Convert it to absolute first, or keep that path whole as one letter group.
- **Keep counters with their letter.** An `o`, `p`, `a` or `e` is an outline plus a hole. Put both `d` strings in the same letter array (`["M…outline", "M…counter"]`); the engine joins them into one path. If you split them apart, the hole paints solid.
- **Group subpaths into letters** by x-overlap of their bounding boxes; `getBBox()` in a browser is easiest. Letters go left to right. Some fonts draw `n`, `d` or `h` as a stem plus an arch that barely overlap. Use a low overlap threshold (about 20% of the narrower box), then check that the letter count matches the word.
- **Find the mark.** It is usually the group on one side of a clear gap, most often on the left. When it sits to the right of the wordmark, the engine notices and pulls the letters out leftwards. If it has two interlocking or mirrored parts, give them `"part": 0` and `"part": 1` so they can use the `assemble` lock-in.
- **When there is no outlined wordmark** (logo is only a symbol plus live text), use a text wordmark: `"text"` plus a Google Fonts family, weight and letter-spacing.

### 3. Pick the theme
Read the site's CSS (body background, logo colour, primary button colour).

- `background`: the brand's page ground (dark brands stay dark).
- `ink`: the logo colour on that ground.
- `bloom`: five colours.
  - Slot 1 is the brand accent and carries the most weight.
  - Slots 2 to 4 are analogous colours.
  - Slot 5 is a complementary colour with a small weight.
- `bloomOpacity`: about 0.88 on light grounds, 0.72 to 0.8 on dark ones.
- `shimmer`: leave it at the default violet, cyan and pink unless the brand has its own iridescent palette.

### 4. Choose the lock-in
| Logo | `lockIn` |
|---|---|
| Mark sits on a shape (rounded square, circle) | `{ "type": "badge" }` plus `mark.badge` |
| Mark has two parts that interlock, like links, rings or hooks | `{ "type": "assemble", "direction": [dx, dy], "distance": n }` |
| Mark has inner layers that can fill a shape (a ring filling up, a gauge) | `{ "type": "rise", "direction": [0, 1], "distance": n }` plus `mark.clip` |
| Mark is rotationally symmetric (asterisk, star, flower) | `{ "type": "spin", "angle": 120 }`, using a multiple of its symmetry |
| Anything else | `{ "type": "pulse" }` |

For `assemble`, `direction` is the axis the parts pull apart along, and `distance` is how far each part moves, in logo units. Start at about 20% of the mark's size, and keep parts clear of the wordmark. For `rise`, set `distance` larger than the clip shape so part 1 starts fully hidden.

The lock-in plays at 2.6 s, after the wordmark. Add `"at": 1.1` to play it on the landed mark first; the wordmark then waits for it.

A badge can be a rounded rectangle or any path (`"badge": { "d": "…", "color": "#…" }`), for example a hexagon.

A mark that is one shape split into two parts (for example cut on a diagonal) can `assemble` as well. Overlap the halves by about a unit along the cut so no seam shows once they close.

**Multi-colour marks.**
- Give each path its own `color`, or a `gradient` (`{ "from": [x, y], "to": [x, y], "stops": [[0, "#…"], [1, "#…"]] }`) for gradient logos. Gradients also rebuild shaded ribbons and folds better than tracing their colour bands.
- Set `theme.markInk` to the colour the mark should have during the monochrome close-up.
- Hollow marks such as rings read better with `"closeUp": 0.8`.
- Long wordmarks leave the mark small. Set `"scale": 1.3` on the brand to enlarge the whole lockup.

### 5. Build and check
```bash
node scripts/build-html.mjs brand.json --out intro.html
```
Open the page, then scrub or call `logoIntro.seek(t)` in the console. Check each beat:

| t (s) | Expect |
|---|---|
| 0.4 | Mark fills the screen, curved by lens warp, with coloured fringes |
| 1.0 | Mark at resting size in the centre; for `assemble`, the parts are apart |
| 2.3 | Mark slid aside; the wordmark reads correctly, counters are open, spacing is even |
| 2.8 | Badge popped or parts snapped; the blob is hollowing into a ring |
| 3.5 | Shimmer band crosses the mark and letters as one continuous band |
| 5.0 | Clean final lockup, centred |

Some embedded preview panes throttle `requestAnimationFrame` or pause hidden pages. Judge motion in a normal browser tab, and judge frames with `seek()`.

### 6. Export a video (optional)
```bash
npm i -D playwright && npx playwright install chromium
node scripts/export-video.mjs brand.json --out intro.mp4 --width 1920 --height 1080 --fps 60
```

### 7. Embed as a site splash (optional)
```js
import { mountLogoIntro } from './logo-intro.js';
import brand from './brand.json' with { type: 'json' };

const seen = sessionStorage.getItem('intro-seen');
if (!seen && !matchMedia('(prefers-reduced-motion: reduce)').matches && !navigator.webdriver) {
  sessionStorage.setItem('intro-seen', '1');
  mountLogoIntro(document.body, brand, { overlay: true, exitAt: 4.35, skippable: true });
}
```
The splash plays over the page while it keeps loading. Any click or key skips it. Browsers with software-only WebGL skip it automatically, and it removes itself when done.

## Notes
- Every frame is a pure function of `t`; `seek(t)` is exact and is what video export uses.
- During the close-up the mark renders in one colour (`markInk` or `ink`). Per-path colours show once it lands.
- Only animate and publish logos you have the right to use.
