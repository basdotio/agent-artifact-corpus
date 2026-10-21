# Prompting: how to brief a deck

## What a good brief contains

- **The decision or the change.** What should the audience do, believe or approve at the end? "Approve a $400K pilot", "pick vendor B", "join the waitlist". A deck without a decision is a report.
- **The audience and the room.** Investors in a 20-minute slot, a board reading it cold as a PDF, 300 people at a conference, one skeptical CFO. This sets density, tone and how much the slides must work without the speaker.
- **The raw material.** Numbers, quotes, the product, what was tried. Paste it; do not describe it. Say which numbers are real and which are placeholders.
- **Length.** Minutes or slides. Rule of thumb: one slide per minute for a talk, fewer and denser for a read-alone PDF.
- **Style in words, if it matters.** "Like a railway departure board", "Swiss poster", "lab notebook", "annual report from 1970". Not a mood board. If you have a brand, give the colours and fonts.
- **What to avoid, by name.** "No gradients, no icon grids, no stock-photo feel, no centred bullet lists." A general "don't make it look like AI" swaps one default for another.

## Two modes

**Short, about the subject.** When you want the model to shape the story and the look.

```
Pitch deck for a seed round: a scale for restaurant kitchens that weighs food waste
and prints tomorrow's prep list. 12 slides, 8 minutes. Invent illustrative numbers
and say so on the title slide.
```

**Precise, about the structure.** When the story is fixed and you need the build.

```
Deck from the outline below, one slide per line, the line is the slide title.
Slide 4: waterfall chart, one bar per click: 1,000 → −230 → −110 → −70 → 590 kg.
Slide 7: morph the device from slide 6 into the first node of the flow.
Transitions: camera within a section, tear between sections, nothing else.
```

## Templates

The short templates below suit small decks (up to about ten slides). For a technical talk, a pitch or a launch that has to hold an argument for 8-30 minutes, use the script-first prompts in the next section.

### Startup pitch
```
Seed pitch for [product] in [N] slides for [investors / accelerator demo day].
Story: problem → why now → product → how it works → traction → market → competition → business model → team → ask.
Numbers: [paste; mark illustrative ones].
Style: derive it from what the product touches physically; explain the choice in one line.
One chart per claim, the title states the answer. End on the ask and use of funds.
Plan first (titles, steps, transitions), then code, then check and a contact sheet.
```

### Product launch / keynote
```
Launch keynote for [feature], [N] minutes, projected on stage.
Open with the moment the user feels the problem, then reveal the product with a morph
from the old way to the new way. Three features, one slide each, each with a live-looking
UI mock built in HTML. Big type, little text, everything else in speaker notes.
```

### Internal idea / proposal
```
Proposal to [leadership team] to [decision]. They will read the PDF before the meeting.
Structure: the situation, the complication, the question, our answer (SCQA).
Each slide must work without me: full-sentence titles, annotated charts, sources in the footer.
Options slide with 3 options and the one we recommend, costed. Last slide: the decision and the date.
```

### Quarterly / board review
```
Q[n] review for the board, [N] slides. Lead with the three numbers that matter and whether
each is on plan. Then what went well, what did not, what we changed, the plan for next quarter.
Every chart shows plan vs actual. Red only for misses.
```

### Tech talk
```
Conference talk on [topic], 25 minutes, projected. Audience: senior engineers.
Diagrams build step by step with the explanation; code on slides at most 12 lines, 28 px,
with the line that matters highlighted. One running example through the whole talk.
```

## Script first: prompts for talks, pitches and launches

For anything that has to make an argument over minutes, the agent writes the script before any slide: `SCRIPT.md` (template: `template/SCRIPT.md`, method: 03-story.md), checked by `scripts/plan.mjs`. The three prompts below force the same loop: script, `--check`, `--animatic`, wait for approval, skeleton, then slides. Fix the script rows while they are cheap; do not let the agent start slide code before you have said yes.

### Technical talk
```
Conference talk on [topic], [N] minutes, projected. Audience: [senior engineers / SREs / ...].
Follow SKILL.md and 03-story.md; type: tech-talk.
1. Write SCRIPT.md from template/SCRIPT.md: the header (thesis in one sentence, length, through-line,
   bookend), then one row per slide. Spine: problem -> failed attempts -> mechanism -> proof/benchmark
   -> how to adopt. One running example through the whole talk: [the service / request / build].
   The through-line is [p99 latency / build time / cost]: it must change at least three times and
   get worse once (the failed attempt). Titles are claims. Every slide has a Visual decision; code at
   most 12 lines, diagrams build step by step, the benchmark chart shows a baseline, hardware and method.
2. Run `node scripts/plan.mjs SCRIPT.md --check` and `--animatic`, fix every warning you agree
   with, and show me the titles-alone list, the animatic and the warnings you left, with the reason.
3. Stop and wait for my OK.
4. Then `node scripts/plan.mjs SCRIPT.md --new talk.html`, build the slides one chapter at a time,
   check after each chapter (`node export/deck.mjs check` and `sheet`), and finish with the last
   slide returning to the first image.
Real numbers: [paste]. Anything you invent is labelled as illustrative.
```

