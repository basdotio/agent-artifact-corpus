# Auditing your always-loaded surface

On-demand reference for the no-false-flags skill. How to take stock of everything
that loads into every session and shrink it to what earns its place.

## Why

The always-loaded surface — global rules, any always-on project memory, and the
root `CLAUDE.md` — is paid by every session. It grows silently: rules get added,
rarely removed. An audit finds what no longer earns its slot and, in doing so,
cuts the surface a safety check can react to on legitimate work.

## The audit

1. **List everything that always loads.** The global rules directory, the root
   `CLAUDE.md`, the output of `SessionStart` hooks (a saved summary of the last
   session reloads its stopped text after `/clear`), any always-on memory, and **memory indexes and summaries** (such as
   `MEMORY.md`). An index line is paid in every session even when the file it
   points to loads on demand, so one alarming summary line is enough to trip the
   check on every first message. Also count the **project docs read at every
   start** (`Brain/`, plan documents) and the **kickoff prompt** the user pastes
   each session. The kickoff prompt should open with one line: what the project
   is, whose it is, what it is for (context in the request itself is what was
   measured to help).
2. **Measure the size.** A rough line/token count per file and the total. If the
   total is large, that is the budget spent on every task, relevant or not.
3. **Run the four checklist questions on each file** (short? cross-cutting?
   explicit intent? right layer?). Flag any that fail. See
   [../examples/checklist.md](../examples/checklist.md).
4. **Flag three problems specifically:**
   - **Overlap** — two files covering the same thing. Merge them; one owner per
     topic.
   - **Stale** — refers to things that no longer exist. Delete or update.
   - **Accidentally global** — only matters in one project or one domain. Demote
     to `references/` or to that project's memory.
   - **Sensitive / dual-use always loaded** — specialized-vocabulary material
     sitting in the always-loaded layer. This is the surface that most often
     causes false positives on capable models. Demote it to `references/`.
5. **Propose, do not apply silently.** For each flagged file give a verdict:
   keep / shorten / demote to `references/` / move to project memory / turn into a
   hook or permission / delete.

## Measure without dumping, edit without re-exposing

The surface you are auditing is the surface that trips the check. Reading it into
the conversation re-injects it, and the session can get stopped in the middle of
the cleanup.

- **Measure:** `grep -il <term> <files>` lists the files that match, `grep -c`
  counts matching lines per file. Names and counts only; do not print the lines.
- **Locate:** `grep -n <term> <file> | cut -d: -f1` prints line numbers only (plain
  `grep -n` prints the lines too). Show the user the file name and line number, not
  the line.
- **Edit:** Edit needs the file read first, so Read only that line (`offset` on it,
  `limit` 1), then replace it with Edit, written by its purpose (see
  [framing-intent.md](framing-intent.md)). Do not Read the whole file or paste the
  block around it.
- **Verify:** the same `grep -c` now returns 0 for that file.

## Output

A short list: `file -> verdict -> where it should go`. Then move them following
[demotion.md](demotion.md).

## Cadence

Run it when the always-loaded surface feels heavy, when sessions start flagging
legitimate work, or periodically. It is cheaper than letting the surface rot.
