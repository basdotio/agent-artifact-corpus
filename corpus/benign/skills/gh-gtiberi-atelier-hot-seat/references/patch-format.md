# State and patch format

`HS init` creates `<workdir>/state.json`. You never edit it by hand: `HS record` fills answers, `HS next` merges your patch and rebuilds the page. Everything below is what the patch may contain. Unknown keys are ignored.

## Design tree nodes (`tree`, upserted by `id`)

| field | meaning |
|---|---|
| `id` | short stable id (`d1`, `d2`...). `d0` (topic and scope) and `dm` (mode) exist after init. |
| `parent` | the node this decision hangs off (draws the tree) |
| `title` | the decision, as a noun phrase |
| `state` | `settled`, `frontier` (asked this round), `blocked` (waits for other decisions), `running` (waits for a lookup), `parked` |
| `blockedOn` | node ids that must be settled or parked first. A node with all `blockedOn` settled that is not asked is a warning: the round must be the WHOLE frontier. |
| `decision` | required when `settled`: the decision stated precisely (numbers, ordering, negatives), faithful to the user's words |
| `parkedReason` | required when `parked`: "needs a prototype: ...", "user does not know; depends on ...", "out of scope (user)", "waiting on an external fact only the user can get: <what, from whom>", or "OPEN UNKNOWN: <what>" (the user chose to leave it undecided and asked that it be recorded rather than decided silently; the ledger lists it under Parked) |

A question's node gets `frontier` automatically. `next` refuses a question whose node has an unsettled `blockedOn`, or is fed by a running fact.

## Facts (`facts`, upserted by `id`)

`{id, title, state: "running"|"done", feeds: [nodeIds], result}`. Facts found by lookup are never asked of the user. `running` facts show as "looking up..." on the page.

## Questions (`questions`, this round)

`{node, title, body, kind, choices, recommended, why, multi, figure, stakes, basis}`. `stakes: "low"` shows a chip (safe to accept the recommendation); `basis` is a one-line "based on: ..." for cards resting on a lookup. `kind`: `choice` (default) or `free`. Choices `{id, label, detail}`; `recommended` is a choice id (array for `multi`); for `free` it is the suggested text. `why` is the reason and is required. `figure`: `{svg}` (inline SVG), `{html}` (a mock; scripts and inline handlers are stripped), `{img, alt}` (a file next to the page) or `{frame, height}` (an HTML file next to the page shown in a sandboxed frame; scripts run inside it, nothing else is allowed. Sibling files next to the page (images, sprites) load under Lavish (verified); for a prototype that must survive `lavish-axi export`, inline CSS and JS and embed images as base64 data URIs. Do not rely on CDN fonts), plus `caption` inside the same object. A `prefill` string pre-fills a free-text card. Ids `Qn` are assigned.

Instead of `questions`: `confirm: {summary}` (frontier empty; refused otherwise) or `finish: true` (after a "yes" on the confirm card; optional `summary`).

## Glossary (`glossary`, upserted by `term`)

`{term, fr?, definition, avoid?: [], status, note?, written?: bool, edited?: bool, file?, conflict?}`. `status`: `resolved` (a term this session settled: write it to CONTEXT.md now, `written: true`), `existing` (already in CONTEXT.md and unchanged; used when a loose word maps onto it), `rejected` (considered and decided against, not added), `conflict` (unresolved clash with the glossary; say what in `conflict`; when it is settled, move the entry to `existing` or `resolved` and record the outcome in `note`), `proposed`. In codebase mode `written: true` is checked: `**Term**` must be in a `CONTEXT.md` and be a line this session added (or set `edited: true` if you changed its definition in place); `existing` must already be there. In stateless mode terms are never written or existing: they stay on the page and in the ledger.

## ADRs (`adrs`, upserted by `title`)

`{title, gates: {hardToReverse, surprising, tradeoff: {met, why}}, status: "candidate"|"written"|"skipped", file?, skipReason?, skippedBy?}`. The gates are YOUR assessment; if the user vetoes an ADR, keep your gates as they were and set `status: "skipped"`, `skippedBy: "user"`, `skipReason`. `written` needs all three gates met and the file present. A new file under `docs/adr/` with no record is refused.

## Other

`title` (required in the first patch after the intake: short topic name for the header and ledger; `assumptions` and `corrections` APPEND across rounds, they are not replaced), `note` (shown on top of the next page: what you changed because of their answers and steering), `corrections` (strings, kept in the ledger), `assumptions` (strings: things you inferred that the user never said; also accepted inside `confirm`), `answers` (chat fallback only), `topic`, `mode` (`me`|`docs`, only if the user switched it mid-session).

## What `next` refuses (nothing is changed)

patch without `title` (until one is set); glossary with an unknown status; question without title/body; choice question with fewer than 2 choices or duplicate ids; no `recommended`, or one that is not a choice id; no `why`; unknown `node`; a node depending on an unsettled node or on a running lookup; `settled` without `decision`; `parked` without `parkedReason`; `confirm` while any node is not settled/parked; `finish` without a "yes"; glossary `written` but absent from `CONTEXT.md` or never added by this session; glossary `existing` but not in `CONTEXT.md`; ADR `written` without three gates; an ADR file created with no record; stateless mode claiming writes.

## What it warns about (visible on the page)

answered, skipped, unsure or prototype-flagged question whose node is still `frontier`; unblocked node not asked; frontier node with no question; rounds over 12 questions; resolved glossary term not yet written (codebase mode).
