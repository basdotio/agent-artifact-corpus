---
title: Tare, a seed pitch (replace with your deck)
type: pitch
length: 8 min
rate: 140 wpm
audience: seed investors at demo day
thesis: Kitchens bin a tenth of what they buy, and a scale that writes tomorrow's prep list cuts it by 41%, so we are raising $4M to reach a thousand kitchens.
through-line: waste per kitchen, in kg per week (it falls, jumps back once when the pilot misses, then falls for good)
bookend: the scale read-out that tares to 0.000 on slide 1 tares again on the last slide, now with the saving printed under it
default-transition: camera
---

# SCRIPT.md: the deck as a table

Write this before any slide. One row is one slide. `scripts/plan.mjs` reads the table:

```bash
node scripts/plan.mjs SCRIPT.md --check       # the titles alone in order, then the story lint
node scripts/plan.mjs SCRIPT.md --animatic    # steps, words, time per slide, the whole timeline
node scripts/plan.mjs SCRIPT.md --new deck.html   # a skeleton deck, one section per row
```

The header block above is read by the tool; the table below is the source of the deck. Replace the example
(a pitch for a fictional product) with your own rows. The wording of every row is the wording of the slide.

| # | Chapter | Title (a claim, one full sentence) | Steps | Visual | Transition | Through-line | Note |
|---|---|---|---|---|---|---|---|
| 1 | I · Problem | Restaurants throw away a tenth of the food they buy | 0 | number: the scale read-out tares a full pan to 0.000 | - | 2.4 | Open on the read-out settling to zero, before any words. Every number in this deck is illustrative and the title slide says so. |
| 2 | | A tenth of what a kitchen buys goes in the bin | 1 | chart: unit chart, 100 squares, ten turn red | camera | 2.4 | One square per kilo bought. Ten of them are red: that is the bin. Let the room count them before you say the number. |
| 3 | | Most of it is binned before it reaches a plate | 1 | chart: bars by cause, three kitchen causes in red | camera | 2.4 | Overproduction, trim and spoilage are all decisions made in the kitchen, not on the plate. Guests leave very little. |
| 4 | | Food costs outran menu prices, so the margin went | 1 | chart: two index lines with the gap filled | camera | 2.4 | Costs rose sixteen points faster than prices in three years. The gap is the margin, and the owners feel it every Monday. |
| 5 | II · Insight | Waste is a forecasting problem, not a discipline problem | 0 | none | tear | 2.4 | Kitchens are not careless, they are guessing tomorrow with no record of yesterday. Nobody weighs what they throw away. |
| 6 | III · Product | A scale that knows what it is weighing | 3 | diagram: the device as a blueprint | morph | 2.4 | It sits under the bin. Staff tap a reason. It costs the kitchen about ten seconds per bin. |
| 7 | | Every scrap becomes tomorrow's prep list | 3 | diagram: loop of tag, forecast, prep ticket | - | 1.8 | The loop closes at six in the morning, when the ticket prints with today's quantities already reduced. |
| 8 | IV · Why now | Cheap load cells and thermal printers made this a $249 device | 1 | chart: cost of the hardware over ten years | tear | 1.8 | Five years ago the same device cost ten times more. That is why nobody built it for kitchens. |
| 9 | V · Traction | Pilot: 12 kitchens, 6 months, 41% less waste | 3 | chart: waterfall from 1,000 kg to 590 kg | camera | 3.1 | Waste rose in month two, when the pilot kitchens over-trusted the forecast. The fix is the reason for the second product. |
| 10 | | Paying kitchens grew 38% a month since the pilot ended | 3 | chart: growth line with three points | camera | 1.4 | Eighty-four kitchens and 251 thousand dollars of annual recurring revenue, all inbound from the pilot chains. |
| 11 | | The only tool that weighs waste and changes the prep | 1 | diagram: 2x2 by category, no real competitors named | camera | 1.4 | Scales report and prep software guesses. We are the only one that closes the loop, and nobody else has the data. |
| 12 | VI · Ask | We are raising $4M to reach a thousand kitchens by 2028 | 1 | chart: use of funds donut | tear | 1.4 | Sixty percent hardware and support, twenty-five percent forecasting, fifteen percent go-to-market. Back to the read-out: tare it once more. |

## Header

| Key | Meaning |
|---|---|
| `title` | the deck's title: goes into `<title>` |
| `type` | `tech-talk`, `pitch` or `product-launch`: picks the expected spine, the closing ask and the slides-per-minute band (03-story.md) |
| `length` | the talk length: `8 min`, `1:30`, `45 s`. Timing and the word budget are checked against it |
| `rate` | speaking rate in words per minute; defaults to 130 (tech talk), 140 (pitch), 125 (launch) |
| `thesis` | one sentence: what the room knows or does at the end |
| `through-line` | the metric, motif or running example that changes across the deck |
| `bookend` | which image opens the deck and returns, transformed, at the end |
| `default-transition` | the deck's `data-transition`; rows override how each slide enters |
| `audience` | free text, not checked |

## Columns

| Column | What goes in | Notes |
|---|---|---|
| `#` | the slide number | |
| `Chapter` | the spine step this slide belongs to; leave empty to continue the chapter above | the spine check matches keywords in this column |
| `Title` | the slide's claim as a full sentence with a verb | becomes `data-title` and the `h2`; the title test reads this column alone |
| `Steps` | a number, or the text of each click separated by `;` | `3` makes three placeholders; `bars turn red; bracket` makes two with those words. Text counts as words on screen |
| `Visual` | `kind: description`; kinds: `chart`, `diagram`, `code`, `photo` (screenshot, mock-up), `number`, `none` | `none` is a decision (a statement slide); an empty cell is not. Two kinds: `chart + diagram`. More than one chart on a slide is flagged |
| `Transition` | how the slide enters: `camera`, `tear`, `morph`, `zoom`, `dip`, `push`, `fade` ... (06-transitions.md); `push:left`, `zoom@960,540` set direction and origin; `-` inherits the default | more than three distinct types is flagged |
| `Through-line` | (optional) the value of the running metric or motif on this slide | with three or more numbers the check wants at least three changes and one reversal |
| `Note` | what you will say: full sentences | goes into `<aside class="notes">`. Its length sets the time estimate |
| `Words`, `Sec` | (optional) extra words on screen at the last step; a fixed time for the slide (`45 s`) | `Sec` overrides the estimate |

Rules the check enforces are in 03-story.md; the ones that are heuristics say so.
