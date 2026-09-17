---
name: complex-feature-dev
version: "1.1.0"
description: Full-cycle 7-phase feature development workflow with persistent file-based planning (task_plan.md, findings.md, progress.md) as macro memory.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
hooks:
  PreToolUse:
    - matcher: "Write|Edit|Bash|Read|Glob|Grep"
      hooks:
        - type: command
          command: |
            SCRIPT_DIR="${CODEX_HOME:-$HOME/.codex}/skills/complex-feature-dev/scripts"

            IS_WINDOWS=0
            if [ "${OS-}" = "Windows_NT" ]; then
              IS_WINDOWS=1
            else
              UNAME_S="$(uname -s 2>/dev/null || echo '')"
              case "$UNAME_S" in
                CYGWIN*|MINGW*|MSYS*) IS_WINDOWS=1 ;;
              esac
            fi

            ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
            PLAN_FILE="${ROOT}/task_plan.md"
            FINDINGS_FILE="${ROOT}/findings.md"
            PROGRESS_FILE="${ROOT}/progress.md"

            print_plan_head() {
              local file="$1"
              if command -v head >/dev/null 2>&1; then
                head -30 "$file"
              elif command -v sed >/dev/null 2>&1; then
                sed -n '1,30p' "$file"
              elif command -v pwsh >/dev/null 2>&1; then
                pwsh -NoProfile -Command "Get-Content -Path \"$file\" -TotalCount 30"
              elif command -v powershell >/dev/null 2>&1; then
                powershell -NoProfile -Command "Get-Content -Path \"$file\" -TotalCount 30"
              else
                cat "$file"
              fi
            }

            init_plan_files() {
              if [ "$IS_WINDOWS" -eq 1 ]; then
                if command -v pwsh >/dev/null 2>&1; then
                  pwsh -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/init-session.ps1" >/dev/null 2>&1 && return 0
                fi
                if command -v powershell >/dev/null 2>&1; then
                  powershell -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/init-session.ps1" >/dev/null 2>&1 && return 0
                fi
              fi

              if command -v bash >/dev/null 2>&1; then
                bash "$SCRIPT_DIR/init-session.sh" >/dev/null 2>&1 && return 0
              fi

              if [ -x "$SCRIPT_DIR/init-session.sh" ]; then
                "$SCRIPT_DIR/init-session.sh" >/dev/null 2>&1 && return 0
              fi

              return 1
            }

            if [ -f "$PLAN_FILE" ] && [ -f "$FINDINGS_FILE" ] && [ -f "$PROGRESS_FILE" ]; then
              print_plan_head "$PLAN_FILE"
            else
              echo "[complex-feature-dev] Planning files not found (task_plan.md/findings.md/progress.md). Initializing..."
              init_plan_files || true

              ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
              PLAN_FILE="${ROOT}/task_plan.md"
              FINDINGS_FILE="${ROOT}/findings.md"
              PROGRESS_FILE="${ROOT}/progress.md"

              if [ -f "$PLAN_FILE" ] && [ -f "$FINDINGS_FILE" ] && [ -f "$PROGRESS_FILE" ]; then
                echo "[complex-feature-dev] Initialized planning files."
                print_plan_head "$PLAN_FILE"
              else
                echo "[complex-feature-dev] Init failed. Run manually:"
                echo "  bash \"${CODEX_HOME:-$HOME/.codex}/skills/complex-feature-dev/scripts/init-session.sh\""
                echo "  pwsh -ExecutionPolicy Bypass -File \"${CODEX_HOME:-$HOME/.codex}/skills/complex-feature-dev/scripts/init-session.ps1\""
              fi
            fi
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "echo '[complex-feature-dev] Update planning files with brief macro notes (overall status / current micro-phase / key decisions).'"
  Stop:
    - hooks:
        - type: command
          command: |
            SCRIPT_DIR="${CODEX_HOME:-$HOME/.codex}/skills/complex-feature-dev/scripts"

            IS_WINDOWS=0
            if [ "${OS-}" = "Windows_NT" ]; then
              IS_WINDOWS=1
            else
              UNAME_S="$(uname -s 2>/dev/null || echo '')"
              case "$UNAME_S" in
                CYGWIN*|MINGW*|MSYS*) IS_WINDOWS=1 ;;
              esac
            fi

            if [ "$IS_WINDOWS" -eq 1 ]; then
              if command -v pwsh >/dev/null 2>&1; then
                pwsh -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/check-complete.ps1"
                exit $?
              fi
              if command -v powershell >/dev/null 2>&1; then
                powershell -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/check-complete.ps1"
                exit $?
              fi
            fi

            if command -v bash >/dev/null 2>&1; then
              bash "$SCRIPT_DIR/check-complete.sh"
              exit $?
            fi

            if [ -x "$SCRIPT_DIR/check-complete.sh" ]; then
              "$SCRIPT_DIR/check-complete.sh"
              exit $?
            fi

            echo "ERROR: Unable to run completion check (no bash/pwsh found)" >&2
            exit 1
