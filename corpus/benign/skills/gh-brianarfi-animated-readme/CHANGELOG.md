# Changelog

## [Unreleased]

### Added
- 17 styles for the scenes, chosen with a new `style` key in `readme-scenes.json`: math, typographic, cutpaper, sketchbook, riso, terminal, isometric, blueprint, brutalist (neo brutalism), whiteboard, liquid, holo, glass, clay, ascii, pixel, artdeco. Without `style` the original look is unchanged.
- `assets/style-gallery.html`: one static page with a live sample of every style, to choose from by eye.
- The skill now asks which style to use and shows the gallery before it fills the scenes.

## [0.1.0] - 2026-10-02

### Added
- The `animated-readme` skill and `/animated-readme` command: read the project, write the copy, render the GIFs, show the README for approval.
- Three scene templates: hero, before-after and how-it-works, filled from `readme-scenes.json`.
- `scripts/render.py`: renders every scene, writes still PNGs, warns over 4 MB, writes `readme-snippets.md` with alt text.
- `scripts/record_html.py`: deterministic frame-by-frame GIF recording, ffmpeg or Pillow.
- A writing guide for README copy and alt text.
- This README, with GIFs rendered by the kit itself.
