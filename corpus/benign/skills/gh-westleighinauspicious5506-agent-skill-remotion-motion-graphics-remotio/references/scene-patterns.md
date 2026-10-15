# Motion pattern catalogue

Building blocks that make a kinetic-typography / brand promo feel designed.
Each pattern names the effect, when it earns its place, and the code shape.
Everything uses `frame = useCurrentFrame()`, `prog()` / `springAt()` from
`anim.ts`, and positions from `useLayout()`. Combine 10-15 of these at
1-4 seconds each for a 30-second piece; alternate light and dark backgrounds
so hard cuts read as deliberate.

## Contents
1. Word-by-word reveal (`<Words>`)
2. Phrase swap in a sentence
3. Pill that morphs into a button, cursor click
4. Objects flying into a collage
5. Circle wipe carrying text
6. Ticker + panel wipe + marquee bar
7. Shape that shrinks into the next scene's element
8. Route / line drawing on a map
9. Product-UI moment (typewriter, toggle, radios, dot cursor)
10. Gradient statement text with a swap
11. Character bounce + wordmark letters popping
12. Scrolling bubble rows with one highlighted
13. Card with a growing chart
14. Spotlight beam
15. Burst of chips collapsing into the final lockup
16. Fade to black

---

## 1. Word-by-word reveal
Every headline lands one word at a time (5-7 frame stagger, 12-14 frame
rise + fade + 3px blur that clears). Use `<Words text start stagger dur out>`;
give `out` when the line must leave before the next arrives.

## 2. Phrase swap in a sentence
"Want ⚡ to learn faster? / to grow further? / to stop guessing?" — the fixed
words stay put, the variable phrase cycles. Stack all phrases absolutely at the
same spot and give each an `IN[i]` / `OUT[i]` window (about 40-50 frames per
phrase). Exits accelerate up and fade (EASE_IN); entrances rise (EASE_OUT).
Keep fixed text right-aligned to a fixed x and the phrase left-aligned to it
so the layout never reflows when word widths change.

## 3. Pill → button → click
A small white pill (emoji inside) springs into the sentence
(`springAt(frame,fps,30,{damping:14,stiffness:140})`, width = 92 × p). At the
scene end the sentence fades and the pill eases to centre. Next scene: the pill
grows (`lerp(92,360,prog(frame,0,14))`), the emoji fades, a label types in
(`typed(text, frame, 6, 40, fps)`), a cursor springs to it and "presses"
(scale 0.96 for 5 frames), then the button fades out. Cursor moves are chained
springs so it never teleports:
```ts
const c1 = springAt(frame, fps, 8, { damping: 16, stiffness: 80 });
const c2 = springAt(frame, fps, 34, { damping: 16, stiffness: 80 });
const x = lerp(lerp(x0, x1, c1), x2, c2);
```

## 4. Objects flying into a collage
Cards / photos start off-screen on all sides with ±30° rotation and spring to
scattered resting spots (`damping: 17, stiffness: 95`, 3-frame stagger), a
bold white line lands on top with a dark text-shadow. Define resting and start
positions as fractions of W/H, with a separate set for landscape.

## 5. Circle wipe carrying text
A black circle grows from centre to `diag × 1.25` over 20 frames (EASE_INOUT).
Text sits at the circle's centre (`left:50%; top:50%; translate(-50%,-50%)`) so
it stays fixed while the circle grows; second line appears after the wipe
completes, first line lifts 44px to make room. Do not add a full-frame overlay
"to tidy the edges" — the circle already covers the frame and the overlay hides
the text.

## 6. Ticker + panel wipe + marquee bar
A line translates across at constant speed (`interpolate(frame,[0,41],[W*0.48,-W*0.48])`).
Mid-way a white panel slides in diagonally from the top-right
(`translate((1-p)*W, -(1-p)*H*0.55)`), carrying a black bar with a very wide
blue pill whose text scrolls left 26px/frame. Two motions at once give energy
without a cut.

