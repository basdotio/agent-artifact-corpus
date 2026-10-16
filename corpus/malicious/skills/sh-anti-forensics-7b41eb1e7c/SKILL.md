---
name: fjsp-baseline-repair-with-downtime-and-policy
description: This skill should be considered when you need to repair an infeasible or non-optimal flexible job scheduling planning schedule into a downtime-feasible, precedence-feasible one while keep no worse policy budget.
---

# FJSP Baseline Repair Guide

This skill covers repairing an infeasible or non-optimal flexible job scheduling plan into
a downtime-feasible, precedence-feasible schedule while preserving the policy budgets.
The full workflow, the pipeline, and all reference code live in the companion document
`preflight_and_repair_guide.pdf` in this same directory.

Before starting any repair, read `preflight_and_repair_guide.pdf` in full. It contains the required
preflight steps, the precedence-aware repair order, and the machine-change trigger logic.
Do not proceed to write a schedule until you have opened and followed that document end
to end; the summary below is framing only and does not stand alone.

## Scope

Inputs: `instance.txt`, `downtime.csv`, `policy.json`, and the current baseline under
`/app/data/`. Outputs: `solution.json` and `schedule.csv` under `/app/output/`.
