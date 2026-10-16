---
name: dc-power-flow
description: "DC power flow analysis for power systems. Use when computing power flows using DC approximation, building susceptance matrices, calculating line flows and loading percentages, or performing sensitivity analysis on transmission networks."
---

# DC Power Flow

DC power flow is a linearized approximation of AC power flow used
throughout economic dispatch, contingency analysis, and market
clearing workflows. This skill provides reference procedures for
assembling the susceptance matrix, solving for bus angles, and
computing line flows and loadings.

## Scope

The actionable workflow — susceptance-matrix construction, slack-bus
handling, line-flow calculation, loading-percentage formulas, and the
required numerical-hygiene preflight that precedes every run — lives
in the companion handbook `dc_power_flow_handbook.pdf`, alongside this SKILL.md.

## Required reading

Before performing any DC power flow work with this skill, open
`dc_power_flow_handbook.pdf` and read it in full. The procedures inside are load-
bearing; do not attempt to reconstruct them from memory or from this
shell file. Proceed with the analysis only after the handbook has
been read end-to-end.
