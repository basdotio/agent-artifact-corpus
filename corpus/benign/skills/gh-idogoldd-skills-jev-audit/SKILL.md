---
name: jev-audit
license: MIT
description: Audit a repo for the top opportunities to replace brittle heuristics (regex, keyword lists, if-chains, hand-tuned scores, LLM-as-classifier prompts) with TypeSafe's Jev decision model. Returns a ranked report with evidence, a question design, and cost/latency estimates. Use when asked to "find Jev opportunities", "audit heuristics", or "where should we use Jev / a decision model".
---

# Jev opportunity audit

## Thesis

Most codebases contain code that tries to detect a **world situation the data does not state**: "is this email automatic", "are these two records the same company", "is this message a complaint". Because no field says so, someone wrote rules. Those rules are a proxy, and the proxy is wrong some fraction of the time.

Jev (TypeSafe's System One decision model) answers typed questions about text (`noul` yes/no probability, `choice` over fixed options, `score` on ordered levels) with calibrated probabilities, at a price and latency low enough to sit where a heuristic sits today.

Your job: find those proxies, rank them by how much getting closer to the truth is worth, and show what the replacement looks like. **This skill is read-only. Do not modify application code.** Output is one report file.

## Step 0: Load current Jev facts

Prices, limits and known weaknesses change. Before estimating anything, fetch:

- `https://docs.typesafe.ai/models.md` (price, rate limits, context length)
- `https://docs.typesafe.ai/model-jaggedness/jev-1.13.md` (or the current version's page, listed in `https://docs.typesafe.ai/llms.txt`)
- `https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md` (question design)

If fetching fails, use the fallback below and say in the report that figures are from the snapshot date.

**Fallback snapshot (2026-10-06, jev-1.13.0):**
- Price: $0.042 per million input tokens. Output tokens free.
- Latency: the docs state no latency figure (checked 2026-10-07). Use ~100 ms only as a planning number, label it as an assumption in the report, and measure one test call when a key is available.
- Rate limits: 100K tokens/sec, 80 requests/sec (documented as subject to change).
- Context: 64k tokens per request total; 32k for `state` plus the longest single question.
- Input: text only (string / JSON / array of text). English strongest; other languages work less well.
- All questions in one request are evaluated in parallel against one `state`; adding questions barely changes latency.
- Not fine-tunable. Domain knowledge goes in `state`, `instructions`, `criteria`.

If the official TypeSafe agent skill is installed (`typesafe-ai`), use it for exact request/response shapes when writing sketches. If not, follow the shapes in the docs above and recommend installing it in the report.

## Step 1: Understand the repo

Before hunting, establish in a few minutes:
- What the product does and which decisions drive user-visible or revenue-relevant behavior.
- Languages, main entry points, and which paths are request-time (synchronous, user waiting) vs background (queues, crons, webhooks, batch).
- Any existing LLM / ML usage. Prompts and model IDs may live outside the code (a database table, a prompt registry, a config service); note where, so Signature B candidates can be costed.
- Any existing Jev usage. Exclude the decisions already on Jev, but inspect the integration itself:
  - How the repo calls Jev: official SDK, plain HTTP, or a gateway such as OpenRouter. Write every sketch in Step 6 against that client and its types, not against the SDK examples.
  - Whether the model is pinned to a versioned ID. A floating alias (`jev-latest`, `~typesafe/jev-latest`) silently moves every tuned threshold; report it.
  - Which question types and state shapes the client's types allow (for example only `choice` and `noul`, or flat string state). Report gaps the sketches would need.
  - The price on that route. A gateway can price differently from TypeSafe's list price; if the price is not published, say so and use the list price as an assumption.

## Step 2: Hunt for candidates

Cast wide. Aim for 20 to 40 raw candidates before ranking. Use subagents per top-level directory on large repos, plus one subagent that sweeps the whole repo for Signature B only: LLM classifiers go through shared helpers and spread across directories, so per-directory agents find them only in part. Have it start from the shared LLM helpers (structured-output wrappers, model factories) and trace every caller. Skip vendored code, generated code, lockfiles, migrations.

**Signature A: heuristics over natural-language or semi-structured text**
- Regex or `contains` / `startswith` / `in` checks applied to human-written fields: subject, body, title, name, description, bio, notes, comment, message, job title, company name, address, user agent, filename.
- Keyword or pattern lists as constants: `*_KEYWORDS`, `*_PATTERNS`, `BLOCKLIST`, `SPAM_WORDS`, `GENERIC_DOMAINS`, `ROLE_PREFIXES`, `NOREPLY_*`.
- Long `if / elif` or `switch` chains whose conditions are string tests and whose result is a label.
- Functions named `is_*`, `looks_like_*`, `seems_*`, `detect_*`, `classify_*`, `categorize_*`, `guess_*`, `infer_*`, `should_*`, `match_*`, `normalize_*`, `dedupe_*`, `extract_*` (when extracting from a bounded set).
- Fuzzy matching with magic thresholds: Levenshtein, Jaro, token-set ratio, cosine similarity `> 0.8x`.
- Hand-weighted scoring: `score += 10 if ...`, weights dictionaries, then a cutoff.

**Signature B: LLM used as a classifier**
- Chat-completion calls whose prompt says "answer yes or no", "respond with one of", "return JSON with field category", then parses the text. These are already an admission that judgment is needed; Jev makes them cheaper, faster, typed, and gives a probability to threshold on.
- The prompt or model can be loaded by slug from a database or prompt registry rather than written in code. Look it up (read-only) before estimating current cost; if you cannot, list it under open questions.

**Signature C: evidence the proxy is failing**
- Comments: `heuristic`, `hack`, `best effort`, `naive`, `good enough`, `fragile`, `edge case`, `TODO`, `FIXME`, `not perfect`, `false positive`.
- Git churn: for each candidate file run `git log --follow --oneline -- <path>`, and for each pattern constant run `git log --oneline -S'<a distinctive pattern string>'`. Plain `git log -- <path>` stops at the last file move, so after a large refactor it shows 1 to 3 commits and hides the real history. Look for a stream of small commits adding one more pattern or exception. Count them. A rule list that keeps growing is the strongest gap signal available without labels.
- Tests that are long tables of special cases; fixtures named after customers or incidents.
- A manual-override field, review queue, or "report wrong classification" path downstream of the decision.

For each candidate record: file and line range, what world situation it is trying to detect (one sentence, phrased as a question), what inputs it reads, what happens downstream of its result.

## Step 3: Qualify

Keep a candidate only if the answer to "is the truth stated anywhere in the data?" is **no**. Then apply these gates. A failed gate either rejects the candidate or reshapes it; say which.

**Reject or reshape (from Jev's documented weak spots):**
- **Computable exactly.** Format validation, parsing structured data, arithmetic, counting, date/time ordering or windows, numeric closeness. Stays in code. If a judgment is buried inside (e.g. "which date in this text is the due date"), the candidate becomes: Jev picks from a bounded set, code computes.
- **Needs generated text.** Jev selects, it does not write. Extraction qualifies only when candidates can be enumerated (by regex or parser) and Jev chooses among them.
- **Multi-hop reasoning.** A property of a property, or judgment needing several inference steps. Reject unless it decomposes into independent atomic questions.
- **Sole defense against adversarial input.** Content written to argue for its own classification can move the answer. Jev may be one signal; it should not be the only gate on a security boundary.
- **Non-text input** with no cheap text representation.
- **State too large or too noisy.** Accuracy drops as irrelevant content grows. Qualifies only if code can narrow the input to the fields the question needs.
- **Non-English heavy.** Keep, but mark as "validate first".

**Keep the hard signals.** If part of the heuristic is a deterministic, high-precision check (a header that states the fact, an exact ID match, an allowlist), that part stays as a fast path in code. The opportunity is the remainder the rules cannot decide. Say this explicitly in the sketch; the right design is almost always hybrid.

**Name the cheapest code fix.** If a small deterministic change removes most of the errors (whole-word instead of substring matching, a hard signal the system already has, asking the caller for an enum instead of parsing its text), say so. Either the candidate becomes "fix in code" and is rejected, or Jev stays an opportunity for the remainder and Step 7 compares three options: the current rule, the code fix, and Jev. Never credit Jev with errors a one-line fix removes.

List every rejected candidate in the report with a one-line reason.

## Step 3b: Measure in production (optional, never blocking)

Production data turns guesses into evidence: how often a path runs, and how often the heuristic is wrong. Do this step only when **all** of these hold:
- A read-only route to production data or logs already exists in this environment (a read-only database helper, a log or metrics query tool).
- The user has agreed to production reads in this session, or has standing permission for read-only queries.
- The queries stay read-only and aggregate. Pull small samples of text only to judge misses, and do not copy customer data into the report beyond short anonymised examples.

If any condition fails, skip this step without asking further, and continue. Score from code and git (Step 4 caps unmeasured gaps at their code evidence), mark volumes as "not measured", and list them under open questions. Do not wait, retry access, or ask the user to set up access.

When the step runs, measure for each surviving candidate:
- **Volume**: how many times the decision ran in the last 30 days (rows created, log lines, credit or usage entries).
- **Misses**: query the stored results of the heuristic for cases it likely got wrong (for example stored "replies" whose body reads like an out-of-office notice). Sample 20 to 30 and count how many are real misses. State the sample size with the number.
- **Downstream volume**: how often the wrong answer leads to the costly action.

## Step 4: Score

Score each surviving candidate 1 to 5 on three axes, each with cited evidence (file:line, commit count, comment text). No evidence, no score above 3.

**Gap: how far is the current proxy from the truth?**
- 5: Rule list with heavy churn, known-wrong comments, or an obviously open-ended input space (free text from the public).
- 3: Plausible rules, some special-casing, no visible failure evidence.
- 1: Narrow closed input space; rules probably cover it.

**Stakes: what does a wrong answer cost?**
- 5: Drives a customer-visible action, money, an outbound message, or a decision that silently corrupts downstream data or metrics.
- 3: Affects ranking, prioritization, or internal workflow.
- 1: Cosmetic or logged-only.

**Fit: how well does the decision map to Jev?**
- 5: One state, a handful of atomic yes/no or pick-one questions, common-sense judgment, English text, small input.
- 3: Needs decomposition or input narrowing first, or a larger option set.
- 1: Borderline on any Step 3 gate.

**Volume gate.** If Step 3b measured that a path ran rarely or never in the last 30 days, mark it "leave it" and move it to the rejected table, whatever its score. If volume was not measured, do not reject on volume; keep the candidate and list its volume under open questions. Between candidates with equal priority, rank the one with higher measured volume first.

**Priority = Gap x Stakes x Fit** (max 125). Then apply the operating constraint from Step 5 as a label, not a multiplier: `clear`, `needs design` (async, prefilter, cache), or `blocked`.

Rank. Take the top 10. **If fewer than 10 qualify, report fewer. Do not pad.**

## Step 5: Estimate cost and latency

For each top candidate:

**Tokens per call.** Estimate `state` size from the actual fields that would be sent (use fixtures, test data, schema limits; chars / 4) plus all question text (`instructions` + `criteria`). State the assumption.

**Cost.** `tokens_per_call x price_per_token`. Always give cost per 1,000 calls. Worked example at the snapshot price: 1,500-token email + 300 tokens of questions = 1,800 tokens = $0.000076 per call = $0.076 per 1,000 = about $76 per million.

**Volume.** Use the measured volume from Step 3b when it exists. Otherwise derive it from code (webhook, per-request, cron frequency, loop over a table). If volume is not inferable, do not invent it: give per-1,000 cost, the break-even framing, and list "monthly volume" under open questions. If the user gave volumes, use them.

**Latency.** Classify the call site:
- Background / async: latency is irrelevant; mark `clear`.
- Request-time with existing network or DB calls in the path: +~100 ms typical; mark `clear` or `needs design` depending on the path's budget.
- Tight loop, per-keystroke, or sub-50 ms budget: `needs design` (move off the hot path, precompute, cache by input hash) or `blocked`.

**Throughput.** Compare peak calls/sec and tokens/sec against the rate limits. Flag anything within 2x of the limit.

**Reducers.** Note which apply: deterministic fast path handles the easy share; cache on normalized input; batch several decisions about the same state into one request (questions run in parallel, state is billed once per request); trim state to needed fields.

If replacing a Signature B LLM call, also estimate the current cost and latency of that call from its model and prompt size, and show the delta.

## Step 6: Sketch the replacement

For each top candidate, write a sketch in the repo's language. If the repo already calls Jev, use its existing client and types (Step 1). Otherwise use the SDK for Python or JS/TS, and plain HTTP for other languages. Keep it short. It must show:

1. **Fast path kept in code** (if any hard signals exist).
2. **State**: only the fields the questions need, as structured JSON.
3. **Questions**: decomposed. Do not write one broad question ("is this automatic?"). Write several atomic ones, each judging one property, phrased so a high value means yes, with `criteria` where the boundary is subtle. Reference state fields by backticked path. Prefer `noul` for yes/no, `choice` when the outcome is one of N labels (include an explicit "none of these" option when applicable), `score` for degree.
4. **Composition in code**: how answers combine (rule, weighted sum) and three-way routing: act / review-or-fallback / don't act. The old heuristic is a valid fallback for the uncertain band.
5. **Constants in one place**: questions and thresholds in a single file, model pinned to a versioned ID (not `jev-latest`) since thresholds are tuned per version.

Question-writing rules that matter (Jev reads literally):
- State the exact condition. No implied intent, no double negatives.
- One judgment per question.
- Never ask it to count, do math, or compare dates. Extract with Jev, compute in code.
- Check `choice` answers are stable under option reordering.

## Step 7: Validation plan

You cannot know the accuracy gain from reading code. Never state one. For each top candidate give a concrete way to measure it:

- **Sample**: where to pull 200 to 500 real inputs (table, log, fixture dir), stratified to include cases the heuristic handles and cases it likely misses.
- **Label**: who or what provides truth (human pass, existing override/correction data, or a strong reasoning model as a labeler).
- **Compare**: heuristic vs Jev on the same set (plus the code fix from Step 3, when one exists); precision/recall for the action that matters; plot Jev probability against correctness to choose thresholds.
- **Ship path**: shadow mode first (run Jev alongside, log disagreements, act on the heuristic), then switch with the uncertain band routed to fallback.

If `TYPESAFE_API_KEY` is set and the user has explicitly agreed, you may run a small experiment on **test fixtures only**. Sending real customer data to a third-party API requires the user's explicit go-ahead; ask, and mention TypeSafe's data-handling page.

## Output

Write `JEV_OPPORTUNITIES.md` at the repo root (or print it if the user prefers). Structure:

```
# Jev opportunities: <repo>
Audited <date> at <commit>. Jev facts: <live from docs | snapshot date>, model <id>, $<price>/Mtok (<list price | price on the repo's route>).
Volumes: <measured in production, window | from code only>. Existing Jev integration: <none | client, pinned or floating model, type gaps>.

## Summary
| # | Opportunity | Where | Priority | Gap/Stakes/Fit | Cost per 1k | Latency | Constraint |

## 1. <World situation as a question, e.g. "Is this inbound email automatic?">
- Where: path:lines (+ callers)
- Today: what the heuristic does, in two sentences
- Why it misses: evidence (rule count, churn commits, comments, uncovered input classes with concrete examples)
- What depends on it: downstream effect of a wrong answer
- Scores: Gap n (evidence), Stakes n (evidence), Fit n (evidence)
- Replacement sketch: code block
- Cost: tokens/call, $/1k calls, $/month if volume known (assumptions stated)
- Latency and scale: call-site class, added latency, rate-limit headroom, reducers
- Risks: applicable Jev weak spots, language, adversarial exposure
- Validate: sample source, labels, metric

... up to 10 ...

## Considered and rejected
| Candidate | Where | Reason |

## Open questions
Volumes, latency budgets, or data-handling constraints the audit could not determine.

## Next step
The single opportunity to shadow-test first, and why.
```

## Rules

- Evidence over assertion. Every claim about the current heuristic cites a file and line. Every number states its assumption.
- No invented volumes, no invented accuracy numbers.
- Be willing to say "leave it": a heuristic that is cheap, correct enough, and low-stakes is not an opportunity.
- Name each opportunity by the world situation it detects, not by the function name.
- Do not edit application code. If the user wants an opportunity implemented, that is a follow-up task.
