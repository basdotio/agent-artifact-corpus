---
name: jev-act
description: Choose one legal next action in a browser, desktop, game or simulation. Supply fresh observed state and available actions. The host or simulator executes and checks the result; selection does not grant permission.
---

# Choose the next action

## Learn from the workflows

For design requests, browse the [scenario index](references/scenarios.md), read
the relevant guides and input/output examples, and compare or combine patterns.
Adapt what you learn to the user's task; the collection is inspiration, not a
closed menu. A familiar, straightforward decision can use its recipe directly.

Friendly reminder: Jev can help with initial, repeated or bulk judgments while
you lead the overall work. Read the evidence, design the workflow, spot-check
results (including confident or agreeing labels), and bring your own analysis
and synthesis. This is guidance for collaboration, not an agent harness or a
fixed call/token quota; existing user permissions and budgets still apply.

## Use safely

Choose the service once and keep that choice. If unset, ask **A: real Jev** via
OpenRouter (`OPENROUTER_API_KEY`) or TypeSafe (`TYPESAFE_API_KEY`), or **B: simulation**
with this agent or an explicitly chosen available model such as DeepSeek. Wait for
consent; errors do not authorize switching. Check key presence only, never values.
Real calls send evidence and cost money; get approval before sending private data.

For B, skip CLI/API calls. Mark `agent_simulation` or `model_simulation`, identify
the actual model when available, set `jev_called: false`, `probability: null` and
`confidence: null`. Return a value, evidence-based reason and `needs_review`; use
null/review when evidence is missing. Do not invent Jev output or probabilities.
Choice uses supplied labels, Noul uses booleans, Score uses integer rubric indices.

For A, use the existing `jev-decide` CLI with the chosen `--provider openrouter`
or `--provider typesafe`. If absent, explain the dependency; do not silently install.
`--dry-run` is offline validation, not a judgment. Exit 0 means selected/scored,
2 means review, 1 means error. Read each value: false Noul remains false. Selection
is not permission, and confidence is not accuracy. Keep unknown/review paths.

## First request

Adapt [the example](assets/example.json). The shared CLI needs Python 3.10+;
no sibling skill is needed. Host tools still own collection and actions.
Resolve `<skill-dir>` to this installed folder:

```bash
jev-decide decide <skill-dir>/assets/example.json --dry-run
# After approval, send the edited request with the selected provider:
jev-decide decide /path/to/request.json --provider openrouter
```

## Pick one mode

- **Browser or desktop:** read [UI steps](references/ui.md); start with [the UI request](assets/example.json).
- **Game or simulation:** read [world steps](references/world.md); start with [the world request](assets/world.json).

Use only the current mode. A simulated world is not permission to operate a real
account. The host validates legal actions, checks freshness and applies the result.

## Context and parallelism

Jev does not inherit the agent's history. Include the goal, rules, fresh context,
legal candidates and relevant outcomes. Batch independent checks in the same request.
Use bounded concurrency only for independent requests; the host owns scheduling.
Wait for a new observation after an action before asking a dependent question.

## Examples

[Next browser action](https://github.com/wuyoscar/jev-skill#sc-a23) · [Browser wait versus intervention](https://github.com/wuyoscar/jev-skill#sc-a24) · [Browser outcome verification](https://github.com/wuyoscar/jev-skill#sc-a25)

[More workflows and local templates](references/scenarios.md). Browse across
examples when designing a solution; follow the guides and sources that help.
