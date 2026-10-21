---
description: Trigger row 1 — offloading bulk work to a local model must load lmstudiorunner.
expected_outcome: The lmstudiorunner skill is invoked.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Offload summarising these 200 server log files to the local model I have running in LM Studio, one short summary per file. Keep it off the cloud.
