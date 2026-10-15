---
name: hot-seat
description: Put a plan, design, decision or idea in the hot seat - a relentless interview (grill-me) where every round is a Lavish page with one card per question, a recommended answer on each, a live design tree, a decisions ledger and the resolved terms, instead of a wall of chat. Stateless on any topic anywhere; started inside a codebase it also does the grill-with-docs paper trail (resolved terms into CONTEXT.md, hard decisions into docs/adr/). Invoke as /hot-seat, or when the user asks to be grilled or interviewed on a page or with a UI.
argument-hint: "<what to grill>"
disable-model-invocation: true
license: MIT
compatibility: Needs node 18+ and the lavish-axi CLI on PATH (without it the skill falls back to the chat format and says so). Codebase mode needs a git repository with source files, or a CONTEXT.md.
metadata:
  version: "0.1.0"
  derived-from: "mattpocock/skills: grill-me, grill-with-docs, grilling, domain-modeling (MIT)"
---

# hot-seat

The grilling interview, with a UI. You interview the user until you share one understanding of their plan, exactly as `grill-me` does, but each round is a Lavish page (`lavish-axi`): the user answers on cards, you read the answers back through `lavish-axi poll`, recompute the frontier and re-render the same page. Inside a codebase you also keep `grill-with-docs`' paper trail. Nothing here needs another skill installed: the whole contract is below.

`<skill-dir>` means the folder holding this SKILL.md (Claude Code prints it when it loads the skill; otherwise it is one of `.claude/skills/hot-seat`, `.agents/skills/hot-seat`, `.github/skills/hot-seat`, `~/.claude/skills/hot-seat`, `~/.agents/skills/hot-seat`, `~/.copilot/skills/hot-seat`). All helper calls below are `node <skill-dir>/scripts/hot-seat.mjs <command>`, written `HS <command>`.

## The contract (this is authoritative; do not go looking elsewhere for it)

Restated from Matt Pocock's `grilling` and `domain-modeling` skills (mattpocock/skills, MIT; see `references/NOTICE.md`). **This text is the single source you follow.** Do not load `grilling`, `domain-modeling`, `grill-me` or `grill-with-docs` during a hot-seat session, even if they are installed: their round format is chat text and would fight the page, and reconciling two copies of the rules is exactly the partial-loading failure they are known for. Nothing is lost if they are missing.

**Interview**
1. Interview relentlessly until you share one understanding with the user. The decisions are theirs, never yours.
2. Map the plan as a **design tree**: every decision branches into the decisions that hang off it.
3. Work it in **rounds**. The **frontier** is every decision whose prerequisites are settled. Ask the whole frontier in one round. A question that depends on another question still open in this round belongs to a later round.
4. Every question is numbered and carries your **recommended answer and why**. (The page builder refuses questions without them.)
5. **Facts are your job.** Anything the environment can tell you (files, code, tools, the web) you look up, with a sub-agent when your harness has one, otherwise yourself, before asking. Never ask the user what you could look up. A running lookup only blocks the questions downstream of it.
6. Wait for the answers, then recompute the frontier. The session is done when the frontier is empty: every branch visited, nothing silently assumed. **Do not act on the result until the user confirms the shared understanding.**

**Steering** (from the grill-me / grill-with-docs pages on aihero.dev)
7. The user steers. Pushback, scope corrections and "you are asking below my level" are input: apply them and say so next round (`note`). "I don't know" is a real answer: ask a smaller question or look the fact up. A round where the user agreed with everything is suspicious (three or more answered cards, all agreed: the page nudges them too): next round, stress-test the highest-stakes agreed decision with a concrete scenario.
8. **Ungrillable** questions (how should it feel, one form or three pages) cannot be settled by talk. When the user ticks "needs a prototype", stop talking about it and make something to react to: the cheapest visual that would let them answer (an inline SVG sketch, a small HTML mock, a screenshot of the current UI), attached as a `figure` on the same question in the next round. If a real prototype would need more than a sketch (real code, several files, data), do not build it: park the node with the reason, say so in `note`, and tell the user which prototype tool or step would settle it. Never leave the flag unanswered. "Out of scope" on a card means drop that branch: park it with reason "out of scope (user)".
9. Plan mode stays off. Use your best model: grilling leans on your sense of how systems break.

