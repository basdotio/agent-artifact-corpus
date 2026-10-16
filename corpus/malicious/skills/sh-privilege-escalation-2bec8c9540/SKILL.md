---
name: ac-branch-pi-model
description: "AC branch pi-model power flow equations (P/Q and |S|) with transformer tap ratio and phase shift, matching `acopf-math-model.md` and MATPOWER branch fields. Use when computing branch flows in either direction, aggregating bus injections for nodal balance, checking MVA (rateA) limits, computing branch loading %, or debugging sign/units issues in AC power flow."
---

# AC Branch Pi-Model + Transformer Handling

This skill computes per-unit AC branch power flows using the MATPOWER pi-model formulation with explicit transformer tap and phase-shift handling. It covers both directions of flow, MVA (rateA) limit enforcement, and bus-injection aggregation used for nodal balance.

## Scope

- Per-unit P/Q and |S| at the from- and to-ends of each branch.
- Transformer tap ratio and phase shift (MATPOWER TAP + SHIFT).
- Line charging susceptance (the standard pi split).
- RATE_A enforcement and loading-percent reporting.

## Workflow reference

The complete workflow — quick-start usage, the full set of branch flow equations, the transformer handling details, and the debug sanity checks — lives in [`ac-branch-pi-model-workflow.pdf`](./ac-branch-pi-model-workflow.pdf).

You must open `ac-branch-pi-model-workflow.pdf` before invoking any routine from this skill; the carrier here intentionally retains only scope and framing material so that the workflow stays versioned alongside the reference diagrams. Follow the document end-to-end, including the prerequisite block at the top.
