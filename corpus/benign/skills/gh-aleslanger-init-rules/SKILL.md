---
name: init-rules
description: Initialize, audit, or improve the CURRENT repository's Claude Code rules (CLAUDE.md and .claude/rules/*.md) from verified repository evidence. Explicit invocation only via /init-rules.
disable-model-invocation: true
argument-hint: "[help | enforce | coordinator | herdr | <focus area>]"
---

# /init-rules: evidence-based project rules

You are creating, auditing, or improving the Claude Code configuration of the **current repository only**. Optional user focus: $ARGUMENTS

## Help mode

If the arguments are `help`, `--help`, `-h`, or `?`, output ONLY the help below, in the user's conversation language, and stop. Don't read, run, or write anything else.

```text
/init-rules: create, audit, or improve this repository's Claude Code rules
(CLAUDE.md + .claude/rules/*.md) from verified repository evidence.

Usage
  /init-rules                  analyze the repo; create the rules or audit/update existing ones
  /init-rules <focus area>     same, with extra attention to an area (e.g. "API", "migrations")
  /init-rules coordinator      also generate the coordinator model: the main agent doesn't write code;
                               it delegates, reviews (accept/return/reassign/discard/escalate),
                               merges, and supervises agent state
  /init-rules herdr            also generate Herdr (herdr.dev) rules, even without repo evidence of Herdr
  /init-rules enforce          after the rules, propose mechanical guardrails (permissions deny/ask,
                               a fast per-file lint/format feedback hook) and install only the ones
                               you confirm, merged into .claude/settings.json
  /init-rules help             show this help
  Arguments can be combined, e.g. /init-rules coordinator herdr API

Writes   only CLAUDE.md and .claude/rules/*.md of the current repo; with `enforce` and your
         per-item confirmation also .claude/settings*.json and .claude/hooks/
         (Claude Code asks you to approve writes to .claude/)
Never    global ~/.claude config, application code, unconfirmed settings/hooks, commits, pushes
Rules    built only from VERIFIED evidence; commands must exist in the repo; path-scoped where possible;
         include verification, surgical-change, failure-handling, security, architecture (boundaries,
         dependency direction, exemplars), performance (budgets/benchmarks when found, hot paths),
         code quality (coding standard, conventions, no duplicate code), verified language/library
         versions (no invented APIs, no newer syntax, no deprecated APIs), docs/comments kept in sync
         with changes, and orchestration rules where they apply, plus a Definition of Done
Rerun    safe and idempotent; an unchanged repo gives little or no diff
Report   findings, files changed, highest-impact rules, preserved/rewritten rules, unknowns, risks,
         mechanical-enforcement candidates, feedback-hook and workflow-recipe (project skill)
         proposals, exact validation performed
```

## 0. Scope and hard limits

- Write ONLY to the current project's files: `CLAUDE.md` (root or `.claude/CLAUDE.md`, whichever the project already uses; default root), and `.claude/rules/*.md`. The only exception is the conditional `AGENTS.md`/nested `CLAUDE.md` edit described below.
- NEVER modify `~/.claude/CLAUDE.md`, `~/.claude/rules/`, `~/.claude/settings*.json`, user skills, or any other global or user-level configuration.
- NEVER modify application source, tests, CI, manifests, or dependencies. NEVER commit, push, or change git state.
- Do NOT edit `.claude/settings*.json` or `.claude/hooks/` unless the arguments include `enforce` AND the user confirms each item, following `references/enforcement.md` (merge, never overwrite). Otherwise mechanical enforcement is only RECOMMENDED in the final report.
- Do NOT edit `AGENTS.md` or nested `CLAUDE.md` files unless they are clearly Claude config for this repo AND the change is needed to remove a conflict; if so, say so in the report.
- Determine the repository root first (`git rev-parse --show-toplevel`, else the working directory). If the working directory is your home directory or not a project, stop and ask.

## 1. Core philosophy (applies to analysis AND to the rules you write)

