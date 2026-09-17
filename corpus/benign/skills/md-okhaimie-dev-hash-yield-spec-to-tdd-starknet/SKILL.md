---
name: spec-to-tdd-starknet
description: Build a TDD-ready Starknet/Cairo repo from a detailed protocol spec using progressive disclosure. Use when asked to transform a deep spec into interface/abstract skeletons, test infrastructure, BTT trees, and placeholder tests, with strict coverage validation and no business-logic implementation.
---

# Spec To TDD Starknet

## Overview
This skill turns a detailed protocol spec into a **TDD-ready** Cairo repo: interface/abstract scaffolding, comprehensive testing infrastructure, BTT trees, and placeholder tests that compile and validate coverage before any implementation begins.

**Key Patterns (Ekubo + Starknet-Staking Inspired)**:
- Co-located tests under `src/tests/` with `#[cfg(test)]`
- snforge deploy helpers using `declare().unwrap().contract_class().deploy()`
- Action/Result enums for complex test flows (Ekubo)
- Flow-based testing with `SystemState` abstraction (Starknet-Staking)
- Event test utilities module with per-event assertion helpers
- Structured errors with `Describable` trait
- Type aliases for domain concepts (Amount, Epoch, Commission)
- Test constants module with addresses as `'NAME'.try_into().unwrap()`

## Progressive Disclosure Map
Load only what is needed:
- **Workflow gates**: `references/workflow-gates.md`
- **BTT format**: `references/btt-format.md` (manual BTT application for Cairo)
- **Test infra blueprint**: `references/test-infra-blueprint.md` (Ekubo patterns)
- **Fixtures/scenarios**: `references/fixtures-and-scenarios.md`
- **Mock patterns**: `references/mocks-patterns.md` (MockERC20, Locker, Extension)
- **Assertions/events**: `references/assertions-and-events.md`
- **Repo conventions**: `references/repo-conventions.md` (Ekubo-style layout)
- **Naming rules**: `references/naming-rules.md`
- **Config guidance**: `references/snforge-config.md`
- **Spec -> tests mapping**: `references/mapping-spec-to-tests.md`
- **Commands**: `references/lint-and-test-commands.md`
- **Path configuration**: `references/path-configuration.md`

## Inputs (Configurable Per Repo)
Confirm these before doing any work; stop and ask if missing or ambiguous. Do not assume fixed paths.

- `PROJECT_ROOT`: repo root for the current project
- `SPEC_PATH`: spec file path (relative to `PROJECT_ROOT`)
- `TEMPLATE_DEST`: where to copy the template asset (relative to `PROJECT_ROOT`)
- `TESTS_DIR`: test files root (relative to `PROJECT_ROOT`)
- `BTT_DIR`: BTT tree files root (relative to `PROJECT_ROOT`)
- `SPEC_DOCS_DIR`: test-spec docs root (manifest/invariants/risk matrix)
- Allowed edit scope: exact folders/files the implementation agent may touch
- Test/lint commands: `scarb fmt`, `scarb build`, `snforge test` (or repo-specific equivalents)

Use `references/path-configuration.md` to set defaults and allow overrides.

## Non-Negotiables
- No business logic before tests and scaffolding are approved.
- No bypassing failing validation, lint, or type checks.
- No edits outside allowed scope.
- Do not invent requirements; ask when spec is unclear.

## Assets And Scripts
- **Template asset**: `assets/cairo-repo-template/` (comprehensive repo skeleton, includes SNForge config in `Scarb.toml`; copy and adapt to the repo layout).
- **Coverage validator**: `scripts/validate_coverage.py` (enforces naming and mapping rules; pass repo-specific paths).

## Workflow (Progressive Disclosure With Gates)
Follow this sequence strictly. Stop after each gate and ask for confirmation.

### Gate 0 - Intake & Constraints
Use: `references/workflow-gates.md`

Actions:
- Confirm `PROJECT_ROOT`, `SPEC_PATH`, `TEMPLATE_DEST`, `TESTS_DIR`, `BTT_DIR`, `SPEC_DOCS_DIR`, and allowed edit scope.
- Confirm where to copy the template asset inside the repo and what to rename/adjust.
- Confirm toolchain versions if relevant.

Stop: ask for confirmation.

### Gate 1 - Spec Decomposition Map
Use: `references/mapping-spec-to-tests.md`

Actions:
- Read the spec in slices (avoid loading the full file at once).
- Extract: contracts/interfaces/events/storage, logic flows, invariants, risks, test requirements.
- Present a concise coverage map (no files) and ask for approval.

Stop: ask for confirmation.

### Gate 2 - Apply Template (No New Spec Package)
Use: `references/repo-conventions.md`, `references/snforge-config.md`

Actions:
- Copy `assets/cairo-repo-template/` into `TEMPLATE_DEST`.
- Update `Scarb.toml` values as needed (name, versions, fork URL) and align to existing repo layout.
- Do not add business logic.

Stop: ask for confirmation.

### Gate 3 - Interface + Abstract Skeletons
Use: `references/repo-conventions.md`, `references/naming-rules.md`

Actions:
- Create Cairo interface/trait files and abstract shells per the spec.
- Include storage layouts, events, and access control surfaces.
- No real logic.

Stop: ask for confirmation.

### Gate 4 - Testing Infrastructure + Placeholders
Use: `references/test-infra-blueprint.md`, `references/btt-format.md`, `references/fixtures-and-scenarios.md`, `references/mocks-patterns.md`, `references/assertions-and-events.md`

Actions:
- Populate `SPEC_DOCS_DIR` with test manifest, invariants, risk matrix, pre/post conditions, property tests, and infrastructure notes.
- Create BTT trees in `BTT_DIR` with TEST-IDs in leaf nodes.
- Create placeholder tests in `TESTS_DIR` (unit/integration/property structure as configured).
- Every test must include a `// TEST-ID: TEST-...` marker.

Stop: ask for confirmation.

### Gate 5 - Coverage Validation
Use: `scripts/validate_coverage.py`

Actions:
- Run the validator with explicit paths and fix gaps until it passes.
- Validator enforces TEST-ID naming, BTT presence, stub presence, invariant/risk mapping.

Stop: ask for confirmation.

### Gate 6 - Handoff
Actions:
- Summarize what is ready for the implementation agent.
- Confirm that all constraints were met.

## Output Quality Bar
- Clear traceability from spec -> skeletons -> tests.
- All tests mapped to BTT + stubs + invariants + risks.
- Template compiles and tooling config is present.
- No business logic implemented.
