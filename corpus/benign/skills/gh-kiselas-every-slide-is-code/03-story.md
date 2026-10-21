# Story: what the deck says

A deck is an argument first and a design second. Good motion cannot save a deck whose titles, read in order, do not add up to a case. For anything longer than about ten slides, the argument is written as data before any slide exists: `SCRIPT.md`, checked by `scripts/plan.mjs` (see "The script as data" below).

## The title test

Write the slide titles as a list before anything else. Each title is one full sentence with a verb that states the point of the slide.

| Topic title (weak) | Action title (strong) |
|---|---|
| Market | Room to grow: 1.1 million kitchens |
| Q3 results | Revenue beat plan by 8%; margin missed by 2 points |
| Architecture | Every request passes one gateway, so we can meter it |
| Competition | The only tool that weighs waste and changes the prep |

Read the list aloud. If someone who sees only the titles understands the argument, the story works. If not, fix the list; do not start the slides. `node scripts/plan.mjs SCRIPT.md --check` prints exactly this list, in order, before it lints anything.

## The thesis: one sentence

Before the title list, write what the room knows, believes or does at the end, in one sentence. Concrete, and a little surprising. It goes in the `thesis:` line of the SCRIPT.md header, and it is the test for every slide: a slide whose title does not carry the thesis forward is cut, however good its chart is.

| Weak | Strong |
|---|---|
| "Our platform improves developer productivity" | "Content hashing cut our builds from 40 minutes to 4 because it rebuilds only what changed, and you can adopt it in an afternoon" |
| "We are building the future of kitchens" | "Kitchens bin a tenth of what they buy; a scale that writes tomorrow's prep list cuts that by 41%, and $4M puts it in a thousand kitchens" |
| "Introducing Ledger 3" | "Invoices now write themselves, so the Friday you spend on billing comes back" |

The thesis is also the first and the last title, in two forms: the first slide states the claim, the last slide states what you want done about it.

## Structures that work

**Problem → solution (pitch).** Problem, why now, product, how it works, proof, market, competition, business model, team, ask. Each step answers the question the previous one raised.

**SCQA / Minto pyramid (proposal, read-alone).** Situation (what everyone agrees on), Complication (what changed), Question (what we must decide), Answer (our recommendation), then the supporting arguments, each with its evidence. Put the answer early; executives read the first three slides.

**What is / what could be (keynote).** Alternate between the painful present and the better future, and end on the future with a call to action. The contrast carries the energy; each return to "what is" should feel worse.

**Before → after → how (product launch).** Show the old way at human scale (one person, one afternoon), show the new way doing the same job, then explain how.

**Situation → plan → risks → ask (board, review).** Numbers against plan first, then decisions.

### Spines for the three talks this kit is tuned for

A spine is the order of questions the room asks. Each chapter answers the one before it; the Chapter column of SCRIPT.md names them, and `plan.mjs --check` warns when one is missing (`type:` in the header picks the spine). The shares are starting points for the time of the talk.

| Talk (`type:`) | Chapters, in order, with the question the room is asking | Each chapter needs | Ends on |
|---|---|---|---|
| **Technical talk** (`tech-talk`) | 1 Problem (15%): why should I care? 2 Failed attempts (15%): why not the obvious fix? 3 Mechanism (35%): so what actually works? 4 Proof / benchmark (20%): how do you know? 5 How to adopt (15%): what do I do on Monday? | 1 a number or an incident; 2 the obvious approach, shown failing on the running example; 3 a diagram that builds step by step, code of at most 12 lines; 4 a chart with a baseline, the hardware and the method in the footer; 5 one command, one first step | the command to run, the repo, the first step |
| **Investor / idea pitch** (`pitch`) | 1 Problem: who hurts, how much? 2 Insight: what do you see that others do not? 3 Product: what is it? 4 Why now: what changed? 5 Traction: is it real? 6 Ask: what do you want from me? | 1 the problem at human scale, then one number; 2 one sentence, huge; 3 the product doing the job; 4 the shift with a date and a number; 5 one chart with the growth or the pilot result; 6 amount, use of funds, what it buys, the date | the ask |
| **Product launch** (`product-launch`) | 1 Before / after: what was it like? 2 The moment: what is new? 3 How it works: why should I believe it? 4 Proof: who has used it, with what result? 5 Availability: can I have it, when, for how much? | 1 one person, one afternoon, old way vs new way; 2 the reveal, a morph from the old to the new; 3 three features at most, one slide each, a UI mock built in HTML; 4 a customer, a number, a screenshot; 5 date, place, price | availability |

