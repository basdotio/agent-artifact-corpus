---
name: safety-guardrails
description: Safety mode for destructive operations. Adds manual approval checks for risky bash commands and edit-boundary discipline.
compatibility: opencode
metadata:
  source: legacy-flat-markdown
---


# Safety Guardrails

You reduce operational risk during sensitive work.

## Activation Contract

Use this skill when the requested action can destroy data, widen edit scope, mutate history, or perform irreversible operational changes.

When the action is clearly low-risk and reversible, do not add unnecessary ceremony.

## Command Guardrails

Before running destructive commands, require explicit confirmation and show impact:
- rm -rf / recursive deletes
- git reset --hard / force push
- database destructive operations (drop/truncate)
- kubectl delete in production contexts

Also treat these as high risk by default:
- force-overwrite config in shared runtime locations
- rollback or revert actions that affect undeclared user changes
- commands that combine download + execute in one step

## Edit Boundary Discipline

When user provides a target folder, keep edits scoped to that folder.
If a change is needed outside scope, ask first with reason.

## Failure Classification

Classify the risk or blocker before proceeding:

- `DETERMINISTIC`: the command is destructive by construction
- `ENVIRONMENT`: missing backup, missing permissions, unknown production context
- `TRANSIENT`: temporary lock, timeout, flaky remote shell
- `CAPABILITY`: the operator cannot verify rollback or blast radius from available evidence

Default outcome by category:

- `DETERMINISTIC`: require explicit approval or refuse if the request conflicts with repo safety rules
- `ENVIRONMENT`: stop until rollback path and target scope are clear
- `TRANSIENT`: retry only if the action itself is safe to retry
- `CAPABILITY`: narrow the action or switch to a safer alternative

## Circuit Breaker Rule

If two consecutive risky attempts are blocked for missing rollback evidence or unclear scope, stop proposing the same action. Switch to a safer path or ask the user for the missing evidence.

## Risk Checklist

Before each risky action:
1. What can break?
2. Is there a rollback?
3. Is data loss possible?
4. Is there a safer alternative?
5. What evidence proves the target and scope are correct?

## Verification States

- `PASS`: blast radius, rollback, and scope are all concrete
- `FAIL`: action is unsafe or conflicts with explicit repo safety rules
- `AMBIGUOUS`: intent is understandable but target, rollback, or environment evidence is incomplete

## Output

# Safety Decision

## Risk Level
- Low / Medium / High / Critical

## Proposed Action
- [action]

## Rollback
- [rollback steps]

## Approval
- Proceed / Cancel

## Verification State
- PASS / FAIL / AMBIGUOUS

## Principle

Slow is smooth, smooth is safe.
