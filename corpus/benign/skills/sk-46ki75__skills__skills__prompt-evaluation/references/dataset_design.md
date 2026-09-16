# Dataset Design

A prompt eval is only as good as its test set. A polished judge and
clean tooling mean nothing if the inputs are unrepresentative or
the golden answers are wrong. This reference covers how to build
test sets that actually tell you something — drawn from the
practitioner consensus (Husain, Yan, Shankar) and Anthropic's
published guidance.

## The four parts of an eval row

Every eval row, regardless of grading approach, has the same shape:

- **Input** — variable(s) the prompt template consumes (question,
  complaint, article, code snippet). Should reflect what real users
  / real callers actually send.
- **Golden answer** — correct or ideal output. For classification,
  the label(s); for extraction, the expected value(s); for open-
  ended generation, a reference output or a rubric.
- **Model output** — what comes out at eval time. The eval produces
  this; you don't author it.
- **Score** — produced by the grader. Pass/fail, a number, or a
  GradingResult dict, depending on tool.

Inputs and golden answers are the part you author. Get them right.

## Look at real failures first (Hamel's correction to "evals first")

The canonical mistake is to start by writing eval cases in the
abstract — what *should* fail, what *might* fail. Don't. **Read
20–50 real failures first.** Eugene Yan's five-step method opens
with literal "Observation": "examining our inputs, AI outputs, and
how users interact with our systems." Hamel Husain is sharper:
*"Don't practice eval-driven development. Begin with error
analysis instead — reviewing actual failures reveals which
evaluators matter."*

Anthropic's published guidance matches: *"20–50 simple tasks drawn
from real failures is a great start."* The bias toward real
failures (vs. synthetic happy paths) is intentional.

If the user has no production data yet, this becomes: "show me
3–5 example inputs and your ideal outputs." Those are the seed
golden pairs. Grow from there.

## Capability suite vs. regression suite

These have **opposite design goals**. Anthropic's Engineering blog
articulates the split bluntly:

| Suite | Pass-rate target | Purpose |
| --- | --- | --- |
| **Capability** | **Start low**, target tasks the agent struggles with | Probe the ceiling; expose failure modes; drive prompt iteration |
| **Regression** | **Near 100%** | Enforce the floor; "a decline in score signals that something is broken" |

In practice:

- **Regression suite** = the "golden set." Small (50–200 rows),
  hand-curated, high-signal, owned by a named SME. Frozen — only
  grows when a real regression slips through. Anthropic's rule:
  *"A good task is one where two domain experts would independently
  reach the same pass/fail verdict."*
- **Capability suite** = the "silver set." Larger, noisier, often
  synthetically grown. Used to find the next bug, not to gate
  deploys.

If you're just starting, you only need the regression suite. Add
the capability suite when you've stopped finding new failure
categories in the regression set.

## How big should the dataset be?

| Phase | Size | Notes |
| --- | --- | --- |
| Seed | 20–50 | Real failures, not synthetic. Anthropic's recommended start. |
| Iteration loop | 20–100 | Husain's **20-trace stop rule**: stop sampling when 20 traces yield no new failure category. Review at least 100 in total. |
| Pre-deploy regression | 100–500 | Stratified, owned by an SME. Frozen between releases. |
| Capability / exploration | 500+ | Generated, noisier, evolving. |

A 12-row dataset that **covers the failure modes you care about**
beats a 200-row dataset of similar easy cases. **Diversity > size**
at small N. Grow size only when adding rows produces new failure
categories.

## What to include

A useful 20-case seed dataset is roughly:

- **~60% typical cases** — the boring things real users send all
  day. Sets the baseline.
- **~25% edge cases** — boundary conditions the user already knows
  about. Long inputs, short inputs, multi-label inputs, ambiguous
  phrasing.
- **~15% adversarial cases** — designed to break the prompt. The
  course's fox-leg-counting example is the canonical illustration:
  a trick input exposing weak reasoning. For a classifier, an
  input that genuinely sits between two categories. For a refusal-
  trained prompt, a near-miss request.

