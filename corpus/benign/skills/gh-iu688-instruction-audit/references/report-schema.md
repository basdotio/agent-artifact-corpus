# JSON report schema

The JSON output has a stable top-level schema. `schema_version` is currently
`"1.1"`; a breaking field or meaning change must increment it.

Required top-level fields:

- `schema_version`: string version of this report contract.
- `roots`: strings supplied to the audit invocation, with `/` separators.
- `files_scanned`: sorted instruction-file paths.
- `packages_scanned`: sorted Skill package paths.
- `confirmed_findings`: findings with `confidence: "confirmed"`.
- `heuristic_candidates`: findings requiring human review.
- `package_integrity_issues`: frontmatter, reference, dependency, path,
  readability, size, symlink, or file-type issues.
- `dependency_checks`: declared dependency availability and fallback checks.
- `workflow_consistency_checks`: explicit entrypoint stage-table mappings to directly linked Markdown guides, sorted by entrypoint line. Each object gives both paths and line numbers, stage name and numbers, and `status` (`matched`, `mismatch`, or `not-comparable`). This is a bounded comparison, not a claim that all guide prose was semantically audited.
- `skipped`: inputs that were not scanned.
- `unreadable`: files that could not be decoded or read.
- `findings`: compatibility view containing the union of confirmed findings and
  heuristic candidates.

Finding objects contain `category`, `severity`, `path`, `start_line`,
`end_line`, `quote`, `reason`, and `confidence`. Confirmed workflow mismatches also contain `evidence` with both original quotes, file paths, and line numbers. The auditor reports evidence
and judgment only; it does not emit edit or rewrite suggestions.

The implementation sorts paths and findings before serialization so identical
inputs produce stable output. All report paths use `/` separators on Windows,
Linux, and macOS. Consumers should treat unknown future fields as
forward-compatible additions and gate on `schema_version` for strict parsing.
