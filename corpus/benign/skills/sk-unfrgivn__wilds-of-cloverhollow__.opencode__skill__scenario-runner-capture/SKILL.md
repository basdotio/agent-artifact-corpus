---
name: scenario-runner-capture
description: Add or run deterministic Cloverhollow Scenario Runner scenarios with real input, traces, and captures. Use for gameplay verification, level iteration, boundary checks, and rendered evidence.
compatibility: "./tools/ci/run-scenario.sh, ./tools/ci/run-scenario-rendered.sh, Godot 4.5.1"
---

# Scenario Runner and capture

Read `docs/testing/scenario-runner.md` and an existing scenario before editing.
Use only action types documented there and actual `tests/scenarios/*.json` paths.
The wrappers accept a scenario ID and write `run.log` plus `trace.json` under
the capture directory; seeds and frame counts can be set with `SEED`,
`CAPTURE_DIR`, and `QUIT_AFTER_FRAMES`.

Completion evidence requires: command exit 0, a valid trace with `passed: true`,
no `errors`, no `error` or `noop` events, expected action events, and expected
PNG labels. `check_*` actions are log observations, not assertions. Use real
`move`/`press` actions for behavior. Read the trace and log and inspect every
capture with image reading/vision. Fail closed on missing or ambiguous evidence.
No OS-level window control.
