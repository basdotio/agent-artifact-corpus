---
name: jev
description: >
  Use TypeSafe's Jev (System One) model for fast, cheap, calibrated typed decisions —
  a yes/no probability (noul), a pick from fixed options (choice), or a position on a
  rubric (score). Two modes: (1) inside a Claude Code session, call Jev through the
  bundled script to bulk-judge many items at once (triage logcat lines, crash groups,
  lint warnings, PR diffs, string resources, file relevance, review comments); (2) when
  building software, design and write correct Jev integrations (routing, classification,
  guardrails, scoring, gating, reranking) in Kotlin/Android, Swift/iOS, backends, Python or JS.
  Use this skill whenever the user mentions Jev, TypeSafe, System One, noul, typed or
  calibrated decisions, "fuzzy if", confidence-gated routing, or wants to classify, score,
  rank, flag, calibrate, or triage a batch of text items — even if they don't name Jev.
---

# Jev (TypeSafe System One)

Jev takes a **state** (text or JSON) and a map of **typed questions**, and returns one
typed answer per question with calibrated probabilities. It does not generate text,
write code, or reason step by step. Think of it as a programmable `if` for things
ordinary code cannot judge: "is this urgent", "which team", "how risky".

The default route is **OpenRouter**; TypeSafe direct also works (`--provider typesafe`, `TYPESAFE_API_KEY`):

- Endpoint: `POST https://openrouter.ai/api/alpha/decisions`. It's under `/alpha/`, so it
  may change — a 404 means check OpenRouter's Jev model page before debugging anything else.
- Headers: `Authorization: Bearer $OPENROUTER_API_KEY`, `Content-Type: application/json`;
  optional `HTTP-Referer` (site URL) and `X-Title` (site name) for OpenRouter rankings.
