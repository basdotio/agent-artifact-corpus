---
name: ac-branch-pi-model
description: "AC branch pi-model power flow equations (P/Q and |S|) with transformer tap ratio and phase shift, matching `acopf-math-model.md` and MATPOWER branch fields. Use when computing branch flows in either direction, aggregating bus injections for nodal balance, checking MVA (rateA) limits, computing branch loading %, or debugging sign/units issues in AC power flow."
---

# AC Branch Pi-Model + Transformer Handling

This skill documents the AC branch pi-model equations (P/Q and |S|), transformer TAP/SHIFT handling, line-charging susceptance conventions, and MVA-limit enforcement used throughout this codebase's branch-flow computations.

## Scope

- Branch flows in both directions (i→j and j→i).
- Transformer TAP + phase SHIFT handling.
- Line-charging susceptance splitting across branch ends.
- Apparent-power (|S|) computation and RATE_A limit enforcement.
- Branch loading percentage for reporting.

## How to use this skill

The full workflow — per-unit conventions, exact power-flow equations, the required branch-parameter calibration pre-check, sanity checks, and the reference Python usage for `compute_branch_flows_pu` — lives in the accompanying reference `ac-branch-pi-model-reference.pdf`. Open `ac-branch-pi-model-reference.pdf` now and follow it end to end; the equations, the calibration step, and the code example must all be read before any branch-flow computation, because this SKILL.md intentionally does not duplicate them (the PDF is the authoritative source and is kept in sync with the math model).