## 7. Shape that becomes the next element
Grey card, a blue pill with a word → text fades, pill shrinks to a circle,
background darkens (`interpolateColors`), circle travels to exactly where the
next scene's marker sits. Export the marker position from a shared helper
(`markerPos()` in layout.ts) so both scenes agree.

## 8. Route drawing
`<path pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />` with
`draw = prog(frame, 0, 45, EASE_INOUT)`. Define the path in fractions of W/H so
it survives both orientations. Add a pulsing halo (`sin` on scale/opacity), a
marker, a tooltip that types two lines, and a slow 10% zoom on the whole map
with `transformOrigin` at the marker.

## 9. Product-UI moment
Typewriter headline + body (`typed()` with `whiteSpace: "pre-line"`), a toggle
whose knob slides with a spring and whose track alpha follows the same value,
radio dots that change on a click, and a black dot cursor with chained springs
that presses on the toggle then the radio. Lay the group out as a fixed 900px
block centred with `gx = cx - 450; gy = cy - 240`.

## 10. Gradient statement text
Two lines stacked at the same spot; each has `background: linear-gradient(...)`,
`WebkitBackgroundClip: "text"`, `color: "transparent"`. Line 1 scales
0.94→1 and fades in, exits up (EASE_IN); line 2 rises in 4 frames later. A
radial glow behind grows from 0 over 40 frames.

## 11. Character bounce + wordmark letters popping
Use `SvgArt` with `parts: { body: { indices, origin: "50% 100%", style: characterStyle({ entrance: 4, bobAmp: 55, period: 36, tilt: 2.5 }) }, letters: { indices, popEach: { start: 12, stagger: 2 } } }`.
Bob amplitude is in viewBox units (50-60 on a 4096 canvas). Order letter
indices along the arc (sort by angle around a point below the arc) so they pop
in reading order. Add `fadeLeft` when the artwork is cropped at the canvas
edge.

## 12. Scrolling bubble rows
6-7 rows of dark rounded pills (random widths via `random(seed)`), alternating
direction and speed, one fixed pill with a blue border and glow that types a
short line. Portrait: rows start at ~17% height; landscape: start above the
frame so rows fill it.

## 13. Card with a growing chart
Sample 48 points of a rising noisy function into a polyline; reveal with a
`<clipPath>` rect whose width = head.x; put a white dot at the interpolated
head point; area fill under the line with a vertical brand gradient. Card
scales 0.9→1 and drifts a few px over the scene.

## 14. Spotlight beam
Two stacked cones (wide soft + narrow bright). Put `filter: blur()` on the
wrapper and `clipPath: polygon(...)` on the inner div — CSS applies filter
before clip-path, so blurring a clipped element gives hard edges. Sway with
`rotate(sin(frame/15)*2.5deg)` from `transformOrigin: "50% 0%"`.

## 15. Burst → lockup
18 chips start on a ring (radius 700-1200, seeded angle), rush to centre with
EASE_IN over 16 frames while blurring (`blur((1-p)*6px)`) and fading; the logo
springs in with `damping: 11-12` (visible bounce) as they vanish; letters pop;
tagline rises; URL pill springs; feature chips stagger 4 frames apart.
Landscape: logo left, copy right; portrait: logo above copy.

## 16. Fade to black
Full-frame ink overlay `opacity: prog(frame, T-14, 14, EASE_IN)` in the last
scene. Always end on a resting frame (nothing still moving).

---

## Timing that felt right (30 fps)
- Hook with 3 phrase swaps: 135 frames. Button + collage: 75. Wipe + line: 45.
- Ticker/panel: 41. Shape hand-off: 19. Map: 105. UI: 105. Statement: 75.
- Character: 60. Bubbles: 60. Chart: 45. Character 2: 75. Spotlight: 45.
- Closing line: 51. Burst + lockup + fade: 84. Total ≈ 1020 (34 s).
Cut faster than feels comfortable in code; it plays slower than it reads.
