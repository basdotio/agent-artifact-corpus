---
name: pr-docs
description: "Generate PR documentation from completed spec and git diff. Use when: pr docs, generate docs, pull request docs, baldrick docs. Triggers on: pr docs, generate docs, document changes."
---

# PR Documentation Generator

Generate PR-ready documentation from a completed spec and git changes.

> **Philosophy:** Clear documentation makes reviews faster and preserves context.

---

## The Job

1. Receive spec name from user
2. Read the spec file from `specs/[name].md`
3. Analyze git diff for the related changes
4. Generate comprehensive PR documentation
5. Save to `docs/[name]-changes.md`

---

## Output Format

```markdown
# [Feature Name]

## Summary

Brief description of what was implemented.

## Changes

### Files Modified
- `path/to/file.ts` - What changed and why
- `path/to/other.ts` - What changed and why

### Files Added
- `path/to/new-file.ts` - Purpose of new file

## Implementation Details

### Key Decisions
- Decision 1 and rationale
- Decision 2 and rationale

### Trade-offs
- Trade-off considered and why this approach was chosen

## BDD Coverage

| Scenario | Status |
|----------|--------|
| Happy path login | ✅ Implemented |
| Invalid email | ✅ Implemented |
| Wrong password | ✅ Implemented |

## Testing

- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing steps

## Screenshots/Examples

(If applicable - UI changes, API responses, etc.)

## Related

- Spec: `specs/[name].md`
- Related PRs: (if any)
```

---

## Process

1. **Read the spec** - Understand what was supposed to be built
2. **Analyze git diff** - See what actually changed
3. **Map changes to requirements** - Connect code changes to spec scenarios
4. **Document decisions** - Capture why things were done a certain way
5. **Note BDD coverage** - Show which scenarios are implemented

---

## Example Usage

User: "Generate PR docs for the login feature"

Output saved to: `docs/login-changes.md`

---

## Output

- **Format:** Markdown (`.md`)
- **Location:** `docs/`
- **Filename:** `[spec-name]-changes.md`

---

## Checklist Before Saving

- [ ] Read the spec completely
- [ ] Analyzed all git changes
- [ ] Documented all modified files
- [ ] Listed key implementation decisions
- [ ] Mapped scenarios to implementation status
- [ ] Saved to `docs/[name]-changes.md`
