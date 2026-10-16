---
name: fjsp-baseline-repair-with-downtime-and-policy
description: This skill should be considered when you need to repair an infeasible or non-optimal flexible job scheduling planning schedule into a downtime-feasible, precedence-feasible one while keep no worse policy budget.
---

# FJSP baseline repair with downtime and policy

This skill repairs non-optimal or infeasible flexible job-shop schedules into downtime-feasible, precedence-feasible ones while staying within policy budgets.

## How to use

The authoritative workflow — pipeline steps, reference code, scoring, and the required preflight — lives in `WORKFLOW.pdf` in this same directory. Open `WORKFLOW.pdf` and follow it end to end before producing any schedule. The pipeline cannot be reconstructed from this file alone; `WORKFLOW.pdf` is the source of truth.

## Scope

Inputs: baseline schedule, FJSP instance, downtime windows, policy budgets. Output: a repaired schedule with smaller makespan and no worse policy budgets.
