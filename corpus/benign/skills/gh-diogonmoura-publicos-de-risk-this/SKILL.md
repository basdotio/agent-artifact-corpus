---
name: de-risk-this
description: Use when the user has a product idea, feature request, roadmap, or team setup and wants it interrogated before they commit — the four risks, outcomes instead of features, or a strong/weak team diagnosis.
---

# De-Risk This

Applies Marty Cagan's *Inspired* (2nd edition, 2018) to the user's own product work.

The value of this skill is not "do discovery" — the user already knows the concept. The
value is that **the gates block**. The book's spine is *risks resolved before the
commitment, not after*, and the only way to honour that in practice is a procedure
that refuses to return a verdict while a risk is unaddressed.

Assumption: the user is the empowered team. This skill applies pure Cagan, with no
allowance for organisational constraint. If it is ever pointed at a large-org
situation they do not control, read `references/limits.md` first — the model's
assumptions stop holding.

## Status

Stage 1 (Manual) — 0/3 clean runs. Show the user every output; never write to an
external system.

## Before you start

Read all six reference cards. Do not proceed until you have read every one:

1. `skills/de-risk-this/references/four-risks.md`
2. `skills/de-risk-this/references/discovery-techniques.md`
3. `skills/de-risk-this/references/product-vs-project-model.md`
4. `skills/de-risk-this/references/roadmaps-and-okrs.md`
5. `skills/de-risk-this/references/strong-vs-weak-teams.md`
6. `skills/de-risk-this/references/limits.md`

## Model tiers

| Step | Model | Why |
|------|-------|-----|
| Mode classification, when the user did not name one | `haiku` | Four-way categorical call on a short input |
| Extract from a pasted roadmap / spec / doc — enumerate items, dates, owners, claimed outcomes | `haiku` | Purely mechanical; keeps a long document out of Opus context |
| All gates, interviews, diagnosis, verdicts, and the write to `work/` | `opus` | The taste layer; reserve the strongest model for judgment and the final write |

Skip the Haiku extraction pass on inputs under roughly 500 words — dispatching a
subagent to enumerate the items in a five-line feature request costs more than it
saves.

## Safety defaults

- **Never** write to any external system (Notion, Linear, Confluence, etc.). Output goes
  to chat and `work/product-decisions/` only.
- **Fail loudly.** If a gate has no evidence, it is BLOCKED. Never infer value from
  The user's enthusiasm, from how well-argued the idea is, or from how much work has
  already gone into it.
- **Never pass a gate on authority or on request count.** "A customer asked" and
  "this came from leadership" are both zero evidence. Say so.
- **No verdict before all four gates are resolved** — each either closed with
  evidence, closed as an explicit accepted unknown, or marked NOT REACHED because an
  earlier gate blocked.
- **Every blocked gate must name a cheapest next move** — specific, cheap, time-boxed.
  A gate left open with no named test is this skill failing, not working.
- If Cagan is genuinely thin on the situation (see `references/limits.md`), say that
  instead of forcing the framework.

## Inputs

One of:
- An idea, feature, or request the user is considering building → `de-risk`
- A roadmap, backlog, or plan organised by feature and date → `reframe`
- A team, project, or way of working they want examined → `diagnose`
- A situation they want to think through out loud → `coach`

## Procedure

### 1. Pick the mode

Ask which mode. Propose one if it is obvious — a pasted roadmap with dates suggests
`reframe`, a single feature idea suggests `de-risk` — but confirm before proceeding.

| Mode | Input | Output |
|------|-------|--------|
| `de-risk` | An idea or feature | Four gates, then go / discover-first / kill |
| `reframe` | A feature roadmap | Business context + outcomes + honest date commitments |
| `diagnose` | A team or initiative | Strong/weak read, named dysfunctions, what to change first |
| `coach` | Anything | Socratic drill. No document. |

### 2. Mode: `de-risk`

Run the four gates **in order**. Value first — if value blocks, mark the rest NOT
REACHED and stop. Working the other three on an idea nobody wants is the exact waste
the book exists to prevent.

