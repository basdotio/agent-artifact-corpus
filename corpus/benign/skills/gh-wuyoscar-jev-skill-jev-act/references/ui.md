# Browser and desktop

Start with [the template](../assets/example.json).

## Workflow

1. Use an available connector/browser/computer-use tool for observation. Follow its native instructions; Jev receives sufficient relevant text state, not hidden UI or fabricated element IDs.
2. Build candidates only from fresh observed controls and operations actually supported by the host. Prefer an exact known action without Jev when no judgment is needed.
3. Keep known typing values in the host. If text generation is needed, do it separately and validate it before choosing the target.
4. Interpret the selected action, recheck snapshot freshness, execute only a permitted step, and read the result. Do not treat a DONE choice as completion evidence.
5. Return to the host for sensitive actions, consent, stale state or unsupported controls. This skill does not grant browser, desktop or OS permissions.

## Context and parallelism

Jev does not inherit the agent's history. Give every request sufficient context:
the goal, permitted scope, fresh page/accessibility text, observed controls and
their IDs, relevant preceding actions and errors. A list of button IDs alone is
not enough. Remove unrelated page content and secrets without losing task evidence.

Batch independent page-state, candidate-suitability and completion-evidence checks
over the same snapshot instead of serial LLM calls. Use bounded concurrency only
for independent requests, with snapshot IDs, rate limits and a cost/time budget;
the host schedules calls and the CLI has no parallel scheduler. Questions cannot
read other answers in the same request. Do not precompute later clicks using old
state: execute a permitted step and observe its result before dependent decisions.
Jev's low latency helps the judgment stage, not authorization or browser execution.

## Make it yours

Replace the example's evidence, candidate IDs and criteria together. Preserve a
no-match route when the real task can fall outside the labels. Agree on how the
host or person consumes each answer before enabling any automatic effect.

## Precedent

[Related project or author example](https://github.com/browser-use/jev-ultrafast). Our workflow is an adaptation,
not that project's code, an automatic installer, or a reproduced benchmark.
[OpenRouter request contract](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-questions-and-answers-request).
