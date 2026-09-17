---
name: "Work Kanban Workflow"
description: "Manages file-based work items through a lightweight kanban system using folder-based state management. Handles backlog capture, design phase, active work, review, and archiving. Creates items in 00-backlog/, moves through 10-in-design/, 20-in-progress/, 30-in-review/, to 90-archive/. Applies templates and checklists at each stage. Zero-friction backlog entry, clear decision gates between stages."
dependencies: []
---

# Work Kanban Workflow - Lightweight File-Based Task Management

This skill helps you manage work items using a **folder-based kanban system** where state = folder location and each work item = one Markdown file.

## Core Philosophy

- **Backlog is zero-friction**: Drop anything in with any filename, any format
- **State represented by folders**: Moving files between folders changes state
- **Checklists are decision gates**: They determine when work is ready to progress
- **No YAML/front matter**: Keep it simple - just Markdown content
- **Content > filenames**: What's written matters more than perfect naming

---

## Folder Structure

The system uses these folders:

```
work/
  README.md
  00-backlog/          # Frictionless capture
  10-in-design/        # Define problem, goal, approach
  20-in-progress/      # Active work
  30-in-review/        # Ready for verification
  90-archive/          # Done or cancelled
  templates/
    backlog.md
    design.md
    review.md
```

### State Meanings

