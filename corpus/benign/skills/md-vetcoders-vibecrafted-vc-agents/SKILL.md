---
name: vc-agents
version: 1.4.1
description: >
  Spawn external subagents via the VibeCrafted method using the portable spawn
  scripts. Use when the user wants
  full isolation, visible Terminal agents, durable artifacts in the canonical
  `~/.vibecrafted/artifacts/` store,
  and real delegated implementation instead of in-thread analysis. Trigger
  phrases: "spawn agents", "terminal agents", "agent fleet", "odpal agentow",
  "deleguj przez terminal", "codex agents", "power agents".
---

# VibeCrafted Agents

## When to use

Trigger when the user asks to delegate work, especially phrases like:

- "Uzyj ... do agentow", "Deleguj ... agentom", "Zlec to agentowi"
- Any request that implies parallelization or multi-track execution
- Any request that wants visible Terminal agents or long-running isolated work

## Why use agents

- Your context is precious and built through many sessions, so you should delegate precisely and minimize context bloat.
- Spawning through the VibeCrafted method requires a strict execution pattern.
- The command shape is canonical and obligatory without exceptions. If you hesitate to use it as provided, do not use this skill.
- Agents are copies of yourself: same smart, same capable, just lighter and more agile because they do not carry your full context window.
- Spawn exists so field teams can implement, research, review, and converge outside the main thread while still leaving durable artifacts in the canonical store.

## Why-matrix

Use `vc-agents` as the default first choice whenever the task benefits from model-specific strengths.
Reach for native `vc-delegate` only when the task is small, bounded, and model-agnostic.

| Model  | Why choose it                                                                   | Best for                                                                                              | Avoid when                                                                                                                |
| ------ | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Codex  | Precision, implementation purity, and highly reliable code surgery.             | Critical implementations, exact refactors, test-gated fixes, and bounded engineering execution.       | The repo is in a chaotic state, the brief is vague, or you are really asking someone to explore and clean up chaos first. |
| Claude | Investigative depth, stubborn logic tracing, and exhaustive research instincts. | Bug hunts, codebase forensics, audits, architecture research, and SoTA framework assessment.          | The work is mostly straightforward code surgery and does not need a full investigative pass.                              |
| Gemini | Bold reframing, creative system redesign, and fearless simplification.          | Architecture leaps, radical cleanup ideas, product reframing, and high-variance creative exploration. | The task only needs predictable, surgical implementation and low-variance execution.                                      |

If the task wants one of these strengths, external agents win by default because you can route work to the right mind instead of forcing a generic in-thread delegation path.

## Goal

Create a small fleet of subagents that each get a precise task into the
canonical `plans/` directory under
`~/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/`.

Delegate:

- exploration
- research
- implementation
- review

Then collect their results in `~/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/reports/` in the current repo.

## Standard workflow

1. Clarify scope if needed.
   - If tasks are not explicit, propose a split into 2-5 items and get alignment.
2. Prepare repo folders.
   - Ensure `skills/vc-agents/scripts/common.sh` `spawn_prepare_paths()` has materialized `~/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/{plans,reports,tmp}/`.
   - Repo-local `.vibecrafted/plans -> ~/.vibecrafted/artifacts/.../plans` and `.vibecrafted/reports -> ~/.vibecrafted/artifacts/.../reports` are convenience symlink paths only.
3. Write one plan per subagent in the canonical `plans/` directory.
   - Keep it high level, decisive, and test-gated.
   - Provide reason and context.
   - Give a clear `[ ]` todo list.
   - Include acceptance criteria and required checks.
   - End with a short call to action.
4. Spawn subagents through the portable spawn scripts.
5. Observe progress through artifacts and transcripts.
6. Synthesize results back into the main thread.

## Mandatory plan rules

Every subagent plan should:

- be high level, decisive, and test-gated
- include reason and context
- include a clear checkbox todo list
- include acceptance criteria
- include required checks
- end with a short call to action

## Living tree rule

Always include this exact preamble in every subagent plan or prompt:

```text
You work on a living tree with Vibecrafting methodology, so concurrent changes are expected.
Adapt proactively and continue, but this is never permission to skip quality, security, or test gates.
Run required checks. If something is blocked, report the exact blocker and run the closest safe equivalent.
```

Keep this preamble repo-agnostic.

Add this living-tree coordination note below the preamble whenever the plan
needs it:

- State explicitly whether the agent is working solo at that stage or alongside
  other agents in parallel.
- The agent needs to know whether the stage is solo or shared, but does not
  need to read other agents' plan files unless the plan explicitly requires it.
