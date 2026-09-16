# Code-Graded Evaluations

Code-graded evals use a deterministic function — `output == expected`,
a regex, a set check, JSON schema validation — to decide pass/fail.
They are cheap, fast, and reproducible. Reach for them whenever the
correctness criterion can be expressed as code.

This reference covers the Python + Anthropic SDK pattern with the
**current** API surface (Structured Outputs, prompt caching,
extended-thinking-safe block extraction). For the promptfoo
equivalent, see `promptfoo.md`. For model-graded judging see
`model_graded.md`.

## When code-graded works

- **Exact string match** — fixed short answer (a number, a label,
  a yes/no). E.g. "how many legs does this animal have?"
- **Set match** — multi-label classification where order doesn't
  matter. E.g. classify tickets into one or more of N categories.
- **Substring / keyword presence** — output must mention specific
  required words. Brittle but acceptable for compliance / required-
  citation checks.
- **Regex** — output must match a pattern, e.g.
  `r"Your score of \d{3} (qualifies|does not qualify)"`.
- **Structured-output validation** — output parses as JSON and
  conforms to a schema. **Use Anthropic's Structured Outputs** to
  force the model to emit conforming JSON in the first place; see
  below.
- **Programmatic checks** — output is code that compiles, SQL that
  executes against a fixture and returns expected rows, etc.

## When code-graded breaks down

- **Open-ended generation** — summaries, explanations, rewrites.
  Switch to model-graded (`model_graded.md`).
- **Tone, refusal, faithfulness** — language-level criteria.
  Switch to model-graded.
- **Numeric answers with formatting noise** — model outputs "The
  answer is 5." instead of "5". Two fixes:
  1. **Tighten the prompt** — "Respond only with a digit, nothing
     else." Usually the right move.
  2. **Use Structured Outputs** with a schema that forces an
     integer field. The API enforces conformance.
  3. **Extract before grading** via a transform — e.g. instruct
     the model to wrap its answer in `<answer>...</answer>` tags
     and strip them in code. Best paired with chain-of-thought.

If the deterministic check is fundamentally the wrong measurement
("does this paragraph summarize the article well?"), do not
torture a regex into shape — switch to model-graded.

## Three Anthropic-API patterns every eval pipeline needs

These three patterns are the difference between "works on the
example notebook" and "works on production Claude":

1. **Extended-thinking-safe block extraction** — when adaptive
   thinking is on (Opus 4.7+), `response.content[0].text` returns
   the *thinking summary*, not the answer. Always iterate.
2. **Structured Outputs** (not prefill) — prefill is deprecated
   on Claude 4.6+ and returns HTTP 400. Use `output_config.format`.
3. **Prompt caching** — eval datasets re-send the same long
   system prompt across many rows. Caching on the stable block
   cuts cost ~10×.

### Pattern 1: extended-thinking-safe extractor

```python
def extract_text(response) -> str:
    """Get the text reply, robust to extended thinking blocks."""
    return "".join(
        block.text for block in response.content if block.type == "text"
    )
```

Use `extract_text(resp)` everywhere instead of
`resp.content[0].text`. Cheap, never wrong.

### Pattern 2: Structured Outputs (replaces deprecated prefill)

The old `assistant`-prefill + `stop_sequences` trick to force JSON
**returns HTTP 400 on Claude Opus 4.6+, Sonnet 4.6, Opus 4.7,
Opus 4.8 and Claude Mythos Preview**. Use Structured Outputs
instead — works on every current model and guarantees the response
parses as JSON conforming to your schema.

```python
SCORE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "integer"},
            "rationale": {"type": "string"},
        },
        "required": ["answer", "rationale"],
        "additionalProperties": False,
    },
}

resp = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    messages=[{"role": "user", "content": prompt}],
    output_config={"format": SCORE_SCHEMA},
)

import json
parsed = json.loads(extract_text(resp))
# parsed["answer"] is guaranteed to be an int.
```

Caveats:

- `stop_reason: "refusal"` or `"max_tokens"` can still yield
  non-conforming output. Wrap `json.loads` in try/except for
  defense in depth.