| Folder | Purpose | Structure Required |
|--------|---------|-------------------|
| **00-backlog/** | Capture anything | ❌ None - any format OK |
| **10-in-design/** | Define the work | ✅ Design template |
| **20-in-progress/** | Active implementation | ✅ Notes + updates |
| **30-in-review/** | Ready for verification | ✅ Review template |
| **90-archive/** | Complete or cancelled | ✅ Outcome note |

---

## When User Asks to Track/Capture Work

### For New Ideas, Bugs, Features

**Always start in `00-backlog/`:**

1. Create a file in `work/00-backlog/` with any name (even `tmp.md` is fine)
2. Dump the content - any format, any structure
3. Don't enforce completeness or templates

**Example:**
```markdown
# Fix slow search

Users complaining search takes 5+ seconds

Maybe index the name and email columns?

Link: https://github.com/org/repo/issues/123
```

**Key**: Make this **frictionless**. No rules, no structure, no naming conventions in backlog.

---

## Moving to Design Phase

### Backlog → Design Gate

Only move to `10-in-design/` when you can answer:
- [ ] What problem are we solving?
- [ ] What does "good" look like?
- [ ] What's a plausible approach?

### Apply Design Template

When moving to `10-in-design/`, structure the file like this:

```markdown
# [Clear Title]

## Problem
What hurts / what are we solving?

## Goal  
What does "good" look like?

## Approach
How we'll do it (rough is fine).

## Acceptance checklist
- [ ] Problem is clear
- [ ] Goal is clear
- [ ] Approach is plausible
```

### File Naming (Optional)

Use readable slugs: `improve-search-performance.md`, `add-user-dashboard.md`

But if not renamed, that's fine - content matters more.

---

## Active Work Phase

### Design → In Progress

Move to `20-in-progress/` when starting implementation.

**While working:**
- Add notes about decisions made
- Update the approach section if it changes
- Track remaining steps
- Keep it concise

**If work stalls:**
- Move back to `00-backlog/` (that's okay!)
- Add a note about why

**If new work is discovered:**
- Create a NEW backlog item instead of bloating the current one

---

## Review Phase

### In Progress → Review

Move to `30-in-review/` when complete and ready for verification.

### Apply Review Template

```markdown
# [Title]

## What changed
Short summary of what was done.

## Review checklist
- [ ] Meets the original goal
- [ ] Doesn't break existing behavior
- [ ] Edge cases considered
- [ ] Notes updated / follow-ups captured

## Outcome
- Decision: ✅ accept / ❌ reject / 🟨 follow-ups needed
- Notes: [explain decision]
```

**Review Rules:**
- Use the checklist as the decision gate
- Document the outcome clearly
- If follow-ups needed, create new backlog items

---

## Archiving

### Review → Archive

Move to `90-archive/` when:
- Review checklist is satisfied ✅
- OR work is explicitly cancelled ❌

**Always keep the outcome note** so future reference is possible.

---

## Complete Workflow Example

Let me show you a concrete progression:

**Day 1 - Capture (Backlog):**
```
File: work/00-backlog/search.md

Search is slow - users complaining
Maybe we need database indexes?
```

**Day 2 - Shape (Design):**
```
File: work/10-in-design/improve-search-performance.md

# Improve Search Performance

## Problem
Search queries take 5+ seconds on production database.

## Goal
Sub-1-second search response time for 95% of queries.

## Approach
Add database indexes on users.name and users.email columns.
Test with production-scale data.

## Acceptance checklist
- [x] Problem is clear
- [x] Goal is clear
- [x] Approach is plausible
```

**Day 3-4 - Build (In Progress):**
```
File: work/20-in-progress/improve-search-performance.md

[Previous content...]

## Progress Notes
- 2024-01-15: Added index on users.name - reduced query time to 2s
- 2024-01-16: Added index on users.email - now sub-1s
- 2024-01-16: Tested with 1M records - performance holds

## Remaining
- [x] Test with production-scale data
- [x] Verify no breaking changes
```

**Day 5 - Review:**
```
File: work/30-in-review/improve-search-performance.md

[Previous content...]

## What changed
Added B-tree indexes on users.name and users.email.

## Review checklist
- [x] Meets the original goal (sub-1s achieved)
- [x] Doesn't break existing behavior (verified)
- [x] Edge cases considered (tested with 1M records)
- [x] Notes updated / follow-ups captured

## Outcome
- Decision: ✅ accept
- Notes: Performance goal achieved. No regressions detected.
```

**Day 6 - Archive:**
```
File: work/90-archive/improve-search-performance.md
[Keep full history - it's done!]
```

---

## Commands & Patterns

### When User Says...

**"Track this idea / bug / feature"**
→ Create in `work/00-backlog/[simple-name].md`
→ Capture essential info, no structure required

**"Let's work on [backlog item]"**
→ Move to `10-in-design/`
→ Apply design template
→ Ensure acceptance checklist is complete

**"Starting work on [item]"**
→ Move to `20-in-progress/`
→ Add progress notes section

**"This is ready / done"**
→ Move to `30-in-review/`
→ Apply review template
→ Fill out review checklist

**"Review passed / approved"**
→ Move to `90-archive/`
→ Keep outcome note

**"This is blocked / stalled"**
→ Move back to `00-backlog/`
→ Add note about why

---

## Anti-Patterns (Don't Do)

❌ **Don't enforce structure in backlog** - defeats the purpose of frictionless capture

❌ **Don't add YAML front matter** - we avoid it intentionally for simplicity

❌ **Don't skip states** - don't create items directly in `10-in-design/` or later

❌ **Don't bloat work items** - if new work emerges, create a new backlog item

❌ **Don't skip checklists** - they're the decision gates that ensure quality

❌ **Don't delete archived items** - keep them for historical reference

---

## Templates Reference

See the `templates/` folder for:
- `backlog.md` - Optional, any format works
- `design.md` - Required structure for design phase
- `review.md` - Required structure for review phase

---

## Tips for Helping Users

1. **Always start in backlog** - never create work items in other folders first

2. **Ask clarifying questions** when moving to design:
   - "What problem does this solve?"
   - "What does success look like?"
   - "How might we approach this?"

3. **Keep items short** - prefer bullets and checklists over prose

4. **Create new items freely** - if something new comes up, make a new backlog item

5. **Move backward is OK** - if work isn't ready, move it back to backlog

6. **Preserve history** - when moving files, keep all previous content

---

## Integration with Code/Projects

When working on code or projects related to work items:

- Reference the work item in commit messages: `"Add search indexes (work/20-in-progress/improve-search-performance.md)"`
- Mention the work item in design documents
- Link work items to PRs, issues, or tickets
- Use work items as context for technical discussions

---

## Remember

This system values:
- **Quick capture** (backlog)
- **Clear gates** (checklists)  
- **Visibility** (folder state)
- **Flow** (easy movement)

Over rigid processes and perfect documentation.

The goal is to make work visible and help it flow smoothly from idea to completion.
