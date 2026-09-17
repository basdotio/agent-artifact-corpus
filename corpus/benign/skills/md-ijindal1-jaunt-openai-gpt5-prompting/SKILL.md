---
name: openai-gpt5-prompting
description: Write, critique, and iterate prompts for OpenAI GPT-5 series models. Use for tasks like: (1) turning vague requirements into high-signal instructions, (2) selecting between quick vs deep reasoning behaviors, (3) creating robust structured-output prompts (JSON schemas, tool calls), (4) designing evaluation prompts and rubrics, and (5) debugging prompt failures (hallucinations, format drift, tool misuse). Trigger when the user mentions GPT-5, prompt engineering, system/developer messages, structured outputs, agent prompts, or wants best-practice templates.
---

# GPT-5 Prompting (OpenAI)

## Overview

Use this skill to produce prompts that are: unambiguous, testable, robust to edge cases, and aligned to the desired tradeoff between speed and reliability. Avoid hardcoding model IDs or limits; confirm current model names and features with `$openai-docs` when needed.

## Prompt Pack (Use These Defaults)

### System Message Template

Use a system message that defines role, priorities, safety bounds, and formatting constraints.

Required elements:
- Role: what the model is (and is not) responsible for.
- Output contract: exact format, sections, and any JSON schema constraints.
- Non-goals: what to avoid (guessing, inventing APIs, ignoring inputs).
- Clarification policy: what to ask if required info is missing.

### Developer Message Template

Use a developer message for task-specific instructions, context, and constraints (without contradicting system).

Include:
- Task statement (1 sentence).
- Inputs provided and their meaning.
- Constraints and preferences (libraries, time, cost).
- Acceptance criteria (how you will judge success).

### User Message Template

Make the user message concrete and data-heavy:
- Provide examples (good and bad).
- Provide edge cases.
- Provide “definition of done”.

## Workflow: Draft -> Test -> Patch

1. Draft the prompt (system/developer/user separation).
2. Add 3 to 10 targeted test cases:
- Typical case, tricky case, adversarial case, empty/degenerate input.
3. Run a “prompt diff” patch cycle:
- Identify failure mode (ambiguity, missing constraints, competing goals).
- Patch the smallest instruction that fixes it.
- Re-run tests.

## Structured Output Guidance

Prefer:
- Explicit JSON schema (or a strict example) plus “no extra keys”.
- Deterministic ordering only if needed.
- “If you cannot comply, return an error object with fields …” (never silently fallback).

## Common Failure Modes (And Fixes)

1. Hallucinated facts:
- Add: “If unknown, say `I don’t know` and ask for X.”
- Add: cite-only-from-provided-sources rule when applicable.

2. Format drift:
- Add: strict schema, no prose, and a single top-level object.
- Add: “Validate output against schema before responding.”

3. Tool misuse:
- Add: tool selection rule (“Only call tools when …”), plus examples.
- Add: “Never fabricate tool outputs.”

## References

See `references/templates.md` for copy-paste prompt templates and a test-case checklist.
