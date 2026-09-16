# Judge Prompt Template

Two variants depending on the criterion: **binary** (preferred
default for actionability) and **anchored numeric** (when you
genuinely need granularity).

> **Modern Claude does not support assistant-message prefilling.**
> The docs state: *"Prefilling is not supported on Claude Opus 4.8,
> Claude Mythos Preview, Claude Opus 4.7, Claude Opus 4.6, and
> Claude Sonnet 4.6."* Requests with a prefilled assistant turn
> are rejected. Use **Structured Outputs** (`output_config.format`)
> to guarantee parseable JSON instead. The prefill + stop-sequence
> pattern still works on Haiku 4.5, Sonnet 4.5 and older models —
> but Structured Outputs works everywhere and is the recommended
> approach.

---

## Variant A: Binary judge with Structured Outputs (preferred default)

This is what most graders should look like. Read it before reaching
for the numeric form.

```text
You are grading a <OUTPUT_KIND>.

Criterion: <ONE-SENTENCE CRITERION, e.g. "the answer is
faithful to the source — every claim is supported by the
provided context, and nothing is invented">.

<INPUT_CONTEXT_TAG>{input_context}</INPUT_CONTEXT_TAG>

<OUTPUT_TAG>{output_to_evaluate}</OUTPUT_TAG>

Think briefly about whether the criterion is met, then return a
verdict.
```

Schema (passed to the API as `output_config.format`):

```json
{
  "type": "json_schema",
  "schema": {
    "type": "object",
    "properties": {
      "reasoning": {
        "type": "string",
        "description": "One short paragraph of reasoning before the verdict."
      },
      "verdict": {
        "type": "string",
        "enum": ["correct", "incorrect"]
      }
    },
    "required": ["reasoning", "verdict"],
    "additionalProperties": false
  }
}
```

Python call shape:

```python
resp = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    temperature=0,
    system=JUDGE_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": judge_user_prompt}],
    output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
)
import json
parsed = json.loads(resp.content[0].text)
passed = parsed["verdict"] == "correct"
```

Why this shape:

- **Binary verdict** — Hamel Husain, Eugene Yan, Arize, Databricks
  converge on this. "It's not actionable… people don't know what to
  do with a 3 or 4." Binary makes thresholding trivial and aligns
  with how Cohen's κ wants to be computed.
- **Reasoning before verdict** — "reason then collapse to a label"
  is the canonical shape from MT-Bench and Anthropic's own grader
  template; "increases evaluation performance, particularly for
  tasks requiring complex judgment" (Anthropic docs).
- **Structured Outputs over prefill** — works on every current
  model, guarantees parseable JSON, no `JSON.parse` errors.

---

## Variant B: Anchored numeric judge with multi-axis Structured Output

Use when binary is too coarse — e.g. when you need to track
"summaries got more concise without losing accuracy" over time.
**Keep the scale low-cardinality (0–3 or 1–5), never 1–10 or
0–100** — high-precision scales show poor judge consistency
(Databricks).

```text
You are grading a <OUTPUT_KIND>.

Score each criterion below. For each, pick the integer whose
behavioral anchor best matches the output. Do not split the
difference between anchors.

1. <CRITERION_1> (1-5):
   - 1: <concrete behavior — what a 1 looks like>
   - 3: <concrete behavior — middle case>
   - 5: <concrete behavior — what a 5 looks like>

2. <CRITERION_2> (1-5):
   - 1: <...>
   - 3: <...>
   - 5: <...>

3. <CRITERION_3> (1-5):
   - 1: <...>
   - 3: <...>
   - 5: <...>

Notes on what to ignore:
- Length: ignore unless concision is itself a scored criterion.
- Formatting: ignore decorative structure (bullets, headings).
- Style preferences: only score what the criteria above name.

<examples>
<example>
This <OUTPUT_KIND>:
<output>
<paste a concrete example output that should score well>
</output>
Scores: <criterion_1>=5, <criterion_2>=5, <criterion_3>=5
Reason: <one-sentence explanation>
</example>

<example>
This <OUTPUT_KIND>:
<output>
<paste a concrete example that should score poorly on at least
one axis>
</output>
Scores: <criterion_1>=1, <criterion_2>=5, <criterion_3>=3
Reason: <one-sentence explanation>
</example>
</examples>

<INPUT_CONTEXT_TAG>{input_context}</INPUT_CONTEXT_TAG>

<OUTPUT_TAG>{output_to_evaluate}</OUTPUT_TAG>

Think briefly about each axis, then return the scores.
```

Schema:

```json
{
  "type": "json_schema",
  "schema": {
    "type": "object",
    "properties": {
      "reasoning": { "type": "string" },
      "criterion_1": { "type": "integer", "minimum": 1, "maximum": 5 },
      "criterion_2": { "type": "integer", "minimum": 1, "maximum": 5 },
      "criterion_3": { "type": "integer", "minimum": 1, "maximum": 5 }
    },
    "required": ["reasoning", "criterion_1", "criterion_2", "criterion_3"],
    "additionalProperties": false
  }
}
```

Important: **prefer one isolated judge per criterion** (one API
call per axis) over a single multi-axis judge. Anthropic's
guidance: "grade each dimension with an isolated LLM-as-judge
rather than using one to grade all dimensions" — compound rubrics
confuse judges and produce halo effects.

The multi-axis form above is a compromise for cost-sensitive
loops; if you have budget, split it into three judges.

---

## Variant C: Pairwise comparison with position-swap

