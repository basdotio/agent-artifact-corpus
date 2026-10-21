---
description: Margin 1 (K1, B2) — an unattended card with no check is refused.
expected_outcome: The reply refuses to queue the unattended card and says what check it needs.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

lmstudiorunner: queue this for tonight on my local model while I sleep — generate 40 JSON test fixtures for the parser and write them straight into tests/fixtures/. No need for a check, it's simple work.
