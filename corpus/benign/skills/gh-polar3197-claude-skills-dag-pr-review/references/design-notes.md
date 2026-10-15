# Design notes

These notes explain why `dag-pr-review` is built the way it is. They draw on published designs of LLM code
reviewers and on agent-orchestration research, surveyed in September 2026.

## What the prior art does

| Source | Idea we borrowed | Where it lives here |
|---|---|---|
| Anthropic `code-review` plugin ([command](https://github.com/anthropics/claude-code/blob/main/plugins/code-review/commands/code-review.md)) | Parallel specialist reviewers, then **one validation subagent per issue**, and dropping anything unvalidated. An explicit false-positive list ("pre-existing", "linter-catchable", "pedantic"). Guideline violations must quote the rule. | `collect` → verify nodes; `prompts/common.md` "Do NOT report"; guidelines lens |
| Anthropic `pr-review-toolkit` ([review-pr](https://github.com/anthropics/claude-code/blob/main/plugins/pr-review-toolkit/commands/review-pr.md)) | Choose specialists based on what changed (tests, types, error handling). | `autoplan` adds lenses from file tags |
| Cloudflare AI code review ([blog](https://blog.cloudflare.com/ai-code-review/)) | **Risk tiers**: trivial, lite and full reviews use 2, 4 and 7 agents, and security-sensitive files always get the full tier. | `init` tiering |
| Qodo PR-Agent ([docs](https://github.com/qodo-ai/pr-agent/tree/main/docs/docs/core-abilities)) | Packing files into a token budget; dropping deletion-only and generated files from line review while still listing them; widening context to the enclosing function. | `autoplan` packing, skip tags, leaf prompt |
| Cursor Bugbot ([blog](https://cursor.com/blog/building-bugbot)) | Redundant passes whose agreement signals real bugs; a validator model; deduplicating findings. | `corroborated` flag, `dedupe` |
| CodeRabbit ([context engineering](https://www.coderabbit.ai/blog/context-engineering-ai-code-reviews)) | Code-graph and call-site context; verification agents that run scripts (such as ast-grep) before posting. | Cluster prompt greps callers; verifier runs cheap checks |
| Greptile ([blog](https://www.greptile.com/blog/make-llms-shut-up)) | A model's self-rated severity or confidence is close to random as a filter. What worked was learning from feedback on real comments. | Confidence is only a pre-filter (0.2); verification decides. Feedback learning is on the roadmap |
| Refute-or-Promote ([arXiv 2604.19049](https://arxiv.org/html/2604.19049)) | Adversarial refuters that see only the claim; an empirical check beats consensus. | Verifier prompt: try to refute; run a check when cheap |
| Confirmation bias in LLM review ([arXiv 2603.18740](https://arxiv.org/html/2603.18740v1)) | A PR description claiming the code is safe cuts vulnerability detection by 16–93 points. Redacting it recovers nearly all of that. | Only the intent node sees the description, and it is told to treat it as claims |
| obra/superpowers ([requesting-code-review](https://github.com/obra/superpowers), [subagent-driven-development](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md)) | Reviewers must list what they "declined to judge"; worker statuses DONE, DONE_WITH_CONCERNS, BLOCKED; a ledger file that survives context compaction. | `declined`, result statuses, `state.json` |
| wshobson/agents `full-review` | Phase outputs kept in files, and a resumable `state.json`. | Run directory, `reclaim` |
| LLMCompiler ([arXiv 2312.04511](https://arxiv.org/abs/2312.04511)) | A planner emits a DAG, and a fetching unit dispatches each task as soon as its dependencies resolve, passing results by reference. | `next` is the fetching unit; upstream summaries are injected into prompts |
| ADaPT ([arXiv 2311.05772](https://arxiv.org/abs/2311.05772)) | Decompose **as needed**, only when the executor can't handle the task. | `NEEDS_EXPANSION` → runtime children, with a bounded depth |
| Graph Harness ([arXiv 2604.11378](https://arxiv.org/html/2604.11378v1)) | Output contracts for each node; bounded, escalating recovery: retry, then local repair, then give up and report. | Result validation, `max_attempts`, retry prompt with the exact error |
| Claude Code docs ([subagents](https://code.claude.com/docs/en/sub-agents)) | Parallel subagents come from several Agent calls in one message. The concurrency cap is 20 by default. Subagents do not see the parent conversation. The TaskCreate tools are not on by default for newer models. | Launch rule in SKILL.md; `max_parallel` ≤ 16; self-contained prompt files; state lives in our own file |

## Key decisions

**A deterministic scheduler instead of an LLM scheduler.** The ready set, cycle checks, coverage, retries and
dedupe are pure functions of the state file. This makes the orchestrator's behaviour predictable, lets a run resume
after a crash or context compaction, and keeps the orchestrator's context tiny: it only sees JSON status lines.

**Edges carry context.** Each node writes a summary of at most 150 words, made of facts rather than opinions. Its
dependents receive it, together with the intent summary. This is what a DAG adds over flat fan-out: leaves stop
rediscovering the same facts and stop contradicting each other.

**Critical path first.** When more nodes are ready than there are slots, `next` launches the ones with the longest
remaining chain of descendants, breaking ties by the number of security-sensitive files. Nodes on the critical
path stall the most work, so starting them first shortens the run.

**Verification is the quality lever, not scoring.** Every critical and major finding gets its own adversarial
verifier. The verifier sees neither the author's description nor the reviewer's confidence. Only `confirmed`
findings are reported as issues. Severe `unverifiable` findings go to a separate "needs a human look" section
rather than being silently dropped.

**Prompt-cache friendly.** Every prompt file starts with the same static text for its kind, and all node-specific
content comes last. Sibling subagents therefore share a cacheable prefix.

**Coverage is explicit.** `load` refuses a plan that leaves a changed file unowned. Declined scopes, failed nodes and
skipped files all appear under "Coverage gaps", so a clean review means *reviewed and clean*, not *silently skipped*.

## Roadmap

- **Feedback learning:** record whether each posted comment was resolved or dismissed, then filter new findings by
  similarity to past dismissed ones. This is the approach Greptile found most effective.
- **Redundant leaves for high-risk clusters:** two leaves read the same files in different orders, and findings
  that both report are marked corroborated. The dedupe step already credits multiple sources.
- **Workflow backend:** compile the DAG into a Claude Code dynamic workflow script (`parallel()` per wave,
  `agent({schema})` per node), for runs that are resumable and cached without an orchestrator in the loop.
- **Language-aware clustering:** build clusters from the import graph instead of directory structure.