- If the original plan clearly calls for a stabilization checkpoint, the agent
  must preserve its tranche of work with a local commit, without push.
- Never change branches during active work. The intent is to stay on the
  current working branch and keep building inside that living tree.
- Plans may explicitly instruct the agent to finish and harden one seam, spawn
  another `vc-agents` worker for the next plan, commit locally for
  preservation, and continue.

## VibeCrafted doctrine

- Do not treat agents like couriers or report printers. Treat them like artists and implementers.
- Do not over-restrict them into tiny bureaucratic slices when the task wants a real rewrite.
- Sometimes a full replacement is cleaner than patching scar tissue.
- VibeCrafted builders ship real products through vibeguiding. Agents should be trusted to do the same.

## Plan template

Use this structure:

```text
# Task: <short title>

Goal:
- <1-3 bullets>

Scope:
- In scope: <files/areas> as high-level suggestions
- Out of scope: <explicit>

Constraints:
- No --no-verify
- Follow repo conventions

Acceptance:
- [ ] <objective outcome>
- [ ] <objective outcome>

Test gate:
- <command(s)>

Context:
- <very short summary>

Living tree note:
- You work on a living tree with Vibecrafting methodology, so concurrent changes are expected.
- Adapt proactively and continue, but this is never permission to skip quality, security, or test gates.
- Run required checks. If something is blocked, report the exact blocker and run the closest safe equivalent.
- Coordination mode: <solo on this stage / parallel with other agents on this stage>
- You do not need to inspect other agents' plans unless this plan explicitly tells you to.
- If this plan explicitly calls for a stabilization checkpoint, commit your own changes locally without push and continue on the current branch.
```

## Spawn commands

The canonical launch path for agent-to-agent delegation is through the portable spawn scripts.

If the environment has optional shell aliases (like `codex-implement`), those are just convenience wrappers around these exact same scripts. Always use the portable scripts to ensure maximum compatibility.

### Codex

```bash
PLAN="$HOME/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/plans/<plan>.md"
bash $VIBECRAFT_ROOT/skills/vc-agents/scripts/codex_spawn.sh "$PLAN" --mode implement
```

### Claude

```bash
PLAN="$HOME/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/plans/<plan>.md"
bash $VIBECRAFT_ROOT/skills/vc-agents/scripts/claude_spawn.sh "$PLAN" --mode implement
```

### Gemini

```bash
PLAN="$HOME/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/plans/<plan>.md"
bash $VIBECRAFT_ROOT/skills/vc-agents/scripts/gemini_spawn.sh "$PLAN" --mode implement
```

If these tools are unavailable, stop pretending spawn is correctly configured and say so explicitly.

## Output convention

- Plans: `~/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/plans/<timestamp>_<slug>.md` or another stable per-task filename
- Reports: `~/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/reports/<timestamp>_<slug>_<agent>.md`
- Transcripts: `~/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/reports/<timestamp>_<slug>_<agent>.transcript.log`
- Metadata: `~/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/reports/<timestamp>_<slug>_<agent>.meta.json`

## Observation

Observe progress through durable artifacts in `~/.vibecrafted/artifacts/<org>/<repo>/<YYYY_MMDD>/reports/`.

If your environment exposes the observer helper, the standard check is:

```bash
bash $VIBECRAFT_ROOT/skills/vc-agents/scripts/observe.sh codex --last
```

Use the equivalent agent observer when needed.

## Quality gate expectations

Keep the standard VibeCrafted quality bar:

- loctree-mcp as first-choice exploration and search tool with fail-fast if inaccessible
- semgrep as first-choice security guard when available
- Rust repos: `cargo clippy -- -D warnings`
- Non-Rust repos: choose the closest equivalent lint/type/test gate
- Tests: run if reviewing; write if implementing new behavior; prefer real e2e coverage for the actual pipeline
- If a gate is blocked, report the exact blocker and run the closest safe equivalent

## Safety rules

- Do not log secrets or commit `.env` files.
- Never use `--no-verify` for `commit` or `push`.
- Do not rewrite git history unless the user explicitly asks.
- Treat concurrent edits as normal, but still verify before overwriting.
- If a repo has a strict command such as `make check`, run it or explain why not.

## Final principle

Spawn is not for outsourcing thought.
Spawn is for deploying equally capable front-line agents through a strict, canonical launch path.
Use them to implement, not merely to comment on implementation.
lementation.
nch path.
Use them to implement, not merely to comment on implementation.
lementation.