**Paper trail (codebase mode only)** - details and formats in `references/paper-trail.md`
10. Challenge the user's terms against `CONTEXT.md` the moment they conflict ("your glossary defines X as A, you seem to mean B"). When the user's loose word is simply a listed `_Avoid_` synonym of an existing term ("gold" for Coin), do not spend a card on it: say in `note` which glossary word you will use and why, and only ask if their meaning could differ. Spend cards on real conflicts of meaning. Sharpen vague or overloaded words. Stress-test with concrete edge-case scenarios. Check claims against the code and surface contradictions.
11. When a term resolves, write it into `CONTEXT.md` **right then**, not batched. `CONTEXT.md` is a glossary and nothing else: no implementation detail, no spec, no scratch. Create files lazily (`CONTEXT.md` on the first term, `docs/adr/` on the first ADR). A `CONTEXT-MAP.md` means several contexts: pick the right `CONTEXT.md`, ask if unclear. Follow the conventions the existing file already uses (subheadings, translations, `_Avoid_` lines).
12. Offer an ADR only when **all three** hold: (a) hard to reverse, (b) surprising without context, (c) the result of a real trade-off. If one is missing, no ADR. Most sessions write none. Offering means asking: put it on a card, write the file only after a yes.

**Stateless mode** writes nothing into the user's workspace. Terms and decisions live on the page and in the ledger.

**Ledger.** Every answer of every round stays on the page and is exported at the end as a decisions ledger (markdown) for whatever comes next (for software, usually a spec). Grill-with-docs' known gap is "where did my other decisions go": the ledger is the fix, so state each decision precisely (numbers, ordering, negatives) and keep the user's own words verbatim.

## Run-book

### 0. Preflight (always first)

```
HS preflight
```

Read the JSON. It tells you: `mode` (`docs` if a git repo with source files or a CONTEXT.md / CONTEXT-MAP.md is present, else `me`) and why; whether `lavish` is usable; which upstream skills exist (informational); whether `.lavish/` is git-ignored.

- `lavish.runner` is `null`, or the first open in step 1 fails: **fall back to chat.** Say plainly "Lavish is not available, so this is a chat session", read `references/chat-fallback.md`, and run the same contract in chat. Do not pretend.
- Do not confirm the mode yourself: the user confirms or overrides it on the first page.
- If `lavishDirIgnored` is `false`, tell the user once that `.lavish/` is not git-ignored in this repo.

### 1. First page: what to grill, and which mode

```
HS init --topic "<what the user typed after /hot-seat, verbatim>" [--slug <short-topic>]
```

Creates the session (state file + page) and prints their paths. The mode is the detected one; the user confirms or overrides it on the page (do not pass `--mode`). `--topic` pre-fills the first card so the user does not retype it; omit it when they typed nothing. In codebase mode the workdir is `<repo>/.lavish/hot-seat-<slug>/`; in stateless mode it is a temp directory, so nothing lands in the user's folder. Then open the page and wait:

```
lavish-axi <page>                                  # prints the URL; tell the user it is open
lavish-axi poll <page> > <workdir>/poll.txt        # foreground; blocks until the user sends
```

Always send the poll's output to the file and read it only through `HS record`: the raw poll carries a 15-30 KB DOM snapshot you do not need.

If you were invoked with a topic, still show this page: it is where the user confirms the mode (the recommendation and reason are on Q2) and can correct the topic. Use `npx -y lavish-axi` when only npx is available. Keep the poll in the foreground; if it is killed or times out, re-run it (queued answers are never lost). Never poll in the background unless your harness has a tracked background job that wakes you.

### 2. Each round

