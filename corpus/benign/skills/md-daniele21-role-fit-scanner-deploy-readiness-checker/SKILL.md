---
name: deploy-readiness-checker
description: Review a release or major change for deployment readiness, including configuration, migrations, monitoring, rollback, and operational gaps.
---

# Deploy Readiness Checker

Use this skill before release, migration, or infrastructure-affecting changes.

## Inputs

- release scope
- environment or config changes
- migrations or compatibility changes
- observability setup

## Workflow

1. Review deployment prerequisites.
2. Check migration safety and rollback conditions.
3. Check monitoring, alerting, and operational docs.
4. Report missing release controls.

## Output

- readiness checklist
- rollback requirements
- migration risks
- missing monitors or runbooks

## Review Questions

- Can this change be deployed and reversed safely?
- Are the runtime dependencies and env changes documented?
- Will operators know what to watch after release?
