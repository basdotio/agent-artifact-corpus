---
name: project-plan
description: Use when the project's plan, TODO/PROJ items, deadlines, notes, or summaries live in the central project org file, usually `project.org`. Also use when Codex should write an agreed plan into that file, update it after technical review or status discussion, mark finished work as DONE, record notes or summaries under `* Note`, or when the user explicitly invokes `$project-plan`. If `$project-plan` is invoked without any follow-up prompt, switch to plan mode, list the current active plans from the project org file, and ask the user which one to execute or review.
---

# Project Plan

Treat the project's central org file as the source of truth for project plans, deadlines, notes, and summaries.

## Working Rules

1. Resolve the active project root first. Prefer the live Emacs project context over guessing from filesystem paths.
2. Resolve the central project org file next. Prefer `(+org-project-current-file)` or `(+org-project-file-dwim)` when available. If no helper is available, fall back to `project.org` in the active project root.
3. Read before writing. For planning or review work, inspect the active task headings plus `* Note` and any active project subtree. For note-only requests, read `* Note` first and ignore task sections unless they are directly relevant.
4. Treat an explicit `$project-plan` invocation with no follow-up prompt as a request to enter plan mode. Enumerate the active `PROJ`, `TODO`, `WAIT`, and imminent deadline items from the project org file, then ask the user which item to execute, continue, or review.
5. Treat an explicit `$project-plan` invocation with follow-up text as an update request. Classify the content before editing: actionable work belongs in plan/task headings, while non-actionable facts, notes, and summaries belong under `* Note`.
6. Write agreed plans into the project org file instead of leaving them only in chat. When the user asks to make or refine a plan, convert the outcome into org entries that match the existing file structure.
7. Represent multi-step efforts as `PROJ` entries with child `TODO` or `WAIT` items when that matches the existing file. Add `DEADLINE:` when a due date is known.
8. Update the corresponding org entries after technical discussion changes the plan. Adjust task state, wording, order, deadlines, or notes so the file stays current after review.
9. Mark completed work as `DONE` when execution finishes. Do not leave finished plan items open unless the user explicitly wants to defer that update.
10. Keep remembered facts, design notes, meeting notes, and summaries under `* Note` unless they are actionable tasks. Do not silently convert note content into TODO items.
11. Preserve human-authored task wording when possible. Keep agent-generated status or worklog content clearly marked as AI-authored.
12. Do not silently delete human-captured tasks. Close, rewrite, or archive them only when the conversation or the existing org workflow supports that change.

## Preferred Helpers

Use Emacs helpers when available instead of hand-editing headings:

- `(+org-project-current-file)` to locate the current project's central file
- `(+org-project-file-dwim)` to detect or choose a project file
- `(+org-project-append-log FILE TEXT)` to append project log entries
- `(+org-project-archive-done-task)` when the user explicitly asks to archive completed work

When no dedicated helper exists for plan maintenance, edit the relevant subtree directly and keep the surrounding structure intact.

## Content Conventions

- Treat the project org file as the system of record for plans, deadlines, notes, and summaries
- Prefer `project.org` when no project-specific helper or existing org file says otherwise
- Prefer updating the existing heading layout over inventing a new schema
- Use `PROJ` for multi-step efforts and child `TODO` or `WAIT` items for concrete next actions
- Use `DEADLINE:` for due dates
- Use `* Note` for non-actionable notes and end-of-task summaries
- Use `* Log` for agent-generated status updates only when that section already exists or the workflow clearly expects it
- Keep human-captured tasks tagged as human-authored when the file already uses those tags or properties

## Core Workflow

1. If the skill is invoked without follow-up text, enter plan mode, summarize the active plans, and ask the user to choose one path before making changes.
2. If the skill is invoked with follow-up text, classify the request as plan/task work or note/summary work and update the correct section of the project org file.
3. Write or revise the plan in the project org file after the user and agent agree on the work.
4. Reflect technical review outcomes back into the matching org entries instead of keeping updated intent only in chat.
5. Mark completed items as `DONE` when the implementation or investigation finishes.
6. Append a short summary or note under `* Note` when the result is worth remembering but is not itself a task.

## Good Patterns

- Call `$project-plan` alone, list the current active plans from the project org file, and let the user choose which one to execute next
- Turn a chat-level implementation plan into concrete org entries in the project file before or while starting the work
- Update an existing `PROJ` subtree after scope, sequencing, or deadlines change during discussion
- Mark the finished `TODO` or `PROJ` entry as `DONE` after the work lands
- Add a short post-work summary under `* Note` when the user wants a durable record of the outcome
- Keep `Archive` folded and out of the active working set unless the task is explicitly about cleanup or review
