---
name: knip-audit
description: Audit and clean unused files, dependencies, and manifest issues with Knip in this repository. Use when running `pnpm lint:knip` or `pnpm lint:knip:strict`, triaging findings, fixing real hygiene issues, or deciding whether a Knip finding should become a targeted ignore in `.knip.jsonc`.
metadata:
  short-description: Triage and fix Knip findings
---

# Knip Audit

Use this skill when the task is repository hygiene through Knip, not when the user just wants general linting.

## Repo defaults

- Baseline command: `pnpm lint:knip`
- Failing command: `pnpm lint:knip:strict`
- Config file: `.knip.jsonc`
- Main lint gate: `pnpm lint`

Knip is intentionally separate from the blocking lint gate unless the user explicitly asks to change that and the baseline is genuinely low-noise.

## Audit order

1. Run `pnpm lint:knip:strict`.
2. Classify each finding before editing anything:
   - Real dead file or dependency
   - Manifest hygiene issue
   - Intentional file or dependency that Knip cannot infer
3. Prefer real cleanup over ignores:
   - Delete dead files
   - Remove unused dependencies from the owning `package.json`
   - Add missing dependencies where a script or config really imports them
4. Only add Knip ignores for findings that are clearly intentional.
5. Re-run `pnpm lint:knip:strict`.
6. If `package.json`, root scripts, or other lint-relevant files changed, run `pnpm lint`.

## Decision rules

### Delete or remove

Prefer deletion or manifest cleanup when:

- A file has no consumers and is not structurally required by repo invariants
- A dependency is declared but not imported or required anywhere meaningful
- A root or workspace script imports a package that is missing from the relevant manifest

### Ignore in `.knip.jsonc`

Use targeted ignores only when the finding is clearly intentional, for example:

- Peer dependencies required by another library but not directly imported
- Expo or framework config/package conventions Knip does not model well
- Generated-code mutators or similar files referenced indirectly by config
- Repo-invariant shim files that must exist for colocated test structure

Keep ignores narrow:

- Prefer per-file `ignoreIssues`
- Prefer per-workspace `ignoreDependencies`
- Do not add broad global ignores when a file-scoped ignore is enough

## Repo-specific cautions

- This repo enforces colocated test/source structure. If deleting a file causes an invariant failure, restore the minimal colocated module and ignore that file in Knip only if it is intentionally structural.
- Do not add Knip to `pnpm lint` by default just because the current report is clean. That is a policy decision, not an audit default.
- If a finding points at `apps/mobile` or framework config files, assume Expo/tooling false positive until proven otherwise.
- If a finding points at `apps/web` UI peer deps, verify whether they are required by `react-admin` or another UI library before removing them.

## Exit criteria

A good Knip audit ends with:

- `pnpm lint:knip:strict` passing
- `.knip.jsonc` updated only with narrow, justified ignores
- Real dead files and dependencies removed
- `pnpm lint` still passing if repo-wide lint inputs changed
