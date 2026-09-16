---
name: prompt-evaluation
description: >
  Eval-driven prompt refinement for Anthropic / Claude API prompts.
  Turn vibes-based prompt tweaking into a measurable loop: look at
  real failures, build a dataset, pick a grading approach
  (code-graded, model-graded, or both), scaffold a runnable eval
  (Anthropic SDK, `promptfoo`, or Claude Console), run it, analyze
  failures by category, propose targeted edits, re-run, compare.
  Invoke whenever the user wants to evaluate, improve, compare,
  A/B test, regress-test, or iterate on a prompt — even if they
  don't say "eval". Phrases like "is this prompt good?", "make this
  prompt better", "compare these two prompts", "my prompt fails on
  X", "tests for this prompt", "edge cases this classifier misses",
  "switch to Haiku without regressions", "evaluate this RAG answer",
  "grade this agent's tool use" all qualify. Covers code-graded,
  model-graded (LLM-as-judge), RAG-specific (faithfulness,
  answer-relevance), tool-use / agent evals, dataset design, and
  production patterns (capability vs regression suites, CI/CD).
license: MIT
metadata:
  author: "Ikuma Yamashita"
  version: "1.0.0"
---

# Prompt Evaluation

This skill is a **router and workflow**. It teaches eval-driven
prompt refinement, then dispatches to one reference file for the
chosen grading approach or tool. Read the references on demand —
do not pre-load all of them.

## When this matters

Prompt engineering without evals is guesswork. Two prompts can
both "look good" on a handful of cherry-picked inputs and still
differ by 20+ points on a real test set. The whole point of this
skill is to replace "v2 feels better than v1" with a number you
can defend.

The user wants one of these:

- **Improve a prompt** they already have, in a measurable way
- **Compare two or more prompts**, or the same prompt across models
- **Catch regressions** before they ship a prompt change
- **Find failure modes** on edge cases they haven't enumerated
- **Evaluate a RAG answer** for faithfulness / relevance / context
- **Grade an agent's tool use** (calls correct tools with correct args)

In every case, the deliverable is the same shape: a runnable eval,
a baseline score, a proposed prompt change, and a new score.

## Quick start (the 5-minute path)

If the user is in a hurry and the prompt is small (single-shot,
deterministic-ish output):

1. Get 5–10 example inputs and the user's ideal outputs. Save as
   `dataset.csv` with `__expected` per-row assertions.
2. Drop `assets/promptfooconfig.template.yaml` into the user's repo,
   pin `claude-haiku-4-5-20251001` as a provider, point `tests:` at
   the CSV.
3. `npx promptfoo@latest eval && npx promptfoo@latest view`. Show
   the user the dashboard, read failures together, propose one
   targeted prompt edit, re-run.

For anything more involved (open-ended output, RAG, agents,
regression suite), read on.

## Look at the data first (Hamel's correction to "evals first")

Before you build an eval, **read 20–50 real failures**. Don't
practice "eval-driven development" in the abstract — error analysis
reveals which evaluators matter. The dataset and the rubric should
be downstream of failure patterns you actually see, not patterns
you guessed at.

If the user has no production logs yet, this becomes "show me
3–5 example inputs and your ideal outputs"; those become the seed
golden pairs.

