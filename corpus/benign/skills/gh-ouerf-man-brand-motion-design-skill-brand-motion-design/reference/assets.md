# The user's assets

Ask for assets in the interview ("Do you have any of these?") and accept whatever comes: a logo, photos, screenshots, screen recordings, footage, a song, a voiceover. Everything is optional. Without assets, the film is built from the brand (type, colour, 3D made from the logo and the subject). Before using any file, open it and look at it.

Put files in the film project, never link to them:

```
videos/<film>/assets/
  logo/      logo.svg (best), logo.png (transparent, 1000 px+ wide)
  images/    product photos, cut-outs, screenshots, photos of people (with consent)
  video/     screen recordings, footage (H.264 MP4)
  audio/     the song (licensed), a voiceover
  fonts/     the brand's font files
```

## What each asset becomes

| Asset | Best use in a showreel | How |
|---|---|---|
| **Logo, SVG** | the lockup build (the paths draw, the mark lands), particles converging into it, a 3D extrusion of the mark | read the paths into a `logo.js` twin; `PF.three.samplePoints` for particle targets; never redraw or recolour |
| **Logo, PNG only** | a flat lockup card with a fade and scale; particles sampled from its alpha | `PF.loadImages`, `PF.three.photo`; say in one line that an SVG would allow a proper build |
| **Product photo, cut-out PNG** | the hero: a 3D card that orbits in lit space, close shots on details, a floor reflection | `PF.three.photo(st, PF.img.hero, 3)`; keep it unlit so its colours stay true (and `mesh.material.fog = false` if it must not fade into the background); light the world around it |
| **Photo with a background** | a full-bleed chapter, a card flying past the camera, a before/after pair | crop in the frame, never stretch; a colour grade only towards the brand palette, from `/media-use` treatments |
| **App screenshots** | UI cards in 3D (tilted, stacked, flying through), a close shot on the key element | `PF.three.photo`; for crisp small text keep the card near 1:1 pixel size in the close shot |
| **Screen recording** | the product really working, inside a device frame or a tilted card | a HyperFrames `<video muted>` clip with `data-start`, `data-duration`, `class="clip"` in the DOM layer, tilted with CSS `perspective` from `t`; its sound, if any, as a separate `<audio>`; trim to the 2 to 4 seconds that show the move |
| **Footage** | a chapter background under giant type, a cut on the beat | same as a recording; cut on the grid; read `/media-use` before changing how it looks |
| **Song** | the grid and the energy | `beats.py`, then `audio-edit.py` on bars ([music.md](music.md)); ask for the licence |
| **Voiceover** | the timing source | place words on its phrases; keep the music under it (duck 6 to 9 dB) |

## Rules

- **Rights and consent.** Use only what the user owns or has licensed. Photos of people need their consent (a parent's for a minor). Reviews and results must be real, with permission to show them.
- **Look first.** Open every image and a few frames of every video before planning around it: resolution, crop, what is actually in it. A 640 px photo cannot be a full-bleed 1080 x 1920 hero; use it as a smaller card instead.
- **Load before setup.** Images: `PF.film({ waitFor: [PF.loadImages({...}), PF.signal("three")] })`, then `PF.img.<key>` in `setup()`. A failed load logs an error and gives `null`: handle it.
- **No network at render time.** Download remote files into `assets/` first.
- **Missing assets are fine.** Say what you used instead in one line ("no product photo, so the product is built as a 3D shape from your logo's colours"), and offer to swap in the real asset later.
