# Slide design

## Defaults to move away from

Models have a house taste for slides: a dark navy or near-black background, a purple-to-blue gradient, glassmorphism cards, three icon cards in a row, emoji bullets, every block centred, big rounded corners everywhere. None of it is wrong when chosen, but as a default it makes every deck look the same. If no style is given, derive one from the subject:

- food, hospitality: receipts, kitchen tickets, chalkboards, enamel signs (the demo deck);
- logistics, travel: departure boards, luggage tags, route maps;
- finance: annual-report typography, ledger rules, one ink colour;
- science, health: lab notebook, specimen labels, journal figures;
- developer tools: terminal, man pages, diff colours used with meaning;
- climate, energy: survey maps, engineering drawings, weathered print.

Say the choice and the reason in one line of the plan.

## The canvas

1920×1080 pixels. A grid keeps slides consistent:

| | Value |
|---|---|
| Outer margin | 150–160 px left and right, 110–130 px top, 90 px bottom |
| Columns | 12, gutter 40 px (content width 1600 px) |
| Title baseline | same position on every content slide |
| Safe area | nothing important within 60 px of the edge; `check` flags under 38 px |

Positions of the kicker, title and footer do not move between slides. When they stay put, the eye goes to what changed, and `camera` and `morph` transitions look intentional.

## Palette

4–6 colours with roles, defined as CSS variables on `:root`:

| Role | Share of a slide | Example (demo deck) |
|---|---|---|
| background | most | `--paper: #f2eee5` |
| ink | text, main shapes | `--ink: #1c1b18` |
| muted | labels, axes, secondary text | `--muted: #6e685c` |
| rule | grid lines, separators | `--rule: #cbc3b2` |
| accent | the one thing to look at | `--waste: #dd4428` |
| second accent | only when it has a meaning | `--saved: #2b7a4b` |

Rules:

- The accent covers under 10% of a slide and means the same thing everywhere. In the demo, red is always waste and green is always saved; neither is ever decoration.
- Grey out what is context. A chart with one coloured bar and three grey ones says more than four colours.
- Text contrast: at least 4.5:1 for body text, 3:1 for 40 px and above. Projectors wash out contrast; test with the lights on. `check` measures it (`low-contrast`, 12-export-qa.md).
- A saturated accent is usually 3 to 4:1 on a light background: fine for a 250 px number, not for a 24 px label. Give small text its own darker variant of the same hue (`--waste-text`, `--saved-text` in the demo) and keep the accent for big numbers, bars and lines. The same goes for the second accent.
- Text on a filled disc or button needs 4.5:1 against the fill: white on `#dd4428` is 4.05:1, so the demo's numbered discs use the darker text variant as the fill.
- Light backgrounds survive projectors and PDFs better. Dark decks need higher contrast and fewer thin lines.

Starting palettes (background, ink, muted, accent). Muted is at least 4.5:1 on the background in every row; the last column says what the accent may do as text:

| Direction | Background | Ink | Muted | Accent | Accent as text |
|---|---|---|---|---|---|
| Receipt | #f2eee5 | #1c1b18 | #6e685c | #dd4428 | 40 px and up (3.7:1); `#ba2100` below |
| Editorial (template) | #f4f2ee | #16161a | #6f6b63 | #2b4fe0 | any size (5.7:1) |
| Swiss poster | #f1efe9 | #111111 | #6b6b6b | #e3242b | 40 px and up (4.0:1) |
| Ledger | #fbfaf5 | #1f2a44 | #6a7284 | #0f7b5f | any size (5.0:1) |
| Blueprint | #17324d | #eaf2f8 | #8fb0c9 | #ffb000 | any size (7.2:1) |
| Terminal | #0f1110 | #d8f3dc | #6b8f71 | #ffd166 | any size (13.1:1) |
| Lab notebook | #fdfcf7 | #22302a | #6b7570 | #c44536 | any size (4.8:1) |

### Generate a palette

Start from one accent and let the script derive the rest in OKLCH, with the contrast rules above guaranteed and measured:

```bash
node scripts/palette.mjs --accent "#dd4428" --name receipt --html receipt-swatches.html
node scripts/palette.mjs --accent "#2b4fe0" --bg dark --second "#ffb000"
node scripts/palette.mjs --accent "#0f7b5f" --bg "#f4f2ee"
```

