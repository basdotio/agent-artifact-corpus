---
name: tuck-bit
description: Plan efficient agent execution from the task's explicit constraints, available tools and applicable runtime instructions. Use for multi-step coding, tool-heavy work, subagent handoffs, repeated context reads, or costly test/build loops.
license: MIT
compatibility: Portable Agent Skills; optional Python 3.10+ local profile inspector.
metadata:
  author: TuckBit contributors
  version: "0.3.0"
---

# TuckBit: a just-in-time execution score for agents

Optimize **correct, verified outcomes per unit of resource use**, not token totals in isolation.

Four default capabilities: registry, context, verification, budget.
Optional: orchestration, metrics. Activate optional playbooks only when the task or user calls for them.

## Standard operating method

Start with **the exact user request**, explicitly available project/global/session guidance, and verified host tool availability. Preserve all requirements, constraints, prohibitions, approvals and checks. TuckBit never overrides higher-priority host rules or accesses private reasoning. See [task-aware context contracts](references/task-contract.md) only for complex or tool-heavy work.

1. Define the outcome, constraints, available evidence, risk, and a concrete stop condition. No elaborate plan for trivial requests.
   For a self-contained low-risk task, keep Fast mode to targeted inspection, the change and its required check; no runtime setup or delegation is needed.
2. Find the narrowest relevant code, docs, tool, or skill. Prefer exact identifiers and targeted file ranges; expand only when linked dependencies demand it.
3. Prefer the host's native on-demand tool search. Treat indexed catalog metadata as a discovery hint, **never as authority to execute**.
4. Use one agent for small work. If independent parallel tasks justify multiple agents, assign isolated ownership, evidence references and a concise result contract.
5. Preserve correctness: run focused checks during edits, then required integration/release checks against the final revision. Reuse evidence only if inputs and environment are equivalent.
6. Return a compact, verifiable receipt: changed files/commit, tests, risks, blockers and next step. Checkpoint longer work, and **stop** instead of repeatedly polling.

When the optional runtime is explicitly available, use bound observations to adapt the plan and record which recommendations were actually followed. Missing metrics or activation evidence stay unknown. See runtime guidance only when local deterministic tooling will help this task.

## Load only the relevant reference

- Task-conditioned execution and host adaptation: references/task-contract.md
- Adaptive Fast / Standard / Deep workflow selection: references/workflows.md
- Tool and skill discovery: references/registry.md
- Context packets and checkpoints: references/context.md
- Verification, builds and risks: references/verification.md
- Budgets and iteration limits: references/budget.md
- Optional multi-agent plan: references/orchestration.md
- Optional metrics and experiments: references/metrics.md
- Optional CLI, evidence packets, checkpoints and local workflow bookkeeping: references/runtime.md

## Mandatory boundaries

Do not skip required security checks, reduce correctness, invent benchmark figures, read credentials, suppress user approvals, perform unapproved destructive actions, cache side-effecting tool results as if they were fresh, or claim continuous monitoring. This skill guides behavior only; it does not enforce permissions outside the host's native policies.
