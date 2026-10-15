---
name: inline-comments
description: Copilot-style "comment to change" workflow. The user leaves `@claude <instruction>` comments in their code (or `@claude? <question>` to ask without editing); this skill finds every marker, makes one small edit per instruction, and removes each marker as it is handled, so each change can be reviewed on its own. Use when the user says "do my comments", "apply the @claude comments", "address my inline notes", "handle the markers", or mentions having left @claude comments in files.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/find_markers.py *)
---

# Inline comments

The user has written instructions directly in their code as comments. Your job is to
carry each one out as a separate, minimal, reviewable edit.

## 1. Find the markers — once

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/find_markers.py --json [PATH ...]
```

- Pass the files or directories the user named. With no paths it scans every file git
  would track under the current directory (gitignored files skipped).
- An explicitly named file is scanned even if it is untracked or gitignored.
- Each output line is one marker: `path`, `line`, `kind` (`edit` | `question`),
  `instruction`, `needs_clarification`, and `removal` (how to delete the marker).

Run it **once** at the start and work from that list. Do not rescan mid-run: that would
pick up markers you already handled or deliberately left in place.

If the scan finds nothing, say so and stop. Do not go looking for other kinds of TODOs.

## 2. Handle each `edit` marker

For each marker, in file order:

1. Read enough of the surrounding code to understand the instruction.
2. Make the **smallest edit that satisfies it**, as its own Edit call, and remove the
   marker in that same edit, so the code change and marker removal are reviewed together.
   Separate edits give the IDE the best chance of showing one change per marker, but the
   diff viewer decides how hunks are grouped — don't promise the user one hunk each.
3. Remove the marker exactly as `removal` says:
   - `lines` — delete lines `start`..`end` (a standalone marker comment).
   - `span` — on line `line`, delete only `text` (a trailing `// @claude …` after code, or
     a marker inside a larger block comment). **Leave the code on that line intact.**
4. Don't touch unrelated code, don't reformat, and don't "improve" anything nearby that
   the instruction didn't ask for. **Don't create new files** (tests, notes, helpers)
   unless a marker asks for one: every change should trace back to a marker the user can
   review. If you want to sanity-check an edit, do it without leaving files behind.

If an instruction needs changes across several files, still treat it as one marker: make
the edits, then remove the marker last.

**Skip and report instead of guessing** when `needs_clarification` is true (empty
instruction), when the instruction is ambiguous, or when it conflicts with another
marker. Leave such markers untouched and ask about them in the summary.

## 3. Handle each `question` marker (`@claude?`)

Read-only. Answer in chat with file and line. **Do not edit the file and do not remove the
marker** — the user removes it when they're satisfied with the answer.

## 4. Summarise — always, as your final message

End with one line per marker found in step 1, in file order, and include the full
answer to every question marker. Do this even if you also report other things.

    src/api.ts:42  done      — made fetchUser async
    src/api.ts:57  answered  — yes, the cache is per-request (see below)
    src/db.py:12   skipped   — "fix this": fix what? the query or the retry?

## Limits

The scanner only reads comments in known languages (C-family, JS/TS, Go, Rust, Python,
shell/YAML/TOML, Terraform/HCL, PHP, SQL, Lua, Haskell line comments, CSS, HTML/XML).
Markdown and plain text are never scanned. It is a lightweight tokenizer, not a parser:
heredocs, raw strings with custom delimiters, and nested template literals can confuse
it. If a reported marker looks like it is inside a string, skip it and say so. See
[references/limits.md](references/limits.md).