- The Python SDK also offers `client.messages.parse(...,
  output_format=PydanticModel)` returning `.parsed_output` typed.
  Useful when your schema mirrors a Pydantic model anyway.

### Pattern 3: prompt caching for cheap reruns

Eval datasets re-send the same long system prompt (or rubric) for
hundreds of rows. Cached reads cost **0.1× base price** — a 10×
cost reduction. Put `cache_control` on the *stable* block:

```python
resp = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    system=[{
        "type": "text",
        "text": LONG_RUBRIC,                          # stable across rows
        "cache_control": {"type": "ephemeral"},       # 5-min TTL (default)
    }],
    messages=[{"role": "user", "content": test_case}], # varies per row
)
```

Critical details:

- **Put `cache_control` on the stable content**, not on per-row
  user content. Cache-control on dynamic content silently misses.
- **Minimum cacheable tokens**: 4,096 (Opus 4.5/4.6/4.7 / Mythos
  Preview / Haiku 4.5); **1,024 (Opus 4.8 / Sonnet 4.5 / Sonnet 4.6)**.
  Below the minimum, content is processed without caching and
  **no error is returned**.
- **TTL**: `{"type": "ephemeral"}` = 5 min;
  `{"type": "ephemeral", "ttl": "1h"}` = 1 hour at 2× write cost.
  Longer TTL must appear before shorter in multi-breakpoint
  configs.
- **Verify hits** by summing `response.usage.cache_read_input_tokens`
  across the run. Zero hits = misconfigured.
- **Up to 4 cache breakpoints per request.** Useful for tools +
  system + multi-turn conversation.

## Minimal Python eval loop (combining all three)

```python
from anthropic import Anthropic

client = Anthropic()
MODEL = "claude-haiku-4-5-20251001"

SYSTEM = """You are a customer support triage assistant.
Classify the complaint into one or more of: Software Bug,
Hardware Malfunction, User Error, Feature Request, Service Outage.
Respond with only the category name(s), comma-separated."""


def extract_text(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text")


def classify(complaint: str) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=[{
            "type": "text",
            "text": SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": complaint}],
    )
    return extract_text(resp).strip()


def grade(output: str, golden: list[str]) -> bool:
    predicted = {c.strip().lower() for c in output.split(",")}
    expected = {c.lower() for c in golden}
    return predicted == expected


eval_data = [
    {"complaint": "App crashes on upload",
     "golden_answer": ["Software Bug"]},
    # ...
]

results = []
for item in eval_data:
    out = classify(item["complaint"])
    results.append({
        "item": item,
        "output": out,
        "passed": grade(out, item["golden_answer"]),
    })

passes = sum(r["passed"] for r in results)
print(f"Score: {passes}/{len(results)} = {passes/len(results):.1%}")

for r in results:
    if not r["passed"]:
        print(f"FAIL: {r['item']['complaint']!r}")
        print(f"  expected={r['item']['golden_answer']}  got={r['output']!r}")
```

Important details:

- **Print failures with input + expected + got**, not just the
  pass count. Eyeballing failures is where prompt edits come from.
- **Lowercase / strip / split** consistently on both sides before
  comparing. Whitespace is the #1 cause of false-fail.
- **Pin the model ID** for reproducibility. The `-latest` aliases
  are convenient for development but bad for a regression suite —
  use the dated ID (`claude-haiku-4-5-20251001`) when you need
  frozen behavior.
- **Temperature 0** for both the model under test (reproducibility
  while iterating on the prompt) and any judge.

## Common grader patterns

### Exact match

```python
def grade(output, golden):
    return output.strip() == golden.strip()
```

Use only when the prompt is tight enough to produce bare answers.
Structured Outputs is usually a better way to enforce this than a
hopeful instruction.

### Set match (multi-label classification)

```python
def grade(output, golden):
    predicted = {c.strip().lower() for c in output.split(",")}
    expected = {c.lower() for c in golden}
    return predicted == expected
```

### Substring / keyword presence

```python
def grade(output, required_keywords):
    o = output.lower()
    return all(kw.lower() in o for kw in required_keywords)
```

