---
name: idea-panel
description: Run a parallel panel of thinking-skills mental-model lenses over a topic to generate fresh ideas, then synthesize and rank them. Use when brainstorming new products, business directions, research angles, or creative options.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
  - Write
  - AskUserQuestion
---

# idea-panel

## `-h` / `--help`

If the argument text (trimmed, case-insensitive) is exactly `-h`, `--help`, or
`help`, output only the block below and stop — do not run any other step in this
skill.

> **⚠️ Writes a report file to disk by default, without asking first** — unless
> `--no-write` (or `--write-to` a specific path) is passed, the synthesized
> shortlist is saved to `docs/ideas/<date>-<topic-slug>.md` after spawning a
> 4–5-agent lens panel.

Runs a parallel panel of thinking-skills mental-model lenses over a topic, then
synthesizes and ranks the results into a shortlist of ideas. Use it to
brainstorm new products, business directions, research angles, or creative
options — not to evaluate an existing idea/proposal or to reason through a
single mental model alone.

| Option | Values | Default | Effect |
|---|---|---|---|
| `<topic...>` (positional) | free text | required — empty topic hard-fails | Problem space the lens panel generates ideas for |
| `--lenses <csv>` | comma-separated `thinking-<name>` slugs or named specialist agent names | default roster: first-principles, jobs-to-be-done, inversion, effectuation | Overrides which lenses run in the panel |
| `--panel-size <n>` | integer, clamped to 3–4 | 4 (full default roster) | Truncates the default roster to N lenses; ignored when `--lenses` is explicit |
| `--context <path>` | file or directory path | none | Background material prepended to every lens brief (16 KB cap) |
| `--write-to <path>` | file path | `docs/ideas/<date>-<topic-slug>.md` | Overrides where the report is saved; refuses to overwrite unless `--force` |
| `--no-write` | flag | off | Suppresses the report file; prints to stdout only. Mutually exclusive with `--write-to` |
| `--force` | flag | off | With `--write-to`, allows overwriting an existing file |

## 1. Purpose

Generative sibling of `multi-agent-review`. Instead of a panel of *reviewers* finding faults in an existing artifact, this skill runs a panel of **thinking-skills mental-model lenses in parallel** to *generate* candidate ideas for a topic, then a synthesizer clusters, ranks, and de-duplicates them into one shortlist.

The skill itself produces no ideas — it orchestrates lens agents and relays the synthesized output. Each lens is a distinct cognitive frame (first-principles, jobs-to-be-done, inversion, effectuation, …), so the same topic gets attacked from angles that a single pass would collapse into one.

Full lens roster, per-lens brief template, and the synthesizer brief live in the references — this file is the orchestration contract only.

- [`references/lens-briefs.md`](references/lens-briefs.md) — the lens brief template, the default roster, and each lens's role framing + output contract.
- [`references/synthesizer-brief.md`](references/synthesizer-brief.md) — the synthesizer brief template and the fixed-heading report structure.

## 2. When to use

Trigger phrases:
- "brainstorm ideas for …" / "generate ideas about …"
- "what could we build in <space>?" / "new directions for <project>"
- "run an idea panel on …" / explicit `idea-panel …`

Do NOT use for:
- Evaluating an *existing* idea/proposal — use `idea-autopsy:evaluate-proposal-harsh` (go/no-go) or `idea-autopsy:stress-test-idea` (hardening).
- Single-model reasoning — invoke the specific `thinking-skills:thinking-<name>` skill directly.
- Anything that writes to source files — this skill is read-only.

## 3. Invocation grammar

```
idea-panel <topic...> [--lenses <csv>] [--panel-size <n>] [--context <path>] [--write-to <path>] [--no-write]
```

Examples:

```
idea-panel genetic security — new project/product directions
idea-panel loyalty rewards for indie coffee shops --panel-size 3
idea-panel developer tooling --lenses thinking-triz,thinking-second-order,thinking-jobs-to-be-done
idea-panel authentication UX --context docs/research/ --write-to docs/ideas/auth-panel.md
```

