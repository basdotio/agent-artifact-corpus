---
name: PRD
description: Comprehensive PRD (Product Requirements Document) management skill for creating, planning, and implementing PRDs. USE WHEN the user mentions PRDs, wants to plan a feature, or needs to implement planned tasks.
model: opus
---

You manage PRDs (Product Requirements Documents) through their complete lifecycle. Based on the user's request, you will select and follow the appropriate workflow.

## When Invoked

1. **Read PRD Spec**: You MUST read the PRD specification completely before proceeding:
   @./reference/prd-spec.md

2. **Gather Context**: If a PRD name is mentioned or implied:
   - Run `claude-PRD-list-prds` to verify the PRD exists
   - Run `claude-PRD-task-status <prd-name>` to understand current state

3. **Determine Intent**: Analyze the user's request to identify:
   - Are they creating something new or working with an existing PRD?
   - What specific action do they want (create, plan, implement)?
   - Look for trigger words from the Workflow Routing table

4. **Select Workflow**: Select the appropriate workflow based on the user's intent and trigger words:
   1. Does the user want to create something new? → **CreatePRD**
   2. Does a PRD already exist for this feature? No → **CreatePRD**
   3. Does the PRD have defined tasks ready for implementation? No → **PlanPRD**
   4. Yes → **WorkPRD**
   5. When in doubt: Ask the user which workflow they want to use.

5. **Execute Workflow**: Report to the user "Running <workflow-name> using the PRD skill..." You MUST read the workflow document completely before proceeding, then follow the workflow's process completely

6. **Report Results**: Summarize what was accomplished and suggest next steps

## Workflow Routing

| Workflow | Trigger Words | When to Use |
|----------|---------------|-------------|
| [CreatePRD](./workflows/CreatePRD.md) | "create", "new", "start", "begin", "draft", "write" | User wants to create a new PRD from scratch, define a new feature, or start planning something new |
| [PlanPRD](./workflows/PlanPRD.md) | "plan", "analyze", "research", "refine", "complete", "fill out", "detail" | User has an existing PRD that needs analysis, research, task generation, or refinement |
| [WorkPRD](./workflows/WorkPRD.md) | "work", "implement", "build", "execute", "do", "code", "develop" | User wants to implement tasks from a planned PRD |

## Reference

- [CLI Tools](./reference/cli-tools.md)
