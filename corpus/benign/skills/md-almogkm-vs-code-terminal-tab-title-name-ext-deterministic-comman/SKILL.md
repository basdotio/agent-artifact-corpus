---
name: deterministic-command-line-parsing
description: Deterministic command-line parsing for stable command classification and target extraction. Use when parsing terminal commandLine values or updating parser rules.
---

# Deterministic Command Line Parsing

## Purpose
This skill keeps command parsing deterministic and reproducible so title derivation does not drift across runs. It is used to classify commands and extract primary targets predictably.

## When to Use
- When parsing terminal `commandLine` values.
- When adjusting parser rules for new command forms.
- When debugging title mismatches from command text.

## Inputs
- Raw terminal command line strings.
- Parsing rules and tokenization constraints.
- Known command patterns (python, R, shell, node, pytest, and other).

## Outputs
- Stable parse objects (kind/target/title fields).
- Predictable command classification.
- Fewer false positives in terminal renaming.

## Procedure
1. Tokenize command input deterministically.
2. Segment the primary command portion using deterministic separators.
3. Classify command kind using fixed matching rules.
4. Extract primary target only when rules clearly support it.

## Constraints
- Must:
  - Use deterministic parsing rules.
  - Keep behavior predictable for the same input.
- Must Not:
  - Depend on runtime side effects or filesystem checks to parse.
  - Infer targets from ambiguous tokens without explicit rules.
- Avoid:
  - Opportunistic parsing expansions without tests/examples.

## Examples
- Example 1:
  - Context: `python3 "with space.py"` is executed.
  - Steps:
    - Tokenize with quote-aware handling.
    - Identify python file-run shape.
    - Extract basename target.
  - Expected result:
    - Stable title output for repeated executions.

## Verification
- Run parser examples through unit-test-friendly calls.
- Confirm same inputs always produce the same parse output.

## Notes
The source statement does not define exact grammar depth. Keep deterministic behavior primary and avoid adding non-deterministic heuristics.
