# Model-Graded Evaluations (LLM-as-Judge)

Use a model to grade another model's output when the criterion
can't be reduced to deterministic code: tone, faithfulness, refusal
quality, summary completeness, "is this explanation grade-school
appropriate?". Model-graded evals are **expensive, slower, and
noisier** than code-graded ones. The payoff is being able to
evaluate things that no regex can capture.

This reference covers (1) when to reach for a judge, (2) what shape
the judge should take, (3) the empirically-measured biases and how
to mitigate each, (4) calibration against human labels, and (5)
the Anthropic-API patterns you need to make all of it work.

## When to use a judge

- The criterion is naturally expressed in language ("response is
  apologetic", "summary is grade-school appropriate", "answer is
  faithful to the passage")
- Outputs are open-ended and vary across acceptable responses
- You've tried code-graded and it either catches the wrong thing
  or is impossible to write

## When **not** to use a judge

- The criterion is exact-match or set-match — code is cheaper and
  has zero variance
- The judge would need information it doesn't have (private DB,
  user's true preference)
- You're testing the same model family that's generating the output
  on a subtle criterion — self-enhancement bias dominates

## The default judge shape: binary + reasoning, Structured Outputs

The empirical consensus across senior practitioners (Husain, Yan,
Anthropic, Arize, Databricks, Shankar) is:

1. **Binary verdict** (`correct` / `incorrect`) by default.
2. **Reasoning before verdict** ("CoT-before-scoring").
3. **One isolated judge per criterion** — Anthropic's published
   guidance: "grade each dimension with an isolated LLM-as-judge
   rather than using one to grade all dimensions."
4. **Structured Outputs** for parsing (not prefill — deprecated).
5. **Temperature 0** and **pin the judge model**.

```python
import json
from anthropic import Anthropic

client = Anthropic()
JUDGE = "claude-haiku-4-5-20251001"

JUDGE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string"},
            "verdict": {"type": "string", "enum": ["correct", "incorrect"]},
        },
        "required": ["reasoning", "verdict"],
        "additionalProperties": False,
    },
}

JUDGE_SYSTEM = (
    "You are grading <OUTPUT_KIND>. The criterion is: "
    "<ONE-SENTENCE CRITERION>. "
    "Reason briefly about whether the criterion is met, then "
    "return a verdict."
)


def extract_text(resp):
    return "".join(b.text for b in resp.content if b.type == "text")


def judge(reference, output) -> tuple[bool, str]:
    user = (
        f"<reference>{reference}</reference>\n"
        f"<output>{output}</output>"
    )
    resp = client.messages.create(
        model=JUDGE,
        max_tokens=400,
        temperature=0,
        system=[{
            "type": "text",
            "text": JUDGE_SYSTEM,
            "cache_control": {"type": "ephemeral"},   # rubric is stable
        }],
        messages=[{"role": "user", "content": user}],
        output_config={"format": JUDGE_SCHEMA},
    )
    parsed = json.loads(extract_text(resp))
    return parsed["verdict"] == "correct", parsed["reasoning"]
```

Three details to notice:

- **`output_config.format`** replaces the old prefill + stop-sequence
  trick. Prefill is now a 400-error on Opus 4.6+ / Sonnet 4.6.
- **`cache_control` on the system block** — the rubric is identical
  across all rows; cached reads cost 0.1× base. For a 200-row eval
  that's ~10× cheaper.
- **`extract_text` over `content[0].text`** — when adaptive
  thinking is on, the first block is `type: "thinking"`. Filter
  explicitly.

## When binary isn't enough: anchored numeric

If you need to track "summaries got more concise without losing
accuracy" *over time*, you may want a numeric score. In that case:

- **Use 0–3 or 1–5, not 1–10 or 0–100.** Databricks tested every
  scale; "lower-precision grading scores like 0, 1, 2, 3 or even
  binary (0, 1) can largely retain precision" while higher-precision
  scales (0–100) showed poor consistency.
- **Each integer needs a behavioral anchor.** Not "5: excellent",
  but "5: includes all essential information without superfluous
  detail." Without anchors, judges drift toward 3 or 4.
- **Decompose by criterion.** One axis per judge call. Compound
  rubrics produce halo bias — a well-formatted answer scores
  higher across unrelated criteria.

See `assets/judge_prompt.template.md` Variant B for the format and
schema.

## Bias taxonomy (with measured effect sizes and mitigations)

LLM judges have systematic biases that are large and reproducible.
The numbers below come from MT-Bench (Zheng et al., 2023) and are
corroborated by Eugene Yan's independent replication. Ignoring them
will mislead you.

### Position bias (pairwise)

Judges favor whichever answer appears first.

| Judge | Position consistency (same verdict on swap) | First-position preference |
| --- | --- | --- |
| Claude-v1 | **23.8%** | **75%** |
| GPT-3.5 | 46.2% | ~50% |
| GPT-4 | 65.0% | — |

**Mitigation: position swap with agreement gate.** Always call the
judge twice with reversed order; count the result only if both
calls agree, otherwise declare a tie. Few-shot examples raise
consistency further (GPT-4: 65.0% → 77.5%). Cost is 2× the judge
calls but eliminates the bias.

```python
def pairwise_judge(a, b, prompt):
    v1 = call_judge(prompt, a, b)["winner"]          # A=a, B=b
    v2_raw = call_judge(prompt, b, a)["winner"]      # swapped
    v2 = {"A": "B", "B": "A", "tie": "tie"}[v2_raw]  # back to original labels
    return v1 if v1 == v2 else "tie"
```

### Verbosity bias

Judges prefer longer answers even when content is matched or worse.
Zheng et al. ran a "repetitive list" attack that pads an answer
with redundant bullets. Failure rates (judge prefers the bloated
version):

| Judge | Verbosity-attack failure rate |
| --- | --- |
| Claude-v1 | **91.3%** |
| GPT-3.5 | 91.3% |
| GPT-4 | 8.7% |

**Mitigation**: include "ignore length; concision is a virtue" in
the rubric; for binary judges, score conciseness as its own
criterion so it can't halo; for pointwise scoring, normalize by
length; for pairwise, pre-truncate both sides to comparable length.

### Self-enhancement bias

Judges score outputs from their own family higher. Measured win-
rate inflation: GPT-4 self-judges +10%; Claude-v1 self-judges +25%.

**Mitigation**: heterogeneous judge family. If the model under
test is Claude, prefer a non-Claude judge for adversarial benchmarks.
If that's impractical (your stack is Anthropic-only), at minimum
use a *different generation* (e.g. judge with Opus 4.8 outputs
generated by Haiku 4.5).

### Format / concreteness / halo bias

Structured output (bullets, headings, code fences) consistently
scores higher than equivalent prose, even when format isn't a
criterion. JudgeLM lists "format bias" alongside position and
knowledge bias as primary targets.

**Mitigation**: criteria decomposition — one criterion per judge —
so format can't halo over correctness. Explicit "ignore formatting
unless it's scored" in the rubric.

### Sycophancy / authority bias

Judges agree with implied "preferred" answers when the prompt
encodes a preference ("which response is *better*?") or authority
("the expert chose..."). The 2024 survey groups this under
"judgment-specific biases."

**Mitigation**: neutral wording. Don't reveal which is v1 vs v2;
don't say "which is better at being helpful" — say "which output
meets criterion X." For pairwise, randomize labels (A/B vs
prompt1/prompt2).