The point of the adversarial slice is **not** to drive the pass
rate to 100%. It's to give you a yardstick that doesn't saturate
the first time you fix the easy bugs.

## Stratification: features × scenarios × personas

Hamel Husain's **Critique Shadowing** method formalizes test-case
coverage along three axes:

- **Features** — capabilities required (classification, extraction,
  summarization, refusal)
- **Scenarios** — situational contexts (exact match, multiple
  matches, no matches, invalid criteria, empty input)
- **Personas** — user types with distinct needs (novice vs power
  user; English vs non-English speaker; technical vs business
  audience)

"At a minimum, you want to generate enough data so that you have
examples for each combination of dimensions."

The product can explode quickly (3 features × 4 scenarios × 3
personas = 36 cells). Prioritize cells your product is most
exposed to.

## Sourcing golden answers

Where the golden answer comes from matters as much as having one.

| Source | Quality | Cost | Use for |
| --- | --- | --- | --- |
| **Hand-authored by SME** | Highest | Highest | Regression seed; adversarial cases; calibration set |
| **Hand-authored by the user** | Good (when user is the SME) | Low | Iteration loop |
| **Production logs + human review** | Realistic distribution | Medium | Capability suite; growth |
| **Generated by a strong model, then human-reviewed** | Acceptable for bulk | Low | Capability suite expansion |
| **Generated by a strong model, NOT reviewed** | Bakes the model's mistakes in as "truth" | Lowest | **Don't.** |

For open-ended tasks (summarization, explanation, rewriting), a
single fixed golden answer is usually the wrong shape. Switch to a
**rubric** (see `model_graded.md`). Or keep a reference output and
use it as one possible target via `similar` (embedding cosine) or
a reference-guided judge rather than exact match.

## Edge cases worth thinking about

Common categories worth checking explicitly before declaring a
dataset done:

- **Boundary lengths** — empty input, single token, very long input
- **Format variants** — uppercase, lowercase, missing punctuation,
  multilingual, code-mixed
- **Ambiguity** — inputs that legitimately match more than one
  golden category (decide whether to allow multi-label)
- **Negation and conditionals** — "not a bug, but a feature request"
- **Adversarial near-misses** — for refusal prompts, a benign
  request that pattern-matches a refused one
- **Distribution shift** — inputs from a slightly different domain
  than expected (new product line, new locale)
- **PII / safety adversarial** (when relevant) — inputs designed
  to elicit leakage or harmful output

You won't cover all of these in 20 rows. You can cover most of them
in 100. Pick the categories your product is most exposed to.

## Synthesizing test cases (with guardrails)

LLMs can generate realistic test inputs, but with rules (Hamel):

- **Generate user inputs, not outputs.** Outputs you generate are
  going to look like the model's prior, not real users.
- **Incorporate real system constraints** — actual product
  vocabulary, real customer-id format, real category names.
- **Verify scenario coverage** — make sure the synthetic inputs
  span the feature × scenario × persona grid.

promptfoo has a built-in generator that follows this principle:

```bash
npx promptfoo@latest generate dataset \
  --config promptfooconfig.yaml \
  --output tests.yaml \
  --instructions "Cover edge cases for international shipping" \
  --numPersonas 5 \
  --numTestCasesPerPersona 3
```

This is great for hitting the feature × persona grid quickly.
Still review the output before committing — generated inputs need
the same hygiene as everything else.

## Storing the dataset

Pick the format the tool consumes most easily, not the prettiest.

**CSV** — recommended for promptfoo + structured inputs:

```csv
complaint,golden_answer,__metadata:case_type
"App crashes on photo upload","Software Bug","typical"
"My printer isn't recognized","Hardware Malfunction","typical"
"Service down AND I need a CSV export","Service Outage,Feature Request","multi-label"
```