(Source: Hamel Husain, *LLM Evals FAQ*; Anthropic Engineering,
*Demystifying Evals for AI Agents* — "Start early and don't wait
for the perfect suite. Source realistic tasks from the failures
you see.")

## The loop you are running

1. **Capture the prompt under test and what it's supposed to do.**
   Exact prompt string, the inputs it consumes, the shape of a
   correct output. If vague, ask for an example input + ideal output
   — that's the first golden pair.

2. **Pick a starting venue.** Three options:
   - **Claude Console Evaluate tab** (lowest friction; non-engineers
     can use it; human 1–5 grading; no built-in LLM judge in the UI)
   - **`promptfoo`** (YAML, browser dashboard, multi-prompt × multi-
     model grids, rich assertion library, CI-friendly)
   - **Python + Anthropic SDK** (lives in user's codebase, full
     programmatic control)

   See "Picking a venue" below for guidance. Console is great as a
   Step 0 for the prompt author; you'll usually want to scaffold
   `promptfoo` or Python for anything Claude Code is automating.

3. **Build a small but real dataset.** See
   `references/dataset_design.md`. Start with **20–50 cases drawn
   from real failures** (Anthropic). Stratify by feature × scenario
   × persona (Hamel). Distinguish capability suite (start at low
   pass rate, probe ceiling) from regression suite (target ~100%
   pass, enforce floor).

4. **Pick a grading approach.** Decision tree:

   - Output is a **fixed label, number, JSON shape, or extractable
     value** → **code-graded** (`references/code_graded.md`)
   - Output is **open-ended** (summary, explanation, refusal,
     rewrite, tone) → **model-graded**
     (`references/model_graded.md`)
   - Output is **a RAG answer** with retrieved context → use the
     RAG-specific metrics in `references/rag_evals.md`
     (faithfulness, answer relevance, context precision/recall)
   - Output involves **tool calls** → use the tool-use patterns in
     `references/tool_use_evals.md`
   - **Both** kinds of criteria apply → use multiple assertions per
     test (one per criterion — see "isolated judges" below)

5. **Scaffold the eval.** Produce a runnable artifact in the user's
   repo (a `evals/` or `prompt-evals/` directory). For promptfoo,
   the assets in `assets/` are copyable starters. Show the command
   to run.

6. **Analyze failures, don't just report the score.** A pass rate
   is the headline. The interesting work is in the failing rows:
   group them by failure mode (see categories below), name each
   mode, and tie each mode to a specific prompt edit you'll
   propose. "Failed 4 of 20. Three are the model adding prose
   around the answer (fix: tighten output-format instruction). One
   is a genuine reasoning error on the adversarial row (fix: try
   chain-of-thought)."

7. **Propose a v2 prompt with a one-line hypothesis**, re-run on
   the *same* dataset, and report the delta. If the score went
   down, say so — don't paper over it.

## Picking a venue

| Venue | Use when |
| --- | --- |
| **Console Prompt Improver** (upstream) | The user has a rough prompt and wants an *AI-generated* improved draft to start from. Four-step pipeline: example identification → initial draft → CoT refinement → example enhancement. Accepts free-text feedback. Use as Step 0 to *generate* prompt edits; come here for the *measurement* loop that validates them. |
| **Console Evaluate** | Prompt author is non-technical; iterating in the browser; want side-by-side prompt comparison with human 1–5 grading; **no programmatic gates needed** |
| **`promptfoo`** | Compare prompts × models in a grid; want a browser dashboard; declarative YAML config; **CI/CD gating with junit.xml**; rich assertion library including `g-eval`, `factuality`, `answer-relevance`, RAG triplet, `trajectory:*`; can iterate with `--filter-failing` |
| **Python + Anthropic SDK** | Eval lives inside an existing Python codebase or CI script; programmatic input sourcing (database, S3); want full control over batching, caching, async; single-language stack |

If the user has no preference, ask. Don't pick for them silently.
The Prompt Improver and the eval venues compose: use the Improver
to *propose* a v2 prompt, then use the eval venue to *measure*
whether v2 actually beats v1 on the dataset.

## Code-graded vs model-graded — be honest about cost

**Code-graded** evals are cheap, fast, deterministic, and
reproducible. Use them whenever you can. The trap is forcing them
onto an open-ended task ("does this summary cover the main
points?") via brittle regex — that measures presence, not quality,
and the score will mislead you.

**Model-graded** (LLM-as-judge) evals are expensive, slower, and
have grader variance and known biases. Use them when the criterion
genuinely needs language understanding (faithfulness, tone, refusal
quality, RAG context relevance). When you do:

- **Prefer binary (correct / incorrect) judges** over Likert scales
  for actionability. If you need granularity, use 0–3 with
  behavioral anchors, not 1–10. (Source: Hamel Husain, Eugene Yan,
  Arize, Databricks all converge on this.)
- **Use an isolated judge per criterion** — Anthropic's published
  rule: "grade each dimension with an isolated LLM-as-judge rather
  than using one to grade all dimensions." Compound rubrics confuse
  judges.
- **Mitigate the known biases** explicitly. Without mitigations,
  Claude judges show 75% first-position bias in pairwise (MT-Bench)
  and prefer the longer answer 91% of the time. See
  `references/model_graded.md`.
- **Calibrate against human labels** before trusting the judge.
  Target Cohen's κ ≥ 0.6 / ≥80% agreement on a calibration sample
  of 25–50 rows.

When both code- and model-graded apply, run them as separate
assertions on the same rows.

## Dataset size and growth

| Phase | Size | Notes |
| --- | --- | --- |
| Seed | 20–50 | Real failures, not synthetic happy paths. Anthropic's recommended start. |
| Iteration loop | 20–100 | Small enough to scan by eye. Husain's "20-trace stop rule": stop sampling when 20 traces yield no new failure category. |
| Pre-deploy / regression suite | 100+ | Stratified by feature × scenario × persona. Regression suite frozen, ~100% pass rate. Capability suite evolving, start at low pass rate. |

Grow the dataset when:

- A real production failure shows up that isn't in any row → add it
- The pass rate has been 100% for two iterations → either the prompt
  is genuinely good or the set is saturated; add harder cases
- Stddev across runs is so high the score isn't informative → add
  rows in the noisy category

## Failure-mode taxonomy

Most prompt failures fall into a small number of categories.
After the first run, classify each failing row:

- **Format issues** — model adds prose, uses wrong delimiter, misses
  required tags. Fix: tighten output-format instruction; add a
  concrete example of the exact output shape; **use Structured
  Outputs (`output_config.format`)** for JSON. (Note: assistant
  prefill is deprecated on Claude Opus 4.6+ / Sonnet 4.6 — use
  Structured Outputs instead. See `references/code_graded.md`.)

- **Reasoning errors on hard cases** — model gets the easy cases
  but fails on tricky ones (the course's "fox lost a leg and
  grew back two"). Fix: add chain-of-thought
  (`<thinking>...</thinking>` then `<answer>...</answer>`) and
  extract the answer via a transform; or enable adaptive thinking
  on Opus 4.7+ (note that thinking changes the response shape —
  see `references/code_graded.md`).

- **Category confusion in classification** — model picks the
  wrong label when two are close. Fix: expand category definitions
  in the prompt; add discriminating examples; allow multi-label
  when the task genuinely is.

- **Hallucination / faithfulness** — model invents facts not in
  the source. Fix: "find a supporting quote per claim" verifier;
  allow Claude to say "I don't know"; restrict to provided
  documents. See the hallucination patterns in
  `references/model_graded.md`.

- **Subjective failures (tone, length, refusal)** — usually only
  visible to a model judge. Fix: add the missing constraint
  explicitly to the prompt with a positive example.

- **Tool-use errors** — wrong tool called, wrong arguments,
  unnecessary tool calls. See `references/tool_use_evals.md`.

For each category, propose **one targeted prompt edit**, not a
rewrite. Then re-run.

## Cost levers (do not skip)

Eval datasets re-send the same system prompt / rubric across many
rows. This is highly cacheable:

- **Prompt caching** — put `cache_control` on the stable
  system/rubric block. Cached reads cost 0.1× base price (10×
  reduction). Minimum cacheable content: 4,096 tokens (Opus
  4.5–4.7 / Mythos Preview / Haiku 4.5), or 1,024 tokens (Opus
  4.8 / Sonnet 4.5 / Sonnet 4.6). See
  `references/code_graded.md` for the cache pattern.
- **Batch API** — Anthropic's batch endpoint is ~50% cheaper, ideal
  for nightly regression sweeps.
- **Cheap judge by default** — Haiku 4.5 with a tight rubric and
  binary output handles most graders. Promote to Opus only on the
  disagreement set or for calibration.

## Output you produce

By the end of an interaction, leave the user with:

- A directory in their repo containing the dataset and eval
  config/script (e.g. `evals/`)
- A documented command to run it (`npx promptfoo@latest eval` or
  `python evals/run.py`)
- A baseline score for the original prompt
- A revised prompt with a one-line hypothesis
- The new score and a short failure-mode summary

Templates in `assets/`:

- `promptfooconfig.template.yaml` — minimal promptfoo config
- `python_eval.template.py` — Anthropic SDK eval loop with prompt
  caching and extended-thinking-safe block extraction
- `judge_prompt.template.md` — rubric judge with Structured Outputs

## References

Load only what's relevant. Each file has a single-purpose focus:

- `references/dataset_design.md` — capability vs. regression suites,
  stratification by feature × scenario × persona, 20–50 from real
  failures, two-SME-agreement rule, criteria drift, dataset growth
- `references/code_graded.md` — exact match, set match (multi-label),
  regex, `<answer>` extraction, Structured Outputs (replaces
  prefill), extended-thinking-safe block extraction, prompt
  caching, async/concurrency, Batch API
- `references/model_graded.md` — binary judges, behavioral anchors,
  CoT-before-scoring, **bias mitigation with measured effects**
  (position swap, length-neutral, heterogeneous family), calibration
  with Cohen's κ, judge model selection, **Structured Outputs
  replaces deprecated prefill**, Anthropic logprobs gap (G-Eval
  caveat)
- `references/rag_evals.md` — RAGAs metrics (faithfulness,
  answer-relevance, context-precision/recall) with formulas,
  promptfoo `context-*` assertions, quote-then-answer pattern
- `references/tool_use_evals.md` — `stop_reason == "tool_use"`,
  `tool_use.name`/`input` checks, `tool_choice` options,
  `trajectory:*` assertions, "grade output not path"
- `references/promptfoo.md` — full config anatomy, current provider
  strings, assertion taxonomy (deterministic + model-graded
  including `g-eval`, `factuality`, `answer-relevance`,
  `context-*`, `agent-rubric`, `trajectory:*`, `max-score`),
  iteration flags (`--filter-failing`, `--repeat`, `--resume`),
  `generate dataset` / `generate assertions`, CI/CD with
  junit.xml
- `references/production_patterns.md` — capability vs. regression,
  eval-on-PR, threshold gating, shadow scoring, Goodhart/criteria
  drift, ownership (Principal Domain Expert), 60–80% effort on
  error analysis

## Common pitfalls / FAQ

**"My eval shows 100% pass."** Either the prompt is genuinely good
or the dataset has saturated. Add adversarial rows; promote passing
rows to the regression suite and write new capability rows. See
`references/dataset_design.md` § "When to grow."

**"My judge disagrees with me on calibration."** Iterate on the
**rubric, not the judge model**. Vague anchors and missing "what to
ignore" guidance are almost always the cause. Target Cohen's κ
≥ 0.6 / ≥80% raw agreement before deploy. See
`references/model_graded.md` § "Calibration."

**"The eval is too slow / too expensive."** In priority order:
prompt-cache the rubric (10× cheaper reads), batch via the Message
Batches API (~50% cheaper), use Haiku as the default judge with a
binary rubric, run code-graded filters before the LLM judge.

**"My score changes when I rerun."** Set `temperature: 0` on both
the model under test and the judge. Pin model IDs (don't use
`-latest` for a regression suite). If still flaky, the judge is
under-anchored — add behavioral anchors.

**"I changed the prompt and the dataset in the same iteration."**
Don't. You can't tell which moved the score. Pin one, change the
other.

**"My v2 prompt scored lower than v1 on the eval but feels better."**
Trust the eval *if* the dataset is representative. If it isn't,
that's the bug — add the rows that v2 handles better and v1
doesn't. The dataset, not the score, is the artifact under test.

**"My grader uses `response.content[0].text` and now it breaks."**
Extended thinking on Opus 4.7+ puts a `thinking` block first.
Iterate: `"".join(b.text for b in resp.content if b.type == "text")`.
See `references/code_graded.md` § "Pattern 1."

**"My judge returns invalid JSON sometimes."** You're probably using
the deprecated prefill + stop-sequence pattern. Switch to
Structured Outputs (`output_config.format`) — works on every
current Claude model, guaranteed parseable.

**"My pairwise judge always picks A."** Position bias. Call the
judge twice with swapped order, only count when both calls agree.
See `references/model_graded.md` § "Position bias."

**"My judge prefers longer answers."** Verbosity bias (91% on
Claude). Add "ignore length; concision is a virtue" to the rubric,
or score conciseness as its own criterion.

**"The user asks for an eval but the prompt is in production
already."** Add an online (shadow) layer — sample 1–10% of
production, judge with a cached cheap judge, alert on drift. See
`references/production_patterns.md` § "Offline vs. online."

## What this skill is not

- **Not a model capability benchmark** (MMLU, ARC). This evaluates
  *your* prompt on *your* task.
- **Not human-in-the-loop labeling at scale** — though the Console
  Evaluate tab supports manual 1–5 human grading for small sets.
- **Not a substitute for production monitoring.** Offline evals
  catch regressions before deploy; online (shadow) evals catch
  them in production. See `references/production_patterns.md` for
  the offline/online split.