### Quick-reference table

| Bias | Effect on Claude judges | Mitigation |
| --- | --- | --- |
| Position | 75% first-pos pref | Position swap + agreement gate |
| Verbosity | 91% prefer padded | Length-neutral instruction; decompose |
| Self-enhancement | +25% own win rate | Heterogeneous judge family |
| Format / halo | Halo on structured outputs | Per-criterion isolated judge |
| Sycophancy | Agrees with implied preferred | Neutral wording; blind labels |

## Rubric design technique: "reason then collapse to a label"

The dominant pattern across the literature:

1. Judge **reasons** in a `<thinking>` or `reasoning` field first.
2. Judge then emits a **single label or score**.
3. Grader code **discards the reasoning** and acts on the verdict.

Anthropic's official grader template
([anthropics/claude-cookbooks — misc/building_evals.ipynb](https://github.com/anthropics/claude-cookbooks/blob/main/misc/building_evals.ipynb))
uses this exact shape:

```text
You will be provided an answer that an assistant gave to a
question, and a rubric that instructs you on what makes the answer
correct or incorrect.

Here is the answer that the assistant gave to the question.
<answer>{answer}</answer>

Here is the rubric on what makes the answer correct or incorrect.
<rubric>{rubric}</rubric>

An answer is correct if it entirely meets the rubric criteria, and
is otherwise incorrect.
First, think through whether the answer is correct or incorrect
based on the rubric inside <thinking></thinking> tags. Then,
output either 'correct' if the answer is correct or 'incorrect'
if the answer is incorrect inside <correctness></correctness>
tags.
```

OpenAI Evals' canonical model-graded template is `cot_classify` —
described as "typically the most accurate model-graded evaluations."

This pattern is why every binary judge schema in this skill has a
`reasoning` field first, then the verdict.

## Reference-guided judging (a cheap accuracy win)

When the task has a ground truth (math, factual QA, code, RAG
faithfulness), **include a reference answer in the judge prompt**.
MT-Bench shows reference-guided judging drops math-question failure
rates **from 70% to 15%**.

```text
You are grading whether the model output matches the reference in
substance. Paraphrases and semantically equivalent formulations are
fine.

<reference>{reference}</reference>
<output>{output}</output>

Verdict: <correct | incorrect>
```

Use it whenever a reference exists, even an approximate one. For
RAG, the "reference" is the retrieved context — see
`rag_evals.md`.

## Pairwise vs pointwise

The 2024 LLM-as-a-Judge survey is direct: "LLM and human
evaluations are more aligned in the context of pairwise comparisons
compared to score-based assessments." But pairwise costs 2× the
judge calls (position swap), so pick deliberately:

| Use **pairwise** when | Use **pointwise** when |
| --- | --- |
| Comparing two prompt versions / A/B | Single-output production gate |
| Subjective qualities (style, helpfulness) | Objective rubrics (faithfulness, refusal, classification) |
| Need ranking, not absolute calibration | Need a scalar to monitor over time |
| Iterating in a loop | Capturing regression in CI |

The two are not mutually exclusive — many production stacks use
pointwise for monitoring and pairwise for A/B picking.

## Calibration: validate before trusting

You cannot deploy a judge without validating it against human
grades on a held-out set. The procedure:

1. **Hand-grade 25–50 outputs yourself** (or a Principal Domain
   Expert does — see `production_patterns.md` on ownership).
2. **Run the judge on the same outputs.**
3. **Compute agreement.** Target reference numbers:
   - Anthropic / MT-Bench: **80%+ raw agreement** = comparable to
     human-human (81% baseline).
   - Databricks: 80%+ agreement, 95% within ±1 on a 0-3 scale.
   - Husain: target **TPR/TNR ≥ 0.9** before deploy.
4. If agreement is low, **fix the rubric, not the judge model**.
   Vague anchors and missing "what to ignore" guidance are almost
   always the cause.

### Pick the right agreement metric

| Output type | Metric |
| --- | --- |
| Binary | **Cohen's κ** (κ ≥ 0.6 = substantial; ≥ 0.8 = near-perfect) |
| Multi-class categorical | Cohen's κ; per-class precision/recall |
| Ordinal scores | Spearman ρ or Kendall τ |
| > 2 raters or missing data | Krippendorff's α |

**Do not use raw agreement on imbalanced classes** — Husain calls
this out: with a 90/10 split, an always-says-pass judge gets 90%
agreement. Always compute κ to net out chance agreement.

### Re-calibration cadence

Re-validate the judge when:

- The judge model is upgraded (Sonnet 4.6 → 4.7) — judge behavior
  shifts.
- The rubric is edited.
- Every quarter, regardless.

Persistent judge drift over time is called **criteria drift**
(Shankar et al., "Who Validates the Validators?"): "it is
impossible to completely determine evaluation criteria prior to
human judging of LLM outputs." The labeling ritual itself reveals
the criteria; the rubric is downstream of human judgment, not
upstream.

## Judge model selection

| Choice | When |
| --- | --- |
| Haiku 4.5 (cheap default) | Most graders. Tight rubric + binary verdict + cached system block. Cost-effective at scale. |
| Sonnet 4.5 / 4.6 (middle) | When Haiku disagrees with humans on calibration. |
| Opus 4.7 / 4.8 (strong) | Hard rubrics; subtle distinctions; calibration baseline; never as production default unless cost is irrelevant. |
| **Different family** (GPT-4, Gemini) | Adversarial benchmarks against Claude; self-enhancement-sensitive comparisons. |

**Judge cascade pattern**: cheap judge on everything, expensive
judge on the disagreement set or low-confidence cases. Databricks'
recipe: GPT-4 to discover the rubric, then GPT-3.5 (cheap) with one
example per score in production — 10× cheaper, 3× faster, preserves
~95% of accuracy.

## promptfoo equivalents

In promptfoo, the same patterns are available as built-in
assertions. Use whichever maps to your criterion:

```yaml
assert:
  # Binary, free-form rubric. Default grader auto-selected from
  # available API keys (Anthropic with ANTHROPIC_API_KEY only).
  - type: llm-rubric
    provider: anthropic:messages:claude-haiku-4-5-20251001
    value: "Response is faithful to the source — every claim has support."
    threshold: 0.8

  # Closed-QA binary Y/N from OpenAI evals (simpler than llm-rubric).
  - type: model-graded-closedqa
    value: "Explains the concept without technical jargon."

  # Five-way factuality classifier (A subset, B superset, C identical,
  # D disagree=fail, E differs-but-factual). Customize weights.
  - type: factuality
    value: "Sacramento is the capital of California"

  # CoT-anchored scoring with default threshold 0.7. Array → axes
  # averaged.
  - type: g-eval
    value: ["Factually accurate", "Well structured"]
    threshold: 0.7

  # Pick the best of N parallel outputs.
  - type: select-best
    value: "criterion for 'best'"
```

For RAG-specific judges (`answer-relevance`, `context-faithfulness`,
`context-recall`, `context-relevance`), see `rag_evals.md`. For
agent / tool-use judges (`trajectory:*`, `agent-rubric`), see
`tool_use_evals.md`.

## Anthropic-API constraints to know

- **Prefill is deprecated** on Opus 4.6 / Opus 4.7 / Opus 4.8 /
  Sonnet 4.6 / Mythos Preview — use Structured Outputs.
- **`response.content[0].text`** breaks when extended thinking is
  on — use `extract_text` (iterate filtering `type == "text"`).
- **No token logprobs.** The Anthropic Messages API does not
  expose logprobs as of 2026. G-Eval's probability-weighted
  scoring (`Σ p(s) · s`) cannot be implemented natively on Claude.
  Fall back to repeated sampling and averaging — more expensive
  and noisier than the OpenAI implementation.
- **Cache the rubric.** Identical across rows; 0.1× cost on hit.
  Minimums: 4,096 tokens (Opus 4.5/4.6/4.7 / Mythos / Haiku 4.5);
  1,024 tokens (Opus 4.8 / Sonnet 4.5 / Sonnet 4.6).
- **Temperature 0** on the judge for reproducibility.

## Cost considerations

A model-graded eval roughly **doubles** token cost (one call to
generate, one to grade) and adds latency. For a 20-row iteration
loop, fine. For a 200-row pre-deploy gate, plan for it.

Cost-control levers, in priority order:

1. **Prompt-cache the rubric** — 10× cheaper rubric tokens.
2. **Use Haiku 4.5** as the default judge with a tight binary rubric.
3. **Cascade**: Haiku on everything → Opus on the disagreement
   set.
4. **Batch API** for nightly regression runs — ~50% cheaper than
   sync.
5. **Run the judge only on rows where the output changed** from
   the previous run (diff-only eval).
6. **Skip the judge on rows that fail code-graded gates first** —
   format / length / refusal checks are nearly free.

## Source citations

- [Anthropic — Cookbook: misc-building-evals](https://platform.claude.com/cookbook/misc-building-evals) — official judge template
- [Anthropic — Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — isolated judge per criterion
- [Anthropic — Structured Outputs](https://platform.claude.com/docs/en/docs/build-with-claude/structured-outputs)
- [Anthropic — Prompt caching](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching)
- [Anthropic — Increase output consistency (prefill deprecation)](https://platform.claude.com/docs/en/docs/test-and-evaluate/strengthen-guardrails/increase-consistency)
- [Zheng et al., 2023 — Judging LLM-as-a-Judge with MT-Bench](https://arxiv.org/abs/2306.05685) — bias measurements
- [Liu et al., 2023 — G-Eval](https://arxiv.org/abs/2303.16634) — form-filling, CoT, logprob scoring
- [Survey on LLM-as-a-Judge, 2024](https://arxiv.org/html/2411.15594v6) — pairwise vs pointwise consensus
- [Hamel Husain — LLM-as-Judge that drives business results](https://hamel.dev/blog/posts/llm-judge/) — binary over Likert
- [Eugene Yan — LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/) — Cohen's κ over raw correlation
- [Databricks — RAG auto-eval best practices](https://www.databricks.com/blog/LLM-auto-eval-best-practices-RAG) — scale-precision study
- [Shankar et al. — Who Validates the Validators?](https://arxiv.org/abs/2404.12272) — criteria drift
