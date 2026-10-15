---
name: dag-pr-review
description: Thorough multi-agent review of a pull request, branch or diff. Plans a dependency graph of review tasks (intent, then component clusters, then file/hunk leaves, plus security/tests/performance/guideline lenses), runs ready tasks as parallel subagents in waves, splits oversized tasks at runtime, adversarially verifies every finding, and writes a high-signal review. Use when asked to review a PR, branch, or large multi-file change in depth.
---

# DAG PR review

You are the **orchestrator**. You never review code yourself. You drive a deterministic scheduler,
`scripts/dagctl.py`, and launch one subagent per graph node. The scheduler does all of these:
- owns the graph and the run state
- decides what is ready, critical path first
- writes each node's prompt
- validates each node's JSON result
- expands oversized nodes
- deduplicates findings
- creates one adversarial verifier per finding
- assembles the final report

Your job is to feed it inputs, launch agents, and relay results. Keep your own context small: do not read the diff,
the prompts, or the result files unless something breaks.

Set these once, where `<skill-dir>` is the directory containing this SKILL.md:

```bash
DAG="python3 <skill-dir>/scripts/dagctl.py"
RUN=.dag-review          # run directory at the repo root; pass --dir to use another
```

Every command prints JSON with a `next` field telling you what to do next.

## 1. Resolve what to review

Run from the repository root.

- **PR number or URL:** `gh pr view <n> --json number,title,body,baseRefName,headRefOid`. Make sure the head commit
  exists locally, using `git fetch origin pull/<n>/head` if needed. Do not check out branches or touch the user's
  working tree without asking. Write the body to `$RUN/pr-body.md`. Base is `origin/<baseRefName>`, head is
  `headRefOid`.
- **Branch or refs:** use them as given. With no argument, review `HEAD` against the default branch; `init` finds it.
- **Resuming:** if `$RUN/state.json` already exists, run `$DAG status`. If it's the same PR, run `$DAG reclaim` and
  jump to step 4. Otherwise start over with `init --force`.

Add the run directory to `.git/info/exclude` so it never gets committed:
`grep -qx '.dag-review/' .git/info/exclude || echo '.dag-review/' >> .git/info/exclude`.

## 2. Init

```bash
$DAG init --base <base> --head <head> [--pr-number N --pr-title "..." --pr-body-file $RUN/pr-body.md]
```

This classifies the changed files (sensitive, test, docs, generated, binary, deleted) and picks a **risk tier**:

| tier | when | graph | caps |
|---|---|---|---|
| `trivial` | ≤ 20 changed lines, nothing sensitive | intent → 1 leaf | 6 nodes, 4 parallel |
| `lite` | ≤ 300 lines, nothing sensitive | intent → leaves + tests/guidelines lenses | 16 nodes, 8 parallel |
| `full` | > 300 lines, or any security-sensitive path | intent → clusters → leaves + security/tests/performance/guidelines lenses | 40 nodes, 8 parallel |

Honour user overrides with `--tier` or `--max-parallel`. Keep `--max-parallel` at 16 or below, which is below Claude
Code's concurrent-subagent limit.

## 3. Plan

```bash
$DAG autoplan     # deterministic draft: groups files by directory and packs leaves to a line budget
```

- **trivial or lite:** use the draft as it is.
- **full:** improve the draft before loading. Read only `git diff --stat <merge_base> <head_sha>` and
  `$RUN/plan.json`. Where the directory grouping splits a feature or lumps unrelated things together:
  - regroup clusters so each one is a coherent feature or module
  - give clusters and leaves a one-line `focus`
  - add a lens crosscut if the change warrants it, such as `api-compat`, `concurrency` or `data-migration`

  The rules are in [references/plan-format.md](references/plan-format.md). Every non-skipped file must stay owned by
  a leaf.

```bash
$DAG load         # validates: ids, deps, cycles, depth, node cap, file coverage. Fix and re-run on errors.
```

## 4. Execute: review phase

Loop until `next` reports `phase_complete`:

```bash
$DAG next
```

For **every** entry in `launch`, start a subagent. Put all the launches in a **single message**, so they run
concurrently. Use a general-purpose subagent that can read files, run shell commands and write files, and use the
entry's `model` if one is set. Give each one exactly this prompt:

> You are node `<id>` of a pull request review graph. Read `<prompt_file>` and follow it exactly. It tells you where
> to write your JSON result. Reply with one line only.

As subagents finish, run `$DAG complete <id> [<id> ...]`, then `$DAG next` again. If your environment reports each
completion separately, call `complete` and `next` right away rather than waiting for the whole wave. That keeps the
pipeline full: nodes become ready as soon as their own dependencies finish.

- **Rejected results** (bad JSON, schema violations, `BLOCKED`) are re-queued automatically with the error included
  in the prompt. After `max_attempts` they are marked failed and reported as coverage gaps. Do not fix result files
  by hand.
- **Expansion:** when a node returns `NEEDS_EXPANSION`, `complete` inserts its children and rewires any dependents.
  Just keep looping.
- **A subagent that crashed or returned nothing:** run `$DAG fail <id> --reason "..."`.

## 5. Collect and verify

```bash
$DAG collect
```

This merges duplicate findings (same file and overlapping lines, with a similar category or title), discards
findings with confidence below 0.2, and creates verifier nodes:
- one verifier per critical or major finding
- minor findings batched up to 4 per file
- nits are not verified

Then repeat the same `next` / launch / `complete` loop until it reports that verification is complete. Verifiers
never see the PR description or the reviewers' confidence scores, and they are told to try to refute each finding.

## 6. Report

```bash
$DAG report [--min-severity major] [--include-nits]
```

Read `$RUN/review.md` and present it to the user. Lead with the confirmed critical and major issues and give the
counts: confirmed, needs a human look, refuted, and coverage gaps. Don't pad it or re-review anything yourself.

**Posting to GitHub happens only if the user explicitly asks.** Then use `$RUN/review.json`:
- one inline comment per confirmed finding, via `gh api repos/{owner}/{repo}/pulls/{n}/reviews` with
  `commit_id` = head SHA
- a suggestion block only when the suggested fix fully resolves the issue
- the summary as the review body
- never `REQUEST_CHANGES` or `APPROVE` unless the user asks for it

## Rules

- Never skip verification, even when the user is in a hurry. Use `--tier trivial` for speed instead.
- Never pass the PR description to subagents yourself; the scheduler decides who sees it (only the intent node).
- Never edit `state.json` or result files; use the commands.
- If the environment has no subagent tool, run each node yourself in sequence by reading its prompt file and writing
  its result. Say that the review ran in degraded, single-agent mode.
- `.dag-review/` is scratch space. Leave it in place so the user can inspect it, and mention that it can be deleted.

Why the design looks like this, with sources: [references/design-notes.md](references/design-notes.md).
