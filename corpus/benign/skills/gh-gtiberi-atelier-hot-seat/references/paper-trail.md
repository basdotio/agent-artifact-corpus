# Paper trail (codebase mode)

Restated from `domain-modeling` (mattpocock/skills, MIT; see NOTICE.md). Applies only when the session mode is `docs`. In stateless mode none of this touches disk.

## Where things live

```
/
├── CONTEXT.md            single-context repo: one glossary at the root
├── docs/adr/0001-slug.md decisions, sequentially numbered
```

If a `CONTEXT-MAP.md` exists at the root the repo has several contexts. The map lists where each `CONTEXT.md` lives and how the contexts relate; each context may also have its own `docs/adr/`, system-wide decisions live in the root `docs/adr/`. Infer which context the topic belongs to; if unclear, ask on a card.

Create files lazily: `CONTEXT.md` when the first term resolves, `docs/adr/` when the first ADR is needed.

## CONTEXT.md

A glossary and nothing else. No implementation detail, no spec, no scratch notes, no decisions (those are ADRs or stay in the ledger).

```md
# {Context name}

{One or two sentences: what this context is and why it exists.}

## Language

**Order**:
{One or two sentence definition: what it IS, not what it does}
_Avoid_: Purchase, transaction
```

- Be opinionated: several words for one concept, pick the best, list the rest under `_Avoid_`.
- Tight definitions: one or two sentences.
- Only terms specific to this project's context. General programming concepts (timeouts, error types, utility patterns) do not belong.
- Group under subheadings when clusters emerge.
- **Match the file you are editing.** If existing entries carry extra fields (a French counterpart, a lifecycle line), follow that convention exactly. Never rename or redefine an existing term because the conversation drifted: challenge it instead (question card, glossary entry with `status: "conflict"`), and only change it if the user decides to.

A term is resolved when its name AND every field the file's convention requires are settled (in a bilingual glossary, ask for the translation in the same card as the name, so the entry is complete when written). Extending an existing entry, for example adding a state to a lifecycle line, is an edit, not a rename or redefinition: allowed, with `edited: true` in the record. Write a term the moment it resolves (an edit to the file, not a batched write at the end), then record it in the patch's `glossary` with `written: true` and `file`. `next` checks that the term really is in a `CONTEXT.md`.

## During the session

- **Challenge against the glossary.** When the user's word conflicts with `CONTEXT.md`, call it out at once: "Your glossary defines X as A, but you seem to mean B. Which is it?" Make it a card with a recommendation.
- **Sharpen fuzzy language.** Propose a precise canonical term for vague or overloaded words.
- **Discuss concrete scenarios.** Invent edge-case scenarios that force the user to be precise about the boundary between concepts.
- **Cross-reference with code.** When the user states how something works, check the code. Surface contradictions ("your code cancels whole Orders, but you said partial cancellation is possible").

## ADRs

`docs/adr/NNNN-slug.md`, numbered by scanning the folder for the highest number and adding one.

```md
# {Short title of the decision}

{1-3 sentences: the context, what was decided, and why.}
```

That is enough; an ADR can be one paragraph. Optional, only when they add value: a `Status` frontmatter (`proposed | accepted | deprecated | superseded by ADR-NNNN`), `Considered Options` (when the rejected alternatives are worth remembering), `Consequences` (when non-obvious downstream effects need calling out). Match the tone and shape of the ADRs already in the folder.

**Offer an ADR only when all three are true:**

1. **Hard to reverse**: changing your mind later costs something meaningful.
2. **Surprising without context**: a future reader will wonder "why on earth did they do it this way?".
3. **A real trade-off**: there were genuine alternatives and one was chosen for specific reasons.

Any one missing: skip it. Easy to reverse, you will just reverse it. Not surprising, nobody will wonder. No real alternative, there is nothing to record beyond "we did the obvious thing".

What qualifies: architectural shape, integration patterns between contexts, technology choices with lock-in, boundary and scope decisions (the explicit no-s), deliberate deviations from the obvious path, constraints not visible in the code, rejected alternatives when the rejection is non-obvious.

### How hot-seat handles an ADR

1. A settled decision looks like it clears all three gates: add an `adrs` record with `status: "candidate"` and a `gates` object, one `{met, why}` per gate, and put a card in the next round: "Record this as an ADR?" (recommended yes, with the one-line title you would write).
2. The user says yes: write the file, then patch the record to `status: "written"` and `file`.
3. If the user says no, or a gate fails on reflection: `status: "skipped"`.
4. Never write an ADR file without a record; never mark one written unless all three `gates.*.met` are true. `next` refuses both. Do not list every decision as a candidate: only real near-misses the user might expect to see.

```json
{"adrs": [{"title": "Fusion is decided by the Virtue pair alone",
  "gates": {"hardToReverse": {"met": true, "why": "Baked into saved Heroes"},
            "surprising": {"met": true, "why": "Order of Promotions is the obvious model"},
            "tradeoff": {"met": true, "why": "Considered order-dependent classes"}},
  "status": "candidate"}]}
```