Two rules hold for all three. The proof chapter carries a chart or a number, not an adjective. And the middle chapter is the longest: the room came for the mechanism, the product or the how, so that is where the time goes.

## The through-line: something that changes across the deck

A deck of fifteen good slides can still be fifteen separate slides. Something must carry state from the first slide to the last, so that slide 12 could not be swapped with slide 4. Pick one:

- **A metric** that moves: waste per kitchen, p99 latency, minutes per invoice, cost per unit. It is drawn the same way in the same place every time it appears (a chart line, a counter, a bar), so the eye reads the change.
- **A motif** that recurs and transforms: the scale read-out of the demo deck, one object that changes role (`data-morph` moves it between slides), an image that starts blurred and ends sharp.
- **A running example**: one customer, one service, one request, one build. The problem is shown on it, the failed attempts fail on it, the mechanism fixes it, the proof measures it.

It must change at least three times, and it must **reverse at least once**: latency drops, the failed attempt makes it worse, then it drops for good; waste falls, the pilot misses in month two, then it falls again. A number that only goes one way is a chart, not a story; the reversal is the twist that makes the middle interesting. Write it into the `Through-line` column of SCRIPT.md, one value per slide where it appears; `plan.mjs --check` counts the changes and looks for the reversal.

## The ending returns to the first image

The strongest last slide is the first slide again, changed by what the room now knows: the same composition with a different value. The demo deck opens on a scale read-out that tares a full pan to 0.000 and closes on the same read-out taring once more, now with the saving printed under it. A tech talk opens on the 40-minute build log and closes on the same log, four minutes long. Use the same layout and position so the change is what the eye sees; a `morph` or the same `data-morph` key from the last content slide makes it deliberate.

Put the ask on that frame: the last slide stays up during Q&A, so it should be the picture you want remembered, with the decision, the amount, the command or the date on it. The header line `bookend:` names the image; `plan.mjs --check` warns when a deck of eight or more slides has none.

## One idea per slide

- If a slide needs two titles, it is two slides.
- A slide has one focal point: the number, the highlighted bar, the node that lights up. Everything else is quieter (muted colour, smaller, dimmed).
- Builds are how you keep one idea per moment without splitting slides: the chart appears, then the highlight arrives on the click as the speaker says why it matters.
- One chart per slide. Two charts is two questions; `plan.mjs --check` flags it.

## Evidence

- Every number has a unit, a period and a source (footer, 20 px, muted). "41% less waste" means nothing; "41% less food binned per kitchen per month, 12-kitchen pilot, Mar–Sep" means something.
- Compare with something: last year, plan, the competitor, the status quo. A lone number is a decoration.
- Round for the room: $3.9K, not $3,912.47. Keep the precision in the notes.
- Invented numbers in a sample or a mock deck are labelled as illustrative on the first slide.

## Openings and endings

- Open with the problem at human scale or with the one number that makes the room care. Not with an agenda, not with "About us".
- The agenda, if any, is the argument in three lines (template slide 2), not a table of contents.
- End on the ask or the decision and the date. The last slide stays up during Q&A, so it should be the thing you want remembered. "Questions?" and "Thank you" are not endings; the check flags both.

## The script as data: SCRIPT.md

The source of a long deck is a table, one row per slide, written before any slide code. Reading a table costs a minute; reading a rendered deck costs an hour. Start from `template/SCRIPT.md`:

| # | Chapter | Title (a claim) | Steps | Visual | Transition | Through-line | Note |
|---|---|---|---|---|---|---|---|
| 9 | V · Traction | Pilot: 12 kitchens, 6 months, 41% less waste | 3 | chart: waterfall from 1,000 to 590 kg | camera | 3.1 | Waste rose in month two, when kitchens over-trusted the forecast. |