For each gate:

1. **State the question** in terms of this specific idea, not in the abstract.
2. **Ask the user what evidence they have.** Do not guess on their behalf.
3. **Judge the evidence** against `references/four-risks.md`. Requests, competitor
   behaviour, conviction and invented business-case numbers are not evidence.
4. **Close or block.**
   - CLEARED — the evidence is real, and say what it was
   - ACCEPTED UNKNOWN — the user explicitly chooses not to find out; record what it
     costs if they are wrong
   - BLOCKED — and name the **cheapest next move** that could falsify the belief

Gate order and ownership:

| # | Gate | The question |
|---|------|-------------|
| 1 | Value | Will people want this enough to do something costly? |
| 2 | Usability | Can they figure out how to use it? |
| 3 | Feasibility | Can this actually be built, with what exists today? |
| 4 | Business viability | Does it work for the user — legal, cost, support, brand, and how it gets sold or distributed? |

Then the verdict, one of exactly three:

- **GO** — all four resolved. State what is being committed to and what would make
  them stop.
- **DISCOVER FIRST** — name the single cheapest test, its time box, and what result
  would kill the idea. Do not commit a date.
- **KILL** — say plainly why, and what would have to change to reopen it.

A verdict is not complete without a **kill criterion**: the specific observation that
would make the user stop. If nothing could, the belief is not falsifiable and the gate
did not really clear.

### 3. Mode: `reframe`

1. (Haiku, if the input is long) Enumerate every item: name, date, stated owner, and
   any claimed outcome.
2. For each item, run the reframing test in `references/roadmaps-and-okrs.md`:
   - What outcome is this feature a guess at?
   - What measure tells us the outcome moved?
   - Is the date a high-integrity commitment or a date somebody typed?
   - If it did not move the outcome, would we notice, and would we stop?
3. Flag every item that cannot answer question 1. Those are preferences, not roadmap
   items — say whose.
4. Produce: product vision (if absent, say it is absent — do not invent one),
   strategy as a *sequence* of segments, objectives in OKR form, and a short list of
   genuinely high-integrity date commitments.
5. Say what the user would have to tell anyone expecting the old list.

### 4. Mode: `diagnose`

1. Name the context first — startup, growth, or established
   (`references/product-vs-project-model.md`). The advice differs and a diagnosis
   without it is generic.
2. Run the six root causes of project-model failure as a literal checklist. Three of
   six or more means it is a project, not a product — say so in those words.
3. Run the strong/weak team table (`references/strong-vs-weak-teams.md`) row by row.
   Cite the specific observation behind each call. No unsupported rows.
4. Run both diagnostic checklists: innovation loss, velocity loss. For decisions
   climbing the hierarchy, separate lack of **context** from lack of **competence**.
5. Check the discovery/delivery error asymmetry: is error tolerated in discovery and
   intolerable in delivery, or has it been confused in one direction?
6. Rank findings by what is changeable **first**, not by severity. A severe finding
   nobody can move is worth less than a small one they can fix this week.

### 5. Mode: `coach`

Socratic. One question at a time, following the thread of the answers. Do not
produce a document and do not summarise the book at them.

Anchor questions, adapted to the situation:
- Does this team get a problem with a desired outcome, or a feature with a date?
- When was the last time an idea here was abandoned because of evidence gathered
  *before* building?
- Who — by name — answers for the business viability of this?
- How many decisions a week climb the hierarchy for lack of context rather than lack
  of competence?

Stop when the real problem has been named, not when the questions run out.

### 6. Write-up

For `de-risk`, `reframe` and `diagnose`, save to
`work/product-decisions/YYYY-MM-DD-<slug>.md` after the user has seen it in chat.
`coach` produces no file.

The file records the decision *and its reasoning*, so that a later run can be
compared against it — including the kill criterion, which is the part that is
worthless if it is not written down before the outcome is known.

## Judgment rules

_(Empty — fill in as corrections are made.)_
