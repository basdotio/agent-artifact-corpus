# Typography

## Fonts

- Two families at most, with clear contrast: a display face for titles and numbers, a text face for everything else. Serif + grotesque, condensed + wide, or a monospace for a technical voice.
- Load from Google Fonts with `&display=block`; the runtime waits for `document.fonts.ready` before the first frame and the exporter waits for it before any capture.
- Pairings that avoid the default look:

| Voice | Display | Text |
|---|---|---|
| Industrial, loud (demo) | Big Shoulders Display 800–900 | IBM Plex Mono |
| Editorial (template) | Instrument Serif | Instrument Sans |
| Engineering | Space Grotesk 700 | JetBrains Mono |
| Finance, sober | Newsreader | Public Sans |
| Warm, human | Fraunces | Work Sans |
| Swiss | Archivo 800 | Archivo |

Inter, Roboto and Montserrat are not wrong, but they are the default; choose them deliberately.

## Sizes on the 1920×1080 canvas

| Role | Size | Notes |
|---|---|---|
| Hero number | 240–380 px | tabular figures, tight line-height (.8–.85) |
| Title slide | 150–330 px | |
| Slide title | 72–110 px | line-height .94–1.05, max about 1500 px wide |
| Statement | 110–160 px | one sentence |
| Body | 28–38 px | line-height 1.35–1.45, max about 60 characters per line |
| Labels, axes | 20–26 px | muted colour, often uppercase with .06–.2 em tracking |
| Footer, source | 20–22 px | muted |

`check` fails anything under 20 px. On a projector at the back of a room, 24 px is the practical minimum for anything you expect people to read.

## Titles

- Sentence case or uppercase, consistently. Uppercase suits condensed display faces; tighten tracking slightly at large sizes.
- Balance line breaks by hand with `<br>` or `max-width` so a title never leaves one word alone on the last line.
- The title is already there when the slide lands. Animate content, not titles, except on the title slide and statements.

## Text on a slide

- Left-aligned by default. Centre only symmetric, ceremonial slides (title, statement, close).
- Numbers in running text use the same figures as the charts; use `font-variant-numeric: tabular-nums` wherever numbers change or line up.
- Use real typographic characters: −, ×, →, ’, “ ”, en dashes for ranges (Q3–Q4).
- Highlight with weight, the marker (`data-anim="highlight"`) or the accent colour: one of them, sparingly.

## Kinetic type that earns its place

| Technique | `data-anim` | Where |
|---|---|---|
| Mask reveal (the line rises from an invisible edge) | `mask` | title slide, statements, the close |
| Count up | `count` | the hero number |
| Typewriter | `type` | a quote, a prompt, a terminal line |
| Highlight sweep | `highlight` | the phrase the speaker is saying now |
| Strike and replace | `strike` + `count` with `data-from` | before → after numbers |
| Word by word | `data-stagger` on spans | a short manifesto line, not paragraphs |
| Character by character | `chars` | a tagline or a short title, 20-40 characters, once per deck or section |
| Tight to loose | `tracking` | the title slide, one word in capitals; slow and solemn |
| Settle from noise | `scramble` | a title about a system, a signal or an incident; it earns its place when the subject is data or failure |
| Split-flap | `flip` with `data-words` | one word of a sentence that changes per click: plans, states, audiences |

Multi-line mask reveals: wrap each line in a `<span style="display:block">` inside a `data-stagger` container, so the lines rise one after another.

### The four kinetic anims

```html
<h1 data-anim="tracking" data-spread=".14">BLACKBOX</h1>
<p  data-anim="chars" data-stagger=".026" data-delay=".9">Every incident, on tape.</p>
<h2 data-anim="scramble">At 03:12 checkout stopped</h2>
<h2>Built for <span data-anim="flip" data-words="teams|platforms|enterprises" data-step="0">teams</span></h2>
```

- **`chars`**: every character rises .42 em and fades in. `data-stagger` is the gap (default .03 s), `data-order` the order (`reverse`, `center`, `random`). The whole line takes gap x characters + .55 s: under 1.5 s means under about 30 characters.
- **`tracking`**: characters start pulled towards the centre of their line and spread to their place; `data-spread` is how far (default .2, a fraction of the distance from the centre). Overlap at the start is intended.
- **`scramble`**: every character shows a seeded random glyph of its own kind (capital, lowercase, digit; punctuation stays) and settles left to right with jitter. Cells keep the real character's width, so nothing reflows; a wide random glyph may overlap a narrow neighbour for a moment.
- **`flip`**: a split-flap with the width of the widest word reserved. Word *k* shows from step `data-step` + *k*; the slide gets that many extra steps. The markup keeps the first word as the fallback; `aria-label` follows the current word.

What they all guarantee: the real text is in `aria-label` (the pieces are `aria-hidden`), the layout is the authored one (measured once at load, kerning restored, no reflow), no inline style is left at rest, and `prefers-reduced-motion` turns them into a fade. Limits: plain text and inline tags; do not split a word across a tag; text inside SVG `<text>` is not supported. `data-fit` runs before the split, so it works.

Taste: one kinetic title per section. Never `chars` on a paragraph, never `scramble` on a title that is not about noise, never two of them on one slide unless one is a `flip` word inside the other's sentence.

## Statements: "Setup:|*payoff*"

A statement is one claim in two beats: a small setup line, then the payoff, larger and in the accent colour.

```html
<h2 class="stmt" data-say="Incidents leave no tape.|*You debug from rumours.*"></h2>
<h2 class="stmt" data-say>Pilot on 20 services.|*Decide by 14 October.*</h2>   <!-- the element's own text is used -->
<p class="proof">Illustrative: median 3 h 40 min to reproduce a production bug.</p>
```

- `|` separates the setup from the payoff (a `|` inside the payoff is a line break); the asterisks around the payoff are optional. From code: `Deck.say(el, 'Setup:|*payoff*')`.
- The result is `<span class="say-s">setup</span> <em class="pay">payoff</em>`: semantic emphasis, and the slide title reads "Setup: payoff". The element's font size is the payoff (110-160 px, see the table above); the setup is .36 em, at least 26 px.
- **At most 8 words per statement, setup and payoff together.** The runtime warns in the console above that. If it does not fit in 8 words, it is two statements or a paragraph, and this is the wrong slide.
- It works with `data-fit="3"` (the whole block shrinks together) and with animation: `data-anim="rise" data-stagger=".4"` on the statement makes the setup arrive first and the payoff .4 s later.
- Theme it with custom properties on `.deck` or the slide: `--dk-say-setup` (colour), `--dk-say-pay` (default `--accent`), `--dk-say-setup-size`, `--dk-say-pay-size`, `--dk-say-setup-font`, `--dk-say-setup-weight`, `--dk-say-setup-tracking`, `--dk-say-setup-transform`, `--dk-say-gap`, `--dk-say-pay-lh`, `--dk-say-pay-weight`.
- **`<p class="proof">`** is the small caption under a claim: its source or the arithmetic behind it ("Median of 1,204 incidents, Q3"). 26 px, muted, tabular figures; `--dk-proof`, `--dk-proof-size`, `--dk-proof-font`, `--dk-proof-width`. It usually arrives one click after the claim. Figures that are made up say so here.

## Speaker notes

Notes are text too, and presenter view shows them at 26 px (`A−`/`A+` change that). Write them as you would say them: short paragraphs, the transition line to the next slide at the end. Tie a passage to a click with `data-step="N"`, `class="click"` or a leading ▸; presenter view lights the passage of the current click (11-presenting.md).
