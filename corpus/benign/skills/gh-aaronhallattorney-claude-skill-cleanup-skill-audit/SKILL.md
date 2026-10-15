---
name: skill-audit
description: 'Consistency audit of one skill''s instruction files: builds the load graph, then finds contradictions between SKILL.md and its supporting files, directives no load path reaches, and stale pointers (renamed paths, skills, flags, headings). A fresh-context reader writes the report; a second pass re-verifies each finding and fixes what is clear. Use for "/skill-audit <skill>", "audit this skill", or when a skill that has been edited many times starts behaving inconsistently. Not for writing a new skill or making one known fix.'
argument-hint: <skill> [report | fix]
---

# Skill Audit

Skills drift. Each edit is made with one file open, so over time two files of the same skill come to disagree, a rule ends up in a file nothing tells Claude to read, and a pointer names a path or skill that was since renamed. A per-file review cannot see any of these. This skill reads the whole skill at once, as one system.

The audit has two passes, run by two readers who never share a context:

1. **Read.** A subagent with a fresh context reads the skill and writes a report. It fixes nothing.
2. **Fix.** This session re-verifies every finding against the files, then fixes what is clear and asks about what is not.

A finding is a lead until the fix pass confirms it. A reader who fixes its own findings tends to trust them; a second reader who must re-check each one catches the false positives.

## Arguments

- `<skill>`: the skill's folder name. Look first for `.claude/skills/<skill>/SKILL.md` in the current project, then `~/.claude/skills/<skill>/SKILL.md`. If neither exists, list the skills you can see and stop. Skills installed from a plugin are out of scope: their updates would overwrite any fix, so send findings to the plugin's author.
- `report`: run the read pass only.
- `fix`: run the fix pass only, on the newest open report for `<skill>`.
- No second word: run the read pass, then the fix pass if the report has findings.

**Report location:** `.claude/skill-audits/<skill>-<YYYY-MM-DD>.md` beside the `skills/` folder the skill lives in (the project's `.claude/` or `~/.claude/`). A report is open until it carries a `## Disposition` section.

## Read Pass

1. Resolve the skill folder and the report path. If today's report already exists with a `## Findings` section and no `## Disposition` heading, and the argument is not `report`, skip to the fix pass.
2. Read `audit-prompt.md` (in this skill's folder). Replace `{skill}`, `{skill_dir}`, `{report_path}`, and `{project_root}` with their values. `{project_root}` is the current project root for a project skill, or `~/.claude/` for a user-level skill.
3. Launch one subagent (Agent tool, general-purpose type) with the rendered prompt as its whole task. Pass it nothing from this conversation; its independence is the point.
4. When it returns, confirm the report file exists and has `## Findings`. If the subagent failed or wrote nothing, say so and stop.
5. If the report says "None." under Findings, tell the user the skill is clean and stop. If the argument was `report`, summarize the findings in a few lines and stop.

## Fix Pass

Read and follow `dispose.md` (in this skill's folder).
