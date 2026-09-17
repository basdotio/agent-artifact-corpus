---
name: og-life
description: Oil and gas lifecycle management for Beep.OilandGas.LifeCycle. Use when modifying or adding lifecycle process workflows, entity state transitions, PPDM status tables, process/lifecycle services, DTOs, or orchestration across Exploration/Development/Production/Decommissioning phases.
---

# Og Life

## Overview

Enable process/workflow orchestration and entity lifecycle state management for the Beep.OilandGas.LifeCycle solution, including PPDM integration and phase services.

## Quick start

1. Identify the change type: process workflow, entity lifecycle state, integration/orchestration, or database schema.
2. Read `references/lifecycle-overview.md` for service map and dependencies.
3. Apply changes in the correct layer; keep process status and entity status in sync.
4. Update DTOs, integration helpers, and docs if the API surface changes.

## Task playbooks

### Add or modify a process workflow

- Update definitions and steps in `Beep.OilandGas.LifeCycle/Services/Processes/ProcessDefinitionInitializer.cs`.
- Add or change orchestration methods in `Beep.OilandGas.LifeCycle/Services/<Phase>/Processes/*ProcessService.cs`.
- Keep validation rules in `Beep.OilandGas.LifeCycle/Services/Processes/ProcessValidator.cs`.
- Extend DTO mappings in `Beep.OilandGas.PPDM39/Core/DTOs/ProcessDTOs.cs` and `Beep.OilandGas.LifeCycle/Services/Processes/ProcessServiceExtensions.cs` when new inputs or outputs appear.
- Ensure process tables match changes in `Beep.OilandGas.LifeCycle/Scripts/ProcessWorkflowTables.sql`.

### Add or modify entity lifecycle states

- Update state transitions and history in `Beep.OilandGas.LifeCycle/Services/<Entity>Lifecycle/*LifecycleService.cs`.
- Align PPDM status tables and model classes in `Beep.OilandGas.PPDM39/Scripts/Sqlserver/` and `Beep.OilandGas.PPDM.Models/39/`.
- Keep state validation consistent with process workflows.

### Integrate process services and orchestration

- Register services in API DI (see references).
- Use `Beep.OilandGas.LifeCycle/Services/Processes/ProcessIntegrationHelper.cs` to coordinate process execution with state transitions.
- Update `FieldOrchestrator` or phase services to use process services where needed.

### Database and schema updates

- Process workflow schema: `Beep.OilandGas.LifeCycle/Scripts/ProcessWorkflowTables.sql`.
- PPDM entity status schema: `Beep.OilandGas.PPDM39/Scripts/Sqlserver/` plus matching model classes.

## Resources

### references/

- `references/lifecycle-overview.md` - project scope, services, dependencies, migration notes.
- `references/processes-guide.md` - workflow architecture, available processes, entity states, setup.
- `references/implementation-status.md` - current progress and next steps.
- `references/implementation-summary.md` - component inventory and file map.
- `references/solution-readme.md` - solution-wide architecture, data patterns, and service conventions.
