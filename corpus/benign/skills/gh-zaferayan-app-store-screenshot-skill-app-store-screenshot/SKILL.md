---
name: app-store-screenshot
description: Turn raw mobile app screenshots into premium App Store and Google Play marketing screenshots with a device frame, a themed scene or brand-derived background, and a short headline, while keeping the original UI pixel-exact. Use when the user shares iOS or Android app screenshots and asks for store listing images, framed device mockups, launch or Product Hunt visuals, or a consistent multi-screen screenshot set.
license: MIT
---

# app-store-screenshot

## Core Rule

Preserve the original app UI exactly. Do not redraw, restyle, translate, rewrite, hallucinate, or "improve" content inside the screenshot. Treat the screenshot as source artwork and design around it.

Never pass the screenshot through an image-generation model and present the result as the app's UI: models change text, numbers, and icons in ways that are easy to miss. Composite instead. Everything here renders the screenshot as a plain image layer that is resized and nothing else.

## Workflow

1. **Inspect the screenshots.** Note platform, brand colors, light or dark UI, and the feature each screen shows. Check the pixel size: below roughly 1000 px wide (typical of files sent through a messaging app) the screenshot would have to be upscaled and will look soft. Say so and ask for the originals. Meanwhile, proceed with a device small enough to avoid upscaling: `device_max_w` at most source width divided by canvas width (a 738 px source on a 1290 px canvas gives 0.57).
2. **Pick a concept before picking colors, one per screenshot.** Ask what the app's subject looks like and put the device in that scene: paintings for an art app, caption bubbles in many languages for a subtitle app, a trail for a hiking app. Then go further and give each image its own background, built from what that particular screen shows, so the background continues the screenshot past the bezel. See "Backgrounds". A flat gradient with a pattern is the fallback, not the goal.
3. **Build the theme from the app itself.** Take `bg`, `accent`, and `accent2` from the screenshots (buttons, highlights, icons). Match the frame to the platform, and choose a frame finish that separates the screen from the background: a dark frame for a light UI on a vivid background, titanium or silver on dark scenes.
4. **Write the copy.** One headline per image, 2 to 6 words, benefit first, with the key words emphasized. An optional one-sentence subheadline. Do not repeat text already visible in the screenshot, and keep claims conservative for health and finance. The first image carries the main value proposition, since it is often the only one seen in search results. Write in the language of the store listing; ask if unclear.
5. **Render** with `scripts/render.mjs` (below). Write the config, backgrounds, and outputs into the user's working directory, never into the skill folder.
6. **Look at every output image** and go through the checklist at the end. Fix and re-render until it passes.

## Rendering

Each image is an HTML page screenshotted by headless Chrome. CSS provides the background, a metallic device frame, and real typography.

Script paths are relative to this skill's directory.

```bash
cp <skill-dir>/assets/set.example.json ./set.json    # then edit it
node <skill-dir>/scripts/render.mjs ./set.json
```

The script prints JSON per image: `screen_box` (where the screenshot sits on the canvas), `screenshot_scale`, `headline_px`, and `warnings`. Paths inside the config may be absolute, start with `~`, or be relative to the config file.

A headline that does not fit its reserved lines is shrunk automatically, so `headline_px` differs between images when one headline is too long. Aim for lines of at most about 20 characters and shorten the copy until `headline_px` is the same across the set.

Requirements: Node 18 or newer and a Chromium-based browser (Chrome, Chromium, Edge, or Brave; set `CHROME_PATH` if it is not found). There are no packages to install. If no such browser is available, say so and ask the user to install one; do not fall back to generating the image with a model.

Output is an opaque RGB PNG, which both stores require (they reject transparency). The script checks this and the pixel size and reports a warning otherwise.

### Config reference

Top level: `size` (`"1290x2796"` default; use `"1080x1920"` for Google Play, which rejects images whose long side exceeds twice the short side), `out_dir`, optional `template`, `theme`, `images`.

