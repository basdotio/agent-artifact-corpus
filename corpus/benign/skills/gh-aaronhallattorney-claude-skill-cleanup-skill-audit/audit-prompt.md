## Task

Audit the `{skill}` skill's instruction files for internal consistency. Find:

- (a) contradictions between `SKILL.md` and its supporting files, or between any two files the skill loads;
- (b) directives that no load path reaches;
- (c) stale pointers: paths, skill names, script flags, section headings, and step numbers that no longer exist.

Write one report. Fix nothing.

## Context

- Skill folder: `{skill_dir}`. Project root: `{project_root}`.
- "Reachable" means one of three things: a step in `SKILL.md`; a file that another reachable file tells the reader to read; or text that a script inserts into a prompt.
- A grep hit, a name match, or a count is a lead, never a finding. Before you call anything a contradiction, read both sides in context. Quote each side verbatim with its `path:line`.

## Files

- **Read:**
  - every file in the skill folder;
  - each script in the project that loads or names the skill's files (search the project for the skill folder's name);
  - each file outside the folder that a reachable file tells the reader to read (a `CLAUDE.md`, a rules file, a shared helper).
- **Write:** `{report_path}` only.

## Steps

1. **Build the load graph.** From `SKILL.md`'s steps and any scripts, list which files are loaded, by whom, and when. Name every file in the folder that sits outside the graph.
2. **Collect the directives.** Read every reachable file in full. Note each directive that states a rule or a default (must, never, always, only, before, after, default, if no X then Y) with its `path:line`.
3. **Compare across files.** Look for the same decision with a different rule. Apply the three contradiction checks below to every subordinate file and the file it defers to.
4. **Verify every named artifact,** whether or not it looks suspect. That includes each path, script, flag, skill name, heading, and step number that a reachable file names. Check them with `ls`, `grep`, or `--help`.
5. **Date both sides of each contradiction.** If the project is a git repository, run `git log -1 --format=%cs -- <file>` for each file. Otherwise write "undated." Never assume the main file is the correct side. A fix is often made in the supporting file where the problem showed up, so the supporting file is frequently the newer and deliberate side.
6. **Write the report** (§ Report).

## Contradiction Checks

The following three checks are quoted from skill-stocktake by shimo4228 (https://github.com/shimo4228/skill-stocktake, `skills/skill-stocktake/SKILL.md`, MIT License; see `THIRD-PARTY-NOTICES.md` in the claude-skill-cleanup repository). In skill-stocktake they apply to a cluster labelled `DOCUMENTED_LAYERING`, meaning one file defers to another. Here they apply to any subordinate file and the canon it defers to.

> - **Does the subordinate file comply with the canon it defers to?** Read the canonical file's rules and look for the subordinate stating a *different* rule for the same decision — especially **defaults** ("if the user gives no X, use Y"), which contradict quietly because they only fire in the unspecified case.
> - **Is the defer bidirectional?** A one-directional defer (canon claims the subordinate, subordinate says nothing) means the subordinate **loads alone without its correction** whenever its own description wins the trigger. A broad description on a subordinate file turns a latent contradiction into an active one.
> - **Do the two files presuppose the same author / project model?** Imported skills (`origin` = an external repo) carry their author's premises. A conflict of premises reads as a normal-looking instruction and survives every per-file check.

Judge provenance here from what is on disk: a `LICENSE` or notices file naming another author, or a git remote that is not the user's own.

## Report

Use three sections: `## Load graph`, `## Findings`, and `## Not findings`.

- **Findings:** numbered and ordered by severity. Each entry gives:
  - the type: contradiction, one-directional defer, premise conflict, unreachable directive, or stale pointer;
  - a severity and a confidence, each high, medium, or low;
  - both quotes with their `path:line`;
  - for a contradiction, each side's last-change date;
  - why it matters, in one sentence;
  - the smallest fix, in one sentence.

  Report every finding you believe is real, whatever its severity. The fix pass does the filtering.
- **Not findings:** each candidate you examined and cleared, one line each.
- **Zero findings:** write `## Findings` followed by the line "None.", then end the report with `## Disposition (none required, 0 findings)`.

## Out of Scope

You may write only the report. Do not modify any skill, script, or other file. If you find yourself editing one, stop and write the problem into the report as a finding. Do not run the audited skill itself.