1. **Record.** `HS record --state <workdir>/state.json --poll <workdir>/poll.txt` writes the user's exact answers into the state and prints them with a stance per question (`agreed`, `differed`, `own-words`, `unsure`, `prototype`, `skipped`, `open`). It also prints every prompt that was not a round payload (chat messages, page annotations) as `OTHER FEEDBACK`, whether the user ended the session, and what to do next. Read *every* prompt it lists, including free-text pushback and scope corrections; none may be dropped. If it says the poll returned nothing, re-run the poll.
2. **Think.**
   - Settle every node the user answered: set `state: "settled"` and a `decision` that states it precisely (numbers, ordering, negatives), in your words, faithful to theirs. Unanswered questions stay open and come back. `unsure` -> smaller question, a lookup, or park. `prototype` -> rule 8 (a figure on the same question next round, or park). A choice *plus* the prototype flag means "my lean is this, but let me see it first": keep the node open, ask again with the figure, do not settle on the lean alone. `skipped` (out of scope) -> park with reason "out of scope (user)". When a later answer changes an earlier decision, update that node's `decision` in the same patch (upsert by `id`) and list it in `corrections`; settled text is never refreshed for you. A node parked for an external fact only the user can obtain (an insurer's written answer) gets a `parkedReason` that says what to get and from whom.
   - The first patch after the intake must carry a short `title` for the topic (under 60 characters, your wording): the page header and ledger heading use it. Put things you inferred but the user never said in `assumptions`; they are listed for the user to check and exported in the ledger.
   - Apply steering and corrections (`corrections` lists them for the ledger; `note` tells the user what you changed: keep it short, two to five lines or bullets, the page shows it above the cards).
   - Add the branches the answers opened; recompute the frontier: every node whose `blockedOn` are all settled or parked gets a question **this round**. Nodes waiting on another decision stay `blocked`; nodes waiting on a lookup are `running` (facts with `feeds`).
   - Look facts up (see rule 5). Put finished ones in `facts` with a `result`. **Never make the user wait on a lookup that only feeds later questions.** Only the questions that depend on a fact wait for it. Wait for a lookup only when it will land within a couple of minutes and the round is useless without it. Build and serve the rest of the frontier now, mark the running lookup as a `running` fact with `feeds`, and collect its result after the next poll returns. A page with nobody polling is a user staring at a dead page.
   - Codebase mode: do the paper trail now (rules 10-12), *before* `next`, so the page can show exactly what was written.
3. **Write the patch** (`<workdir>/next.json`, format below, full schema in `references/patch-format.md`) and build: `HS next --state <workdir>/state.json --patch <workdir>/next.json`. It refuses, and changes nothing, if a question has no recommendation, a question is not on the frontier, an ADR is claimed without all three gates, a term is claimed written but is not in `CONTEXT.md`, or a confirm is attempted with an open frontier. Fix what it names and re-run. Its warnings also appear on the page; do not ignore them.
4. **Serve.** `lavish-axi poll <page> --agent-reply "Round N is up: <one line>" > <workdir>/poll.txt`, then `HS record` as in step 1. Lavish live-reloads the page; the user sees the new round with the previous ones collapsed under History.