**Evidence over assumptions.** Repository evidence is the source of truth. Never invent commands, technologies, versions, architecture, deployment, test procedures, security mechanisms, production behavior, ownership, or operational requirements. Classify every finding as:
- **VERIFIED**: directly observed in executable config, manifests, CI, or code.
- **INFERRED**: plausible from evidence but not directly confirmed. Never state as fact in a rule.
- **UNKNOWN**: not established. Never becomes a rule. Goes to the report's Unknowns.

**Accuracy beats comprehensiveness.** A small, precise configuration beats a large, plausible-looking one. Every rule must change behavior; delete anything that would not.

Use these behaviors while doing the work. Add one to the generated rules only when repository evidence gives it a specific trigger, command, path, or recurring failure that future sessions would otherwise miss. Do not copy universal working advice into every repository:
- **Think before coding:** inspect the implementation, nearby context, callers/consumers, and relevant tests; understand expected behavior and blast radius before editing. The first plausible location is not proof the full change has been found.
- **Prefer simplicity:** smallest coherent solution; established repo patterns; no speculative abstractions, premature generalization, unnecessary dependencies, or hypothetical architecture.
- **Surgical changes:** every changed line traces to the task, a necessary supporting change, a correctness issue the task exposed, or required validation. No opportunistic refactors, unrelated formatting/renaming, dependency churn, or drive-by cleanup.
- **Own the outcome:** understand → implement → validate → investigate failures → fix introduced failures → completeness sweep → inspect final diff → report remaining uncertainty accurately. Editing files is never "done".
- **Never invent what doesn't exist:** no fabricated functions, methods, classes, modules, packages, config keys, CLI flags, env vars, files, endpoints, or library options. Anything used in code or cited in a report must first be confirmed to exist in the repo, in the installed or locked dependency version, or in that version's documentation. If its existence can't be confirmed, say so instead of guessing.
- **Version-correct code:** write code for the language, runtime, and dependency versions the repo actually targets. Use no syntax or API newer than the minimum supported version, and no deprecated API.
- **Verify before reporting:** distinguish implemented / statically checked / unit tested / integration tested / manually exercised / fully validated / unverified. Never claim tests pass, build succeeds, the app works, a bug is fixed, or a migration is safe unless that verification actually ran and succeeded. State exactly what remains unverified.
- **Condition → action → verification:** write rules as `WHEN <condition> → DO <action> → VERIFY <observable result>` wherever the shape fits. Never write "write clean code", "follow best practices", "be careful", "write secure code", or similar filler.

## 2. Workflow

Track these phases with a todo list. Do not skip phases; keep each one proportional to the repo's size.

### Phase A: Inventory existing agent configuration (always first)

Read, if present: root and nested `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md` (read-only; it is personal, never edit it), `AGENTS.md`, `.claude/rules/**`, `.claude/settings.json`, `.claude/settings.local.json` (note only; never copy values), `.claude/hooks/`, `.claude/skills/`, `.claude/agents/`, `.claude/workflows/`, `.cursorrules`, `.github/copilot-instructions.md`, and contributor/architecture docs (`CONTRIBUTING*`, `docs/architecture*`, ADRs).

Record what already exists. This decides whether this run is a **create** or an **audit/update** (idempotency, section 9).

### Phase B: Targeted repository discovery

Use cheap evidence first: `git ls-files | head`/counts, top-level tree, manifests, CI files, then targeted reads. Do not read the repository blindly. For large repos, you may delegate read-only discovery to an Explore subagent, using a smaller/faster model where the tool allows it, and keep only conclusions.

Establish everything listed in `references/discovery.md` (read it now; it lists structure, tooling, versions, deprecation tooling, architecture, performance, code-quality conventions, documentation, data, security, operations, and the evidence hierarchy). Label each item VERIFIED / INFERRED / UNKNOWN, and surface material conflicts between sources in the report instead of silently resolving them.

### Phase C: Canonical commands

