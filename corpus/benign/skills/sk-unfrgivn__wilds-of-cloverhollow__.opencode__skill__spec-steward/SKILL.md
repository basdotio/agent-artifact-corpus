---
name: spec-steward
description: Keep Cloverhollow behavior, interfaces, and decisions aligned with spec.md. Use whenever game behavior, scenes, assets, input, tests, or project workflows change.
compatibility: "repository ./tools/ci/run-spec-check.sh"
---

# Spec steward

Read `spec.md` and the relevant docs before changing behavior. Keep diffs small,
record material behavior/interface/decision changes in `spec.md`, and preserve
the repository's Scenario Runner evidence requirements. Run
`./tools/ci/run-spec-check.sh`; if it fails, inspect the reported drift and fix
the source-of-truth mismatch rather than suppressing it. Fail closed when the
spec or canonical path is unclear. Do not claim `check_*` log events prove
behavior, and do not use OS automation.
