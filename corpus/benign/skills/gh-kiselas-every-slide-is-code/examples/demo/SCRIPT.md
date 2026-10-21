# Demo deck: Tare, a seed pitch in 15 slides

A pitch for a fictional product, built strictly by this kit. Tare is a scale for restaurant kitchens: it weighs what gets binned, asks why, and prints tomorrow's prep list so the kitchen cooks less. Every number is illustrative, and the title slide says so.

## Passport

| | |
|---|---|
| Length | 15 slides, 40 rest frames, about 8 minutes spoken; the video timeline runs 117 s |
| Canvas | 1920×1080 |
| Style | thermal receipt: paper `#f2eee5`, ink `#1c1b18`, muted `#857f72`, rule `#cbc3b2` |
| Colour meaning | red `#dd4428` is always waste, green `#2b7a4b` is always saved. Nothing else is coloured |
| Type | Big Shoulders Display 800–900 for titles and numbers (kitchen signage), IBM Plex Mono for text (the receipt) |
| Bold decision | the deck is a receipt roll: the camera feeds down it inside a chapter and tears it off between chapters |
| Motif | the scale read-out: it tares a full pan to 0.000 on the title slide, and again on the last one |

## Transitions and their meaning

| Transition | Meaning | Where |
|---|---|---|
| `camera` down the roll | the same chapter continues | inside each chapter |
| `tear` | a new chapter | 4→5, 7→8, 10→11, 14→15 |
| `morph` | the same object, new role | the device (5→6) |
| `zoom` into a point | look inside | from the "prep ticket" node into the ticket (6→7) |

## Storyline (titles only)

**I · The problem**
1. Tare: *Restaurants throw away a tenth of the food they buy.*
2. A tenth of the food a kitchen buys goes in the bin
3. Most of it is binned before it reaches a plate
4. Food costs outran menu prices

**II · The product**
5. A scale that knows what it is weighing
6. Every scrap becomes tomorrow's prep list
7. The prep list writes itself

**III · The proof**
8. Pilot: 12 kitchens, 6 months, 41% less waste
9. Each kitchen keeps $3,900 a month
10. Paying kitchens, up 38% a month

**IV · The plan**
11. Room to grow: 1.1 million kitchens
12. The only tool that weighs waste and changes the prep
13. Eighteen months to a thousand kitchens
14. Raising $4M
15. Weigh it. Waste less.

## Slides

| # | Visual | Steps |
|---|---|---|
| 1 | wordmark in a mask reveal; the scale read-out shows 2.418 kg, TARE lights, it settles to 0.000 with a spring wobble | 0 |
| 2 | unit chart: 100 squares, one per kilo bought, appear in a diagonal wave | 1: ten squares go red, "10%" counts up, the cost in one line |
| 3 | horizontal bars by cause, sorted | 1: the three kitchen causes turn red, a bracket: 86% never reaches a plate |
| 4 | two index lines draw with the gap between them filled | 1: "16-point gap = margin lost" |
| 5 | the device drawn as a blueprint: platform, pan, scraps, display, ticket stub, dimension | 1–3: numbered badges and callouts |
| 6 | the device morphs into the first node of a loop | 1–3: Tag, Forecast, Prep ticket; the loop closes and dots run along it |
| 7 | the ticket feeds out of the printer in small increments (custom `feed` animation) | 1: yesterday's quantities struck, today's count down, "27% less" |
| 8 | waterfall: 1,000 kg before | 1–3: each cause drops off; the green 590 kg bar and −41% |
| 9 | $3,900 counts up, a donut of where it comes from | 1: "15×" lands in the hole; Tare costs $249 |
| 10 | growth line draws with points | 1–3: pilot converts, first chain signs, 84 kitchens · $251K ARR |
| 11 | nested circles resting on one baseline | 1–2: full-service, then the 2029 target in green |
| 12 | 2×2 by category (no real companies), dots in a stagger | 1: Tare lands in the empty corner with a pulse |
| 13 | quarterly roadmap, today marked | 1–4: the solid line runs to each milestone |
| 14 | $4M, use-of-funds donut | 1: what it buys |
| 15 | the close, the read-out tares one last time | 0 |

## Commands

```bash
cd export && npm install
node deck.mjs check ../examples/demo/deck.html
node deck.mjs sheet ../examples/demo/deck.html sheet.png
node deck.mjs pdf   ../examples/demo/deck.html tare.pdf
node deck.mjs pptx  ../examples/demo/deck.html tare.pptx
node deck.mjs gif   ../examples/demo/deck.html teaser.gif --hold 1.1 --to 34.4 --fps 10 --width 800
```

## What the checks caught while building it

- "560 mm" at 11 px on the shrunken device copy (slide 6): the dimension lines are dropped from the small version.
- The chart caption of slide 8 overlapped the first bar's value: moved to the top right.
- Every large SVG number rendered at 26 px, because `.art text { font-size }` beat the `font-size` attribute. That is why `Deck.svg()` writes presentation values to inline style.
- The grid of slide 2 flew in from the corner of the SVG: the squares needed `transform-box: fill-box`.
- The stage canvas was stuck at its default 300×150 and stretched: fixed in the runtime, found on the transition strip.
- The scale read-out fit at rest, but while it settled after taring, "−0.825" stuck 29 px out of its frame. Found by `check --timeline`; the read-out is now sized for "−0.000 kg".
- With Google Fonts blocked, "printed at 6 a.m." spilled out of a node with a fixed height. Found by `check --no-webfonts`; nodes now have a minimum height and titles `data-fit="2"`.
- The ticket's `feed` animation read `offsetHeight` every frame; it now measures once in `init`.