Discover the repository-supported command for each applicable task (install, build, focused test, broader test, lint, format, typecheck, static analysis, dev runtime, code generation), following `references/discovery.md`. Never put an unverified command in CLAUDE.md. Never run installs, builds, migrations, deploys, or anything state-mutating without asking.

### Phase D: Risk analysis

Evaluate only risks actually relevant to this repo, with evidence, using the risk list in `references/discovery.md`.

### Phase E: Audit existing configuration (if any)

Never overwrite existing rules blindly. Classify every existing instruction as one of:
- **KEEP**: true, valuable, correctly scoped.
- **REWRITE**: valuable but vague, unactionable, or unobservable.
- **MOVE**: belongs in a path-scoped rule, or vice versa. Treat the move as complete only after the destination file was written and validated; otherwise KEEP the original instruction in its existing file.
- **DELETE**: obsolete, duplicate, contradicted by evidence, generic filler, or references nonexistent commands/paths.
- **ENFORCE MECHANICALLY**: a hard restriction that exists only as prose and whose violation is unacceptable.
- **UNKNOWN**: can't verify; keep unchanged and flag it, rather than delete it on a guess.

Look specifically for: obsolete facts, duplicates, conflicts, nonexistent commands, nonexistent paths, generic filler, wrong scope, and "hard restrictions" that are only prose. Preserve intentional project knowledge (team conventions, gotchas, decisions) even if you can't fully re-derive it, unless evidence contradicts it.

### Phase F: Design and write the configuration

**Architecture:** a compact root CLAUDE.md plus a few focused `.claude/rules/*.md`.

**CLAUDE.md**: only broadly needed, high-value, VERIFIED content:
- project purpose (one or two lines)
- non-obvious architecture boundaries, if they change how to edit the repo
- canonical commands that a future session needs (verified only)
- project-specific invariants, risks, and validation triggers
- a short repository-specific **Definition of Done** only when it adds requirements beyond the verified commands and rules (section 7)

Use the fewest lines that preserve those facts. For a small single-module repo, target at most 40 lines unless a specific risk needs more; do not pad to a minimum or add headings with no content. Exceed about 200 lines only with a stated reason. Before keeping a line, ask what realistic mistake it prevents and whether the same fact is already obvious from a nearby file or another rule. Not a handbook; omit file listings, obvious conventions, generic workflow reminders, and duplicate details. Put obsolete commands and nonexistent paths in the report, never in the generated configuration, even as a warning; a future agent may copy them despite the negation. Preserve exact source and output paths for generated files when that mapping matters. State a verified minimum runtime version in one line, without a catalogue of syntax examples.

**`.claude/rules/*.md`**: one focused concern per file. Create a file only when there is enough repository-specific content to justify it. Candidate names, used ONLY where justified: `verification.md`, `change-discipline.md`, `security.md`, `testing.md`, `architecture.md`, `database.md`, `api.md`, `generated-files.md`, `orchestration.md`, `performance.md`, `code-quality.md`. Fewer strong rules beat many weak ones. Avoid duplicating content between CLAUDE.md and rules files.