metadata:
  short-description: Full-cycle feature development
---

# Feature Development (Complex Tasks)

A codebase-agnostic workflow for building new features safely:
- 7 phases (discovery → exploration → questions → architecture → implement → review → summary)
- Persistent planning files for long tasks (macro memory: goal, status, next actions, and durable decisions)

## Inputs

Minimum input:
- A 1–2 sentence feature description (what to build + who/why).

Helpful extras (optional):
- Acceptance criteria / examples
- Related files or modules
- Docs / tickets / prototypes (if inaccessible, ask user to paste key parts)

## Quick Command: Initialize Planning Files

From a Codex chat/session (run from anywhere inside your repo):

```text
$complex-feature-dev init
```

Behavior:
- Runs `scripts/init-session.(sh|ps1)` (creates `task_plan.md`, `findings.md`, `progress.md` if missing; targets git repo root by default)
- Also creates `AGENTS.md` if missing (unless the init script is run with `--no-agents`)
- Then stops (you can re-run `$complex-feature-dev <feature description>` to start Phase 1)

Hard rule:
- If the user’s request is exactly `init` / `initialize` / `初始化`, run the initializer via the shell tool (Bash on macOS/Linux; PowerShell on Windows) and stop (do not start Phase 1).

## Reference Docs (Richer Guidance)

This skill keeps the core workflow in `SKILL.md`, and ships deeper checklists/prompt templates in:
- `references/complex-feature-dev.md` (full workflow reference)
- `references/code-explorer.md` (Phase 2 checklist)
- `references/code-architect.md` (Phase 4 checklist)
- `references/code-reviewer.md` (Phase 6 checklist)
- `references/examples.md` (example outputs and question style)

## Output Format

At the end of each phase, present results using the output templates in:
- `references/complex-feature-dev.md` → “Phase Outputs”
- `references/examples.md`

Keep user-facing messages structured and scannable (short headings + bullets + file:line where possible). Keep planning files macro/concise; avoid long transcripts.

Also:
- Always label the current phase in user-facing output (e.g. `Phase 3: Clarifying Questions`). Use the user’s language when appropriate.
- In **Phase 3**, do **not** talk about starting implementation. Only say you will propose architecture options next (Phase 4), then wait for answers.

## Quick Start (Persistent Planning Files)

**These files live in the project root (not in the skill folder):**
- `task_plan.md` (macro status + summary + next actions + decisions/errors)
- `findings.md` (durable findings + decisions)
- `progress.md` (short session notes + validations)
- Recommended (agent instructions):
  - `AGENTS.md` (Codex reads this)

This workflow **requires** these files. Do not proceed with Phase 1 until they exist.

Initialize them (defaults to git repo root):
- macOS/Linux (or Windows Git Bash): `bash "${CODEX_HOME:-$HOME/.codex}/skills/complex-feature-dev/scripts/init-session.sh"`
- Windows PowerShell: `pwsh -ExecutionPolicy Bypass -File "$env:CODEX_HOME\skills\complex-feature-dev\scripts\init-session.ps1"`
  - If `CODEX_HOME` is not set: `pwsh -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\complex-feature-dev\scripts\init-session.ps1"`

Alternatively, you can copy templates manually from this skill’s folder:
- `assets/templates/task_plan.md`
- `assets/templates/findings.md`
- `assets/templates/progress.md`
- `assets/templates/AGENTS.md`

## Project Guidelines (Codex)

- During exploration, look for `AGENTS.md` and follow instructions (including any nested ones that apply to the files you touch).
- If `AGENTS.md` doesn’t exist, fall back to project docs like `CONTRIBUTING.md`, `README.md`, and existing code conventions.
- Capture the important conventions you discover in `findings.md`.

## Non-Negotiable Rules

