---
name: session-init
description: Initialize or refresh a research/code project at the start of a session. Generates README.md documenting the directory tree with file counts, seeds CLAUDE.md with binding project guardrails (never delete data/programs, use ./legacy/, copy-not-move on reorgs, stay inside the project root), and reminds Claude to prepend a dated session-log entry before wrapping up (CLAUDE.md keeps only the 8 newest entries; older ones roll into SESSIONLOG.md). Trigger at the start of every session and whenever the user says "init", "session init", "let's start", "kickoff", "starting a new session", "/session-init", or first enters a project that lacks orientation files. Also trigger any time you enter a project that already has a CLAUDE.md — its rules are binding and must be read before doing anything else.
---

# session-init

Run this at the top of every working session in a project — whether the project is brand new or one you've worked in before. The point is to make sure (a) the user's hard rules are loaded, (b) the current directory state is documented, and (c) the end-of-session log gets updated when the conversation wraps.

## The four things to do

1. **Read `CLAUDE.md` first** (if it exists).
2. **Generate or refresh `README.md`** at the project root.
3. **Create `CLAUDE.md`** with the default seed (only if it doesn't exist).
4. **Before the session ends**, prepend a dated entry to CLAUDE.md's session log (capping it at 8 entries — overflow goes to `SESSIONLOG.md`).

Do steps 1–3 right away when the skill triggers. Step 4 happens later, when the conversation is wrapping up.

## Step 1 — Read CLAUDE.md first

If a `CLAUDE.md` sits at the project root, read it before doing anything else in the project. It contains hard rules the user has accumulated over time, and those rules override your defaults for this project.

Re-consult CLAUDE.md whenever the conversation hits a decision point that touches **data**, **programs**, **directory layout**, or **scope** (i.e. whether to touch something outside the project root). The user wants you in the habit of treating it as a live reference, not a one-time read.

## Step 2 — Generate or refresh README.md

`README.md` is a snapshot of "what's in here right now." Regenerate it every time the skill runs — the directory drifts between sessions, and a future reader (the user, or a future Claude with no memory) needs the current picture, not last month's.

### Gather the data

Use `Glob` for filename patterns and `Get-ChildItem -Recurse` (PowerShell) or `find` (Bash) for counts. Group files by extension. Skip `./legacy/` when recursing — that folder is the archive bucket; mention it as a single line with its total file count, not a full tree.

### Use this template

```markdown
# <project name>

<One paragraph: what this project is for. Infer from filenames, manuscript drafts, master do-files, READMEs, anything visible.>

## Directory tree

\`\`\`
<project>/
├── data/        — <one-line description>  (N files)
├── do/          — <one-line description>  (N files)
├── output/      — <one-line description>  (N files)
└── legacy/      — archived prior versions  (N files)
\`\`\`

## File counts by extension

| Extension | Count |
|-----------|-------|
| .do       | N     |
| .dta      | N     |
| .R        | N     |
| .tex      | N     |

## Key files

- `path/to/master.do` — entry point that runs the full pipeline
- `path/to/manuscript.tex` — current draft
- ...

## Notes for the next visitor

- Data sources, version conventions, naming patterns, dependencies — anything that isn't obvious from a file listing.
```

Tailor depth to project size. One page is fine for a small project; longer is fine for a sprawling one, but keep it scannable. If the project is empty, say so plainly — don't pad.

## Step 3 — Create CLAUDE.md (only if missing)

**Do not overwrite an existing CLAUDE.md.** It accumulates rules over time, and overwriting would erase the user's history.

If it's missing, create it with this seed content. Replace `<project-name>` with the actual current directory name (e.g., `cfprobit`):

```markdown
# CLAUDE.md — Read this first, every session

> These rules are binding for the **<project-name>** project. Re-read whenever a decision touches data, programs, directory layout, or scope. New rules will be appended below as the project evolves.

## Hard rules

1. **Never DELETE data.** Move it to `./legacy/` instead.
2. **Never DELETE a program** (`.do`, `.py`, `.R`, `.ado`, `.m`, etc.). Move it to `./legacy/`.
3. **Reorganization is COPY, not MOVE.** When restructuring directories, COPY programs into their new locations — the legacy copy stays put.
4. **Never go UP and OUT of `<project-name>`.** The project is rooted here. Do not read, write, list, or otherwise touch anything outside this directory tree without explicit user permission for that specific path.

## Session log

<!--
Format — newest entry on top:

### YYYY-MM-DD
**Changed:**
- <bullet>
**Next:**
- <bullet>
-->
```

## Step 4 — Update the session log before wrapping up

When the conversation is winding down — the user signals they're done, says goodbye, or the active task is complete with nothing queued — prepend a new entry to the **Session log** section of `CLAUDE.md`:

```markdown
### 2026-05-27

**Changed:**
- <terse bullet about each meaningful change>

**Next:**
- <what to pick up first next session>
```

Use the actual current date (today's date from your system context). Keep entries terse — bullets, not prose. If genuinely nothing of substance happened, write `- (no substantive changes)` rather than skipping the entry; that absence is itself useful information for the next session.

Prepend, don't append — newest entry on top so the next session sees the most recent context first.

### Cap the log at 8 entries — archive the rest to SESSIONLOG.md

CLAUDE.md is loaded into context every session, so a log that grows without bound both wastes tokens and buries the hard rules — the part that must never be skimmed past. Keep CLAUDE.md short and punchy:

- After prepending the new entry, count the entries in the **Session log** section. If there are more than **8**, move the oldest entries beyond the 8 newest into `SESSIONLOG.md` at the project root.
- `SESSIONLOG.md` is the full archive, same format, newest on top. Create it the first time an entry overflows, with the header:

```markdown
# Session log archive — <project-name>

Older session-log entries rolled out of CLAUDE.md (which keeps only the 8 most recent). Newest on top.
```

- When archiving, insert the overflow entries at the **top** of the archive's entry list (just below the header) so the whole file stays newest-first.
- Leave a one-line pointer in CLAUDE.md at the bottom of the Session log section: `> Older entries: see SESSIONLOG.md` (add it once; don't duplicate it).
- Never trim or rewrite archived entries — SESSIONLOG.md is append-only history. Only read it when you actually need older context (e.g., "when did we switch datasets?"); it is *not* part of the every-session read.

## Adding new rules mid-session

When the user introduces a new rule ("from now on, X", "stop doing Y", "always Z"), append it to the **Hard rules** section of `CLAUDE.md` immediately — don't wait for end-of-session. Include a brief **Why:** if the user gave a reason, so future-you can judge edge cases.

Number it as the next rule in the list. Example:

```markdown
5. **Always run `quietly` before regressions to suppress noise.** Why: user finds full output distracting in long do-files.
```

## Enforcing rule 4 (the "never go up" rule)

The harness will not stop you from reading `C:\Users\...\SomeOtherProject\file.dta`. You enforce this yourself. Before any `Read`, `Write`, `Edit`, `Glob`, `Grep`, or shell call that uses an absolute path or `..`, check that the target sits inside the project root. If you need something outside, stop and ask the user — name the specific path and why.

The one exception: your own memory directory under `~/.claude/projects/.../memory/` is session infrastructure, not project content, and is fine to touch.

## When the project is empty or near-empty

If you're triggering on a fresh directory (no files yet), README.md should say so directly:

```markdown
# <project name>

Empty project — no files yet. CLAUDE.md is seeded with the default guardrails.
```

Still create CLAUDE.md with the seed rules so the guardrails are in place from day one.
