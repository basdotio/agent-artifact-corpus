# grace-lite-reviewer

Stripped version of
[grace-reviewer](https://github.com/osovv/grace-marketplace/tree/main/skills/grace/grace-reviewer).

Validates GRACE integrity across code and documentation — semantic markup,
module contracts, knowledge graph synchronization, verification plans, and XML
tag conventions. Operates at phase boundaries or during active execution waves.

## What's included

- **Two review modes**: `scoped-gate` (changed files and deltas only, for active
  execution) and `full-integrity` (full GRACE surface audit, for phase
  boundaries or suspected drift)
- **Five checklist areas**:
  - _Semantic markup validation_ — paired blocks, unique names, reasonable
    sizing, navigable test markup
  - _Contract compliance_ — cross-references MODULE_CONTRACT, MODULE_MAP, and
    function contracts against actual imports, parameters, return types, and
    side effects
  - _Verification integrity_ — test-to-module mapping, log marker stability,
    assertion determinism, success/failure scenario coverage
  - _Graph and plan consistency_ — delta proposals vs real code changes,
    orphaned entry detection in full mode
  - _Unique tag conventions_ — M-xxx, export-name, fn-name, type-Name tags in
    XML documents
- **Structured text report**: mode, scope, file count, issue breakdown
  (critical/minor), escalation flag, PASS/FAIL summary
- **Escalation logic**: promotes `scoped-gate` → `full-integrity` when local
  evidence suggests broader drift
- **Actionable fix suggestions** — never auto-fixes, reports only
- **OpenAI agent interface**: pre-configured display name, short description,
  and brand color

## Scope & Limitations

grace-lite-reviewer is a **read-only review skill** — it audits and reports, but
does **not** modify code, contracts, or documents.

The lite variant is designed for projects that only use the knowledge graph and
AGENTS.md — no full GRACE document suite is required.

## Usage

This is an **agent skill**, not a CLI tool. Trigger it by asking the agent to
review, audit, or validate GRACE integrity — the agent will follow the SKILL.md
workflow:

1. Determine review scope (changed files, a specific module, or full surface)
2. Run the five-point checklist over scoped files and documents
3. Flag critical and minor issues with file:line references
4. Produce a structured `GRACE Review Report` with PASS/FAIL verdict

## Acknowledge

This skill is an almost complete copy of
[grace-reviewer](https://github.com/osovv/grace-marketplace/tree/main/skills/grace/grace-reviewer)
— the original GRACE reviewer skill stripped down to the GRACE-lite artifact set
(knowledge graph only, no GRACE CLI, no full document suite). The full GRACE
ecosystem lives at
[osovv/grace-marketplace](https://github.com/osovv/grace-marketplace).
