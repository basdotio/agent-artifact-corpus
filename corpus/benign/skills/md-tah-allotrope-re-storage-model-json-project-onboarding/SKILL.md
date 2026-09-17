---
name: json-project-onboarding
description: This skill should be used when onboarding a new JSON+CSV project into the RE-Storage pipeline, including loader mapping, pipeline wiring, tests, and reference template setup.
---

# JSON Project Onboarding

Onboard non-Excel projects into the existing layered pipeline without breaking Excel workflows.

## Use When

- Add a new project delivered as JSON config plus hourly CSV.
- Build or update loaders in `src/re_storage/inputs/json_loader.py`.
- Add or update `run_model_from_json()` behavior.
- Create regression and unit tests for JSON input paths.

## Workflow

1. Read mapping checklist in `references/onboarding-checklist.md`.
2. Define field-level mapping using `references/mapping-template.md`.
3. Implement/extend JSON and CSV loaders with strict validation.
4. Ensure pipeline route uses private stages (`_run_physics`, `_run_settlement`, `_run_aggregation`, `_run_financial`) and does not call `run_full_model()`.
5. Return scalar KPIs plus report dataframes under underscore-prefixed keys.
6. Add/refresh tests:
   - `tests/unit/test_json_loader.py`
   - `tests/regression/test_<project>.py`
7. Add placeholder reference JSON using `assets/reference_kpi_template.json`.
8. Run targeted tests, then full test suite.

## Output Contract

- Working JSON project execution via `run_model_from_json()`.
- Passing unit tests for loader behavior.
- Passing/expected-skipped regression test depending on reference completeness.
- Clear note of known assumptions and conversions.

## Constraints

- Preserve existing Excel path behavior.
- Keep naming and KPI keys consistent with current regression conventions.
- Keep unit conversions explicit and validated.

## References

- `references/onboarding-checklist.md`
- `references/mapping-template.md`
- `references/test-patterns.md`
