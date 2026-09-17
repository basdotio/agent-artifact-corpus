---
name: weekly-review
description: Weekly review and next-week planning for Obsidian monthly planning files. Analyze the current or specified week, infer the local section style, summarize milestones and risks, and update one week-level review section inside the week block without nesting it under personal subheadings. Use when the user asks for “周复盘”“本周总结”“下周计划”“这周进度怎么样”“weekly review”“week summary” or similar week-level review/planning tasks.
---

# Weekly Review

Use this skill to update one week block inside `Plan/每日规划/{YYYY}/Q{Q}/{YYYY.MM}.md`.

Read [references/obsidian-weekly-patterns.md](references/obsidian-weekly-patterns.md) before editing. It captures the observed 2026 week structures, naming variants, insertion boundaries, counting rules, and fallback template.

## Workflow

### Phase 1: 收集信息

1. Resolve the target week. Default to the current week. Honor an explicit date range or week name from the user.
2. **Read the quarterly OKR** to understand the season's goals and priorities:
   - Obsidian: `Plan/年度规划/2026 OKR/{YYYY} 第{N}季度.md` (e.g. `2026 第二季度.md`)
   - Notion: search for the same name (e.g. `2026 第二季度`), fetch the page, and read the Overview / KeyResult / ToDo databases to get status and completion data.
   - Obsidian and Notion use the same naming convention for quarterly OKR, so search Notion by the same title.
3. Find candidate month files. Read the current month file first:
   ```bash
   obsidian read path="Plan/每日规划/{YYYY}/Q{Q}/{YYYY.MM}.md"
   ```
   Also inspect the adjacent month file when the week spans two months. If the exact path is uncertain, use `obsidian search query="{week heading text}"` to locate the right file. Treat the week heading text as the source of truth even when the span is not a standard 7-day week.

### Phase 2: 分析与输出进度（先在 chat 中展示，不写文件）

4. **Output a quarterly OKR progress overview in chat.** For each Objective:
   - List every KR and its current status (未启动 / 进行中 / 已完成).
   - Highlight this week's relevant progress against each KR.
   - Use a table format for clarity.
5. **Analyze remaining time and output priority recommendations in chat:**
   - How many workdays / weekend days remain in the week.
   - **P0 (must do)**: items that are time-sensitive, blocking, or directly aligned with high-priority KRs.
   - **P1 (should push)**: items that advance KRs but are not urgent this week.
   - **Can defer**: items safe to push to next week with rationale.
   - Call out risks: carry-over items, KRs falling behind pace, blockers.
6. If the week is still in progress, say `统计截至 {Today}` in chat output.
7. **Wait for user confirmation before writing to the file.** The user may want to adjust priorities or add/remove items.

### Phase 3: 写入文件

8. Detect the local weekly style from the current file. Reuse the existing section name if the file already uses `周总结`, `本周总结`, or `📝 本周复盘`.
9. Update in place:
   - If a weekly review section already exists in the target week block, update that section instead of creating a second one.
   - Insert the weekly review at week-block top level, after the weekly goal sections and before the first day heading.
   - Match the heading depth used by sibling week-level sections and day headings. Do not nest the review under `## 个人` or any category subsection.
   - For inserting a new review section, use `obsidian append path="..." content="..." silent`. For patching an existing section, use the Edit tool directly on the vault file.
10. Analyze progress using the counting rules in the reference file. Prefer parent-task counts when parent tasks own child checkboxes.
11. Produce a concise summary with milestones, risks, and next-week adjustments. Prefer insight over task-by-task narration.

## Output

- **In chat (Phase 2)**: quarterly OKR progress table per Objective, this week's progress mapping, remaining time analysis, priority-ranked task recommendations (P0/P1/defer), risks and blockers.
- **In file (Phase 3)**: preserve the local naming and tone instead of forcing a new review title. Write the weekly review section only after user confirmation.

## Guardrails

- If Obsidian is not running, fall back to reading vault files directly with the Read tool.
- Support non-standard week spans such as holiday blocks. Do not assume every week covers exactly seven days.
- Keep the edit inside the target week block and before the next week heading.
- Ignore malformed checklist lines and explanatory bullets without checkboxes.
- If more than one week heading could match, prefer the heading explicitly named by the user or the one containing today's date. If ambiguity remains, explain it before editing.
- **Never write to the file before showing the progress analysis in chat and getting user confirmation.**