### Investor / idea pitch
```
Pitch for [product], [N] minutes, [seed investors / demo day / leadership]. type: pitch.
1. Write SCRIPT.md first: thesis (what they know and do at the end), spine: problem -> insight ->
   product -> why now -> traction -> ask, [12] slides. Through-line: [waste per customer / hours per week]
   with one reversal (the pilot that missed, the churn we fixed). Bookend: the image on slide 1 comes
   back on the last slide changed, and carries the ask: [amount, use of funds, date].
   One chart per claim, the title states the answer. Numbers: [paste; mark illustrative ones].
2. Run `node scripts/plan.mjs SCRIPT.md --check` and `--animatic`. Fix what is right to fix, then
   show me the titles alone, the timeline against [N] minutes, and the warnings you kept.
3. Wait for my approval.
4. Then `--new pitch.html`, style derived from what the product touches physically (one line on why),
   slides one chapter at a time, `check` and `sheet` after each.
```

### Product launch
```
Launch keynote for [product/feature], [N] minutes, on stage. type: product-launch.
1. Write SCRIPT.md first: thesis, spine: before/after -> the moment -> how it works -> proof ->
   availability. Before/after at human scale: one person, one afternoon, old way against new way.
   The moment is a morph from the old way to the new. At most three features, one slide each, each
   with a UI mock built in HTML. Through-line: [minutes to do the job], from [40 min] to [4 s].
   Big type, little text, everything else in notes. End on availability: what, when, where, how much.
2. Run `node scripts/plan.mjs SCRIPT.md --check` and `--animatic`; show me the titles, the timeline
   and the warnings you left.
3. Wait for my OK.
4. Then `--new launch.html` and build: transitions are a camera within a chapter, one type between
   chapters, and the morph for the moment; nothing else. Check after each chapter.
```

### Named anti-defaults
"Don't make it look generic" swaps one default for another; naming the pattern works. Add the line for the genre to the prompt, or use the same names when reviewing.

| Genre | Name these, and ask for the alternative |
|---|---|
| Technical talk | **The agenda slide** (say the argument in the first minute instead). **The wall of code** (over 12 lines or under 28 px: cut to the lines that matter and highlight one). **The 12-box architecture** (one diagram that builds node by node, one idea per click). **The bare bar chart** (no baseline, no hardware, no units: name all three in the footer). **The feature bullet list** where a mechanism should be. **The terminal screenshot** at 14 px (redraw it as code at 28 px). **"Lessons learned"** as the last slide, and **"Questions?"** (end on the command to run). |
| Investor / idea pitch | **The TAM ring** as the only market argument (start from the first thousand customers you can name). **The hockey stick** without axes or dates. **Three icon cards** for features (one sentence and one picture each, one slide each). **The tick-box matrix** where you win every row (two axes that matter, no real company slandered). **The headshot grid** as the team slide (one line each: what they did that matters here). **"Our vision"** (say what you do on Monday). **"Thank you"** where the ask should be. |
| Product launch | **The "Introducing" blob** (gradient shape, product name, no product). **The six-card feature grid** (three features, one slide each). **"Faster, smarter, simpler"** (the number with its baseline: 40 minutes to 4 seconds). **The floating device mock** with reflection (the real UI, drawn, doing the job). **The vanity count-up** with no comparison. **Release-notes bullets** as a story. **A roadmap** as the last slide (end on availability). |

Two more that apply everywhere: the **fade-in-everything** deck (one transition type inside a chapter, one between chapters), and the **centred everything** layout (a fixed title position, a left-aligned column, one focal point).

## Phrases for iteration

Address slides by number and step, and name the symptom:

- "4.1: the annotation sits on the line. Move it into the gap between the two lines."
- "Slide 7 has 70 words. Keep the title and the chart, move the rest to notes."
- "Titles 3–6 are topics ('Market', 'Team'). Rewrite them as claims."
- "The accent colour is on every slide for different things. Use it only for our product."
- "Too many transitions. Keep camera inside a section and one transition between sections."
- "The bars all grow at once. Stagger them left to right, 80 ms apart."
- "The PDF page for slide 9 does not make sense without the animation. Add a label for the final value."
- "`plan.mjs --check` flags slide 6 as a topic. Rewrite the row in SCRIPT.md as a claim, then regenerate."
- "The animatic says 26 minutes for a 20-minute slot. Cut the two weakest slides in chapter 2, not words from every note."
- "The through-line only ever falls. Add the setback in chapter 3 (the failed attempt makes it worse) and show it on the counter."

## Working habits

- Ask for the plan first: titles only, then the plan with charts and transitions, then code. Plans are cheap to fix; decks are not. For long decks the plan is SCRIPT.md, and `scripts/plan.mjs --check` and `--animatic` are the review.
- Give the whole brief at once, not a series of commands.
- For long decks (30+ slides), build section by section in one file with one theme.
- Keep the numbers in one place (a `DATA` object at the top of the script) so a correction is one edit.
