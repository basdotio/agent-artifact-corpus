# Tool Use / Agent Evaluation

When the prompt-under-test calls tools (function calling, MCP,
agent loops), the eval needs to check more than the final text
reply: did the model decide to call a tool, did it call the right
tool, with the right arguments, in the right order? This reference
covers the patterns.

## Anthropic's design principle: grade the output, not the path

From Anthropic Engineering's [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents):

> "It's often better to grade what the agent produced, not the
> path it took."

In practice:

- **Default**: grade only the final answer / final artifact. A
  correct answer reached via an unusual sequence of tool calls is
  still correct.
- **Grade the path** when the path itself is the criterion ("did
  the agent call the user's preferred billing API?", "did it
  avoid the expensive search tool?", "did it parallelize where
  possible?").
- **Partial-credit rubrics** are appropriate for multi-step
  tasks — give credit for getting 3 of 4 sub-steps right.

This shapes which assertions you reach for: output-grade in most
cases; trajectory-grade when a specific trajectory is required.

## The Anthropic tool-use response shape

When Claude calls a tool, the response looks like:

```json
{
  "stop_reason": "tool_use",
  "content": [
    { "type": "text", "text": "Let me check the weather..." },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "get_weather",
      "input": { "location": "New York, NY", "unit": "fahrenheit" }
    }
  ]
}
```

Things a grader can check directly:

- `stop_reason == "tool_use"` (did the model decide to call vs.
  answer directly)
- the **tool_use block's** `name` matches the expected tool
- the **tool_use block's** `input` matches a schema or set of
  expected args (with `strict: true` on the tool definition you
  get schema-conformance guarantees from the API)
- **trajectory** — number of tool calls, ordering, which tools
  were called in parallel

For multi-turn agent loops, the same pattern repeats — each turn
yields zero or more tool calls, and the grader inspects the full
trace.

## Code-graded assertions for tool use

### Single-turn: was the right tool called with the right args?

```python
def extract_tool_use(response):
    """Return (name, input) for the first tool_use block, or None."""
    for block in response.content:
        if block.type == "tool_use":
            return block.name, block.input
    return None


def grade_tool_call(response, expected_name, expected_input_subset):
    """Pass if the model called the right tool with the right args."""
    result = extract_tool_use(response)
    if result is None:
        return False, "no tool call made"
    name, input_ = result
    if name != expected_name:
        return False, f"wrong tool: got {name}, expected {expected_name}"
    for k, v in expected_input_subset.items():
        if input_.get(k) != v:
            return False, f"wrong arg {k}: got {input_.get(k)!r}, expected {v!r}"
    return True, "ok"
```

### Forcing tool choice

When testing tool-call behavior, you sometimes want to require a
tool call:

```python
resp = client.messages.create(
    model=MODEL,
    max_tokens=1024,
    tools=TOOLS,
    tool_choice={"type": "any"},        # must call some tool
    messages=[...],
)
# Other options:
#   {"type": "auto"}        # natural behavior (only mode compatible with thinking)
#   {"type": "tool", "name": "X"}   # must call X
#   {"type": "none"}        # never call a tool
```

Use `tool_choice` to test specific branches in isolation. For
end-to-end agent evals, leave it as `auto`.

### `strict: true` for input-shape guarantees

```python
TOOLS = [{
    "name": "get_weather",
    "description": "...",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        "required": ["location"],
        "additionalProperties": False,
    },
    "strict": True,                     # guarantees input matches schema
}]
```

With `strict: true`, the API enforces the schema — the grader
doesn't need to validate `input` shape, only its values.

## promptfoo deterministic assertions for tool use

The deterministic `trajectory:*` and tool assertions cover most
needs without writing custom code:

| Assertion | Checks |
| --- | --- |
| `is-valid-function-call` | The output is a valid function-call structure |
| `is-valid-openai-function-call` | OpenAI function-call format specifically |
| `is-valid-openai-tools-call` | OpenAI tools-API format |
| `tool-call-f1` | F1 between expected and actual tool calls |
| `trajectory:tool-used` | The expected tool was used at least once |
| `trajectory:tool-args-match` | The args of a specific tool call match |
| `trajectory:tool-sequence` | Tools were called in the expected order |
| `trajectory:step-count` | The trajectory has ≤ N steps |
| `skill-used` | A named skill (in skill-equipped systems) was invoked |

```yaml
defaultTest:
  assert:
    - type: trajectory:tool-used
      value: "get_weather"
    - type: trajectory:tool-sequence
      value: ["search", "fetch", "summarize"]
    - type: trajectory:step-count
      threshold: 5         # fail if > 5 steps
    - type: tool-call-f1
      threshold: 0.8
```

## Model-graded assertions for agent runs

For "did the agent achieve the goal?" style criteria,
promptfoo offers:

- `trajectory:goal-success` — LLM judges whether the agent's
  trajectory accomplished the stated goal.
- `agent-rubric` — like `llm-rubric` but the grader is a
  coding-agent that can inspect workspace / tool-call evidence.

```yaml
assert:
  - type: trajectory:goal-success
    value: "The agent successfully booked a refundable flight under $400"
    provider: anthropic:messages:claude-opus-4-8

  - type: agent-rubric
    value: "Only the necessary files were modified; no unrelated edits"
```

For multi-axis agent judgment, fall back to a custom Python
assertion calling Claude with Structured Outputs (see
`model_graded.md`).

## Trajectory grading vs output grading: decision rule

Use **output grading** (the default) when:

- The user only cares about the answer / artifact.
- Multiple tool-call paths are legitimately equivalent.
- You don't want the eval to enforce one particular agent
  architecture.

Use **trajectory grading** when:

- Specific tool choice is itself a requirement ("must use the
  preferred billing API").
- Cost / latency caps are tied to step count.
- Reproducibility audits demand a specific path.
- The system is being evaluated for its agent loop quality, not
  just final correctness.

The two can layer: output-grade for the headline pass rate, with
a trajectory `step-count` cap as a secondary gate.

## Tool-use + extended thinking: quirks

When thinking is enabled (Opus 4.6+, Sonnet 4.6, Opus 4.7+):

- Only `tool_choice: {"type": "auto"}` or `"none"` is allowed —
  forcing a specific tool with `{"type": "tool"}` is rejected.
- You **must pass the prior `thinking` block back unchanged** when
  supplying a `tool_result` on the next turn. Strip it and the
  next turn fails.
- The first content block of the response will be `type:
  "thinking"`, so `response.content[0].type == "tool_use"` will
  never be true. Iterate.

## Failure-mode taxonomy for tool use

Common categories to watch for in failing rows:

- **Tool not called** when it should have been — model answered
  from its prior instead of using the tool.
- **Wrong tool called** — model picked a similar-named tool.
- **Right tool, wrong arguments** — schema-valid but semantically
  wrong (`location: "Paris, Texas"` when the user meant France).
- **Unnecessary tool calls** — model called a tool when it could
  have answered directly.
- **Wrong order / wrong parallelization** — multi-tool tasks where
  the model serialized when it could have parallelized, or vice
  versa.
- **Tool call without follow-through** — model called the tool,
  got a result, and then ignored the result in its final answer.

For each, the fix is usually a prompt edit: tighten the tool
descriptions (so the model picks the right one), add explicit
guidance on when to call vs. when to answer directly, or restrict
`tool_choice` for the failing branch.

## Source citations

- [Anthropic — Tool use overview](https://platform.claude.com/docs/en/docs/build-with-claude/tool-use/overview)
- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — grade the output not the path
- [Anthropic — Adaptive thinking](https://platform.claude.com/docs/en/docs/build-with-claude/adaptive-thinking) — tool-use + thinking constraints
- [promptfoo — model-graded](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/) — trajectory:* assertions
