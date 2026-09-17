---
name: progress-auto-sync
description: Synchronizes task completion status across the project's tracking documents (PRD.md, GAP_ANALYSIS.md, EXECUTION_PLAN.md). Use this skill at the end of every significant code implementation or milestone to ensure documentation reflects reality.
---

# Progress Auto-Sync Skill

This skill ensures that project management artifacts and execution plans remain the source of truth for the AI agent and the developer.

## Workflow

1. **Review Changes:** After completing a coding task (e.g., fixing a bug, implementing a feature), review the exact changes made and verified.
2. **Update `EXECUTION_PLAN.md`:**
    - Find the corresponding atomic task in `EXECUTION_PLAN.md`.
    - Mark the acceptance criteria checkboxes `[ ]` as completed `[x]`.
3. **Update `GAP_ANALYSIS.md`:**
    - If the completed feature closes a recognized logic gap, update its status from 🔴 or 🟡 to ✅.
    - Adjust any remaining estimated effort if applicable.
4. **Update `PRD.md` (If Applicable):**
    - If a discrepancy was resolved or a new structure was finalized, briefly reflect the current state in the `Current Status` or documentation summary.
5. **No Code Commits:** This skill is strictly for documentation synchronization. Do not introduce new source code when running this skill.
