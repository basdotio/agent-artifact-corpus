---
name: task-breakdown
description: Break work into trackable tasks and maintain TODO.md. Use when starting features, bug fixes, or complex tasks. Always update TODO.md after completing work.
allowed-tools: Read, Write, Edit, Bash
---

# Task Breakdown Skill

## Purpose
Ensures all work is broken into discrete, trackable tasks stored in TODO.md.

## Instructions

### 1. Starting New Work
When user requests any feature/fix:
1. Read existing `TODO.md` (if exists)
2. Break request into 3-10 concrete tasks
3. Write to `TODO.md` at project root
4. Each task needs unique @id (task-1, task-2, etc.)
5. Assign @priority by dependency order (lower = do first)

### 2. TODO.md Format
```markdown
# Tasks for [Project Name]

## Current Task
- [ ] What you're working on NOW @id:current @priority:0

## Upcoming Tasks
- [ ] Task description @id:task-1 @priority:1
- [ ] Another task @id:task-2 @priority:2
- [x] Completed task @id:task-3 @priority:3

## Metadata
- Total: 3 tasks
- Completed: 1 tasks
- Progress: 33%
```

### 3. After Each Tool Use
1. If task completed, mark [x]
2. Update "Current Task" section
3. Update metadata (Total/Completed/Progress)
4. MUST update after Write, Edit, or Bash

### 4. Task Sizing
- Each task: 1-5 minutes
- Be specific: "Add auth" → "Create User model", "Add login route", "Add JWT middleware"
- If too large, break into subtasks

### 5. Reading User Changes
Before each task:
1. Read TODO.md
2. Check if priorities changed (user may have reordered in UI)
3. Work on lowest @priority number

### 6. File Location
- Always use: `${CLAUDE_PROJECT_DIR}/TODO.md`
- Create if doesn't exist

## Example

```markdown
# Tasks for User Auth Feature

## Current Task
- [ ] Writing JWT middleware @id:current @priority:0

## Upcoming Tasks
- [ ] Create User model @id:task-1 @priority:1
- [ ] Add bcrypt hashing @id:task-2 @priority:2
- [x] Install packages @id:task-3 @priority:3
- [ ] Create /login endpoint @id:task-4 @priority:4
- [ ] Create /register endpoint @id:task-5 @priority:5

## Metadata
- Total: 6 tasks
- Completed: 1 tasks
- Progress: 17%
```