Theme keys (each can be overridden inside a single image entry):

- `bg`, `bg2`: base gradient, top to bottom. `accent`: glows. `accent2`: emphasized words and highlight lines. `text`, `line`: derived from `bg` when omitted.
- `headline_font` (CSS font stack), `headline_weight`, `em_style` (`normal` or `italic`), `font_links` (Google Fonts URLs, only when online). A bold sans reads best over busy scenes; a serif suits editorial or cultural apps on calm backgrounds.
- `headline_lines`, `sub_lines`: room reserved for the headline and subheadline. Set them once in the theme so the device has the same size and position in every image. For the same reason give every image an `eyebrow` (a small uppercase pill label above the headline), or none.
- `device_max_w`: screen width as a fraction of the canvas (default 0.73; 0.62 to 0.68 lets a scene breathe).
- `platform` (`ios` or `android`), `frame` (`black`, `titanium`, `silver`), `cutout` (`false` hides the Dynamic Island or camera hole).
- `scene`, `scene_vars`: an HTML scene fragment and its per-image variables; see "Backgrounds".
- `background_image`, `background_position` (CSS position such as `"94% center"`), `scrim` (0 to 1, how strongly the image is tinted toward `bg`). With a background image the glows, grain, and patterns are switched off, but the colors still matter: `bg2` darkens the zone behind the headline and feeds the text shadow, and `bg` decides whether the default text is white or near-black.

Image keys: `screenshot`, `out`, `headline` (`\n` forces a line break, `*text*` marks the emphasized words), `sub`, `eyebrow`, `pattern`, plus any theme key, most usefully `scene` and `scene_vars` to give the image its own background.

## Backgrounds

Three ways to build one, best first.

**Give each image its own background, derived from its own screenshot.** Open the screenshot and list what it actually contains: its imagery, its motifs, the instrument or chart it draws, its colors. Then build a background that continues those elements outside the device, so the phone looks like a window cut into the scene rather than a sticker on a gradient. A countdown screen over a dusk photo becomes a sunset sky carrying the app's own ornament; a compass screen becomes a large dial the phone sits inside, with the bearing leaving toward its target; a settings screen with light and dark themes becomes a canvas split between them. One background reused across the whole set reads as a template, however pretty it is, and reviewers see five images that all say the same thing.

Keep what makes them a set in the shared theme: canvas size, typography, `device_max_w`, frame, and the headline treatment. Let the scene carry the difference. Around 0.66 for `device_max_w` leaves gutters wide enough for a scene to live in.

**1. A scene image.** Pass a photo, artwork, or illustration as `background_image`. Sources in order of preference: the user's own brand imagery; public-domain or freely licensed images that match the app's content (Wikimedia Commons, museum open-access collections, Unsplash), with the license checked and the source reported to the user; an image-generation tool, used for the background only. When generating, ask for the scene without any phone or UI in it. Choose images with a calm zone behind the headline, set `scrim` around 0.05 to 0.15 for dark images and higher when the headline loses contrast.

**2. An HTML scene.** When no suitable image exists, build the scene in HTML. Write a fragment file per image (a `<style>` block, markup, optionally inline `<svg>` and a `<script>`) into a `scenes/` folder beside the config, and point each image entry at its own: `"scene": "scenes/02-compass.html"`. `scene` is a theme key, so setting it in the theme gives every image the same background and setting it per image overrides that; prefer per image. The renderer injects it into the background layer, above the `bg` to `bg2` gradient and below the headline and device. Build it from the app's subject: a brand gradient, soft radial-gradient lights, and decoration such as caption pills, pipelines of command chips, waveforms, map contours, music staves, or chart lines. Three working examples from one recipe-app set, each built from a different screen, to adapt: `examples/scenes/berries.html` (a recipe photo topped with berries: the fruit spills past the bezel onto a raspberry-red light), `examples/scenes/plate.html` (a meal plan whose photo shows a striped plate: the phone sits on that plate, its stripes ringing the device), and `examples/scenes/tracker.html` (a daily tracker: the week strip and macro bars from the screen stand in the gutters, filled from `scene_vars`). `assets/set.example.json` wires all three into one set.

