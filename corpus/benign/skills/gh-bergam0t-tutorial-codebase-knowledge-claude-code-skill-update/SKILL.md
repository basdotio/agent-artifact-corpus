---
name: update
description: Bring an existing generated codebase tutorial up to date after the code has changed. Compares the tutorial's generation record with the current source, then regenerates and re-checks only the chapters whose source files changed, instead of rebuilding everything. Use when a tutorial made by /codebase-tutorial:write may be out of date, or to set up a CI freshness check.
argument-hint: "[target] [tutorial=<tutorial folder>] [dry_run] [critique=on|off] [ci=install] [keep_work]"
---

# Codebase Tutorial: update (orchestrator)

You refresh a tutorial that `/codebase-tutorial:write` generated earlier. You do not rebuild it. You find which chapters depend on code that changed, ask the same subagents to *revise* just those chapters, re-check them, and update the record. A full run is only recommended when the structure of the project changed.

Pipeline: **locate record → drift check → (dry run stops here) → update outline → revise affected chapters in parallel → reassemble index, glossary and footer → scoped critique → review & render → refresh record**.

This skill reuses the `write` skill's agents, references and scripts. They live next to this skill, in `../write/` (in a plugin install: `${CLAUDE_PLUGIN_ROOT}/skills/write/`). Resolve every path to an **absolute path** before passing it to a subagent. Agent names are scoped as `codebase-tutorial:<name>` (see `write/SKILL.md`). Read `write/SKILL.md` now, and `write/references/config.md` for the record format. Where this file says "as in write step N", follow that step of `write/SKILL.md`.

## 1. Parse arguments and preflight

| Arg | Default | Notes |
|---|---|---|
| `target` | `.` | The repository the tutorial describes (a local path) |
| `tutorial` | auto | The tutorial folder containing `_generation.json` |
| `dry_run` | off | Report what is stale and what an update would cost, then stop |
| `critique` | the record's value | `on` or `off` |
| `ci` | none | `install`: offer to add the CI freshness workflow (step 11) |
| `keep_work` | off | Keep `_work/` |

Preflight, in one Bash call: `python --version` (or `python3`), `git --version`, `quarto --version`. Python 3.9+ is required; without Quarto, say that the render will be skipped. A cloned URL target is not supported: ask the user to clone the repo and re-run.

## 2. Locate the record

If `tutorial` wasn't given, search the target (depth ≤ 4, skipping `.git`, `node_modules`, `.venv`) for `_generation.json`. If there are several, ask which. If there is none, tell the user the tutorial was made before the record existed (plugin < 1.5.0) or isn't a generated one, and suggest `/codebase-tutorial:write` to create it (it will also write the record). Stop.

Read the record. It is `schema` 1 or 2; schema 1 lacks `source_base_url` and the stored `_evidence.yaml` and `_site-profile.yaml`, so fall back as the steps below say. From it, take the resolved options (`format`, `language`, `theme`, `extensions`, `audiences`, `mode`, `docs`, `section`, `args`) and **use those, not today's defaults**. Take the style blocks from `<tutorial>/_styles/`. They also fix each advanced audience's chapter structure (`Structure: tailored` or `shared`; blocks stored before the option existed say `compressed`, which means `shared`), and an update never changes it. If the record's plugin version is older than this plugin's, mention it (new features may not apply to the old pages).

## 3. Drift check

```
python <write>/scripts/check_drift.py --repo <target> --tutorial <tutorial> --fail-on never --json <tutorial>/_work/drift.json
```
(Create `<tutorial>/_work/` first.) Show the user the report. Then:

- **Nothing stale and no unmapped changes**: say the tutorial is up to date, remove `_work/`, and stop.
- **`dry_run`**: report the stale chapters per audience and the number of agents an update would run (writers = stale chapters × audiences, plus the scoped critics and reviewers), then stop.
- **Only unmapped changes** (files that no chapter cites): they may be a new component the tutorial doesn't cover, or just noise (small helpers, config). Continue to step 4, where the analyst judges.
- If the drift report says the recorded commit is unknown to this clone (shallow clone, or rewritten history), compare by file hashes only and say so.

## 4. Update the outline

Spawn one `tutorial-analyst` in **update mode**: the target; the absolute paths to `<tutorial>/_outline.yaml` (as `previous_outline`), `outline-schema.md`, and the output path `<tutorial>/_work/outline.yaml`; `changed_files` (stale files, deleted files and unmapped changes, from `drift.json`); and the usual `language`, `project_name`, `max_abstractions`, the audience summary and the `focus` from the record's `args`.

Validate the result with the rules in write step 5. Then compare it with the previous outline:

- **Same abstraction ids, names, filenames and order** (only descriptions, files, symbols, relationships and so on differ): a *content* update. Continue.
- **Abstractions added or removed, or the order changed**: this is a *structural* change, and renumbering would rename every file and break links. Stop. Show the analyst's `update_notes`, and recommend a full `/codebase-tutorial:write` run (the record's options will be a good starting point). Do not continue unless the user explicitly asks.

If any audience is advanced or a stakeholder preset, also:
- refresh the evidence (write step 5b) into `<tutorial>/_work/evidence.yaml`. If `<tutorial>/_evidence.yaml` exists (schema 2 records and later), spawn `tutorial-evidence-gatherer` in **update mode**: `previous_evidence` = that file, plus the updated outline and the `changed_files` from `drift.json`. It re-gathers only the abstractions whose files changed, and refreshes the repo-wide and GitHub parts. If there is no stored copy (a schema 1 record), run the full step 5b.
- for stakeholder audiences, spawn `tutorial-plain-planner` in **update mode** (`previous_plain_outline` = `<tutorial>/_plain-outline.yaml`, output `_work/plain-outline.yaml`), and validate as in write step 5c. If the page set changed, treat it as structural.

