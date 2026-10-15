# Reference 01: What Jev is (and is not)

Grounded in TypeSafe's official announcement and the linked first-party sources.
Read this before describing Jev to a user.

## The one-sentence truth

Jev is TypeSafe AI's first "System One" model. TypeSafe's own framing: "a
frontier-intelligence function call: unstructured state in, typed probabilistic
decisions out." It is NOT a chat model and NOT an LLM.

## How it actually works

- It does not generate text token by token. It produces its answer in a single
  parallel pass.
- Input: unstructured program state (plain text, or structured JSON serialized to
  text) that describes the situation.
- Output: a typed value chosen from a schema you define in advance, plus calibrated
  probabilities and a confidence score.
- Trained with Reinforcement Learning for Calibrated Decisions (RLCD) so that
  higher confidence should mean higher accuracy and similar inputs give similar
  answers.

## The three decision primitives (this is all Jev does)

1. `noul` - a yes/no question. Returns P(yes) as a float 0..1.
2. `choice` - pick exactly one option from a fixed labeled set. Returns the winning
   option, a probability for every option, and a confidence. Max 255 options.
3. `score` - a graded level on an ordered rubric of 2 to 10 levels (lowest first).
   Returns a position on the rubric (can be fractional), per-level probabilities,
   and a confidence.

Every real Jev use is one or more of these three, asked over some state.

## What Jev is for

Fast, high-volume, bounded decisions inside software: classify, route, score,
extract-a-label, branch, verify, judge, guardrail, detect jailbreaks. TypeSafe
calls these "smart if-statements" and map-reduce over big data.

## What Jev is NOT

- It cannot write prose, explanations, summaries, or code.
- It cannot reason step by step or plan.
- It does not (yet) take images.
- It does not replace an LLM. The intended pattern is System One + System Two: Jev
  makes the fast bounded decision, an LLM does the slow generative work. A common
  loop: an LLM defines the criteria and handles the writing/fixing, Jev scores or
  routes cheaply at scale, and low-confidence cases route back to the LLM or a
  human.

## Honest provenance notes (so you do not oversell)

- The "cannot hallucinate / 0% type errors" claim is a SCHEMA guarantee: the output
  always matches the declared type. It is NOT a guarantee the decision is correct.
  Jev can be confidently wrong. Design around this (see reference 03).
- TypeSafe's speed and cost multipliers (40x to 444x) are single-vendor benchmarks
  with self-disclosed methodology bias. Quote them as "TypeSafe-claimed," never as
  independent fact.
- Founder: Diogo Almeida (ex-OpenAI). Launched 2026-09-15 after ~2 years in stealth.

## Sources

- TypeSafe official: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- Current TypeSafe docs: https://docs.typesafe.ai/
- Official TypeSafe agent skill (MIT): https://github.com/typesafe-ai/skills
- Before publishing or deploying, re-check current product details against the
  linked first-party source and the live OpenRouter model page referenced in
  `02-openrouter-decisions-api.md`.
