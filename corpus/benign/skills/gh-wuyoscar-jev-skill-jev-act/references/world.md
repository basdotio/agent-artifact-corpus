# Games and simulations

Start with [the template](../assets/world.json).

## Workflow

1. Define the world, objective, legal actions, turn budget and authoritative state. Keep fictional simulation actions separate from real-world tool execution.
2. Let a person or reasoning model supply strategy when needed. Ask Jev only for a bounded local choice using visible state; keep unknown and replan outcomes available.
3. Have the simulator validate and apply the chosen transition. Reject stale decisions and update observations before dependent actions.
4. Replan on completed subgoals, violated assumptions or stalled progress. Log state/action/outcome IDs; stop on turn budget or deadlock.
5. Render text, UI or video from the resulting state as an optional separate consumer. Compare objectives across the same seeds; visual appeal is not decision quality.

## Context and parallelism

Jev does not inherit the agent's history. Give every request sufficient context:
the goal and strategy, world rules, current turn/state, legal actions, resources
and relevant prior outcomes. A move label alone is not enough. Keep uncertainty
explicit; omit unrelated lore and secrets without removing decision-relevant facts.

Batch independent judgments over one world snapshot instead of serial LLM calls.
For independent simulation instances, use bounded concurrency with world/turn IDs,
rate limits and a cost/time budget. The host schedules calls; the CLI has no parallel
scheduler. Questions cannot read other answers in the same request: resolve shared
resource/action conflicts in the simulator and obtain the next state before its
dependent turn. Jev's low latency helps action selection, not world design or video
generation; those remain separate planner/renderer tasks.

## Make it yours

Replace the example's evidence, candidate IDs and criteria together. Preserve a
no-match route when the real task can fall outside the labels. Agree on how the
host or person consumes each answer before enabling any automatic effect.

## Precedent

[Related project or author example](https://x.com/gokayfem/status/2101022590722810271). Our workflow is an adaptation,
not that project's code, an automatic installer, or a reproduced benchmark.
[OpenRouter request contract](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-questions-and-answers-request).
