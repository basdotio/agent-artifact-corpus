# Instruction Audit

[中文说明](README.zh-CN.md)

Instruction Audit is a read-only Agent Skill and package auditor. It reviews `AGENTS.md` and complete `SKILL.md` packages for unnecessary work, contradictory directives, pointless waiting, and likely token overuse. It checks frontmatter, local references, file readability, path boundaries, symlinks, supported script types, and declared dependencies. For explicit entrypoint stage-table links, it also compares the stage number with the directly linked guide's same-stage top-level heading. It reports judgments only; it never proposes or applies edits to inspected files.

**Release status:** `v1.0.0`. Heuristic candidates require human review; strict mode blocks confirmed instruction conflicts and package-integrity failures. The scanner is read-only and does not watch downloads in the background.

## Requirements

- Python 3.9 or newer
- PyYAML 6.x for standards compliant frontmatter parsing

Install the scanner dependency with `python -m pip install -e .` from the repository root. Audits themselves do not install packages or use the network.

## Use

Resolve the directory containing `SKILL.md` and pass its absolute script path so the command is independent of the current working directory:

```text
python -X utf8 "<skill-root>/scripts/audit_instructions.py" --root <workspace> --format markdown
```

Use `--format json` for automation, `--strict` for CI, and `--package-root <skill-dir>` for an explicit package. Strict-mode exit codes are: `0` no blocking condition detected, `1` confirmed finding, `2` package-integrity issue or skipped/unreadable/zero-target scan, and `3` argument or runtime error. A directory passed through `--package-root` must have a top-level `SKILL.md` entrypoint (case-insensitive); a wrong path cannot silently pass CI. Reports separate confirmed findings, heuristic candidates, package-integrity issues, dependency checks, and skipped/unreadable files. The scanner does not install or invoke declared dependencies.

Declare dependencies as a YAML list in `SKILL.md` frontmatter. Prefix an optional dependency with `?`; the report still records whether it is available, callable, and covered by a documented fallback.

The JSON contract is documented in [`references/report-schema.md`](references/report-schema.md). It uses `schema_version: "1.1"` and stable ordering for repeatable inputs. The report distinguishes instruction files scanned, packages integrity-checked, and directly linked workflow mappings compared. A zero exit code is not proof of full workflow consistency. See [`RELEASE.md`](RELEASE.md) for the source archive manifest and reproducible build.

Compatible packages use a standalone `SKILL.md` (filename matching is case-insensitive) with Codex-style YAML frontmatter: `name`, `description`, and the supported optional fields `license`, `metadata`, `compatibility`, `argument-hint`, `allowed-tools`, and `skill-dependencies`. Custom frontmatter schemas are reported as integrity issues. Explicit local Markdown links, including links with optional titles, are checked as package references; ambiguous backtick paths are candidates for human review. A Skill that intentionally shares files outside its own directory may produce out-of-bound candidates.

The token-consumption check follows the same practical YAGNI/progressive-disclosure signal used by the [Ponytail project](https://github.com/DietrichGebert/ponytail): flag unconditional rereading, exhaustive output, and context loading that is not tied to the task. It does not claim to measure model tokens and does not issue rewrite suggestions.

## Development checks

```text
python -m unittest discover -s tests -v
python scripts/validate_package.py
python scripts/audit_instructions.py --root . --strict --format json
python -X utf8 "<skill-root>/scripts/audit_instructions.py" --root <workspace> --format markdown
```

The project is intentionally a static, read-only scanner. To audit a newly downloaded Skill, invoke it after the download or from the host's post-download/CI integration. It is not a background filesystem watcher.