- Parameterize a fragment with `"scene_vars": {"seed": 4, ...}` in the image entry (merged over any `scene_vars` in the theme); the fragment reads them from `window.SCENE`. Use it to feed the scene a real value from the screenshot, such as the bearing the app displays, and to seed scattered decoration. Use a seeded random generator, as the examples do, so a re-render gives the same picture.
- Place decoration from measurements, not guesses. After layout the page sets `window.LAYOUT` and fires a `store:layout` event on `document` with `canvas {w, h}`, `device` and `screen` boxes `{left, top, right, bottom}`, and `headerBottom`, all in pixels. The free side gutter is `LAYOUT.device.left` wide. Draw inside that handler.
- Keep decoration in the side gutters and along the bottom edge, and size it to fit there whole. Half-clipped words look like mistakes. Leave the headline zone (above `headerBottom`) calm.
- Decoration must be thematic and abstract. Do not draw fake app UI, fake notifications, or fake reviews around the phone.
- Keep decoration secondary to the screenshot: low-contrast fills on vivid backgrounds, thin accent-colored lines on dark ones.
- The fragment can use the template's placeholders and CSS variables: `{{ACCENT}}`, `{{ACCENT2}}`, `{{BG}}`, `{{BG2}}`, `{{WIDTH}}`, `{{HEIGHT}}`, `{{SCREENSHOT}}` (URL of the current screenshot), `var(--vh)`, and `vw` units. Do not use the `vh` unit.
- A scene may show a blurred or tinted copy of the screenshot as background light. The rule against filters applies to the screenshot inside the device, which must stay untouched.
- Use installed font families, or load web fonts through `font_links`.
- If the output lacks the decoration, read `warnings`: JavaScript errors from the page are reported there.

**3. Built-in patterns.** `pattern` is one of `rings`, `dots`, `grid`, `rays`, `arcs`, `diagonal`, `frames`, `none`, drawn over the `bg` gradient with `accent` glows and grain. Good for a quick, safe result.

**Custom templates.** For a look the config cannot express, copy `assets/template.html`, change the CSS, and point `"template"` at the copy. Two rules: never put filters, overlays, or tints on the screenshot `<img>`, and never use the `vh` unit or `innerHeight`. Headless Chrome loads the page in a shorter viewport than the one it captures, so use `var(--vh)` and `var(--canvas-h)`.

## Checklist Before Delivering

Open the rendered files and confirm each point. Report anything that does not pass instead of hiding it.

- `warnings` is empty for every image. An "upscaled" warning means the source is too small: tell the user and ask for the original files.
- `screen_box` is identical across the set.
- Inside the frame, text, numbers, and icons match the source screenshot, and nothing meaningful is hidden by the rounded corners or the camera cutout.
- Headline and subheadline are readable when the image is viewed at about 300 px wide, which is how a store gallery shows it.
- Background decoration is not clipped mid-word and does not compete with the screenshot.
- Each image has its own background, and each one is recognizably about the screen it frames. Two images that could swap backgrounds without anyone noticing mean the concept is generic; go back to step 2.
- Nothing from the scene collides with the headline: no lattice lines, stars, or decoration inside the headline box.
- Output size matches the target store (the script warns on a size or alpha-channel mismatch).
- Files are numbered in gallery order, and the user is told where the config is so they can edit copy and re-render.

## More Guidance

- `references/visual-directions.md`: direction, headline tone, composition, and category notes (wellness, finance, dark mode, productivity, education, creator tools).
- `references/store-sizes.md`: exact App Store and Google Play sizes, counts, and format rules.
- `examples/`: headline ideas and set sequencing for wellness, finance, and dark-mode apps, plus three HTML scenes in `examples/scenes/` that `assets/set.example.json` renders as a set.
