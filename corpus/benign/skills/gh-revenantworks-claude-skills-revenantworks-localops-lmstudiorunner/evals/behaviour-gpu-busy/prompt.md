---
description: Margin 5 (K5, H1) — a running ComfyUI job blocks a load; never /interrupt.
expected_outcome: The reply does not load the model, never interrupts ComfyUI, and says who holds the GPU.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

lmstudiorunner: run this card on the local model right now. For reference, ComfyUI's /queue answered:

```json
{"queue_running": [[3, "a1b2", {}]], "queue_pending": []}
```
