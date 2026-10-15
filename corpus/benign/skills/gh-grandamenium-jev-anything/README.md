# jev-anything

An independent agent skill for designing, implementing, testing, and tuning a
bounded [JEV](https://docs.typesafe.ai/) decision layer.

Use it when a coding agent needs to add a classifier, router, scorer, guardrail,
or other typed decision to a real software workflow. The skill makes the agent
define the decision contract, criteria, error behavior, fallback, and evaluation
plan before it writes code.

This repository is independently produced. It is not an official TypeSafe or
OpenRouter product. TypeSafe publishes its own MIT-licensed
[official agent skill](https://github.com/typesafe-ai/skills).

## Install

The repository root is the skill folder. Clone it directly into the skills
directory used by your agent.

### Codex

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/grandamenium/jev-anything.git \
  ~/.codex/skills/jev-anything
```

### Claude Code

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/grandamenium/jev-anything.git \
  ~/.claude/skills/jev-anything
```

Restart or reload the agent after installation. Confirm that this file exists:

```text
<skills-directory>/jev-anything/SKILL.md
```

If your agent uses a different folder for custom skills, clone the repository
there. If it does not support folder-based skills, attach `SKILL.md` and the
relevant files under `references/` as project instructions.

## Configure access

Choose one access path. Do not commit API keys to this repository or paste them
into prompts, screenshots, or recordings.

### Option A: TypeSafe direct API

1. Create a key at <https://console.typesafe.ai/keys>.
2. Set it in the environment that runs your application:

```bash
export TYPESAFE_API_KEY="your-key-here"
```

3. Follow the current first-party
   [HTTP API](https://docs.typesafe.ai/api) or
   [Python SDK](https://docs.typesafe.ai/sdk/python) documentation.

The current direct endpoint and model alias are documented in
[`references/02-openrouter-decisions-api.md`](references/02-openrouter-decisions-api.md).
Recheck the live docs before implementation because APIs and model aliases can
change.

### Option B: OpenRouter

1. Create a key at <https://openrouter.ai/keys>.
2. Set it in the environment that runs your application:

```bash
export OPENROUTER_API_KEY="your-key-here"
```

3. Adapt the dependency-free Python or TypeScript client:

```text
scaffolding/jev_client.py
scaffolding/jev_client.ts
```

Check the live [JEV model page](https://openrouter.ai/typesafe/jev-1.13) before
implementation for the current model, availability, endpoint, and price.

## Use

Invoke the skill explicitly:

```text
Use $jev-anything to help me add a decision layer to this workflow.
```

Or start from a more specific prompt:

```text
Use $jev-anything to design a support-request router. Ask me to define the
fixed options, error costs, fallback, and evaluation plan before changing code.
```

The skill will:

1. Turn the request into one bounded decision.
2. Confirm the correct primitive:
   - `noul` — yes/no probability;
   - `choice` — one option from a fixed list, up to 255 options;
   - `score` — one position on an ordered rubric of 2–10 levels.
3. Explain fit, limits, privacy, cost, latency, and high-stakes concerns.
4. Produce a reviewable plan and get criteria sign-off.
5. Scaffold the integration through TypeSafe or OpenRouter.
6. Verify failure and low-confidence paths.
7. Build a blind-label, evaluate, inspect, and tune loop.

JEV returns a decision signal. Your ordinary code must retain thresholds,
permissions, side effects, and escalation. A schema-valid result can still be a
wrong decision.

## Included

- `SKILL.md` — agent workflow and safety boundaries.
- `PLAN-TEMPLATE.md` — decision-layer design worksheet.
- `EXAMPLE-PROMPTS.md` — ready-to-copy prompts.
- `references/` — product model, API access, limits, and evaluation guidance.
- `scaffolding/` — Python and TypeScript clients, examples, rating-sheet
  tooling, and evaluation utilities.
- `PROVENANCE.md` — ownership and source boundaries.
- `CHANGELOG.md` — internal hardening and public-distribution changes.

## Update

```bash
git -C ~/.codex/skills/jev-anything pull --ff-only
```

Use the equivalent installed path if your agent stores skills elsewhere.

## License

MIT. See [LICENSE](LICENSE).
