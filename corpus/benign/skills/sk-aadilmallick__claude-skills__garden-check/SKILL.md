---
name: garden-check
description: Audits a Claude Code setup read-only and reports what has rotted, including dead file references, rules whose paths match nothing, orphaned memory entries, and duplicated instructions. Use for "garden check", "weed the garden", "audit my claude setup", or when a rule or skill never seems to fire.
---

<objective>
Walk the user's Claude Code setup and report what is dead, stale, or too heavy. Report only. Never edit, never delete.
</objective>

<boundaries>
READ-ONLY. MUST NOT create, edit, move, or delete any file in the setup being audited.
Finding and fixing are separate jobs. A tool that fixes what it finds cannot be trusted to report honestly, and a user who cannot see the diff cannot learn their own setup.
When the user asks for fixes, show the change and let them apply it, or ask before touching anything.
</boundaries>

<scope>
Ask the user which garden to check if it is ambiguous. Default to both:

Global setup:
- `~/.claude/CLAUDE.md`
- `~/.claude/rules/` (all files, including subfolders)
- `~/.claude/skills/` (folder names and frontmatter only)

Project setup, for the current working directory and any nested folder that has one:
- `CLAUDE.md` at every level
- `.claude/rules/`
- `.claude/skills/`

Memory:
- `~/.claude/projects/<project-hash>/memory/MEMORY.md` and the memory files it indexes

Follow symlinks. A setup symlinked into a private git repo is normal, not a finding.
</scope>

<checks>
Run all eight. Each finding names the file, the line, and one concrete fix.

1. WEIGHT - Count the lines in each CLAUDE.md. Flag anything past 50. There is no official limit and nothing truncates; 50 is a working target that keeps the file honest, so report it as "past target", never as "over the limit". This file is re-read every session, so every line is rent. For each flagged file, name the two or three sections most worth moving into a rule.

   For SKILL.md files the documented guidance is different and real: keep them under 500 lines, and move detail into linked supporting files past that.

2. DEAD PATHS - Extract every file path, folder path, and command name mentioned in CLAUDE.md and in the rules. Check each one exists. A path that no longer resolves is an instruction pointing at nothing, and Claude will follow it anyway.

3. BROKEN FRONT MATTER - Every file in `rules/` and every SKILL.md must open with valid front matter: three dashes, the fields, three dashes. Flag any file missing it or with malformed YAML. A rule with broken front matter is invisible.

   Parse the YAML, do not eyeball it. The common break is a colon followed by a space inside an unquoted value, as in `description: Reports what rotted: dead paths`. YAML reads the second colon as a new key and the file fails to parse. Fix by rewording to drop the inner colon, or by quoting the whole value.

4. RULES THAT NEVER FIRE - For each rule carrying a `paths:` field, check the pattern matches at least one file that actually exists. A pattern matching nothing is a rule the user believes is active and which has never once loaded. This is the highest-value check: it fails silently.

5. RULES THAT ALWAYS FIRE - List every rule with no `paths:` field. These load on every single session. For each one ask: is this genuinely universal, or is it a rule that wants a `paths:` field? Report them with their line counts so the user sees the standing cost.

6. ORPHANED MEMORY - Every line in MEMORY.md points to a memory file. Check each file exists. Then check the reverse: memory files on disk that MEMORY.md does not index are invisible to recall. Flag both directions.

7. UNLINKED SKILL FILES - Inside each skill folder, list every file other than SKILL.md. Check the SKILL.md body links to it. A supporting file nothing links to never loads: Claude does not discover skill files on its own. Flag it as invisible, not as unused.

8. DUPLICATES - The same instruction stated in two places: global CLAUDE.md and project CLAUDE.md, or CLAUDE.md and a rule, or two rules. Report each pair and say which copy should survive. This is the most common finding and the most expensive, because contradictory duplicates make behavior unpredictable.
</checks>

<output>
Report grouped into three sections, in this order. Skip any section with no findings and say so.

DEAD - points at something that does not exist. Fix or delete.
STALE - real, but describes finished work or a setup that has moved on.
TOO HEAVY - real and current, but costs more than it returns.

One line per finding:

`<file>:<line>` - what is wrong → the fix

End with a two-line summary: total findings by group, and the single change that would improve the setup most. Name that one change explicitly. A list of thirty findings with no priority is a list nobody acts on.

If the setup is clean, say so plainly and name the one thing worth watching as it grows. Do not invent findings to fill the report.
</output>

<delegation>
Optional. Skip this on a small setup, where one pass costs almost nothing. It earns its keep once the scan spans many projects, a large rules folder, or dozens of skills, because reading all those files is where the tokens go.

Split the work by what it demands, following the `efficient-delegation` skill:

DELEGATE the scanning to cheaper sub-agents, one per area (global CLAUDE.md and rules, project CLAUDE.md files, memory, skill folders). Checks 1, 2, 3, 4, 6 and 7 are mechanical: does this path exist, does this glob match anything, does this YAML parse, is this file linked. Each sub-agent returns its findings as structured data, nothing more.

KEEP for the main model: check 5, which is a judgment call about whether a rule deserves to load every session; check 8, which needs every area in one head at once to spot the same instruction written twice; and the final priority ranking. The ranking is what makes the report actionable rather than a list, so never hand it off.

Verify before reporting. A sub-agent claiming a path is dead is a lead, not a fact. Re-check any finding before it reaches the user.
</delegation>

<success_criteria>
- Every finding names a real file and a real line the user can open
- No file was modified
- Findings are grouped dead / stale / too heavy, never one flat list
- The report ends with one prioritized change, not a backlog
- A non-coder can read any line of the report and know what to do next
</success_criteria>