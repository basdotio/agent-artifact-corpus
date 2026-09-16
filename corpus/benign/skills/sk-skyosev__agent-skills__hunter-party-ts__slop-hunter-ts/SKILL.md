---
name: slop-hunter-ts
description: |
  Audit TypeScript code for AI-generated noise — redundant comments, verbose documentation,
  style drift from project conventions, and trivially dead code. Surface-level hygiene
  pass; defaults to branch diff but supports any scope.

  Use when: reviewing AI-assisted TypeScript code before merge, cleaning up generated code,
  enforcing project style on new contributions, or reducing review noise.
disable-model-invocation: true
---

# Slop Hunter

Audit code for **AI-generated noise** — comments that narrate the obvious, documentation that restates code, style
choices that break project conventions, and dead code that slipped in. The goal: **the code reads like a human wrote it,
following existing project idioms.**

## When to Use

- Reviewing AI-assisted code before merge
- Cleaning up a branch after heavy AI pair-programming
- Enforcing project conventions on generated contributions
- Reducing noise in pull request reviews

## Core Principles

1. **Default to the diff.** When scoped to a branch diff, only flag patterns introduced in this branch — pre-existing
   issues are out of scope. When scoped to a path or codebase, flag all matching patterns in the resolved surface.

2. **Comments explain why, not what.** A comment that restates the code ("increment counter") is noise. A comment that
   explains intent, constraints, or non-obvious decisions ("rate limit: 3rd-party API allows 100 req/min") is valuable.

3. **Style is not cosmetic.** Drift from project conventions increases cognitive load for every future reader. New code
   must conform to existing patterns, not introduce alternatives.

4. **Less is more.** AI tends to over-document, over-explain, and over-hedge. Strip to the minimum that preserves
   clarity.

## What to Hunt

### 1. Redundant Comments

Comments that narrate obvious behavior, restate function/variable names, or explain standard language constructs.

**Signals:**

- `// Initialize the array` above `const arr = []`
- `// Return the result` above `return result`
- Comments explaining standard library usage
- Section dividers (`// ---- Helper Functions ----`) in small files

**Action:** Delete. If the code needs explanation, it should be rewritten for clarity first.

**Comment ownership rule** (stated identically in doc-hunter, slop-hunter, and smell-hunter):
- Comment absent and the "why" non-obvious → doc-hunter (add the missing "why" comment).
- Comment present and the code trivial → slop-hunter (delete the redundant comment).
- Comment present and the code non-trivial → smell-hunter (extract/refactor; the comment is deodorant).

### 2. Verbose Documentation

Over-documentation that adds noise without insight — typically AI-generated JSDoc on every function including trivial
private helpers.

**Signals:**

- JSDoc on private/internal functions with obvious behavior
- `@param` tags that repeat the parameter name (`@param name - the name`)
- `@returns` that restates the return type
- README sections that describe implementation details instead of usage

**Action:** Keep JSDoc only on public API. Strip params/returns that add nothing beyond the type signature.

### 3. Style Drift

Patterns that diverge from the project's established conventions in naming, formatting, structure, or idioms.

**Signals:**

- Different naming convention (camelCase where project uses snake_case, or vice versa)
- Different error handling pattern than established code
- Different import ordering or grouping
- Different file/folder organization than existing modules
- Template strings where project uses concatenation (or vice versa)

**Action:** Conform to existing project conventions. Cite the existing pattern as evidence. If a lint rule could
enforce the convention, recommend enabling the rule rather than listing every occurrence.

### 4. Trivially Dead Code

Unused imports, unused variables, commented-out code blocks, and placeholder TODOs.

**Signals:**

- `import { X } from '...'` where X is never used in the file
- `const x = ...` where x is never referenced
- Blocks of commented-out code (`// const old = ...`)
- `// TODO: implement` or `// FIXME` without actionable context

**Action:** Delete unused imports/variables. Delete commented-out code. Convert vague TODOs to actionable tickets or
delete.

### 5. AI-Specific Verbal Patterns

Hedging language, apologetic comments, and over-explanation typical of AI-generated code.

**Signals:**

- `// This is a workaround for...` without specifying the issue
- `// Note: this might need to be updated if...` (speculative)
- `// For safety, we also check...` (unnecessary hedging)
- `// New, improved version..` (references old code)
- Logging that narrates execution flow (`console.log('entering function X')`)

**Action:** Delete hedging and narration. Keep only comments that document concrete constraints or known issues with
references.

## Audit Workflow

### Phase 1: Establish Context

1. **Resolve audit surface.** The prompt may specify the scope as:
   - **Diff**: files changed relative to the base branch — committed, staged, unstaged, and untracked
   - **Path**: specific files, folders, or layers
   - **Codebase**: the entire project (`SCOPE=.`)

   If unspecified, default to **diff** — slop is introduced by new contributions, so the diff is this hunter's
   natural surface (other hunters default to codebase).

   **Party mode:** when the orchestrator supplies a scope snapshot (a resolved file list), use it verbatim and do
   not re-resolve. The resolution below applies to standalone runs only.

   For diff mode, resolve fail-closed:
   ```bash
   BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/@@')
   if [ -z "$BASE" ]; then
     for b in origin/main origin/master main master; do
       git rev-parse -q --verify "$b" >/dev/null && BASE=$b && break
     done
   fi
   # If BASE is still empty: STOP. Ask for an explicit base. Do not continue.

   SCOPE=$( { git diff --name-only --diff-filter=d "$BASE"...HEAD;
              git diff --name-only --diff-filter=d HEAD;
              git ls-files --others --exclude-standard; } | sort -u )
   DELETED=$( { git diff --name-only --diff-filter=D "$BASE"...HEAD;
                git diff --name-only --diff-filter=D HEAD; } | sort -u )
   ```
   If `$SCOPE` is empty, run no scans: write the report with "Audit completed: 0 findings — empty diff scope",
   listing `$DELETED` under "Deleted in diff" if non-empty, and stop. If the resolved surface exceeds what can be
   read within the context budget, report the file count and ask to narrow or chunk.

   **Two surfaces.** Findings are reported only against the **target scope** (`$SCOPE`). Established files outside
   the surface are read as **context** — they define the conventions that new code is measured against.
