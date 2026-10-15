# logo-intro

WebGL logo intros from any SVG logo. The mark arrives from an extreme close-up (lens warp, spectral colour fringes, spin), the wordmark pulls out of it, a gradient bloom grows, a lock-in beat sends out a ring, and one shimmer sweeps the logo. It runs in five seconds.

| CheatGTM: badge lock-in | nuphos: two parts snap |
|---|---|
| ![CheatGTM](docs/cheatgtm.gif) | ![nuphos](docs/nuphos.gif) |
| **LunaBill: layers rise before the wordmark** | **Hearing Action: hexagon badge on a dark ground** |
| ![LunaBill](docs/lunabill.gif) | ![Hearing Action](docs/hearingaction.gif) |
| **XTrace: gradient mark splits on the diagonal and closes** | **AVA Angels: folded-ribbon A, "AVA" rises inside it** |
| ![XTrace](docs/xtrace.gif) | ![AVA Angels](docs/avaangels.gif) |
| **Monid: mark trails the wordmark, spin lock-in** | **Formosa Founders: traced avatar, pulse lock-in** |
| ![Monid](docs/monid.gif) | ![Formosa Founders](docs/formosafounders.gif) |

You can use it four ways:

- **A JS module.** `mountLogoIntro(element, brand)` has no dependencies and uses one fragment shader.
- **A single HTML file.** `scripts/build-html.mjs` writes a self-contained page with a scrubber, and it opens from disk.
- **A video.** `scripts/export-video.mjs` renders frames in headless Chromium and encodes MP4/WebM.
- **A Claude skill.** Clone the repo into your skills folder and ask Claude to "make a logo intro for acme.com".

## Quick start

```bash
git clone https://github.com/CJ10110425/logo-intro && cd logo-intro
node scripts/build-html.mjs brands/cheatgtm.json --out dist/cheatgtm.html
open dist/cheatgtm.html
```

Drag the timeline, try 0.25× playback, or press Space, R, and the ← → keys.

## Make one for your brand

Write a brand JSON. The full field list is in [`references/brand-schema.md`](references/brand-schema.md).

```json
{
  "name": "Acme",
  "theme": { "background": "#ffffff", "ink": "#111111", "bloom": ["#2e9484", "#7ccfc0", "#9fd3e3", "#c9ebb7", "#f2b48e"] },
  "mark": { "viewBox": [0, 0, 36, 36], "paths": [{ "d": "M4 18a14 14 0 1 0 28 0a14 14 0 1 0 -28 0" }] },
  "wordmark": { "text": "acme", "font": { "family": "Inter", "weight": 700, "css": "https://fonts.googleapis.com/css2?family=Inter:wght@700&display=swap" } },
  "lockIn": { "type": "pulse" }
}
```

- **Wordmark**: either live `text` in a web font, or outlined `letters` (path data per letter, counters included) that share the mark's `viewBox`.
- **Lock-in**:
  - `badge` pops a shape under the mark.
  - `assemble` snaps two mark parts together.
  - `rise` slides part 1 into a clip shape.
  - `spin` turns a symmetric mark into place.
  - `pulse` works for anything else.
- **Colours**: the mark and letters use `ink` by default. Individual paths can set their own `color`.

[`SKILL.md`](SKILL.md) walks through extracting and splitting a logo from a live site, including tracing a PNG-only logo with potrace.

## Use it in a page

```js
import { mountLogoIntro } from 'logo-intro';

const player = mountLogoIntro(document.querySelector('#hero'), brand, { loop: true });
player.seek(2.8);   // exact frame at t = 2.8 s
player.play();
```

As a once-per-session site splash over a page that keeps loading underneath:

```js
if (!sessionStorage.getItem('intro-seen') && !navigator.webdriver) {
  sessionStorage.setItem('intro-seen', '1');
  mountLogoIntro(document.body, brand, { overlay: true, exitAt: 4.35, skippable: true });
}
```

| Option | Default | |
|---|---|---|
| `autoplay` | `true` | Starts once fonts are ready |
| `loop` | `false` | |
| `speed` | `1` | |
| `overlay` | `false` | Fixed full-screen layer instead of filling the element |
| `exitAt` | `null` | Seconds; fades out and removes itself |
| `skippable` | `false` | Any click, key, wheel or touch fades it out |
| `scale` | `1` | Lockup size multiplier |
| `maxDpr` | `2` | Canvas pixel-ratio cap; drops to 1 if the first frames are slow |
| `allowSoftwareGL` | `false` | Software WebGL is skipped unless this is set (video export sets it) |
| `reducedMotion` | `'final'` | `'final'` shows the last frame, `'skip'` removes it at once, `'ignore'` plays anyway |

The player has `play()`, `pause()`, `seek(t)`, `replay()`, `setSpeed(s)`, `skip()` and `destroy()`, plus the `ready`, `finished`, `time`, `playing` and `duration` properties.

## Export a video

```bash
npm i -D playwright && npx playwright install chromium   # once
node scripts/export-video.mjs brands/cheatgtm.json --out cheatgtm.mp4 --width 1920 --height 1080 --fps 60
```

Every frame is a pure function of `t`, so the video matches the live page frame for frame.

## Use it as a Claude skill

```bash
git clone https://github.com/CJ10110425/logo-intro ~/.claude/skills/logo-intro
```

Then ask Claude for an intro for any brand. The skill covers finding the logo, splitting mark and letters, picking colours, choosing a lock-in, checking frames and exporting.

## Notes

- Needs WebGL 1. `EXT_shader_texture_lod` is used when present.
- Only animate logos you have the rights to use. The nuphos, LunaBill, Hearing Action, XTrace, AVA Angels, Monid and Formosa Founders marks belong to their owners and appear here as examples.
- Inspired by the ElevenLabs brand intro. This project is not affiliated with ElevenLabs.

## License

MIT
