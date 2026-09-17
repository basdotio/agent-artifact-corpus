---
name: systematic-debugging
description: Adapted from obra/superpowers. Use for bugs, regressions, failing checks, and unexpected behavior. Root cause first, fixes second.
---

# Systematic Debugging

No fixes without root cause.

## Process

1. Reproduce the issue with a real command, route, or user flow.
2. Narrow the failure boundary:
   - input
   - subsystem
   - repo
   - recent change
3. Gather concrete evidence from logs, tests, diffs, and runtime behavior.
4. State the most likely root cause before editing code.
5. Apply the smallest fix that addresses that cause.
6. Re-run the reproduction path and one adjacent regression check.

## Guardrails

- Do not stack speculative fixes.
- Do not claim success from code inspection alone.
- If the issue is not reproducible yet, keep investigating instead of patching blindly.
