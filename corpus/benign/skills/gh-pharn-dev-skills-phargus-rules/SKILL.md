---
name: phargus-rules
description: Create and replay Phargus collector alerts or sandboxed diagnostic rules from an observed Node.js runtime problem. Use when defining a threshold, sustained condition, or custom diagnostic finding.
license: Apache-2.0
compatibility: Node.js >=22.18.0; a compatible Phargus application; isolated-vm only for sandbox rules.
---

# Phargus Rules

Turn an observed condition into an executable, replay-tested diagnostic rule.
Read [rules](references/rules.md), [data semantics](references/data.md) and
[compatibility](references/compatibility.md). Use [tools](references/tools.md) for replay.

1. Establish the condition and select representative normal and incident data. Resolve
   this skill's absolute directory before invoking scripts/phargus.mjs.
2. Prefer collector alert JSON for a single metric threshold. Choose comparison and
   forWindows deliberately, with thresholds in the metric's native units.
3. Use a sandbox .js function body for multi-metric/trend logic. Return findings with
   windowStart and message; the host must not evaluate or import rule text.
4. Run rules on normal and incident data. Inspect equality boundaries, sustained-window
   behavior, firing/resolved transitions and false alarms. Explain any input gaps.
5. Treat missing isolated-vm or ok: false as execution failures. Close runners and provide
   the actual collector/plugin activation recipe after replay passes.

Return the rule files, threshold rationale, both replay results and activation steps.
Avoid describing a heuristic finding (such as rising heap) as proof of a root cause.

Example request: "Alert when event-loop delay exceeds 50 ms for three windows without flagging this normal recording."