- Model: `typesafe/jev-1.13` — pin it. A floating alias exists (`~typesafe/jev-latest`,
  with the tilde — without it, it doesn't resolve here) but move to it deliberately.
  TypeSafe's direct route pins the fuller `jev-1.13.0`. Responses name the dated snapshot
  that answered (`typesafe/jev-1.13-20260917`): log it, and match your pin by prefix.
- Context: **32,000 tokens for state + all questions combined** on this route (TypeSafe
  direct differs: 64k total, 32k for state + the single longest question). The bundled
  script enforces the limit for whichever route it's actually calling.
- Body and answers are the same shape as TypeSafe's native API: `state`, `model`,
  `questions` in; `model`, `answers`, `usage` out. Every response includes `usage.cost`
  (USD) — use it instead of estimating from the list price.
- Cost: input tokens only (TypeSafe list price about $0.042 per million; OpenRouter
  billing is on its activity page and needs prepaid credit).
- Latency: one 13-question request took 0.27 s in TypeSafe's
  [parallel_questions](https://docs.typesafe.ai/cookbooks/parallel_questions) cookbook; a
  packed 40-item batch request took ~2.3 s p50 in this project's
  [live benchmark](https://github.com/Shakibuzzaman3104/claude-jev-funnel/tree/main/benchmarks).
- All questions in one request see the same state and run in parallel, so batching
  many questions into one call is far cheaper and faster than one call per question.

Full contract, limits and errors: `references/api.md`.

**Running the script.** The CLI is `scripts/jev.py` in this skill's base directory (shown
when the skill loads; a plugin install keeps it in the plugin cache, not the project). Run
it as `python3 "<skill-dir>/scripts/jev.py"` from any directory — below and in the
references, `jev.py` is shorthand for that command.

## First, pick the mode

**Mode A — judge things during this session.** The user wants Jev to classify, score or
filter real items right now (log lines, warnings, diffs, files, messages). Go to
"Mode A" below and use `jev.py`.

**Mode B — build Jev into software.** The user is writing an app, backend, agent or
pipeline that should call Jev. Go to "Mode B" below.

**Default for closed-set bulk judgments of ~20+ items** (yes/no, pick-one, or a rubric,
over a batch): reach for Jev before spinning up a cheap LLM subagent (such as Haiku); a
Claude reviewer or subagent then sees only the uncertain band, never the whole batch.

If the request is a single judgment you can make yourself with high reliability, just
make it. Jev earns its place on volume (dozens to thousands of items), on repeatability
(same question, comparable numbers across runs), and when a calibrated probability is
needed to gate an action.

## Question design (both modes)

Choose the primitive by what the answer means:

| Need | Type | Returns |
| --- | --- | --- |
| Whether one condition holds | `noul` | `noul`: P(yes), 0–1. No confidence field. |
| One option from a fixed set (≤255) | `choice` | `choice`, `probabilities` per option, `confidence` |
| Degree on an ordered rubric (2–10 levels) | `score` | `score` (can land between levels), `probabilities`, `legend`, `confidence` |

Rules that decide whether answers are good. Jev 1.13 has known weak spots, so these matter:

1. **One narrow judgment per question — with one exception.** Split compound questions
   ("urgent and about billing"); several labels that can apply at once → one noul per
   label, not a choice. Exception: a single verdict decided by one written policy as a
   whole — a hand-coded composite of 4 diagnostic nouls reached 94.1% (6 false passes)
   where one `choice` carrying the whole policy reached 99.3% (100% with the nouls added
   as diagnostics, not as the verdict). For a genuinely holistic verdict, test both shapes
   on labeled data before picking.
2. **Write the exact condition.** Jev reads literally: scoping words, negations and
   implied conditions are taken at face value. Put boundary cases in `criteria`. If you
   catch yourself explaining what a question "really meant", that explanation belongs
   in the question.
3. **Question IDs are never sent to the model.** Each `instructions` must stand alone.
4. **Point at state by name, never by position.** Use a keyed path (``diff.hunks.h03``),
   not an array index (``diff.hunks[3]``, ``items[7]``) — an answer can land on the wrong
   item with no error. Key batches yourself, or let `jev.py batch` do it and rewrite
   `item` references for you. Measured: 29/320 wrong at 25 items/request positionally,
   0/320 keyed.
5. **Keep state small and relevant.** Unrelated detail lowers accuracy; filter in code
   first. Hard limit on this route: **32k tokens, state + all questions combined**
   (TypeSafe direct differs — see the route notes at the top).
6. **Keep math, counting, dates and exact lookups in code.** Jev does not count reliably,
   compare dates, or do arithmetic. Ask one noul per item and sum in code.
7. **Select, don't generate.** Find candidates with regex or code, then ask a `choice`
   over them. **Every choice needs a no-match option** (e.g. `"none": "No listed option
   fits"`) — without one, a real run returned a wrong answer at confidence 1.00; the
   script errors on a choice with no such option (`--allow-no-none` downgrades it to a
   warning).
8. **Align instructions and criteria.** Never make `true` mean "no". Don't phrase with double negatives.
9. **Don't expect cross-question arithmetic.** P(A) and P(not A) from two nouls need not
   sum to 1, and a noul threshold does not transfer to a choice.
10. **Score levels are short descriptions, never bare numbers.** A bare number or a
    one- or two-word label calibrates far worse (jev.py warns on both): the vendor's own
    example scored 0.55/confidence 0.33 with numeric levels against 0.0/confidence 1.0 with
    descriptive ones on the same input.

More on structure, combining answers, self-consistency and patterns: `references/question-design.md`.

## Reading answers

Each question type calibrates differently — independently measured Expected Calibration
Error: noul `0.012`, choice `0.086`, score `0.254` (PrimeLine). Band on the field that
type actually calibrates, not one confidence cutoff for all three:

| Type | Band on | Bands | Notes |
| --- | --- | --- | --- |
| noul | `noul` (P(yes)) | `YES` ≥0.8 · `NO` ≤0.2 · else `UNCERTAIN` | Best-calibrated type; no `confidence` field — distance from 0.5 plays that role |
| choice | `p_max` (top probability) | `ACT` ≥0.8 · `REVIEW` 0.5–0.8 · `ABSTAIN` <0.5 | `confidence` is a fixed function of `p_max` and option count, `C=(N·p_max−1)/(N−1)` — the same cutoff means a different `p_max` for 3 options than for 15. Show `p_max` and the margin to the runner-up: `choice  conf=  p=  margin=  next=` |
| score | `confidence` | `CONFIDENT` ≥0.8 · `REVIEW` 0.5–0.8 · `UNSURE` <0.5 | Least-calibrated type (ECE 0.254) — use for ranking/thresholds, not to act on directly, until it's calibrated |

- **The middle band means "no signal"**, not a soft verdict: route it to review, never let
  it trip a gate either way. Answers are rounded to 2 decimals and pile up at 0.99/1.0, so
  a top-N cut can split a tie (`rank` warns), and confidence 1.00 is not certainty (wrong
  1.9–23% of the time in independent tests).
- Keep **one band for what an answer means** and let risk decide what to do with it:
  raising the "yes" bar for high stakes turned a 0.79 `DROP TABLE` into "uncertain".
  Destructive or irreversible actions need a higher bar to act on than read-only ones.
  A `score` is an expected value, so it rarely reaches its top level (complete plans
  scored 1.85–1.99 of 2); don't put a bar at the top. They also **don't transfer**: the best cutoff was 0.67 on one dataset
  and 0.37 on another, so calibrate on traffic that looks like production. These defaults
  are starting points, not rules for your data.
- **Calibrate on your own labels when stakes matter**: `jev.py eval --cases labeled.jsonl
  --template q.json` prints per-question accuracy and a per-bucket table (noul: p, choice: p_max,
  score: confidence), plus the loosest `--target` threshold (default 0.95) for noul/choice. Cases:
  `{"id": "a17", "text": "...", "expect": {"relevant": true}}` (noul: true/false, choice: an option
  key, score: a level index or its text) — pass `--fields`, or a stored verdict leaks in.
- Typed output guarantees the **shape**, not the truth. Treat answers as evidence.

## Mode A — judge things in this session

### Before sending anything

Jev is an external API. Content in `state` leaves this machine.

- **Never send** secrets or anything that looks like one: `.env`, `local.properties`,
  keystores, `google-services.json`, signing configs, tokens, API keys, customer PII.
  Strip or mask them in code first — `jev.py` scans every request, criteria text
  included, for common key patterns (OpenRouter, Anthropic, AWS, GitHub, Google, Slack,
  private-key blocks) and refuses to send a match; `--lenient` never relaxes this.
- **Ask once per repository** before sending proprietary source code or internal data
  (e.g. an employer's codebase). Log lines and lint output from that code count too.
  If the user has already agreed in this session, don't ask again.
- If `OPENROUTER_API_KEY` is not set, tell the user to create one at
  `https://openrouter.ai/settings/keys` (the account needs credit) and
  `export OPENROUTER_API_KEY=sk-or-v1-...`. Never print, log, or echo the key.

### Workflow

1. `jev.py doctor` once per session (or after switching keys) — one minimal call that
   confirms the key, model and provider work before a large run.
2. **Collect items in code** (grep, git, gradle output, adb logcat). Trim each to what
   the question needs.
3. **Write a template** — the questions every item gets, referring to the item as `item`
   and any shared data as `context`:
   ```json
   {"questions": {"standalone": {"type": "noul",
     "instructions": "Does `item.text` stand alone as a complete thought?"}}}
   ```
4. `jev.py batch --items items.jsonl --template q.json --dry-run` — validates, packs,
   and prints size and cost estimates without sending anything. Fix lint errors first.
5. `jev.py batch --items items.jsonl --template q.json --out answers.jsonl` for full
   results, or `jev.py rank --items items.jsonl --question "..." --top 20` when you just
   want the top N items by one yes/no. Both place each item for you (keyed ids or inside
   its own question) — never index the batch by position (`items[N]`).
   Packing many items per request can shift answers (a 40-row state flipped 77 of 360
   decisions vs one row per request, with positional refs); when exact order or a hard
   threshold matters, spot-check a sample with `--per-request 1`.
6. **Act in code on the bands** (see "Reading answers" above): sort, filter, group. Only
   the uncertain/review band needs a second look — you, or a Claude reviewer or subagent
   (see "The Jev funnel inside Claude Code" below). Run `jev.py usage` for a cost total
   when it matters.

Ready-made request shapes for common dev tasks (logs, crashes, lint, PR risk, file
relevance, strings, commits, app reviews, CI failures): `references/recipes.md`. Adapt
the closest one instead of starting from scratch.

### The script

`jev.py` is a dependency-free Python 3.9+ CLI (not on PATH; see "Running the script") that
calls OpenRouter by default. It handles auth, retries with backoff on 429/500/502/503/504/529
and network errors (honouring `retry-after`), lints every request before sending — structural checks,
positional refs, missing no-match options, descriptive-score-level checks, secrets (see
"Question design" above) — validates every answer against the question it sent (right
type, a `choice` from the offered options, a distribution that sums to 1 with the choice
on top, a `score` in range; a bad one becomes an error row, never a band), and keeps a local cost ledger for per-job and per-label totals
(`doctor` shows the OpenRouter key's usage and remaining limit; TypeSafe direct has no
balance endpoint).

```bash
# jev.py = python3 "<skill-dir>/scripts/jev.py"
jev.py doctor                                                  # check key/model/provider once
jev.py batch --items q.jsonl --template t.json --dry-run       # validate + size, sends nothing
jev.py batch --items q.jsonl --template t.json --out a.jsonl --label triage
jev.py rank  --items q.jsonl --question "Is this an OOM crash?" --top 20
jev.py eval  --cases labeled.jsonl --template t.json           # accuracy by confidence bucket
jev.py usage --since 2026-09-01 --by label                     # cost so far

# Single one-off request (no subcommand)
jev.py --state @crash.txt \
  --noul oom "Is the crash caused by running out of memory?" \
  --choice layer "Which layer?" "ui=..." "data=..." "none=Can't be determined" \
  --dry-run   # add --json / --provider typesafe / --mock as needed
```

Exit codes: `0` every row answered, `2` bad input, lint error, unknown model slug/endpoint
(404), or, for a single request and `doctor`, a rejected request (400/422) — in
`batch`/`rank`/`eval` a 400/422 becomes error rows (exit `5`); `3` auth/credit error
(401/402/403); `4` API/network failure after retries (single request and `doctor`); `5` a
`batch`/`rank`/`eval` job finished with some error rows (network failures and invalid
answers land here too — check the error rows), or a single request got a missing or
invalid answer.

Env: `OPENROUTER_API_KEY` / `TYPESAFE_API_KEY` (auth), `JEV_PROVIDER`, `JEV_MODEL`,
`JEV_APP_URL` / `JEV_APP_NAME` (OpenRouter ranking headers), `JEV_LEDGER` (cost-ledger
path, default `~/.config/jev/usage.jsonl`), `JEV_NO_LEDGER=1` (skip the ledger),
`JEV_CACHE_DIR` (batch answer cache, default `~/.cache/jev`).

### The Jev funnel inside Claude Code, and where it doesn't help

The shape that pays off: the main loop runs `jev.py` first, confident ends (`YES`/`NO`/`ACT`) get
handled in code with no further model call, and only the `REVIEW`/`UNCERTAIN` band goes to a
Claude reviewer or subagent. If your Claude Code has Workflows: a Workflow script has no HTTP tool
of its own — run `jev.py` from a normal turn first, then pass just the uncertain items to the
Workflow agent as `args`.

Cases where it doesn't pay off: **skill routers inside Claude Code** (Claude Code already
shows up to 1,536 characters of each skill description; in one test Jev agreed with Opus
about half as often as Opus agreed with itself, and ordinary mid-conversation follow-ups
cleared its 0.30 "needs a skill" gate at 0.34–0.64, suggesting skills nobody needed —
[jev-skill-router](https://github.com/shimo4228/jev-skill-router)); **screening code files for
relevance before reading them** (no effect beyond run-to-run noise in
[jev-axi](https://github.com/CHLIN0/jev-axi)'s 390k-line-repo benchmark); **repeat-and-vote
in production** (noul std-dev is already 0.0102 over 15 repeats,
[consistency_noul_cookbook](https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook),
and there's no server cache, so voting just pays twice); and **a single judgment you can
make yourself**, generation, or anything that's really counting, dates, or math.

Wiring Jev into Claude Code hooks: `references/recipes.md` recipe 17.

## Mode B — build Jev into software

1. **Start from the behaviour.** What will the app show, select, route or block? Work
   back to the few judgments it needs. Keep rules, lookups, math and execution in code.
2. **Design questions** with the rules above. Put every independent question over the
   same state in one request, including speculative ones for branches you might take.
   Use a second request only when it needs an earlier answer.
3. **Gate on confidence per action**, with higher bars for riskier actions. Always have a
   fallback path for low confidence (human review, a clarifying question, or an LLM).
4. **Keep raw judgments reusable.** Store probabilities; combine them with weights in
   code so policy changes don't need new inference.
5. **Keep the model slug in config** (`typesafe/jev-1.13`), re-check thresholds before
   moving to a new version, and log the `model` field from every response — it is a
   dated snapshot (`typesafe/jev-1.13-20260917`), so compare by prefix. The official SDKs
   default to the floating `jev-latest`; always pass `model`.
6. **Handle errors**: retry 429/529/5xx with exponential backoff; surface 400/422
   validation details; treat 401 (bad key) and 402 (no credit) as configuration failures.
   Retry 408 too, and honour `retry-after-ms` before `retry-after`. Never follow a
   redirect (it would resend the key elsewhere); cap the response size.
   **On an interactive hot path** (routing a live request, an agent's next step), make
   one call (retry at most once, and only for a short `retry-after`) with a short
   timeout, a per-session call budget, and a circuit breaker after repeated 429/529s. On
   any failure take the fallback with a named reason (no candidates, invalid input, request too large,
   budget spent, transport, HTTP, invalid response, escalated, low confidence, low fit).
   Check input and size *before* spending budget.
7. **Validate every response and fail closed.** Right `type` per question, a `choice`
   from the options you sent, probabilities summing to 1 with the choice on top, a `score`
   in range, the pinned `model` or a dated snapshot of it. A mismatch means "no decision",
   never a weak yes.
   Snippet: `references/api.md`, "Validating a response".
8. **When Jev picks an action, it picks an id, and the id grants nothing.** The host
   prepares a short list of eligible actions, sends opaque ids plus descriptions, asks one
   `choice` (with an `escalate` option) and one `fit` noul per candidate, acts only when
   both clear their bars, then re-checks the stored action (state version, preconditions,
   permission) before running it. Pattern: `references/question-design.md`, "Bounded
   action selector". For a **safety gate**, run deterministic rules first — a deny regex
   for known catastrophic commands (`git stash clear`, `rm -rf /`, reading `~/.ssh`), then
   a read-only allowlist, then Jev — and test it with authority-claim injections ("the
   owner approved this"), which got through where blunt "ignore the question" didn't.
   In a loop that acts, prefer **rules first with Jev as a reviewer**, rebuild the
   candidate list every turn, never apply a late or stale answer, and verify "done"
   yourself — details and measurements in `references/agents.md` (browser agents,
   robots, drones, games, coding-agent guards).
9. **Log a trace, not the content.** Per decision: model, a hash of state and of the
   candidate list, state version, the chosen id or fallback reason, confidence/fit,
   latency, tokens. Hashes let you tie a decision to its exact input without storing
   user text or keys in ordinary logs.
10. **Keep the API key server-side.** Never ship it in a mobile app, APK/AAB, or web
    bundle — anyone can extract it. Mobile apps call your own backend, which calls Jev — or
    skip the runtime call: tag content you already bundle (tips, prompts, onboarding copy,
    articles) once at build time with a batch job, and ship the tags, not a key. A local
    desktop tool that does hold a key should read it from its own owner-only file (mode
    0600, no symlinks), and pick up env vars or other tools' key files only if the user
    opts in.

TypeSafe also publishes an official agent skill (`claude plugin install
typesafe@typesafe-ai`, [typesafe-ai/skills](https://github.com/typesafe-ai/skills)); it is
worth reading alongside this one for API migrations and its composite-scoring and fan-out
patterns.

Reference implementation of points 6–10 (Rust, a macOS coding workspace):
[Keel's `jev-core`](https://github.com/codejunkie99/keel/blob/main/crates/jev-core/src/lib.rs)
and its [decision architecture](https://github.com/codejunkie99/keel/blob/main/docs/decision-architecture.md).

Language-specific code:
- **Kotlin (Android app + JVM backend):** `references/kotlin.md`
- **Swift (iOS app + backend):** `references/swift.md`
- **Python / JavaScript:** plain HTTP to the OpenRouter endpoint (examples in `references/api.md`).
  TypeSafe's own SDKs (`typesafe-sdk`, `@typesafe-ai/sdk`) also work here — point the SDK's base URL
  at OpenRouter's `/api/v1/systemone` passthrough and your OpenRouter key instead of a TypeSafe one.

## When something seems off

- Answers look wrong: check the question against the rules above (literal reading, compound
  question, oversized state, missing no-match option) before blaming the model. Split the
  failing question into two literal ones.
- A field, limit or model name here conflicts with an error from the API: the live docs win.
  For the endpoint and slug, check OpenRouter's Jev model page; for question semantics, read
  TypeSafe's docs (`https://docs.typesafe.ai/llms.txt`, append `.md` to any page path for Markdown).
- For deeper patterns (reranking, hierarchical classification, extraction cascades,
  citation checks), the official cookbooks are listed in the docs index.