**Path scoping:** when a rule applies only to part of the repo (API, migrations, frontend, backend, infra, generated files, a package), scope it with the `paths` frontmatter this Claude Code version supports for `.claude/rules/*.md`:

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "migrations/**"
---
```

If a write to `.claude/rules/` is denied or blocked by a permission prompt, do NOT fold new path-specific rules into CLAUDE.md as a workaround. Keep every valid pre-existing rule in its original file until the replacement was actually written and validated; never leave a durable instruction missing because its proposed destination exists only in the report. Ask the user to approve the write; if that is impossible (headless run), leave CLAUDE.md compact. In the final report, give the exact ready-to-save content of **each** unwritten rule file in its own fenced `markdown` block, including complete `---` frontmatter, `paths` globs, and every rule. A summary or bullet list is insufficient. Validate each proposed glob against tracked files and say explicitly that the files were not written.

Rules without `paths` load always. Every glob MUST match at least one existing tracked file. Check with `git ls-files '<glob>'`, or `find` when the repo is not a git repo. Do not invent other frontmatter keys.

**Rule content requirements** (include each only where applicable to this repo):

Read `references/rule-catalog.md` now and evaluate each rule family that fits this repo: sweep verification, failure handling, validation-bypass protection, generated files, secrets, authN/authZ, data/concurrency, architecture, performance, code quality, versions/real APIs/deprecations, coding standard, conventions, no duplicate code, documentation, external calls, working method, orchestration, and Herdr. Include a rule only if it passes the quality gate below; a relevant family does not require output.

### Phase G: Rule quality gate

For every instruction, ask:
1. **True?** Backed by repository evidence, or genuinely universal agent behavior?
2. **Behavior-changing?** If removing it changes nothing, remove it.
3. **Actionable?** Does Claude know what to do?
4. **Observable?** Can compliance be checked?
5. **Scope?** Should it be path-scoped?
6. **Duplicated?** If so, consolidate.
7. **Filler?** If so, delete.
8. **Is prose enough?** If failure is unacceptable, flag it for mechanical enforcement (section 8).

### Phase H: Adversarial self-review

Run every scenario in `references/self-review.md` that applies to this repo, and fix the rules if any scenario slips through.

### Phase I: Validate the configuration

Using only capabilities that actually exist:
- Files exist at the discovered locations: `CLAUDE.md` (root or `.claude/`) and `.claude/rules/*.md`.
- Frontmatter parses as YAML and uses only `paths` (rules files). Check by inspection or a quick parse (e.g. `python3 -c 'import yaml,sys; ...'` if available; otherwise state that it was inspected manually).
- Every `paths` glob matches existing files (`git ls-files` / `find`).
- Every command in the config is backed by a script, target, or CI step you observed. List each with its evidence.
- Every referenced file or directory path exists, including the named exemplar files. Each exemplar actually represents the convention it's cited for.
- Every version stated in the rules matches its source (version file, manifest, lockfile, CI matrix), and the minimum version is derived correctly.
- Every architecture or performance tool cited (import-linter, dependency-cruiser, a benchmark/budget command, etc.) is configured in the repo, and its command is verified like any other command.
- No rules contradict each other or the remaining existing config.
- No secret values are present: grep the written files for key/token/password-like patterns and high-entropy strings.
- Optional, only if it works in this environment: `/memory` (interactive) lists loaded memory files. Mention it as a manual check for the user; do not claim it ran if you could not run it. Do not invent other diagnostic commands.

### Phase J: Final diff gate

Inspect the complete diff of everything you changed: `git diff` and `git status --porcelain` for tracked and untracked files, or a before/after comparison of copies saved in Phase A when the repo is not a git repo. Confirm:
- only CLAUDE.md and `.claude/rules/*.md` changed (plus any explicitly justified agent-config file, and in `enforce` mode only the confirmed `.claude/settings*.json` entries and `.claude/hooks/` scripts); no application code, tests, CI, or manifests
- no secret values added
- all referenced paths exist, and all commands are repository-backed
- generated files are handled via their source of truth
- no contradictory, duplicate, or filler rules remain
- every valid pre-existing instruction remains in a written file unless a written and validated replacement supersedes it; a proposed file in the report does not count
- local rules are path-scoped appropriately
- no unsupported assumptions (INFERRED stated as fact, or UNKNOWN turned into a rule)
- nothing in the rules or the report implies validation that wasn't performed

Fix any issues, then re-inspect the diff.

## 7. Definition of Done (generated for the repo)

If the repo has non-obvious completion requirements, generate a compact repository-specific DoD in CLAUDE.md. Select only items that apply and add information not already stated elsewhere; name verified commands where relevant. If it only repeats the command list or generic validation advice, omit the DoD heading. Candidate checks:
- the requested behavior is implemented
- focused validation is run (name the verified focused-test command)
- broader validation is proportional to blast radius (name the verified commands)
- architecture checks pass where tooling enforces boundaries (name the command)
- benchmarks or budgets are run when the change touches covered code (name the command), with the numbers reported
- the diff has no unexplained suppressions, dead code, debug output, or unjustified new dependencies
- the formatter/linter pass on the changed files (name the commands); new names follow the verified conventions; no logic duplicates existing code
- every API, option, and flag used exists in the locked versions; the code runs on the minimum supported version; no new deprecation warnings or deprecated APIs
- the related docs, comments, `.env.example`, and changelog (when required) are updated; the doc build or link check passes where configured; CLAUDE.md and the rules are still true after the change
- generated artifacts are refreshed via their generator, where applicable
- every failure is investigated and classified, and introduced failures are fixed
- the final diff is reviewed for unrelated changes
- the report states exactly what was and was not verified

Never require a command that couldn't be verified. If, for example, there's no verified lint command, omit lint rather than invent one.

## 8. Rules vs mechanical enforcement

Prose rules are guidance, not security boundaries. For each critical restriction, ask: *what happens if Claude ignores this?* If the answer includes secret exposure, a destructive production action, irreversible data modification, bypassing mandatory validation, a dangerous deployment, or corruption of protected generated files, list it as a mechanical-enforcement candidate. Possible enforcement points include Claude Code permissions (`deny`/`ask` in `.claude/settings.json`), hooks, CI checks, linters, branch protection, and filesystem permissions. Read `references/enforcement.md` for the verified formats, the candidate list, and the fast per-file feedback hook (a PostToolUse hook that runs the repo's own lint/format check on each edited file). Always evaluate that hook as a candidate when verified fast per-file checks exist.

Without `enforce`: do NOT create these; recommend them in the report with the exact proposed JSON and script. With `enforce`: follow the procedure in `references/enforcement.md`, which requires per-item confirmation, merge-not-overwrite, and testing every hook.

## 9. Idempotency

This skill must be safe to rerun.
- Always start from Phase A: inspect what exists.
- Preserve intentional project knowledge and the existing file structure, headings, and wording when they're still correct. Do not reformat, reorder, or rephrase valid rules.
- Update only stale or incorrect facts, consolidate genuine duplication, and add rules only for newly verified risks.
- Don't recreate a rule that already exists in equivalent form, even under a different name.
- If nothing meaningful changed in the repo or the config, make little or no diff, and say so.

## 10. Final report (concise)

Return:

**Repository findings**: only important VERIFIED findings on architecture, tooling, boundaries, validation, and operations. Report applicable evidence and material conflicts; omit categories with no finding. Keep detailed discovery in the report rather than adding it to CLAUDE.md solely for completeness.

**Configuration changed**: for each file: `path` · purpose · scope (always-loaded or the `paths` globs) · created/updated.

**Highest-impact rules**: which rules most reduce realistic failure risk in this repo, and why.

**Existing knowledge preserved**: important pre-existing instructions that were kept.

**Rewritten or removed rules**: meaningful REWRITE/MOVE/DELETE decisions and the reason for each.

**Unknowns**: relevant facts that couldn't be established, plus conflicts found between sources.

**Risks**: only the relevant categories (correctness, security, data integrity, concurrency, performance, reliability, operations, maintainability).

**Mechanical enforcement candidates**: for each:
- Risk:
- Current guidance:
- Why prose may be insufficient:
- Potential enforcement point:
- Recommendation:

**Feedback hook**: whether verified fast per-file checks exist, and the proposed (or, under `enforce`, installed and tested) hook.

**Workflow recipe candidates**: repeated, multi-step tasks this repo clearly has (e.g. add an endpoint: route + schema + client regeneration + test; add a migration; add a component), each with its verified steps and commands, proposed as a project skill (`.claude/skills/<name>/SKILL.md`). Skip tasks already covered by project skills found in Phase A. Propose only; never create them. Omit this section when no clear multi-step pattern exists.

**Validation**: exactly which commands were executed, which checks were performed, what passed, what failed, what wasn't run, and what remains unverified. Never claim validation that didn't occur.
