---
name: report-format
description: Load before writing an audit, review, or dependency report.
user-invocable: false
---

# Markdown report format

Consistent format for findings reports: audits, reviews, dependency runs, and any other structured list of problems found. A skill that defines its own report template (`investigate`) owns its shape; only the file-naming, path-printing, and ASCII rules below apply to those.

## Required sections

```markdown
# <Report type>: <target>

Generated: <ISO timestamp>
Scope: <file, component, or module>
Stack: <the language lines kit detect-stack prints, if applicable>

## Summary

<One paragraph. What was checked, what was found, overall health in one word.>

## Findings

### <Finding title>

- Severity: <failure | warning | info>
- Location: <file>:<line> or <region>
- What: <problem in one or two sentences>
- Why it matters: <one sentence>
- Fix: <code snippet or concrete instruction>
- Refs: <WCAG criterion, CVE, doc link, etc., if relevant>

### <Next finding>

...

## Cannot be verified statically

<Items that need runtime checks, user testing, or external tools. Omit section if empty.>

## Out of scope

<Things noticed but not part of the task. Omit if empty.>
```

## Rules

- Severity is one of `failure` (a defect or violation that should not ship), `warning` (a smell that compounds with other findings), `info` (a hardening opportunity or note, not a defect). Nothing else. A consumer may narrow a level's meaning for its domain, never add one.
- Sort findings by severity, failures first.
- If a section would be empty, omit it. Do not leave placeholder text.
- No ASCII decoration, no banner comments, no emoji.
- File naming and location: the path `kit scratch-dir <kind> <target-slug>` prints.
- Does not govern `/write` output (commit messages, PR descriptions, release notes, stakeholder summaries) - those have their own formats per `rules/output.md`.

## Summary line rubric

The "overall health in one word" at the end of the Summary helps quick scanning:

- `clean` (no findings)
- `minor` (only info)
- `moderate` (warnings, no failures)
- `serious` (failures present)
- `broken` (multiple critical failures, work should pause)

## Anti-patterns

- `failure`: writing the report body to terminal output instead of a file -- the artifact becomes ephemeral and unreferenceable.
- `failure`: omitting the `## Summary` section or the `## Findings` section when findings exist, in a report this format governs.
- `warning`: inventing severity levels outside `failure`, `warning`, `info` -- e.g. `critical`, `high`, `medium`, `low`, `error`. The rubric has three levels; anything else breaks downstream tooling that parses reports.
- `warning`: leaving placeholder text in empty sections (e.g. `<none>`, `N/A`) rather than omitting the section.
- `info`: not sorting findings by severity (failures first, then warnings, then info).