`--bg` is `light` (a tinted off-white, the default), `dark` (a tinted near-black) or your own hex; `--second` is `auto` (the accent's hue rotated 125 degrees at the same weight, lightness nudged to keep 3:1) or a hex. It prints CSS variables for `:root` and a table of every role with its WCAG 2 ratio and APCA Lc:

```
role         hex      OKLCH               vs bg               APCA Lc  rule
ink          #372a29  L0.300 C0.020 h23   12.02:1             91       >= 7:1        ok
muted        #736260  L0.512 C0.022 h26   5.03:1              70       >= 4.5:1      ok
rule         #c6b6b4  L0.789 C0.019 h26   1.71:1              28       decorative
accent       #dd4428  L0.604 C0.194 h33   3.72:1              59       >= 3:1 large  ok
accent-text  #ca3113  L0.551 C0.194 h33   4.63:1              66       >= 4.5:1      ok
```

- Ink is at least 7:1 (it aims for 12:1), muted at least 4.5:1 (it aims for 5:1; 7:1 on dark backgrounds, where WCAG 2 flatters thin light text).
- `--accent` is your colour untouched. The table says whether it may be text: 4.5:1 and up, any size; 3 to 4.5:1, 40 px and above only; under 3:1, a fill or a line only. `--accent-text` (and `--second-text`) is the same hue darkened on light backgrounds, lightened on dark ones, until it reaches 4.6:1; when the accent already passes it is the accent itself.
- `--on-accent` is the ink or paper tone that reads best on an accent-coloured fill (pure black or white only when neither does); the same for `--on-second`.
- The run exits with code 1 when a guarantee cannot be met, for example a mid-grey custom background that cannot carry 7:1 ink.
- The colour maths (sRGB to OKLab, gamut mapping by chroma, WCAG 2 ratio, APCA SAPC 0.0.98G-4g) is implemented in `scripts/palette.mjs` itself; no dependency. `--json` prints machine-readable output.

Paste the variables into the deck's `:root` and rename them to the deck's own vocabulary (`--paper`, `--waste`). Then run `check`: it is the second opinion, against what is really painted.

## Density

- Under 40 words per step; the title does most of the work.
- One focal element per step. If two things compete, dim one (`data-dim`) or split the step.
- Lists: three to five items, each under ten words, revealed one per step, the previous one dimmed.
- A table on a slide has at most 5 rows × 4 columns; highlight the row that matters. Bigger tables go in an appendix or a handout.
- Code on a slide: at most 12 lines at 28 px, with the line that matters highlighted.

## Layouts that cover most decks

- **Title**: one claim, one line of context, presenter and date.
- **Statement**: one sentence, huge. For the turn in the story.
- **Big number**: the number (240–380 px), the unit and the comparison in one line under it.
- **Chart + title**: the title states the answer; the chart takes 60–70% of the slide; the annotation sits on the chart, not in a legend.
- **Split**: visual on one side, 2–3 short points on the other.
- **Diagram**: a flow or an architecture that builds node by node.
- **Timeline / roadmap**: one axis, milestones per step.
- **Ask**: the number, the use, the date.

## Containment

Text never leaves the box it sits in, in any frame and with any font:

- Boxes that hold text have a fixed width and a **minimum** height; the content decides the rest.
- Leave 10–15% slack. Webfonts can fail on corporate networks and the fallback is wider; `check --no-webfonts` shows what happens then.
- Titles: `data-fit="2"` keeps them to two lines whatever font renders them.
- Changing values are sized for their widest state: sign, all digits, the unit (`−0.000 kg`). Use tabular figures.
- Labels on shapes (inside a bar, a node, a circle) are checked with the longest label; if it does not fit, put the label next to the shape.
- `check` reports `escapes-box` (text outside a box with a background or border, or outside the SVG rect/circle it sits on) and `off-canvas` (a box past the slide edge). `check --timeline` repeats this on frames mid-animation.

## Imagery

Everything should be drawn: SVG illustrations, HTML mock-ups of UI, charts. That keeps the deck one file, crisp at any size, animatable and exportable. When a real photo or screenshot is needed, embed it as a data URI or put it next to the deck and let `bundle` inline it. A photo covers the full slide or a clean crop of it; small photos in boxes read as clip art.

## Style check before code

Write down: palette with roles, 1–2 fonts, the grid (margins, title position), the one bold decision, what the accent means. Imagine a similar prompt from someone else: if the result would look the same, the style is not tied to the subject yet.
