---
name: project-stash
description: >
  Manage the operator's active project board, daily debriefs, and backups.
  Use when the operator: asks about their projects or project status; wants to stash, add,
  or record a new project idea; wants to update project status or progress; marks a project
  as completed or wants to drop/abandon a project; requests a status report, momentum check,
  or daily debrief; mentions PROJECTS.md or the project stash.
---

# Project Stash

Manage the operator's active projects board, take daily snapshots, archive completed work, and run debriefs.

## Common Operations

### Complete a Project

1. Create an archive file in the completed vault with a brief summary of the work done.
2. File naming: `{YYYY-MM-DD}_{Project_Name}.md` (spaces → underscores, date in CST).
3. Remove the project entry from `PROJECTS.md`.

### Add / Update a Project

Edit `PROJECTS.md` directly. Follow the format in [assets/PROJECTS_TEMPLATE.md](assets/PROJECTS_TEMPLATE.md).

### Reviews (Ticklers)

Code reviews, PRDs, and minor check-ins go into a dedicated `## Reviews (Scheduled Ticklers)` section on `PROJECTS.md`.
**Rule:** Review items stay EXACTLY one line per item, with a scheduled time (e.g., "[Tomorrow morning] Trading Bot PRD Review"). Do not let them clutter the main active projects. They should be handled in batches so they do not break the main flow.

### Report Status

Read `PROJECTS.md` and summarize active projects. No snapshots, no backups -- read-only.

## Debrief

Full 6-step debrief procedure (calendar, projects, momentum, pep talk, ask, backup): see [references/debrief.md](references/debrief.md)

## File Structure

Paths, naming conventions, and directory layout: see [references/file_structure.md](references/file_structure.md).

## Scripts

**`scripts/cn_calendar.py`** -- Chinese calendar day classifier. Returns JSON with date, weekday, work/rest status, next workday, next holiday block, and upcoming 补班 days.

```bash
python3 scripts/cn_calendar.py [YYYY-MM-DD]   # defaults to today (CST)
```

### Side Projects / Someday-Maybe

Edit or read `SIDE_PROJECTS.md`. Use this when the operator mentions "side projects", "reading list", or "shopping wishlist". These are low-stakes passion ideas and wishes that only require a weekly review, unlike the main `PROJECTS.md`.