2. Identify the project's style conventions by examining established files outside the audit surface.
3. Note the project's documentation patterns (JSDoc style, comment conventions, naming).

### Phase 2: Scan for Noise

Test files are deliberately **in scope** for this hunter — AI noise (redundant comments, narration, dead code)
lands in tests as readily as in production code.

In **diff mode**, focus on added lines to isolate new noise from pre-existing patterns (untracked files have no
diff — scan them directly with the path-mode commands below):

```bash
# Added comments (committed + working tree)
{ git diff "$BASE"...HEAD; git diff HEAD; } | rg '^\+.*\/\/'

# Added JSDoc (committed + working tree)
{ git diff "$BASE"...HEAD; git diff HEAD; } | rg '^\+.*(\*\*|@param|@returns)'
```

In **path/codebase mode**, scan the resolved surface directly:

```bash
# Dependencies, build output, and generated code excluded; tests stay in scope
EXCLUDE='--glob !**/node_modules/** --glob !**/dist/** --glob !**/*.generated.* --glob !**/__generated__/** --glob !**/*.g.ts --glob !**/generated/**'

# Comments (then classify manually)
rg '^\s*//' --type ts $EXCLUDE -- $SCOPE

# JSDoc blocks
rg '/\*\*' --type ts $EXCLUDE -- $SCOPE
```

In all modes:

```bash
# TODO/FIXME markers
rg 'TODO|FIXME|HACK|XXX' -- $SCOPE

# Console.log statements
rg 'console\.(log|debug|info)' -- $SCOPE
```

### Phase 3: Classify Each Finding

For each finding, determine:

- Is this noise or does it add value?
- Does this match or break project conventions?
- Is this clearly AI-generated or an intentional choice?

### Phase 4: Produce Report

## Output Format

Save as `YYYY-MM-DD-slop-hunter-audit-{model-name}.md` — `{model-name}` is the executing model's short name (e.g.
`fable-5`) — in the project's docs folder (or project root if no docs folder exists). If the caller specifies an
output path (e.g. the party-hunter orchestrator), it overrides this default.

Severity levels, used for per-finding labels and the Recommendations grouping:

- **Critical** — exploitable now, causes data loss, or breaks behavior on production paths.
- **High** — a defect with likely user-visible, security, or reliability impact if left unaddressed.
- **Medium** — correctness or maintainability risk without imminent impact.
- **Low** — hygiene; no behavioral risk.

```md
# Slop Hunter Audit — {date}

## Scope

- Surface: {diff / path / codebase}
- Files: {count or list}
- Exclusions: {list}
- {Deleted in diff: {list} — only for diff scope with deletions}
- Audit completed: {N} findings

## Findings

### Redundant Comments

| # | Location | Comment | Action |
| - | -------- | ------- | ------ |
| 1 | file:line | `// Initialize the array` | Delete |

### Verbose Documentation

| # | Location | Pattern | Action |
| - | -------- | ------- | ------ |
| 1 | file:line | JSDoc on private helper with obvious behavior | Strip |

### Style Drift

| # | Location | Pattern | Project Convention | Action |
| - | -------- | ------- | ------------------ | ------ |
| 1 | file:line | `snake_case` variable | Project uses `camelCase` | Rename |

### Dead Code

| # | Location | Code | Action |
| - | -------- | ---- | ------ |
| 1 | file:line | Unused import `X` | Delete |

### AI Verbal Patterns

| # | Location | Pattern | Action |
| - | -------- | ------- | ------ |
| 1 | file:line | `// This is a workaround for...` | Delete or add specific issue reference |

## Recommendations (Priority Order)

1. **Medium**: {style drift that breaks project conventions}
2. **Low**: {redundant comments, dead code, verbose docs, AI verbal patterns}
```

(Surface noise is by nature Low/Medium; Critical/High are available but a slop finding that rises to them — e.g.
narration logging that leaks secrets — usually belongs to another hunter and should be cross-referenced.)

## Operating Constraints

- **No code edits.** This skill produces an audit report only. Implementation is a separate step.
- **No empty finding sections.** Include only categories with findings. Omit a heading, table, or list entirely when it would contain zero items — do not include empty tables, placeholder subsections, or negative statements like "no dead exports", "none found", or "no issues". Execution status is exempt: the "Audit completed: N findings" line in the Scope section is always present, even at zero findings.
- **Scope: surface noise only.** If a finding doesn't answer "is this noise?", it belongs to another hunter — do
  not flag it here. Apply the comment ownership rule above for the doc/slop/smell split.
- **Evidence required.** Every finding must cite `file/path.ext:line` with the exact code.
- **Preserve intent.** Flag noise, not substance. If a comment captures genuine design intent, keep it regardless of
  verbosity.
- **Project conventions are the standard.** Always cite existing project patterns when flagging drift.