| Position / flag | Required | Values |
|---|---|---|
| `<topic...>` (positional) | yes | Free-text topic/problem space. Everything not consumed by a flag is the topic. Empty topic → hard-fail. |
| `--lenses <csv>` | no | Comma-separated lens tokens (whitespace trimmed). A token is either a `thinking-<name>` slug (dispatched as `general-purpose` applying that mental model) or a **named specialist agent** (e.g. `market-researcher`, `product-strategist`) dispatched via its own `subagent_type` to add domain grounding the thinking-skills lenses lack. Default = the roster in `references/lens-briefs.md` §Default roster. |
| `--panel-size <n>` | no | Clamp the panel to N lenses (3–4; values outside clamp to the nearest bound). Applies to the default roster; ignored when `--lenses` is explicit. |
| `--context <path>` | no | File or directory of background material prepended to every lens brief under `## CONTEXT`. Resolved relative to `git rev-parse --show-toplevel` when not absolute; missing path = hard-fail; 16 KB cap (dir = concatenated `git ls-files` contents, same cap). |
| `--write-to <path>` | no | Explicit path override for the report file; resolved relative to `git rev-parse --show-toplevel` when not absolute. Does **not** control whether a file is written — that is on by default (see `--no-write`). Refuses if the file exists unless `--force`. |
| `--no-write` | no | Suppress the report file; print to stdout only. The shortlist is otherwise written by default to `docs/ideas/<YYYY-MM-DD>-<topic-slug>.md` (§5.1). Mutually exclusive with `--write-to`; passing both is a parse-time hard-fail. |
| `--force` | no | With `--write-to`, allow overwriting. Not needed for the default path, which suffixes `-2` instead. |

## 4. Defaults