## 5. Decide what to rewrite

A chapter (in every chapter-based audience) is **affected** if its drift status is `stale`, **or** its outline entry changed in step 4 (files, key_symbols, description, introduces). A stakeholder page is affected if it's stale, or if its `uses` references a plain-outline item that changed. The `briefing` page is affected whenever any other page of its audience is, and is rewritten **last**, after those pages. With `learning` in the record's `args`, a chapter's self-test or exercise is revised along with the chapter, and the reading paths and first-contribution list are regenerated with the overview.

Also note the **neighbours**: chapters that have a relationship with an affected abstraction but are not themselves affected. They aren't rewritten, but the accuracy critic re-checks them in step 8, because their prose may describe the changed behaviour.

Tell the user the affected list and the neighbours before spawning anything. If more than half of the chapters are affected, say so and suggest a full run would cost about the same, but continue unless the user prefers otherwise.

## 6. Revise the affected chapters (parallel)

Reconstruct `<tutorial>/_work/extensions.md` as in write step 2c, using the record's extension list, and **without reinstalling** extensions that are already in `_extensions/`. Copy the stored style blocks to `<tutorial>/_work/style[-<slug>].md`.

Spawn one writer per affected (audience × chapter or page), all in a single message (batches of about 12 for multi-audience). Use `tutorial-chapter-writer` for chapters and `tutorial-plain-writer` for stakeholder pages. Each brief is the usual write step 6 brief, plus:

- `previous_version`: the absolute path of the existing page (the same path as the output)
- `changes`: the changed source files that matter to this page with their status, and the command to see the change: `git -C <target> diff <recorded commit> -- <path>`. The writer can run it.
- the **updated** outline entry and chapter list (filenames and xrefs are unchanged)

Include `learning` (with `learning.md`) when the record says so. For the briefing, also include the finished pages' paths and the formats from the record's `args.briefing`; re-render the print formats afterwards (book: explicitly, as `stakeholder.md` describes).

Remind them it's **revision mode**: keep what is still true, change only what the code requires, re-copy every verbatim snippet, don't rename anything. Writers write only their own file.

After they return, confirm every file still exists. If `include-code-files` is in use, run `check_snippets.py --restamp --file <page>` on the rewritten pages only, so their drift hashes match the new code. Never restamp pages you didn't rewrite.

## 7. Reassemble

- `index.qmd`: regenerate it as in write step 7 if the outline `summary`, the relationships, the one-line summaries or the evidence-based "Known issues" callout changed. Otherwise leave it.
- `glossary.qmd`: for each affected chapter's `introduces` terms, re-read the chapter and refresh the definition. Leave other entries alone. Stakeholder glossaries come from the updated `plain-outline.yaml`.
- **Footer**: run `write_record.py info` (write step 2) for the new commit, and replace the "Generated from commit" line in `_quarto.yml` (or the attribution line in `index.qmd` in integration mode). Make that one-line change with Edit; leave the rest of `_quarto.yml` alone.
- Multi-audience: re-run `add_audience_switcher.py` as in `multi-audience.md` (it's idempotent).
- Integration mode: never edit the site's `_quarto.yml`.

## 8. Scoped critique

Skip if `critique=off`. Otherwise follow write step 8 (per audience in multi-audience mode; stakeholder rules for stakeholder audiences), with two differences:
- add `only: <the rewritten pages>` to the clarity and code critics' briefs
- give the accuracy critic `only:` the rewritten pages **and the neighbours**

## 9. Review & render

As in write step 9: one `tutorial-reviewer` (per audience in multi-audience mode, then render once yourself). Tell it this is an **update**: it should apply the findings, run both checkers over the whole tutorial, and render. Don't ask it to restyle chapters you didn't touch. Resume it once for unresolved must-fix findings, then stop.

## 10. Refresh the record

Re-run `write_record.py write` (as in write step 7, with the updated outline, plain-outline, evidence and, in integration mode, site-profile copies, and the `_styles` dir), so the record's commit, hashes and timestamp describe the tutorial as it now is. Carry `source_base_url` over from the old record unless the commit changed and the new one is a pushed permalink (write step 2). Re-writing a schema 1 record upgrades it to schema 2. Then run:

```
python <write>/scripts/check_drift.py --repo <target> --tutorial <tutorial>
```
It should report no stale chapters. If one is still stale, tell the user which and why.

Delete `<tutorial>/_work/` unless `keep_work` was set.

## 11. Finish

Report:
- which chapters and pages were rewritten (per audience), and which neighbours were re-checked
- the critics' verdicts, the reviewer's changes, and any unresolved must-fix findings
- whether the render succeeded
- the commit the tutorial now describes
- `git status` on the tutorial folder, so the user can review the diff before committing. **Never commit or push for the user.**

**CI**: if the repo has no `.github/workflows/tutorial-freshness.yml`, offer once to add it (or, with `ci=install`, ask for confirmation, since it writes into their repo). Copy `templates/tutorial-freshness.yml` from this skill, setting `TUTORIAL_DIR` to the tutorial folder relative to the repo root. Explain what it does: it runs `check_tutorial.py` (freshness, snippet fidelity and links) with no AI and no keys, on pull requests, on pushes to the main branch and weekly, and it only fails on stale chapters if `STRICT` is set to `"true"`. The template pins `PLUGIN_REF` to a plugin release tag; tell them to bump it when they upgrade the plugin.