1. **Never skip Phase 3 (Clarifying Questions).** If anything is underspecified, ask and **wait**.
2. **Never start Phase 5 (Implementation) without explicit approval.**
3. **Use the planning files as persistent macro memory.** Keep them concise and durable.
4. **Read before decide.** Before major decisions, re-read `task_plan.md`.
5. **Log errors briefly + don’t repeat failures.** If an action fails, change the approach.

## How to Track Progress

- Use `update_plan` for the UI checklist (7 steps).
- Use planning files for persistence:
  - During the workflow: keep `task_plan.md` updated with `**Overall Status:**` and (optionally) `**Current Micro-Phase:**`.
  - After durable discoveries/decisions: write brief notes to `findings.md` (prefer file:line pointers).
  - After key actions/validations: write brief notes to `progress.md` (commands + results).

---

## Phase 1: Discovery

**Goal:** Make the request concrete and testable.

- If planning files are missing, run the initializer script via the Bash tool (don’t ask the user to manually copy templates), and do not proceed until the files exist.
- Restate the request as acceptance criteria; confirm scope and non-goals.
- Capture constraints (compatibility, performance, time, rollout).
- Write brief confirmed requirements + acceptance criteria to `findings.md`.

## Phase 2: Codebase Exploration

**Goal:** Identify the correct integration points and existing patterns.

Use `references/code-explorer.md` as your checklist for each exploration pass.
When presenting Phase 2 results to the user, match the structure in `references/examples.md` (start with “Found similar features:” and “Key files to understand:”).

Do 2–3 independent exploration passes:
- Pass A: find similar features and trace end-to-end
- Pass B: map architecture boundaries and extension points
- Pass C: identify testing/build/lint/config/observability conventions

For each pass:
- record key files/patterns (prefer file:line; keep it macro) in `findings.md`.

Also:
- locate and follow `AGENTS.md` instructions (if present).

## Phase 3: Clarifying Questions (Hard Stop)

**Goal:** Resolve all ambiguity before architecture and implementation.

When asking questions, use the Phase 3 style from `references/examples.md`:
- Start with a clear phase label (e.g. `Phase 3: Clarifying Questions`)
- Then “Before designing the architecture, I need to clarify:”
- Then a numbered list
- **Do not mention Phase 5 here**; after answers you move to Phase 4 (architecture options).

Ask questions grouped by:
- behavior definition (inputs/outputs/state)
- edge cases (empty values, duplicates, concurrency, ordering, permissions)
- error handling (timeouts, retries, idempotency, rollback)
- integrations (APIs, data models, config, feature flags)
- backward compatibility & migration
- performance assumptions
- observability
- testing & acceptance plan

Wait for answers (or propose defaults and get explicit confirmation). Record final answers in `findings.md`.

## Phase 4: Architecture Design

**Goal:** Present 2–3 viable approaches and let the user choose.

Use `references/code-architect.md` to structure the blueprint(s).
When presenting options, match the Phase 4 style from `references/examples.md` (Approach 1/2/3 + Pros/Cons + Recommendation + “Which approach would you like to use?”).

Provide at least:
- Minimal changes (reuse, low risk)
- Pragmatic balance (cleaner boundaries)
- Optional clean architecture (more refactor, higher long-term clarity)

For each approach include:
- files to create/modify
- key abstractions + data flow
- trade-offs (risk/time/testability/maintainability)

Write the chosen approach + rationale (brief) to `findings.md` and `task_plan.md`.

## Phase 5: Implementation (Requires Approval)

**Goal:** Implement the chosen approach.

- Implement in small verifiable increments.
- Follow existing conventions; avoid unrelated refactors.
- Log key actions/files/tests in `progress.md` (brief).
- Log errors in `task_plan.md` (and brief resolution in `progress.md`).

## Phase 6: Quality Review

**Goal:** Catch high-impact issues before delivery.

Use `references/code-reviewer.md` as the review checklist.
When presenting review results, match the Phase 6 style from `references/examples.md` (“Code Review Results:” + priority buckets + “What would you like to do?”).

Default review scope:
- Prefer reviewing `git diff` (or specified files).

Focus areas:
- correctness, security/permissions, error handling, observability, conventions, simplicity

Confidence filtering:
- score issues 0–100
- **report only issues ≥ 80 confidence**, with concrete fixes (file:line)

## Phase 7: Summary

**Goal:** Deliver a clean handoff.

When presenting the final summary, match the Phase 7 style from `references/examples.md` (“Feature Complete:” + sections).

- Summarize what was built, key decisions, and files modified.
- Provide verification steps (commands/endpoints/UI paths).
- Call out risks and suggested next steps.
