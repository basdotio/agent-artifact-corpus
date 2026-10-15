# Verification loop and gotchas

## The loop (do it every time, it costs a minute)
1. `npx tsc --noEmit` — catches prop and import mistakes before Chrome does.
2. `scripts/check_render.sh <CompId> <out_dir>` — 0.3-scale MP4 + contact
   sheets. View every sheet. Look for: empty frames (a scene crashed or an
   overlay hides content), text under artwork, elements off the safe zone,
   things still moving on the last frame of a scene, colour jumps at cuts.
3. For a suspicious moment, render one still at 0.5:
   `npx remotion still <CompId> out/f200.png --frame=200 --scale=0.5`
   or grab a frame from the preview with `scripts/still_frame.sh`.
4. Fix, re-run 1-2 only for changed scenes if you can (a still is enough for a
   local fix), full check again before the final render.
5. Final: `npx remotion render <CompId> out/final.mp4 --codec=h264 --crf=18`
   (1020 frames at 1080x1920 renders in ~30 s on an M-series Mac).
6. Extract one or two frames from the FINAL file too — the final render is the
   thing being shipped, not the preview.

## Gotchas met in practice
- **Overlay hides content.** A "cleanup" full-frame overlay drawn after the
  content covers the text. Check z-order before adding overlays; usually the
  wipe shape already covers the frame.
- **filter + clip-path order.** CSS applies `filter` before `clip-path`, so a
  blurred cone clipped to a polygon has razor edges. Blur the parent, clip the
  child.
- **Artwork cropped at the SVG canvas edge** (a character running off the
  page) shows a hard vertical cut on a dark background. Mask the element with
  a gradient that is fully transparent for the first ~4% and opaque by ~17%;
  a 9% fade is too weak to hide the cut.
- **Gradient fills in exported SVGs** (`fill="url(#gradient_1)"`) render
  black without their `<defs>`. `svg_to_paths.mjs` swaps them for the first
  stop colour.
- **Per-path transforms in inline SVG** need `transformBox: "fill-box"` plus
  `transformOrigin`, otherwise scale/rotate pivots on the canvas origin.
- **`pathLength={1}`** normalises stroke dash math so `strokeDashoffset = 1 - p`
  draws any path regardless of its true length.
- **`interpolate` input ranges must strictly increase** — duplicate stops crash
  the frame.
- **Negative-frame springs**: guard with `frame <= start ? 0 : spring(...)`
  (`springAt` does) so look-behind sampling for cursor trails is safe.
- **Bob amplitude inside an SVG is in viewBox units**, not screen px (50 units
  on a 4096 canvas ≈ 10 px at 840 px wide).
- **Shell env vars into node**: `export S=...` before `node -e '...process.env.S'`;
  unexported vars come through as `undefined` paths.
- **rsvg-convert / qlmanage are unreliable** for SVG previews on macOS; verify
  artwork splits with a Remotion still instead — Chrome is the renderer that
  matters.
- **Emoji** render fine in Remotion's Chrome on macOS (Apple Color Emoji);
  on Linux CI install a colour emoji font or replace them with SVG icons.
- **Landscape from portrait**: do not letterbox. Derive positions from
  `useLayout()`, keep a 1.2 design scale for 16:9, and give tall artwork a
  side-by-side branch (`wide ? {...} : {...}`). Re-check the portrait sheet
  after the refactor to prove nothing moved.
- **Deliver the file**: copy the MP4 next to the user's source material and
  send it with the file tool; a path in a message is easy to miss.