Use when comparing two prompt versions on the same input. Pairwise
correlates with human judgment better than absolute scoring (LLM-
as-a-Judge Survey, 2024) but Claude is severely position-biased
(75% first-position preference, 23.8% consistency in MT-Bench).
**Always call the judge twice with reversed order**, count the
result only if both calls agree.

```text
You are choosing the better of two <OUTPUT_KIND>s.

Criterion: <ONE-SENTENCE CRITERION>.

<input>{input}</input>

<output_a>{output_a}</output_a>
<output_b>{output_b}</output_b>

Pick the one that better satisfies the criterion. If they are
genuinely indistinguishable, return "tie".
```

Schema:

```json
{
  "type": "json_schema",
  "schema": {
    "type": "object",
    "properties": {
      "reasoning": { "type": "string" },
      "winner": { "type": "string", "enum": ["A", "B", "tie"] }
    },
    "required": ["reasoning", "winner"],
    "additionalProperties": false
  }
}
```

Pairwise loop:

```python
def pairwise(output1, output2, input_text):
    # Call 1: output1 as A, output2 as B
    a = judge(input_text, output1, output2)["winner"]
    # Call 2: swap roles
    b_swapped = judge(input_text, output2, output1)["winner"]
    # Translate the swapped call's verdict back to original labels
    b = {"A": "B", "B": "A", "tie": "tie"}[b_swapped]
    if a == b:
        return a            # agree → trust
    return "tie"            # disagree → call it a tie
```

Cost is 2× a pointwise judge. Use pairwise when comparing variants;
use binary pointwise when monitoring one variant over time.

---

## Reference-guided variant

If the task has a single correct answer (math, factual QA, code),
**include a reference answer in the judge prompt**. MT-Bench
showed this drops math-question failure rates from 70% to 15%.

```text
You are grading whether the model output matches the reference
answer in substance (paraphrases are fine, semantically equivalent
formulations are fine).

<reference>{reference_answer}</reference>

<output>{output_to_evaluate}</output>

Verdict: <correct | incorrect>
```

Reference-guided judging is one of the cheapest accuracy wins
available. Use it whenever a reference exists, even an approximate
one.

---

## Why each part is here

- **Binary verdict by default** — actionable, easy to align on,
  trivially computes Cohen's κ against human labels.
- **Reasoning field before the verdict** — CoT-before-scoring
  reliably improves judge accuracy. Anthropic's official template
  uses this pattern (`<thinking>` then `<result>correct|incorrect</result>`).
- **Structured Outputs over prefill** — prefill is now a 400 error
  on current Claude. Structured Outputs gives the same parsing
  guarantee on every model.
- **Behavioral anchors when numeric** — without anchors, judges
  drift to the middle. Each integer needs a one-line concrete
  behavior description.
- **"What to ignore" section** — preempts the most common ways a
  judge over-penalizes (length, decorative formatting, style).
- **Two calibration examples** — turn the rubric into few-shot.
  Pick one near 5 and one near 1 so the spread is clear. Increases
  judge consistency.
- **Reference inside its own tag** when grading faithfulness or
  accuracy. The judge needs the source. When grading something
  that doesn't need the source (refusal, tone), omit the tag.
- **Pairwise with mandatory position swap** — without swap,
  Claude-as-judge has 75% first-position preference. With swap +
  agreement gate, position bias is eliminated.

---

## Calibration (do this before trusting the judge)

Before you ship a judge, hand-grade 25–50 outputs yourself, then
run the judge on the same outputs. Measure:

- **Cohen's κ** (for binary or low-cardinality categorical) —
  target ≥ 0.6 ("substantial agreement"); ≥ 0.8 is "almost perfect".
- **Raw agreement** as a sanity check — target ≥ 80%. Note:
  with imbalanced classes, raw agreement is misleading; always
  compute κ.
- **Spearman / Kendall τ** (for ordinal scores) — target ≥ 0.5.

If agreement is low, **iterate on the rubric, not the judge model**.
The fix is almost always sharper anchors and clearer "what to
ignore" guidance.

Re-calibrate whenever the underlying judge model is upgraded, the
rubric changes, or every quarter — whichever comes first.

---

## Source citations for this template

- Anthropic, [Cookbook — misc/building_evals.ipynb](https://github.com/anthropics/claude-cookbooks/blob/main/misc/building_evals.ipynb)
  (repo `anthropics/claude-cookbooks`) — official judge prompt
  format (`<rubric>`, `<answer>`, `<thinking>`, `<correctness>`)
- Anthropic, [Increase output consistency](https://platform.claude.com/docs/en/docs/test-and-evaluate/strengthen-guardrails/increase-consistency)
  — prefill deprecation on Opus 4.6+ / Sonnet 4.6
- Anthropic, [Structured outputs](https://platform.claude.com/docs/en/docs/build-with-claude/structured-outputs)
  — `output_config.format` replaces prefill
- Anthropic Engineering, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
  — "isolated LLM-as-judge per criterion"
- Liu et al., 2023, [G-Eval](https://arxiv.org/abs/2303.16634) — form-filling, CoT
- Zheng et al., 2023, [Judging LLM-as-a-Judge with MT-Bench](https://arxiv.org/abs/2306.05685)
  — bias measurements, position swap
- Hamel Husain, [LLM-as-Judge that drives business results](https://hamel.dev/blog/posts/llm-judge/)
  — binary over Likert
- Eugene Yan, [LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/)
  — Cohen's κ over raw correlation