- **Lens roster** (when `--lenses` omitted, in order — see `references/lens-briefs.md` for each lens's framing):
  1. `thinking-first-principles`
  2. `thinking-jobs-to-be-done`
  3. `thinking-inversion`
  4. `thinking-effectuation`
- **Panel-size cap**: 3–4 lenses. This is deliberate — `thinking-model-combination` warns that >4 models produces "model soup." More than 4 requested via `--lenses` → warn on stderr but proceed (explicit override wins). Exception: adding `critical-thinking` as a 5th, non-generative carve-out lens does not count against the soup cap (it interrogates rather than generates — see `references/lens-briefs.md`).
- **Lens agent type**: `general-purpose` (thinking-skills are Skill-tool skills, not dedicated agents; the general-purpose subagent can invoke `thinking-skills:thinking-<name>` and has Read/Grep for `--context`).
- **Synthesizer agent type**: `general-purpose`.
- **Report file**: written by default to `<git-root>/docs/ideas/<YYYY-MM-DD>-<topic-slug>.md` (§5.1). A panel is N+1 agent calls whose whole output is a shortlist; letting it scroll away means paying again to get it back. `--no-write` opts out; `--write-to <path>` overrides the path.
- **Default-path collision**: same topic panelled twice on the same day → append `-2`, `-3`, … rather than refusing. The caller did not choose this path, so a refusal would be a failure they cannot act on.
- **`--write-to` overwrite policy**: refuse if destination exists unless `--force`.

## 5. Workflow

### 5.1 Parse and validate
1. Split positional topic from flags. Hard-fail if topic is empty.
2. Validate `--lenses` CSV: split on `,`, strip surrounding whitespace, reject empty tokens. A token is either (a) a `thinking-<name>` slug — warn (don't hard-fail) if a matching skill can't be located among your installed plugins (e.g. search installed plugin skill directories for a `thinking-<name>` match), since the brief is self-contained; or (b) a **named specialist agent** — validate it against the live agent-type registry + `.claude/agents/*.md` + `~/.claude/agents/*.md` + the parked rosters (`.claude/agents-parked/*.md`, `~/.claude/agents-parked/*.md` — parked agents don't register, so they don't bloat session context; they dispatch via the §5.3 paste method). **Hard-fail if the name matches none of these**, telling the user which agent is missing and to park it at `~/.claude/agents-parked/<name>.md`.
3. Apply `--panel-size`: clamp to 3–4 and truncate the default roster to that length (ignored when `--lenses` is explicit).
4. Resolve `--context` (if present): to absolute; hard-fail if missing; enforce 16 KB cap; read into `{{CONTEXT_BLOCK}}`. Absent → strip the `## CONTEXT` block from the brief.
5. **Resolve the report path** HERE, before any agent is spawned (don't waste N+1 agent calls on a doomed write). Skip if `--no-write`; hard-fail if both `--no-write` and `--write-to` were passed.
   - **`--write-to <path>`** → resolve to absolute (relative to `git rev-parse --show-toplevel`), then canonicalize and require the result to sit inside the git root — reject a `..` escape, an absolute path outside the repo, or an out-of-repo symlink. If it exists and `--force` is not set, hard-fail here.
   - **otherwise (the default)** → slug the topic, in this order: lowercase; collapse every run of non-alphanumerics to a single `-`; trim leading and trailing `-`; truncate to 60 chars on a `-` boundary. This is derivation from free text, not rewriting of a caller's value — there is no `--slug` flag, so there is nothing to reject; a topic like `authentication UX (v2)` normalizes to `authentication-ux-v2` and that is correct, not a validation failure. If the result is empty or a bare `-`, fall back to `panel`. Path is `<git-root>/docs/ideas/$(date +%Y-%m-%d)-<topic-slug>.md`; suffix `-2`, `-3`, … if it exists, giving up after `-20` and appending `$(date +%H%M%S)` instead.
   - **Not in a git repo** → resolve against `$PWD` and warn once on stderr; never hard-fail over it.

### 5.2 Build lens briefs
For each lens in the roster, expand the lens brief template (`references/lens-briefs.md`) with: `{{LENS_NAME}}`, `{{TOPIC}}`, `{{LENS_INSTRUCTION}}` (that lens's role framing — from the references roster table for `thinking-*` lenses, or the §Specialist-agent lenses table for named agents), `{{CONTEXT_BLOCK}}`, and `{{OUTPUT_CONTRACT}}`. Select the contract by lens: `critical-thinking` uses the **carve-out** contract (returns assumptions/questions, not ideas); every other lens (thinking-skill or specialist agent) uses the **generative** contract. Briefs are fully self-contained — lens agents share no conversation state.

### 5.3 Spawn lenses IN PARALLEL

> ⚠️ **PARALLELISM RULE — DO NOT SERIALIZE.** All lens `Agent` calls MUST be issued in a SINGLE assistant message with N parallel tool invocations. Serializing multiplies latency by N and defeats the skill. Each call sets `subagent_type` = `general-purpose` for a `thinking-*` lens; for a specialist-agent lens, use the agent's own name as `subagent_type` only if it is actually registered (e.g. activated into the project's `.claude/agents/`), otherwise — the normal case for parked agents — dispatch `general-purpose` with the agent's `.md` body (the file found during §5.1 validation, everything below the frontmatter) pasted ABOVE the lens brief in the prompt. An unregistered-but-parked agent is not an error — the paste method preserves the persona; §5.1 already hard-failed any name that resolves nowhere. Every call sets `description: "Idea panel: <lens-name>"` and `prompt` = the fully-expanded lens brief.

### 5.4 Collect outputs
After all lenses return, capture each output verbatim, keyed by lens name in roster order. Do not edit or filter. A lens that fails/returns empty is noted to the synthesizer as `<lens-name>: [FAILED — no output]`; continue with the rest.

### 5.5 Invoke synthesizer
Expand the synthesizer brief (`references/synthesizer-brief.md`) with `{{TOPIC}}`, `{{N_LENSES}}`, `{{CONTEXT_BLOCK}}`, and `{{LENS_OUTPUTS}}` (each lens's verbatim output under a `### Lens: <name>` block, `---`-delimited). The synthesizer routes any `critical-thinking` carve-out output to its own "Assumptions & Open Questions" section and never folds it into the idea ranking (see the brief). Spawn one `Agent` call, `subagent_type: general-purpose`, `description: "Idea panel: synthesize"`.

### 5.6 Print verbatim
Print the synthesized report as the final message. Unless `--no-write` was passed, `mkdir -p` the parent of the path resolved in §5.1, write the report there, and prepend one line `Wrote: <absolute path>`. Don't ask first — the earlier ask-before-discarding branch is superseded: an unwanted file costs one `rm`, a lost shortlist costs the whole panel, and any unattended run (or a reflexive "no") threw the output away. Then suggest the natural follow-on pipeline: `idea-autopsy:iterate-to-v2` → `product-management:write-spec` / `to-prd` → `idea-autopsy:evaluate-proposal-harsh`.

## 6. Error handling

| Condition | Action |
|---|---|
| Empty topic | Hard-fail with a one-line usage summary. Do not spawn agents. |
| `--lenses` token empty (consecutive commas) | Hard-fail with the offending CSV. |
| `--lenses` slug not found among installed plugins | Warn on stderr, proceed (brief is self-contained). |
| `--panel-size` outside 3–4 | Clamp to the nearest bound, warn on stderr. |
| `--context` path missing / over 16 KB | Hard-fail with the path and (for size) the cap. |
| `--write-to` exists, no `--force` | Hard-fail in §5.1, before any agent is spawned. Explicit paths only — a default-path collision suffixes `-2` instead. |
| `--write-to` and `--no-write` both passed | Hard-fail at parse time: `--write-to and --no-write are mutually exclusive`. Zero agents spawned. |
| Report write fails (permissions, read-only FS) | Print the report in full with a one-line stderr note naming the path and the error. Never discard a completed panel over a failed write. |
| A lens agent fails / returns empty | Note it to the synthesizer as `[FAILED — no output]`; continue with the rest. |
| Synthesizer fails | Print `Synthesizer failed. Lens outputs follow:` then dump each lens's verbatim output with `---` delimiters, and write the same content to the resolved report path (the default; skipped only by `--no-write`) with a leading header noting the synth failure — better to persist raw lens material than discard it. |
