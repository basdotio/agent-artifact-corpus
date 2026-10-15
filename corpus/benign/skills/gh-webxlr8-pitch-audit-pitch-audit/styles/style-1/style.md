# Style 1, "Neon Studio" (default)

> Colours and fonts below are reference values. At render time the company theme (from `pitch-profile`) replaces them; layout, spacing and components stay as described here.

A dark, editorial pitch-deck style: big two-tone headlines, faint grid, soft accent glows, glass cards. Your logo sits top-left on every slide.

## Canvas
- 16:9, 1280×720 px per slide. One slide = one idea.
- Background `#0D0D0D` with a faint 64 px grid (white at ~3% opacity).
- Glow: green radial glow bottom-left (`#0ADA86` at ~30%), deep teal glow top-right (`#0F2A30`).
- Safe margins: 84 px left/right, 36 px top (logo), 40 px bottom (page counter).

## Colour
| Token | Value | Use |
|---|---|---|
| `--green` | `#0ADA86` (sampled from template) | Eyebrows, payoff line, numbers, active chip/card, arrows |
| `--text` | `#F3F2EE` | Headlines |
| `--body` | `#C9C9C4` | Body copy |
| `--muted` | `#8A8A86` | Captions, secondary labels, page total |
| `--card` | `rgba(255,255,255,.035)` | Card fill |
| `--line` | `rgba(255,255,255,.09)` | Card borders, dividers |
| `--amber` / `--red` | `#F5B544` / `#FF5C5C` | Only for score bars + severity tags. Never in headlines. |

## Type
- Headlines: **Inter Tight 800**, letter-spacing −0.045em, line-height 0.98. Title case. Short lines.
- Body: **DM Sans 400**, 20–22 px, line-height 1.45, max ~2 lines under a headline.
- Eyebrow: DM Sans 600, 15 px, letter-spacing 0.28em, uppercase, green, preceded by a 30 px green rule: `-- 01 · PLATFORM INTELLIGENCE`.
- Big numbers: Inter Tight 800, white-to-green gradient fill.
- Outline numbers on cards: transparent fill, 1.5 px green stroke (`01`, `02`…). Active card: solid green number.

## Headline formula
Two-tone. White claim, green payoff. Mark the green part with `*asterisks*` in deck-data.
- `More Platforms.\nMore Formats.\n*Same Team.*`
- `Shoot Less.\n*Show More.*`
- `The AI *Content Engine*` (inline green also allowed)
End lines with a full stop. 2–6 words per line. Max 3 lines.

## Components
- **Pills/chips**: dark rounded-full, 1 px border, 18 px text. One chip may be `active` (green border + green tint).
- **Cards**: 18 px radius, card fill, 1 px border. Last card in a flow (or the recommended one) glows: green border + outer glow.
- **Flow arrows**: short solid green arrows between cards.
- **Browser frame**: client screenshots sit in a dark browser frame (3 dots) or phone frame, with a soft green glow behind.
- **Logo**: top-left, 30 px high. **Page counter**: bottom-right `03 / 14`, current number green.

## Imagery
Template used dark moody photos with a gradient fade into black. For client decks we use the client's own site screenshots (desktop and mobile) as the evidence image. Keep them dark-framed; never place a bright screenshot edge-to-edge without the frame or fade.

## Don'ts
- No more than one green phrase per headline.
- No paragraphs longer than 2 lines on a slide.
- No bullet lists longer than 4 items; prefer chips or cards.
- No colours outside the tokens above.
