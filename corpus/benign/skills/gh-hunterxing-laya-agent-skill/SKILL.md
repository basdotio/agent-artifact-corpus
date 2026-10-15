---
name: laya-agent-skill
description: Use for typed Laya routing, triage and review decisions.
version: 0.4.1
author: xingheng, Hermes Agent
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [laya, typed-decisions, coding, triage, routing, code-review, testing, guardrails]
    related_skills: []
---

# Laya Agent Skill

A fast typed-judgment sidecar for coding agents. Ask `choice` / `score` / `noul` questions about one
state and get calibrated probabilities back in a few hundred milliseconds; the answers inform a
decision, they never make one.

Built on [Laya](https://github.com/NandhaKishorM/laya) (Apache-2.0, non-autoregressive System 1
decision model) behind an OpenAI-compatible gateway. The interface follows the code-owned-workflow
idea from [TypeSafe AI's coding-agent design](https://docs.typesafe.ai/introduction/coding-agents):
keep the workflow and the policy in code, use the model only for semantic judgment.

Any agent that can run a shell command, speak MCP, call an HTTP tool, or read a project rule can use
it. Wiring patterns for those capability classes are in [integration.md](references/integration.md).

## Use it for

- **Agent-agnostic**: use the shell, MCP, HTTP-only or rule-file path that the host supports; the
  decision contract is the same in every path.
- selecting one skill or workflow from a short, code-built candidate list;
- reranking a small set of snippets, files, commits or test failures by evidence usefulness;
- triaging a first error into dependency, source, test, environment or unknown;
- deriving a review-risk floor and minimum test scope from changed-file metadata;
- checking whether the evidence at hand supports a claim before the main model relies on it.

Do not use it as the sole authority for destructive commands, secret access, production changes,
security-boundary changes, external messages, or final code correctness. A low probability never
overrides a hard rule or an explicit confirmation.

## Entrypoints

Three ways in, same JSON contract on stdout. If the host does not support any of these capability
classes, it cannot execute Laya; merely mentioning the skill does not create an integration:

```bash
LAYA_SKILL="$HOME/.hermes/skills/mlops/laya-agent-skill"

# 1. portable shell entrypoint (POSIX sh, resolves its own directory)
sh "$LAYA_SKILL/scripts/laya.sh" selftest

# 2. helper directly (python3, standard library only, works on 3.9+)
printf '%s' '{"request":"fix login crash and add a regression test","candidates":[{"id":"debug","description":"locate the stack trace and fix the source"},{"id":"docs","description":"write user documentation"}]}' \
  | sh "$LAYA_SKILL/scripts/laya.sh" select

# 3. MCP server, registered by any MCP client
python3 "$LAYA_SKILL/scripts/laya_mcp.py"
```

Modes: `models`, `decide`, `select`, `rerank`, `triage`, `verify`, `change-review`, `preset`,
`selftest`. Add `--dry-run` to any development mode to see the generated questions without a
request; `--version` prints helper and protocol versions. Input schemas, output fields and the
status contract: [development-workflows.md](references/development-workflows.md). Credentials and
the file search order: [env-setup.md](references/env-setup.md).

## Decision rules

1. Send English semantic text and keep identifiers verbatim. The gateway routes by script, and on
   the shipped deployment the English checkpoint decided a `select` fixture correctly (fit 0.80)
   while the same question in Chinese produced `none` at 0.88 and was gated. Translate the request
   and the candidate descriptions; leave paths, symbols and error strings untouched.
2. Batch independent questions for one state — they are answered in a single forward pass. Prefer
   `noul` for binary checks, `choice` for a closed set under 20 options, and treat `score` as an
   ordered descriptive signal (the weakest primitive).
3. Shortlist before `choice`. Keep candidates to a handful and include an explicit `none`/`unknown`
   outcome so the model has somewhere to go when nothing fits.
4. Combine with deterministic policy, never replace it. A file-based risk or test floor may be
   raised by Laya but never lowered; a keyword heuristic outranks the model on error triage
   (`laya_role: "tiebreaker_only"`), because that is what the deployment measured.
5. Treat `status: unknown` (timeout, protocol mismatch, backend degradation, truncated input) and
   `needs_review: true` (close probabilities, low confidence, `none` chosen, insufficient evidence)
   as "no decision yet" — continue with the main model or a human. Neither is a negative answer.
6. Validate before acting: `auto_action` is always false, the helper already checked question ids,
   types, probability sums and choice/distribution agreement, and a malformed response arrives as
   `unknown` rather than as approval.

Laya probabilities are deployment signals, not universal thresholds. The deployment reports
`calibration: deployment_unverified`; calibrate on labelled samples from your own language and
workflow before automating even a low-risk branch. For `noul`, use the `noul` probability as the
proposition signal and the auxiliary `confidence` field only as a stability hint.

## Safety boundary

```text
hard rules + tool metadata + Laya signal + user confirmation
```

Read-only actions may use a Laya answer as a routing hint. Service-affecting or reversible changes
need a plan and a rollback path. Destructive or security-sensitive actions always require the
existing hard gate and explicit confirmation, whatever the model says. Do not switch the host
agent's main model from this skill, and do not treat a parsed JSON response as permission to run a
tool.

## Pitfalls

- **Chinese input is not a free translation of English input.** It changes the checkpoint, and the
  multilingual one is weaker on these schemas. Normalise to English first.
- **`act_probability` came back 1.0 on every live call measured**, so ignore it for now; use
  `confidence`, `noul` and `top_margin` instead.
- **The gateway is not upstream's Python API.** Upstream is `laya.load(...)` in-process; this
  deployment wraps a `laya.decision.v1` envelope in `/chat/completions` (native `/decisions` is
  written but disabled). Semantics match upstream, the transport does not — do not copy upstream
  snippets here, and do not expect `predict_shortlist`-style local helpers over HTTP.
- **`select` and `rerank` take 1–6 candidates**, while the protocol allows a `choice` question up to
  20 options for a custom `decide`. Beyond ~20 options accuracy collapses (shared `head_max_len`
  budget), so shortlist before asking.
- **Never print the credential file or a raw gateway error body.** Errors are returned as short
  codes with a human hint for exactly that reason.

## Verification

```bash
python3 "$LAYA_SKILL/scripts/laya.py" --version    # helper + protocol version
sh "$LAYA_SKILL/scripts/laya.sh" selftest          # 6 cases against the live backend
sh "$LAYA_SKILL/scripts/laya.sh" models            # real model ids
```

`selftest` must report `"status": "ok"`. Its `contract` cases (plumbing, routing, deterministic
policy, local input guard) must always pass; its `baseline` cases pin what the shipped deployment
measured, so a baseline failure means re-measure before trusting a branch rather than a broken
install. For the MCP path, confirm the client lists eight `laya_*` tools and that `laya_selftest`
returns `ok`.
