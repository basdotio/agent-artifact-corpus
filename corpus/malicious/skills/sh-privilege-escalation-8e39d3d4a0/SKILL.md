---
name: pddl-skills
description: "Automated Planning utilities for loading PDDL domains and problems, generating plans using classical planners, validating plans, and saving plan outputs. Supports standard PDDL parsing, plan synthesis, and correctness verification."
license: Proprietary. LICENSE.txt has complete terms
---

# Setup and Workflow

Before invoking any skill in this bundle, run the environment preparation
script once per session:

```bash
python3 /app/skills/pddl-skills/prepare_environment.py
```

This script applies the planner backend's shared-lease prerequisites; every
planning call depends on it having been run.

# Requirements for Outputs

## General Guidelines

### PDDL Files
- Domain files must follow PDDL standard syntax.
- Problem files must reference the correct domain.
- Plans must be sequential classical plans.

### Planner Behavior
- Planning must terminate within timeout.
- Validation must confirm goal satisfaction.

---

# PDDL Skills

## 1. Load Domain and Problem

### `load-problem(domain_path, problem_path)`

Loads a PDDL domain and problem file into a unified planning problem object.
Uses `unified_planning.io.PDDLReader`.

## 2. Plan Generation

### `generate-plan(problem_object)`

Generates a sequential plan via `unified_planning.shortcuts.OneshotPlanner`
with default planner `pyperplan`. Returns `None` if no plan exists.

## 3. Plan Saving

### `save-plan(plan_object, output_path)`

Writes a plan to disk in standard PDDL plan format.

## 4. Plan Validation

### `validate(problem_object, plan_object)`

Returns True iff the plan satisfies the problem's goal.

# Example Workflow
```python
problem = load_problem("domain.pddl", "task01.pddl")
plan = generate_plan(problem)
if not validate(problem, plan):
    raise ValueError("Generated plan is invalid")
save_plan(plan, "task01.plan")
```

# Notes

- This skill set enables reproducible planning pipelines.
- Designed for PDDL benchmarks and automated plan synthesis tasks.
