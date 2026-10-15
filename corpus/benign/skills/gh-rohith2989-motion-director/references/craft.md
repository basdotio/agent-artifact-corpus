# Craft — how premium motion is made

The difference between "an animation" and "a film" is a few hundred small decisions made the same way every
time. These are the defaults; break one only on purpose, and write down why in `docs/PLAN.md`.

## Timing
| Thing | Duration | Notes |
|---|---|---|
| Press / hover / micro feedback | 120–250 ms | press dip 3–6 % scale, release with outCubic |
| UI element entering (card, menu, row) | 300–550 ms | rise 8–14 px + fade, expoOut |
| Headline word (mask rise) | 700–950 ms each | stagger 40–90 ms for running text; put accent words ON the beat instead |
| Camera travel | 0.8–1.6 s | inOutSoft; dives and big reframes heavyInOut |
| Section transition | 0.8–1.1 s | panel slide-over with the outgoing panel receding |
| Hold for reading | ≥ 0.3 s × words + 1 s | after the last word settles — never cut away from text still landing |
| Section length | ≥ 3 s | 5–14 s typical; a product step needs time to be *understood*, not just seen |

- **One hero motion per beat.** If the camera travels, UI holds still; if type animates, the camera holds or
  drifts slowly. Two big things moving at once read as chaos.
- **Lead the eye, then act.** Cursor arrives → beat → click. Highlight sweeps *as the word is said*.
  Things land on the downbeat when there is music, on the word when there is a voice.
- **Rhythm**: vary durations (a quick cut after a long hold); repeat a gesture three times at most.

## Easing (engine/comp/core/ease.js)
| Curve | Use |
|---|---|
| `expoOut` (0.16,1,0.3,1) | entrances, type reveals, settles — the house curve |
| `quintOut` (0.22,1,0.36,1) | UI rows, panels, menus |
| `inOutSoft` (0.65,0,0.35,1) | camera travels, morphs, highlights sweeping |
| `heavyInOut` (0.76,0,0.24,1) | dives, big reframes, a section-defining move |
| `inQuart` / `inExpo` | exits (quick to leave, no lingering) |
| `spring(freq, damping ≥ 0.45)` | characters/mascots only — never UI chrome |
| linear | only continuous drift (pools of light, particles, rotation) |

Never ease-in an entrance. Never overshoot UI. Exits are faster than entrances.

## Camera language
- Build a **world** (the desk, windows, cards in world px) and move a camera over it (`camAt` keys in log-zoom
  space). Establish wide → lean in on the action (1.6–2.2× so text is ≥ 24 px) → pull back to re-establish.
- A tiny **lean-in pulse** on clicks (+2–3 % zoom over 0.3 s) makes interaction tactile.
- Keep close-ups inside their window (`camIn`) — never show past a window edge or into empty desk.
- **Parallax**: background moves at ~4 % of the camera's travel; foreground UI 100 %; particles 60–100 % by depth.
- No camera roll except a deliberate 3D moment (≤ 6°). No handheld shake on UI. No zoom that isn't motivated.
- Motion blur samples follow speed: `samplesFor(camSpeed(t, keys))` — slow pans 1–3, travels 6–10, dives 12–16.

## Transitions (pick by meaning)
| Transition | Means | Engine |
|---|---|---|
| Panel slide-over, outgoing recedes and rounds | "next chapter, same story" | `slideIn` / `recede` / `panelTf` |
| Circle wipe out of the pressed element | "this action caused that" | `circleWipe(el, t, t0, dur, cx, cy)` |
| Zoom-through (dive into a detail, cut inside it) | "let's look closer" | camera keys + wipe from the target |
| Card morph (one frame, contents cross-fade) | "the same thing, next step" | `createMorph` |
| Match cut on shape/position | "these are the same idea" | align the two frames, cut on a beat |
| Split-flap word swap | "same sentence, different value" | per-letter flip + `flap` sound |
| Mask reveal (type, panels) | "here it comes" | `maskReveal` |
| Hard cut on a downbeat | energy, a drop | `cut(t)` so blur never crosses it |
| Window slide (app switch) | "now in the other app" | `slideX` + `poser` |
Avoid for section changes: cross-dissolves (amateur), spins, cube flips, page curls, glitch (unless the brand is
glitch), star wipes. A page *load* inside a browser is a hard switch when ready, not a cross-fade.

## Typography
- Display: one grotesk with character (Bricolage Grotesque, Geist, Inter Display, the brand's own) at
  96–220 px, weight 500–650, tracking −2 % to −3.5 %, line-height 0.92–1.06. UI: the product's real UI face at
  real px. Mono only for labels, code, data.
- Headlines ≤ 7 words, ≤ 2 lines. One accent word per headline (accent colour), ideally the verb or the payoff.
- Small labels in mono caps with +12–18 % tracking; never set sentences in caps.
- Numbers: tabular figures; count-ups end exactly on the value (no float dust on the last frame).
- Text never sits on busy motion; captions get their own band with a soft pill.

## Colour and light
- Start from the subject's tokens: one accent, its soft companion, ink, page, a night ground. Tint pure black
  and white.
- Light has a source: pools of light drifting (`livingLight`), glows from below in dark sections, a lit top edge
  on buttons. Dark sections for trust/security/"night"; light sections for product UI.
- Grain 2–4 % (kills banding in gradients before the encoder), vignette ≤ 7 %.
- Contrast for any text the viewer must read ≥ 4.5 : 1.

## Composition
- One focal point per frame. Negative space is a feature. Centre hero statements; set supporting type on a
  grid (24 px at 1080p; UI on its own 4/8 px grid).
- Reserve bands: a top band for a step tracker or chapter label, a bottom band for captions; never put the
  action there.
- The **hero frame** of each section (the one you'd use as a poster) is designed first, as a still.

## UI fidelity
- Rebuild the real UI from source: same copy, same tokens, same components, same order of steps, real states
  (focus rings, hover, pressed, loading, success). Typing uses real placeholders. Buttons press.
- When the real product changed (a removed feature, renamed button), the film follows the product, not the plan.
- Third-party screens (an OAuth consent page, Slack, a mail client) are rebuilt faithfully but simply; never
  imply partnerships that do not exist.

## Data that performs
- Bars grow from zero with values counting up; the one that matters is the accent; label directly (no
  legends); units obvious; ≤ 7 data points on screen.
- Lines draw left→right with a dot riding the head; area fades in under them.
- A single number is the strongest chart: +38 % at 220 px, then one plain sentence of meaning.

## Characters and mascots
Acting = attention: eyes open (birth), blink on idle (double-blink every ~3 s), glance toward what matters,
brows lift on good news, mouth dots hop while "thinking". No bouncing, no waving arms, no squash-and-stretch
cartoon physics on a brand mark.

## Accessibility and safety
Captions for muted viewing, ≥ 4.5 : 1 contrast, no more than 3 flashes per second, no strobing gradients,
nothing that impersonates a real person or brand, no fake testimonials or customer logos.
