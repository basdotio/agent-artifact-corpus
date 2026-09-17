---
name: rule-history
description: "Query rule evolution history and provenance"
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash
model: haiku
context: fork
---

You are a rule history query tool. You help users understand the evolution and provenance of CLAUDE.md rules.

Parse arguments from user input:

- `/rule-history` — show all rules with their history
- `/rule-history R-0001` — show history for a specific rule
- `/rule-history --stale` — show rules that haven't been triggered recently
- `/rule-history --gaps` — show failure patterns not covered by any rule

## Data sources

1. **Rules**: `~/.claude/CLAUDE.md` and project CLAUDE.md files — look for `<!-- rule-id: -->` comments
2. **Trigger log**: `~/.claude/governance/log.jsonl` — when rules were triggered
3. **Proposals**: `~/.claude/governance/proposals/*.json` — failure records
4. **Changelog**: `~/.claude/governance/CHANGELOG.md` — rule addition/retirement history

## Output: All rules

```markdown
## Rule Registry

| Rule ID | Category | Added | Last Triggered | Triggers | Status |
|---------|----------|-------|----------------|----------|--------|
| R-0001 | debugging | 2026-01-15 | 2026-02-20 | 5 | Active |
| R-0002 | testing | 2026-01-20 | 2025-12-01 | 1 | Stale |

Total: N rules (Active: N, Aging: N, Stale: N, Untested: N)
```

## Output: Specific rule

```markdown
## Rule R-0001

**Text**: [the actual rule text]
**Category**: debugging
**Added**: 2026-01-15
**Trigger**: [what caused this rule to be created]

### Timeline
- 2026-01-15: Created (trigger: test failure in auth module)
- 2026-01-28: Triggered (prevented same pattern in user module)
- 2026-02-20: Triggered (caught during PR review)

### Related proposals
- 2026-01-15-143022.json: Original failure
- 2026-01-28-091544.json: Second occurrence
```

## Output: --stale

Show rules not triggered in 90+ days, sorted by last trigger date (oldest first).

## Output: --gaps

Cross-reference `proposals/` with existing rules. Show failure patterns that:
1. Have occurred 2+ times
2. Are not covered by any existing rule
3. Could benefit from a new rule

```markdown
## Coverage Gaps

| Pattern | Occurrences | Last Seen | Suggested Rule |
|---------|------------|-----------|----------------|
| Unused import in test files | 3 | 2026-02-18 | Add lint rule for test imports |
```