The header (`type`, `length`, `thesis`, `through-line`, `bookend`) makes the talk checkable; the columns decide the visuals before anyone draws them: every slide has a Visual decision (chart, diagram, code, photo, number, or an explicit `none`), a transition tied to a meaning (two or three types for the whole deck), and a note. The table becomes the deck one to one:

```bash
node scripts/plan.mjs SCRIPT.md --check          # the titles alone, in order; then the story lint
node scripts/plan.mjs SCRIPT.md --animatic       # time per slide and the cumulative timeline
node scripts/plan.mjs SCRIPT.md --new deck.html  # a skeleton: one section per row, TODO markers
```

`--check` prints the titles for the title test and flags: titles under four words or with no verb-like word (a heuristic, so read the list yourself), more than three transition types, no closing ask on the last slide, a missing spine chapter for the `type`, more than one chart on a slide, slides with no Visual decision, more than 40 words on screen, the word budget of the notes against the talk length, a through-line that never changes or never reverses, and a missing bookend. `--new` writes each row as a `<section class="slide">` in the template's markup (`data-title`, `data-transition`, `data-step` placeholders, a notes stub, and a visible TODO box where the Visual goes). Fix the script, not the skeleton: edit the row and generate again into a new file.

## The animatic: time before design

Before any slide is designed, the deck exists as titles, steps and notes with placeholders, and you check the clock. `--animatic` prints, per slide, the steps, the words on screen, an estimated time and the running total, and warns when the total is off the target length:

- A slide takes the longest of three things: its note spoken at the header's `rate:` (130 wpm is a talk, 140 a pitch), its words read (1.5 s plus 0.3 s a word), its clicks (3 s plus 2.5 s a step).
- If the notes are stubs the total is a floor, and it says so. Write real notes for the middle chapter first; that is where the time goes.
- Cut or split here. A slide of 2 minutes wants steps; a slide of 8 seconds wants to be merged with its neighbour; a deck 30% over its slot loses whole slides, not words.

Then generate the skeleton, open it with presenter view (`P`) and click through at speaking pace with the timer running. A skeleton with placeholders is enough to feel the rhythm; changing a chapter's order at this stage costs a row, changing it after the charts are drawn costs a day.

## Notes carry the rest

What you will say but the slide should not show goes into `<aside class="notes">`: the full sentence behind a short title, the source, the caveat, the transition line to the next slide ("So where does it go? Mostly before it reaches a plate."). Presenter view shows it; PPTX export keeps it. In SCRIPT.md the notes are the Note column.

## Pacing and reading time

- A talk: about one slide per minute, one to three steps per slide.
- A demo-day pitch: 2–4 minutes, 8–12 slides, almost no text.
- A read-alone PDF: fewer slides, more annotation, every chart self-explanatory. Builds do not exist on paper, so the final step must hold the whole message (00-agent-brief.md, rule 18).

Reading time is the floor for how long a slide stays up; the speaker's words are usually the ceiling:

| Slide | On screen | Stays up at least |
|---|---|---|
| Statement or big number | 6–12 words | 1.5 s + 0.3 s per word: 4–5 s |
| Chart, answer in the title | title + 2–3 labels | 8–12 s, plus the time to say why it matters |
| Diagram building node by node | 3–6 nodes | 3 s per step |
| Code | at most 12 lines at 28 px | 15–25 s: the room reads code slowly |
| Any step | under 40 words at the last step | 3 s |

Slides per minute by talk: technical talk 0.6–1.3 (a mechanism slide can hold 90 seconds), pitch 0.8–2 (12 slides in 8 minutes), product launch 0.7–1.6. Words the speaker can say: about 130 a minute, so a 20-minute talk has a note budget of about 2,600 words; `plan.mjs --check` compares the notes against it.

## Script checklist

- [ ] The thesis is one concrete sentence, and the first and last titles carry it
- [ ] The `type:` spine is complete and in order; the middle chapter is the longest
- [ ] Titles alone tell the argument; every title has a verb
- [ ] Every slide has a Visual decision; no slide has two charts
- [ ] A through-line is in the table, changes at least three times and reverses at least once
- [ ] The last slide returns to the first image and carries the ask
- [ ] Two or three transition types, each with a meaning
- [ ] `--check` has no warnings you cannot explain; `--animatic` is within 10% of the slot
