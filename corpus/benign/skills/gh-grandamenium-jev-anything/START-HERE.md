# JEV Anything Starter Kit

This kit helps a coding agent design, implement, test, and tune a JEV decision
layer for a real workflow. JEV is useful for bounded decisions—classifying,
routing, scoring, and yes/no gates—not for writing, planning, or explanations.

**Version:** 2026-09-24

**Independent resource:** This starter kit is independently produced. It is not
an official TypeSafe or OpenRouter product, and neither company has endorsed it.
TypeSafe also publishes an official, MIT-licensed agent skill at
<https://github.com/typesafe-ai/skills>; use that official skill when you want the
vendor-maintained, live-docs-first path.

## What is included

- `SKILL.md` — the complete agent workflow.
- `PLAN-TEMPLATE.md` — a decision-layer design worksheet.
- `references/` — JEV concepts, API usage, fit/cost/latency, and
  evaluation guidance.
- `scaffolding/` — dependency-light Python and TypeScript clients,
  evaluation tools, and examples for all three JEV decision shapes.
- `EXAMPLE-PROMPTS.md` — prompts you can paste into your coding agent.

## Install from the public repository

This repository's root is the skill folder. For Codex, clone it directly into
your skills directory:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/grandamenium/jev-anything.git \
  ~/.codex/skills/jev-anything
```

For Claude Code:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/grandamenium/jev-anything.git \
  ~/.claude/skills/jev-anything
```

For another agent that supports folder-based skills, clone the repository into
the location the agent uses for custom skills. If your agent does not support
skills, attach `SKILL.md` and the relevant linked references as project
instructions instead.

Restart or reload your agent after installation. Then invoke the skill by name:

```text
Use $jev-anything to help me add a decision layer to this workflow.
```

The skill deliberately asks questions before writing code. That is where the
decision, input state, output type, criteria, error behavior, and escalation path
are defined.

## Choose the correct decision shape

- `noul` — answer yes/no and return the probability of yes.
- `choice` — pick exactly one option from a fixed list (maximum 255 options).
- `score` — place an input on an ordered rubric with 2 to 10 levels.

If you need prose, code, an explanation, or open-ended reasoning, use an LLM for
that part. A common pattern is: JEV makes the fast bounded decision; an LLM or
human handles the generative or ambiguous cases.

## Build your first layer

1. Start with one decision in one sentence.
2. Tell the agent where the input comes from and what happens after each answer.
3. Review the exact criteria wording the agent proposes; criteria quality is one
   of the highest-leverage controls over decision quality.
4. Choose a conservative confidence threshold and a fallback for low-confidence,
   failed, or timed-out calls.
5. Let the agent scaffold the integration from `scaffolding/`.
6. Test on real examples, then label a blind sample and evaluate it before giving
   the layer authority.

## Choose an access path

TypeSafe's direct API is currently available. Create a key at
<https://console.typesafe.ai/keys>, set `TYPESAFE_API_KEY`, and use the current
first-party [HTTP API](https://docs.typesafe.ai/api) or
[SDK documentation](https://docs.typesafe.ai/sdk/python). The official API uses
`POST https://api.typesafe.ai/v1/systemone` and the current model alias
`jev-latest`; confirm both in the live docs before implementation.

The dependency-free clients included in this starter kit instead target
OpenRouter. For that path, create a key at <https://openrouter.ai/keys> and set:

```bash
export OPENROUTER_API_KEY="your-key-here"
```

Never paste a real key into a prompt, source file, screenshot, or recording.
Check the live model page at <https://openrouter.ai/typesafe/jev-1.13> immediately
before implementation for the current model version, availability, endpoint, and
price.

## The production rule that matters most

JEV decides; your code acts. Keep the returned answer, probability distribution,
and confidence visible to your application. Keep thresholds, side effects, and
escalation in your own code. For sensitive or consequential decisions, route to a
human instead of allowing JEV to take an irreversible action by itself.

JEV's typed output guarantee means the answer conforms to the schema. It does not
mean the answer is always correct. Measure decision accuracy on your own data.

## Start here

Open [EXAMPLE-PROMPTS.md](EXAMPLE-PROMPTS.md), choose the closest prompt, and
replace the bracketed fields. The agent will use the full skill and planning
template to turn it into an implementation plan.

See [PROVENANCE.md](PROVENANCE.md) for source boundaries and ownership, and
[LICENSE](LICENSE) for the kit's MIT license.
