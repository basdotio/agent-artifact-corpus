# promptfoo Reference

[`promptfoo`](https://github.com/promptfoo/promptfoo) is a YAML-driven
prompt evaluation framework. It runs your prompt(s) across one or
more models on a dataset, applies assertions (built-in or custom),
and produces a comparison dashboard. Use it when:

- You want a visual diff dashboard (prompts × models × tests grid)
- You want declarative YAML so non-engineers can tweak test cases
- You want CI/CD gating with junit.xml output
- You want a rich built-in assertion library (`g-eval`,
  `factuality`, `answer-relevance`, RAG triplet, `agent-rubric`,
  `trajectory:*`, `max-score`, ...)

Stick with the Python SDK pattern instead when the eval needs to
live in an existing Python codebase or CI script, or when the user
doesn't want a Node.js dependency.

## Installation and project layout

No global install required; use `npx`:

```bash
mkdir my-eval && cd my-eval
npx promptfoo@latest init
```

This creates `promptfooconfig.yaml`. A typical project:

```text
my-eval/
├── promptfooconfig.yaml      # the config
├── prompts.py                # prompt-generating functions (optional)
├── dataset.csv               # test cases (optional)
├── transform.py              # output transform (optional)
├── grader.py                 # custom Python grader (optional)
└── .env                      # ANTHROPIC_API_KEY (don't commit)
```

Run with:

```bash
export ANTHROPIC_API_KEY=...
npx promptfoo@latest eval     # run the eval
npx promptfoo@latest view     # open the browser dashboard
```

## `promptfooconfig.yaml` anatomy

A full-featured config. See
`assets/promptfooconfig.template.yaml` for a copyable starter.

```yaml
description: "Customer complaint classifier"

prompts:
  - prompts.py:v1_prompt
  - prompts.py:v2_prompt

providers:
  - id: anthropic:messages:claude-haiku-4-5-20251001
    label: "Haiku 4.5"
    config:
      temperature: 0
      max_tokens: 1024
  - id: anthropic:messages:claude-sonnet-4-6
    label: "Sonnet 4.6"
    config:
      temperature: 0

tests: dataset.csv

defaultTest:
  options:
    transform: file://transform.py
  assert:
    - type: python
      value: file://grader.py
    - type: llm-rubric
      provider: anthropic:messages:claude-haiku-4-5-20251001
      value: "Response is polite and avoids blaming the user"
      threshold: 0.8

outputPath:
  - results.json
  - results.junit.xml          # for CI integration
```

### Top-level fields

| Field | Required | Purpose |
| --- | --- | --- |
| `description` | no | Suite label shown in the dashboard |
| `prompts` | yes | Prompts (file, function, inline) |
| `providers` / `targets` | one of these | Models under test (`targets` preferred in red-team configs) |
| `tests` | no | Test cases; if omitted, each prompt × provider runs once |
| `defaultTest` | no | Defaults inherited by every test |
| `scenarios` | no | `(config × tests)` Cartesian product |
| `derivedMetrics` | no | Post-eval computed metrics (math.js) |
| `outputPath` | no | One or more output files (json/csv/yaml/html/junit.xml) |
| `evaluateOptions` | no | `maxConcurrency`, `repeat`, `delay`, `cache`, `timeoutMs` |
| `extensions` | no | Lifecycle hooks (`beforeAll`, `afterAll`, `beforeEach`, `afterEach`) |

### `prompts`

Three patterns:

**1. Python function** (recommended for non-trivial prompts):

```yaml
prompts:
  - prompts.py:v1_prompt
  - prompts.py:v2_prompt
```

Each function takes the test `vars` as kwargs and returns a prompt
string.

**2. Inline with Nunjucks templating**:

```yaml
prompts:
  - >-
    Write a paragraph about {{topic}}. Mention {{topic}} exactly
    {{count}} times.
```

**3. File reference**:

```yaml
prompts:
  - file://prompts/v1.txt
  - file://prompts/v2.txt
```

### `providers`

Anthropic provider strings: **`anthropic:messages:<model-id>`**.

Current model IDs (use `-latest` aliases for auto-updates within a
generation, or pinned IDs for frozen reproducibility):

```yaml
providers:
  - anthropic:messages:claude-opus-4-8
  - anthropic:messages:claude-sonnet-4-6
  - anthropic:messages:claude-sonnet-4-5-20250929    # pinned snapshot
  - anthropic:messages:claude-haiku-4-5-latest       # alias
  - anthropic:messages:claude-haiku-4-5-20251001     # pinned snapshot
```

Provider `config:` options the docs accept:

```yaml
providers:
  - id: anthropic:messages:claude-sonnet-4-6
    config:
      temperature: 0
      max_tokens: 4096
      top_p: 1
      top_k: 40
      stop_sequences: ["END"]
      system: "You are an evaluator."
      tools: [...]
      tool_choice: {type: auto}
      thinking:                                     # extended thinking
        type: enabled
        budget_tokens: 20000                        # requires max_tokens >= 20000
      effort: high                                  # adaptive thinking depth
      cache_control: {type: ephemeral}              # prompt caching
      output_format: {...}                          # structured outputs
```

Adding a second `providers` entry runs the same prompt × test
matrix across both models in one go — the cheapest way to answer
"can I switch to Haiku without regressing?"

### `tests`

Three loading patterns.

**CSV file** — tabular, supports `__expected` per-row assertions:

```yaml
tests: dataset.csv
```

```csv
complaint,golden_answer,__metadata:case_type
"App crashes on upload","equals:Software Bug","typical"
"Service is down AND I need exports","contains-all:Service Outage,Feature Request","multi-label"
```

**Inline YAML** — short test sets in the same file:

```yaml
tests:
  - vars:
      complaint: "App crashes on photo upload"
    assert:
      - type: equals
        value: "Software Bug"
  - vars:
      complaint: "I can't find the login button"
    assert:
      - type: equals
        value: "User Error"
```

**File-loaded variables** — large inputs (articles, transcripts):

```yaml
tests:
  - vars:
      article: file://articles/article1.txt
```

Multi-file globs: `tests: file://tests/*.yaml`.
External datasets: CSV, XLSX, JSON, JSONL, Google Sheets, Azure
Blob (`az://...`), HuggingFace datasets, or a JS/Python generator.

### CSV `__expected` syntax (full taxonomy)

Reserved CSV columns: `__expected`, `__expected1..N`, `__description`,
`__prefix`, `__suffix`, `__metric`, `__threshold`,
`__metadata:<field>`.

| Prefix | Behavior |
| --- | --- |
| `Paris` (bare) | `equals` |
| `contains:Paris` | substring (case-sensitive) |
| `icontains:paris` | substring (case-insensitive) |
| `starts-with:The` | prefix |
| `regex:^Hello.*world$` | regex |
| `is-json` / `contains-json` | structural |
| `similar(0.8):Hello` | embedding cosine ≥ threshold |
| `levenshtein(5):expected` | edit distance ≤ threshold |
| `llm-rubric:Is helpful` | LLM judge |
| `factuality:Sacramento is California's capital` | factuality grader |
| `javascript:output.length<100` / `fn:...` | inline JS |
| `python:len(output)>10` | inline Python |
| `file://assertions/custom.js` | external grader |
| `not-contains:error` | negation prefix (works on most types) |

Multi-assertion via `__expected1`, `__expected2`, ...; weight per
assertion via `__metric`/`__threshold`.

### `assert` and `defaultTest`

Assertions run after the model output and decide pass/fail.
Specify per-test or globally under `defaultTest`. `defaultTest`
assertions are **prepended** to every test's `assert` list.

`defaultTest.options.disableDefaultAsserts: true` on a row opts
out for that row.

## Assertion taxonomy

### Deterministic (cheap, fast, reproducible)

String:
`equals`, `contains`, `icontains`, `contains-all`, `contains-any`,
`icontains-all`, `icontains-any`, `starts-with`, `regex`.

Structured:
`is-json`, `contains-json`, `is-xml`, `contains-xml`, `is-html`,
`is-sql`, `contains-sql`.

Tool / function call:
`is-valid-function-call`, `is-valid-openai-function-call`,
`is-valid-openai-tools-call`, `tool-call-f1`.

Trace / agent trajectory:
`trace-span-count`, `trace-span-duration`, `trace-error-spans`,
`trajectory:tool-used`, `trajectory:tool-args-match`,
`trajectory:tool-sequence`, `trajectory:step-count`, `skill-used`.

Similarity / lexical:
`rouge-n`, `bleu`, `gleu`, `meteor`, `levenshtein`, `perplexity`,
`perplexity-score`, `f-score`, `word-count`.

Performance:
`latency` (ms), `cost` (USD).

Behavior:
`is-refusal`, `finish-reason`, `guardrails`.

Custom code:
`javascript`, `python`, `ruby`, `webhook`.

Grouping:
`assert-set` — rolls up child assertions with its own `threshold`.

Every assertion supports `not-<type>` negation.

Examples:

```yaml
assert:
  - type: cost
    threshold: 0.001
  - type: latency
    threshold: 2000
  - type: assert-set
    threshold: 0.5
    assert:
      - type: contains
        value: "foo"
      - type: contains
        value: "bar"
```

### Model-graded (LLM-as-judge)

| Type | Purpose |
| --- | --- |
| `llm-rubric` | General LLM-as-judge against a free-form rubric |
| `agent-rubric` | Same, but the grader is a coding-agent that can inspect workspace / tool evidence |
| `search-rubric` | Same, but with web-search grounding |
| `model-graded-closedqa` | OpenAI evals' closed-QA Y/N criterion |
| `factuality` | OpenAI evals' five-way A/B/C/D/E factuality classifier |
| `g-eval` | Two-step CoT grading; default threshold 0.7 |
| `pi` | Pi Labs preference scorer |
| `answer-relevance` | RAG: generates candidate questions from output, compares to query |
| `context-faithfulness` | RAG: claims supported by context |
| `context-recall` | RAG: ground-truth present in context |
| `context-relevance` | RAG: context relevant to query |
| `conversation-relevance` | Stays on-topic across multi-turn |
| `trajectory:goal-success` | LLM judges if agent run met goal |
| `similar` | Embedding cosine similarity |
| `classifier` | HuggingFace classification head |
| `moderation` | OpenAI / LlamaGuard / Azure content safety |
| `select-best` | Picks best of N parallel outputs |
| `max-score` | Picks the output with highest aggregate score |

**Default grader auto-selection**: with only `ANTHROPIC_API_KEY`
set, Anthropic is the default grader
(`claude-sonnet-4-5-20250929`); with `OPENAI_API_KEY`, it's `gpt-5`;
Google → `gemini-2.5-pro`; Mistral → `mistral-large-latest`. You
can always override with `provider:` on the assertion or
`--grader` on the CLI.

Examples:

```yaml
assert:
  # General-purpose rubric
  - type: llm-rubric
    provider: anthropic:messages:claude-haiku-4-5-20251001
    value: "Response is polite and avoids blaming the user"
    threshold: 0.8

  # Binary Y/N (simpler than llm-rubric, OpenAI evals format)
  - type: model-graded-closedqa
    value: "Explains the concept without technical jargon"

  # Five-way factuality classifier vs a reference
  - type: factuality
    value: "Sacramento is the capital of California"

  # CoT-anchored scoring; threshold defaults 0.7
  - type: g-eval
    value:
      - "Factually accurate"
      - "Well structured"

  # Pick the best of parallel outputs (select-best)
  - type: select-best
    value: "choose the most engaging response"
```

For the RAG triplet (`answer-relevance`, `context-faithfulness`,
`context-recall`, `context-relevance`) see `rag_evals.md`. For
`trajectory:*` and `agent-rubric` see `tool_use_evals.md`.

### Custom Python assertion

```yaml
assert:
  - type: python
    value: file://grader.py
```

```python
def get_assert(output, context):
    topic = context["vars"]["topic"]
    expected = int(context["vars"]["count"])
    actual = len([m for m in output.split() if m.lower() == topic.lower()])
    passed = actual == expected
    return {
        "pass": passed,
        "score": 1 if passed else 0,
        "reason": f"Expected {topic!r} ×{expected}, got ×{actual}",
        "namedScores": {"keyword_count": actual},
    }
```

The `context` object exposes: `prompt`, `vars`, `test`,
`providerResponse`, `trace`, `metadata`, `config`, `logProbs`.
Return one of: `bool`, `float`, or a `GradingResult` dict with
`pass`, `score`, `reason`, optionally `componentResults` and
`namedScores`.

### Custom model-graded assertion (Python that calls a model)

Same plumbing — `type: python` — with a `get_assert` that
internally calls the Anthropic API. See `model_graded.md` for the
canonical pattern with Structured Outputs.

### Transforms

`transform`, `transformVars`, `prefix`, `suffix`,
`disableDefaultAsserts` live under `options` (test-level) or
directly on a single assertion. `contextTransform` is RAG-specific.

```yaml
defaultTest:
  options:
    transform: file://transform.py:get_transform
```

```python
def get_transform(output, context):
    """Strip <thinking>...</thinking><answer>X</answer> down to X."""
    if "<answer>" in output:
        try:
            return output.split("<answer>")[1].split("</answer>")[0].strip()
        except Exception:
            return output
    return output
```

## Generating tests and assertions

When stuck, let promptfoo seed the dataset:

```bash
# Synthesize test cases from the existing config
npx promptfoo@latest generate dataset \
  --config promptfooconfig.yaml \
  --output tests.yaml \
  --instructions "Cover edge cases for international travel" \
  --numPersonas 5 \
  --numTestCasesPerPersona 3

# Brainstorm additional assertions
npx promptfoo@latest generate assertions \
  --type llm-rubric \
  --numAssertions 5 \
  -w                           # writes back to the config
```

Default provider is OpenAI; override with `--provider`. Review the
output before committing — generated cases need hygiene.

## CLI iteration flags

Most important `eval` flags for iteration:

| Flag | Use |
| --- | --- |
| `-c, --config` | Config file(s) |
| `-j, --max-concurrency N` | Parallel calls |
| `--repeat N` | Run each test N times (variance, stability check) |
| `--no-cache` | Bypass the disk cache |
| `--share` | Generate hosted result link |
| `-o, --output` | Write json/csv/yaml/html/junit.xml |
| `--grader <provider>` | Override model-graded grader |
| `--tag key=value` | Attach metadata |
| `--filter-failing <path>` | Re-run only previously failed tests |
| `--filter-pattern <regex>` | Filter by test description |
| `--filter-metadata key=value` | Filter by row metadata |
| `--filter-range start:end` | Index slice |
| `--filter-sample N` | Random sample of N rows |
| `-n, --filter-first-n N` | First N rows |
| `--watch, -w` | Hot reload |
| `--resume [evalId]` | Continue an aborted run |
| `--retry-errors` | Re-run only ERROR rows |
| `--fail-on-error` | Exit non-zero on any failure (CI gate) |
| `--no-table` | Suppress CLI table (saves memory) |

Iteration loop pattern:

```bash
promptfoo eval                                       # full run
promptfoo eval --filter-failing results.json --repeat 3
promptfoo eval --filter-metadata case_type=multi-label
promptfoo eval --grader anthropic:messages:claude-opus-4-8
```

## CI/CD integration

GitHub Actions canonical pipeline:

```yaml
- name: Run eval
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    PROMPTFOO_CACHE_PATH: ~/.cache/promptfoo
  run: |
    npx promptfoo@latest eval \
      -c promptfooconfig.yaml \
      --share \
      -o results.json \
      -o results.junit.xml \
      --tag git.sha="${{ github.sha }}" \
      --fail-on-error

- name: Upload eval report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: eval-report
    path: results.html
```

`--fail-on-error` is the simplest exit-code gate. For threshold-
based gates, post-process the JSON:

```bash
FAILURES=$(jq '.results.stats.failures' results.json)
[ "$FAILURES" -gt 0 ] && exit 1 || true
```

`results.junit.xml` is consumed natively by GitLab (`artifacts.reports.junit`),
Jenkins (`junit '*.xml'`), and most CI dashboards.

## Sharing and hosted view

```bash
promptfoo auth login -k YOUR_API_KEY    # one-time
promptfoo eval --share                  # generate hosted link
promptfoo share                         # share most recent run
```

Self-hosted: set `PROMPTFOO_REMOTE_API_BASE_URL` and
`PROMPTFOO_REMOTE_APP_BASE_URL`. Disable: `PROMPTFOO_DISABLE_SHARING=true`.

## Tips and gotchas

- **`anthropic:messages:` is unchanged** — only the model IDs are
  newer. The Anthropic prompt-evaluations course pins `claude-3-haiku-20240307`-
  era IDs; map to current `claude-haiku-4-5-latest`,
  `claude-sonnet-4-5-latest`, `claude-opus-4-5-latest` (or pinned
  4.x snapshots).
- **Set `ANTHROPIC_API_KEY` in the environment**, not in YAML.
  Never commit keys.
- **Pin model IDs for regression suites**; use `-latest` aliases
  for iteration. Floating IDs make scores non-reproducible.
- **One assertion = one criterion.** Split a compound criterion
  into multiple assertions; you get per-criterion pass rates in
  the dashboard rather than a composite.
- **`temperature: 0` on the model under test and on the judge** —
  reproducibility matters.
- **Save the output JSON** (`outputPath`) when you want diffs
  across iterations or want `--filter-failing` to work.
- **CI memory** — for large eval sets, add `--no-table` and use
  `--output results.jsonl`; set `NODE_OPTIONS="--max-old-space-size=8192"`
  if it OOMs.
- **The docs do not give explicit bias-mitigation guidance** for
  the LLM-rubric grader. Apply the patterns from
  `model_graded.md` yourself: heterogeneous judge family, position
  swap for pairwise, length-neutral instruction, binary verdict.

## Differences vs. the Anthropic prompt-evaluations course

| Topic | Course | Current docs |
| --- | --- | --- |
| Anthropic provider string | `anthropic:messages:claude-3-haiku-20240307` (etc.) | Same prefix; **upgrade model IDs** to 4.x |
| Default grader auto-selection | Implied OpenAI | Auto-detection across OpenAI/Anthropic/Google/Mistral |
| `generate dataset` / `generate assertions` | Not covered | First-class commands |
| Red-team | Not in scope | 157 plugins, multi-turn strategies (Crescendo, GOAT, Hydra) |
| Iteration flags | Not emphasized | `--filter-failing`, `--repeat`, `--filter-pattern`, `--retry-errors`, `--resume`, `--fail-on-error` |
| Trajectory / trace assertions | Not present | `trajectory:*` and `trace-*` for agentic systems |
| Model-graded options | `llm-rubric`, `factuality`, `closedqa`, `similar` | Added `g-eval`, `pi`, `agent-rubric`, `search-rubric`, `answer-relevance`, `context-faithfulness/recall/relevance`, `conversation-relevance`, `trajectory:goal-success`, `max-score` |
| CSV `__expected` syntax | `grade:` and bare-equals | Added `similar(N):`, `levenshtein(N):`, `fn:`, `python:`, `file://`, `not-<type>` |
| Extension hooks | Not discussed | `extensions:` with `beforeAll/afterAll/beforeEach/afterEach` |
| Sharing | Self-hosted at the time | Hosted promptfoo.app + team auth + `--share` |

The mental model the course teaches — prompts × providers × tests
with assertions graded by code, regex, or LLM judge — is fully
intact. The surface area has grown around it.

## Source citations

- [Intro](https://www.promptfoo.dev/docs/intro)
- [Configuration reference](https://www.promptfoo.dev/docs/configuration/reference/)
- [Test cases](https://www.promptfoo.dev/docs/configuration/test-cases)
- [Deterministic assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic/)
- [Model-graded assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/)
- [Anthropic provider](https://www.promptfoo.dev/docs/providers/anthropic/)
- [Command line](https://www.promptfoo.dev/docs/usage/command-line/)
- [CI/CD integration](https://www.promptfoo.dev/docs/integrations/ci-cd/)
- [Datasets](https://www.promptfoo.dev/docs/configuration/datasets/)
- [Red team](https://www.promptfoo.dev/docs/red-team/)