Use sparingly. "Contains X" is a weak signal of quality.

### Regex pattern

```python
import re

def grade(output, pattern):
    return bool(re.search(pattern, output))
```

### Extract-then-compare (for chain-of-thought)

```python
import re

def extract_answer(text):
    m = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL)
    return m.group(1).strip() if m else None

def grade(output, golden):
    extracted = extract_answer(output)
    return extracted == golden
```

Canonical pattern when you've asked the model to reason in
`<thinking>` tags first. If extraction returns `None`, count it as
a fail and surface "no `<answer>` tag" as its own failure mode.

### JSON structure check (with Structured Outputs you usually don't need this)

```python
import json

def grade(output, expected):
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return False
    return parsed == expected
```

If you used Structured Outputs to produce the JSON, parsing is
guaranteed; you only need the equality check.

### Execution-based grading (SQL, code)

For "the SQL must return the right rows":

```python
import sqlite3

def grade(predicted_sql, golden_sql, fixture_sql, order_matters=False):
    conn = sqlite3.connect(":memory:")
    conn.executescript(fixture_sql)
    try:
        pred = conn.execute(predicted_sql).fetchall()
    except sqlite3.Error as e:
        return False, f"SQL error: {e}"
    gold = conn.execute(golden_sql).fetchall()
    if order_matters:
        return pred == gold, None
    return sorted(map(repr, pred)) == sorted(map(repr, gold)), None
```

Solves the "two correct queries" problem by comparing result sets
instead of strings.

## Cost and latency at scale

The synchronous loop above makes one model call per row, in
sequence. For 20 rows this is fine. For 200+:

### Concurrency with bounded parallelism

```python
import asyncio
from anthropic import AsyncAnthropic

aclient = AsyncAnthropic()

async def classify_async(complaint, sem):
    async with sem:
        resp = await aclient.messages.create(
            model=MODEL,
            max_tokens=200,
            system=[{
                "type": "text",
                "text": SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": complaint}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")

async def run(data, concurrency=5):
    sem = asyncio.Semaphore(concurrency)
    return await asyncio.gather(*(classify_async(d["complaint"], sem) for d in data))
```

Cap `concurrency` below your rate limit. Caching plus concurrency
is the production combo.

### Batch API for offline regression sweeps

The Anthropic **Message Batches API** is ~50% cheaper than the
synchronous API and is the right tool for nightly regression runs
where 5-minute-to-24-hour latency is fine. Pattern:

```python
batch = client.messages.batches.create(
    requests=[
        {
            "custom_id": f"row-{i}",
            "params": {
                "model": MODEL,
                "max_tokens": 200,
                "system": [{
                    "type": "text",
                    "text": SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }],
                "messages": [{"role": "user", "content": item["complaint"]}],
            },
        }
        for i, item in enumerate(eval_data)
    ]
)
# Poll batch.processing_status, then fetch results when ended.
```

See [Message Batches](https://docs.anthropic.com/en/api/messages-batches)
for polling and result-fetch shape. Half-price for the same
correctness signal makes this the default for any eval running on
CI or a schedule.

## Reporting and aggregation

When you run the eval, produce:

1. **Headline score** — `passes / total`.
2. **Per-row breakdown** of failures (input, expected, got). Save
   to JSON / CSV so you can diff between iterations.
3. **Failure categorization** — group failures by *kind* (format,
   reasoning, off-topic, classification confusion). This is the
   input to your next prompt edit. See the failure-mode taxonomy
   in `../SKILL.md`.

Compare runs by **same dataset, different prompt** (or same prompt,
different model). Don't change two things at once.

## Source citations

- [Structured outputs](https://platform.claude.com/docs/en/docs/build-with-claude/structured-outputs)
- [Prompt caching](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching)
- [Adaptive thinking](https://platform.claude.com/docs/en/docs/build-with-claude/adaptive-thinking)
- [Increase output consistency (prefill deprecation)](https://platform.claude.com/docs/en/docs/test-and-evaluate/strengthen-guardrails/increase-consistency)
- [Message Batches API](https://docs.anthropic.com/en/api/messages-batches)