The `__metadata:<field>` columns surface in promptfoo's filtering
(`--filter-metadata case_type=multi-label`).

**Inline YAML** — when you have few cases and want them next to
the config:

```yaml
tests:
  - vars:
      complaint: "App crashes on photo upload"
    assert:
      - type: equals
        value: "Software Bug"
```

**Python list of dicts** — when iterating in the SDK:

```python
EVAL_DATA = [
    {"complaint": "App crashes on photo upload",
     "golden_answer": ["Software Bug"]},
    # ...
]
```

**File-per-case** — when inputs are large (transcripts, articles,
source code):

```yaml
tests:
  - vars:
      article: file://articles/article1.txt
```

## Versioning, lineage, and the regression contract

When you ship a prompt change off the back of an eval, **freeze
the dataset version** that scored it. If you keep editing the
dataset during iteration (you will), v1-vs-v2 prompt comparisons
become apples-to-oranges. Choose one:

- Commit the dataset alongside the prompt change (recommended).
- Tag the dataset (`v0.1`, `v0.2`) when you grow it, and record
  which version produced each score.

OpenAI's `openai/evals` repo uses Git-LFS for explicit content-
addressable lineage. LangSmith and Braintrust both model
"experiments" as immutable, comparable records. The underlying
principle: **the dataset is a first-class versioned object**.

This is the difference between a regression test and a vibes check.

## Criteria drift (Shankar's term — important)

Shreya Shankar coined "criteria drift": *"it is impossible to
completely determine evaluation criteria prior to human judging of
LLM outputs."* The rubric you write up front is wrong. You will
discover the criteria *during* labeling, by noticing what makes
you flip a "pass" to a "fail."

Implications for the workflow:

- Rubrics are **downstream** of human review, not upstream.
- Treat your first 20–30 labels as **criteria discovery**, not
  measurement.
- Re-write the rubric after the first labeling pass — it will
  almost always need it.
- Re-calibrate the judge against humans every quarter or whenever
  the model under test, the judge, or the rubric changes.

This is why "look at the data first" beats "design the eval rubric
in advance."

## When to grow the dataset

Grow when:

- A real failure shows up that isn't in any current row → add it.
- The pass rate has been 100% for two iterations → either the
  prompt is genuinely good or the set is saturated; add harder
  cases or retire the row.
- Stddev across runs is so high the score isn't informative → add
  rows in the noisy category.
- The capability/regression split needs rebalancing — failures from
  capability suite that you've now fixed should migrate into
  regression to prevent backsliding.

For ongoing health, Husain recommends "100+ fresh traces per review
cycle (typically 2–4 weeks)" plus "10–20 traces weekly,
prioritizing outliers and automated flags."

## Don't

- **Don't grow the dataset just because 20 feels small.** Diversity
  matters more than size at small N.
- **Don't let one model generate both inputs and golden answers**
  without review — you're baking that model's failure modes into
  your "truth."
- **Don't change the dataset and the prompt in the same iteration.**
  You can't tell which moved the score.
- **Don't ship a model-graded eval without calibrating the judge**
  against ≥25 human labels first (see `model_graded.md`).

## Source citations

- [Anthropic — Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — capability vs regression suites, "20–50 simple tasks"
- [Hamel Husain — LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/) — 20-trace stop rule, 60–80% effort on error analysis
- [Hamel Husain — Critique Shadowing (LLM-as-Judge)](https://hamel.dev/blog/posts/llm-judge/) — feature × scenario × persona
- [Hamel Husain — Field Guide](https://hamel.dev/blog/posts/field-guide/) — synthesis with guardrails
- [Eugene Yan — An LLM-as-Judge Won't Save the Product](https://eugeneyan.com/writing/eval-process/) — Look at the Data
- [Shankar et al. — Who Validates the Validators?](https://arxiv.org/abs/2404.12272) — criteria drift
- [OpenAI evals repo](https://github.com/openai/evals) — Git-LFS lineage pattern
