# Changelog

All notable changes to this skill are documented here.

## [1.0.0] - 2026-10-11

### Added

- Complete Skill-package auditing: frontmatter, local Markdown links, missing references, UTF-8/readability and size checks, path traversal, symlinks, script file types, and dependency availability/callability/fallback reporting.
- `--strict` exit codes and a versioned JSON schema (`1.0`).
- Separate confirmed findings, heuristic candidates, package-integrity issues, dependency checks, and skipped/unreadable files.
- Token-overuse candidates based on bounded-context/YAGNI signals; the auditor reports judgments only and does not emit edit suggestions.
- Boundary tests for invalid metadata, missing and out-of-bound references, non-UTF-8 and oversized files, dependencies, and strict-mode exits.
- Standards compliant YAML parsing with duplicate-key detection, nested Skill package discovery, and a conservative confirmed-conflict path for strict exit code `1`.
- Release validation against installed complex Skill packages; example paths remain heuristic candidates, package-root-relative references resolve correctly, and extensionless scripts with shebangs are supported.
- Release correction: strict scans now flag empty scopes and explicit package roots without entrypoints; Markdown link titles no longer become path text; Skill entrypoints are discovered case-insensitively.
- Private release reissue: compare explicit entrypoint stage-table mappings with directly linked same-stage guide headings, retain both quotes and line numbers for confirmed mismatches, and distinguish workflow comparisons from package-integrity coverage in schema `1.1`.

## [0.1.0] - 2026-10-10

### Added

- Read-only audit of `AGENTS.md` and `SKILL.md` files.
- Heuristic findings for overwork, pointless waiting, and instruction conflicts.
- Markdown and JSON reports with source excerpts, locations, causes, and minimal suggestions.
- Root-isolated scanning with safe handling of roots named `build`, `dist`, or `venv`.
- Regression tests for path handling, root isolation, skipped directories, and candidate conflicts.
- GitHub Actions validation on Python 3.9, 3.11, and 3.13.

### Limitations

- Findings are heuristic candidates and require human review.
- The package does not monitor filesystem downloads in the background.
- The package never edits inspected files.