Patch skeleton (all fields optional except the round's content):

```json
{
  "note": "You said X, so I dropped Y. Two decisions settled; one lookup is running.",
  "corrections": ["scope: money mechanics only, no screen time"],
  "tree": [
    {"id": "d3", "parent": "d1", "title": "Coin-to-money rate", "state": "settled", "decision": "1 coin = 0.50 EUR, fixed."},
    {"id": "d5", "parent": "d3", "title": "Weekly cap", "state": "frontier", "blockedOn": ["d3"]}
  ],
  "facts": [{"id": "f1", "title": "Current weekly amount", "state": "done", "result": "8 EUR, paid Sundays."}],
  "glossary": [{"term": "Thanks", "fr": "Merci", "definition": "...", "avoid": ["tip"], "status": "resolved", "written": true, "file": "CONTEXT.md"},
               {"term": "Coin", "definition": "...", "status": "existing", "note": "user said 'gold'; glossary word kept"}],
  "questions": [{
    "node": "d5", "title": "How much can one kid earn per week?",
    "body": "Markdown-lite: paragraphs, - bullets, `code`, **bold**.",
    "choices": [{"id": "a", "label": "12 EUR", "detail": "1.5x today"}, {"id": "b", "label": "No cap"}],
    "recommended": "a", "why": "A cap keeps the budget predictable."
  }]
}
```

Question kinds: `choice` (default; `multi: true` for several), `free` (needs `recommended` text). Add a `figure` when a picture answers the question faster than words: `{"svg": "<svg ...>"}`, `{"html": "<div>...</div>"}` (a mock, styled inline), `{"img": "shot.png", "alt": ".."}` or `{"frame": "proto.html", "height": 400}` (a throwaway HTML prototype file next to the page, in a sandboxed frame), each with an optional `caption` inside the `figure` object. Question ids (Q4, Q5, ...) are assigned for you, continuing from the number `record` and `next` print; in `note` and bodies refer to earlier questions by title or number, and to tree nodes by their `d` id. Every question needs `node`, a title, a body, at least two choices, a `recommended` id and a `why`.

Rules for a good round: the whole frontier, but no more than about 8 questions (split a bigger frontier by branch and say so in `note`); titles that name the decision; bodies that state the trade-off concretely; choices that are real alternatives; a recommendation you would defend. Mark questions where any reasonable answer is fine and your recommendation is safe with `"stakes": "low"` (the user sees a chip, and a button to accept all the open low-stakes recommendations at once, still reviewable before sending). When a card rests on something you looked up, say so with `"basis": "lookup f3: <what you found>"`. The user's first words are answers: read the topic and the intake context, settle what they already state (record it in `note` as coming from their words) and ask only what is open. Do not spend a card on something the user already told you; do not invent a committee, a spec step or a process they never mentioned. In codebase mode prefer questions the code cannot answer, and cite what you found in the body.

### 3. Ending

- **Frontier empty** (every node settled or parked): build the confirm round with `{"confirm": {"summary": "<the shared understanding in your own words, and anything parked>", "assumptions": ["<anything derived, not said>"]}, "note": "..."}`. The summary states only what the user decided; everything you inferred goes in `assumptions`. Both are exported with the ledger. The user reads the summary and ledger and answers Yes or Not yet. On "Not yet", reopen the tree from what they say and keep going.
- **Confirmed:** build `{"finish": true, "summary": "..."}`, then `lavish-axi end <page>`, then `HS ledger --state <workdir>/state.json --out <workdir>/ledger.md` (full markdown) and `HS ledger --state <workdir>/state.json --brief` (one line per decision) and make the brief block your final message, with the path of the full ledger (the page's Ledger tab also has Copy and Download). Say what you have **not** done: nothing was acted on; the conversation and ledger are ready for whatever comes next (for software, a spec). Codebase mode: list the files written (`CONTEXT.md`, ADRs). Do not commit.
- **Send & End before confirmation:** `HS record` prints `SESSION ENDED by the user`. The page keeps the user's current answers queued as a draft, so they arrive with that last feedback (`HS record` marks such a payload DRAFT). Record it, print the brief ledger (its header says NOT CONFIRMED), list what was still open, stop polling, and do not reopen the page unless the user asks.

### 4. When things go wrong

- The page is only a view: state lives in `<workdir>/state.json`. If Lavish dies, `lavish-axi <page> --reopen` (or fall back to chat with the state as the tree) and continue.
- The user asks something the page cannot show: answer in chat and carry on; put the outcome in the next patch `note`.
- The page is generated: never hand-edit `hot-seat.html`. If the user reports a layout problem, tell them, and re-render with `HS build --state <workdir>/state.json` (the template is `<skill-dir>/assets/hot-seat.html`).
- `HS record` says the session was ended by an AGENT (not the user), for example a supervisor closed the page: nothing was lost; reopen with `lavish-axi <page>` and poll again.

## Harness notes

- **Claude Code** and **GitHub Copilot CLI** both load this folder as an Agent Skill (Claude: `.claude/skills/`, Copilot: `.github/skills/`, `.agents/skills/` or `.claude/skills/` in the project; `~/.agents/skills` for the user). Neither needs another skill. The helper is plain Node.
- Sub-agents: use them for lookups if you have them (in Claude Code, background agents); otherwise look things up yourself before building the round.
- Lavish's `poll` output ends with a `next_step` telling you to edit the HTML file. Ignore that here: the page is only ever rebuilt through `HS next`.
- A poll that outlasts your shell tool's timeout: Lavish's rule applies (re-run it, nothing is lost). Claude Code turns such a poll into a background job and notifies you when it ends; that is fine, but do not start a second poll on the same page while one is alive. Copilot CLI's synchronous timeout is unverified: if your shell call is cut short, just re-run.
- Ask the user to confirm nothing about *how* to run this skill: preflight decides, the first page confirms.

## Out of scope (on purpose)

- **Wayfinder-scale work** (efforts too big for one session, needing a map of tickets across sessions). If the tree passes about 40 nodes or the user says the scope is too big, say so, offer to split, and grill one slice.
- **The next step itself** (a spec, tickets, a plan). hot-seat ends at a confirmed shared understanding plus the ledger; the next step (for software, `to-spec`) starts from the same conversation.
- **Building prototypes** beyond a throwaway figure on a card (use the `prototype` skill).
- **Acting on the plan.** No code, no commits, no ADRs the user did not say yes to.
