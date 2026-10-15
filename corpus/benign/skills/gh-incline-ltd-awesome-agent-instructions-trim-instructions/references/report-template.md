# Instruction audit

## Scope and baseline

- Repository and selected files (relative paths only):
- Agent, version, and task context:
- Git status and baseline revision:
- File hashes from the measurement helper:
- Discovery/loading evidence and unknowns:
- Measurement method: selected-file characters / 4, rounded up per file.

## Protected constraints

Record protected spans and the headings, conditions, and loading scope that
give them meaning. Use line references, not sensitive excerpts. Include
constraints expressed indirectly, without words such as "safety" or "must".

## Findings

| File and lines | Action | Reason and local evidence | Rule and primary source | Scope / checked date |
| --- | --- | --- | --- | --- |

Use KEEP (constraint), KEEP (fact), REWRITE, MOVE, DELETE, ADD, or HOLD.
HOLD is an unresolved judgment, not a deletion suggestion.

## Proposed diff

Include the exact diff and all new reference files. Explain how each intended
agent still receives the needed information. Do not weaken loading scope or
replace mandatory rules with optional suggestions.

## Verification and approval

- Before/after selected-file estimates, labeled as estimates:
- Added or moved content, measured separately:
- Protected text and loading-scope comparison:
- Syntax, reference, and repository checks to run:
- Remaining uncertainties:
- Status: proposed / approved and applied / blocked.

Ask for approval of the concrete diff. After application, replace planned
checks with actual results and include the observed protected-constraint count.
Do not infer performance improvement from file size.
