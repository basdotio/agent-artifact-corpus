---
name: aaf-orchestration-occ
description: Helps build agent orchestration properly using the Orchestrator Capability Contract (OCC) and governance-above-orchestration pattern. Use when choosing or implementing orchestration (graphs, multi-agent, workflows), ensuring tool gateway is non-bypassable, or satisfying OCC requirements for audit and safety.
---

# AAF Orchestration and OCC (Orchestrator Capability Contract)

Use this skill when designing or implementing **agent orchestration** (graphs, multi-agent coordination, workflow engines) so that orchestration remains **pluggable** while **governance stays non-bypassable**. The framework introduces the **Orchestrator Capability Contract (OCC)** to define what any orchestration engine must support.

## Two layers: orchestration vs governance

- **Orchestration layer (pluggable):** Decides **what happens next**—control flow, graphs, state machines, agent handoffs, retries, branching, checkpointing, interrupts/resume. Orchestration tools (graph-based or multi-agent frameworks) live here. They are **replaceable**.
- **Governance layer (non-bypassable):** Decides **what is allowed**—ACC, budgets, approvals, tool allowlists/scopes, gate checks, audit, evidence, safe termination. This layer is the **authority boundary**; it must not depend on a specific orchestration vendor.

**Key constraint:** Orchestrators must **never** call tools directly. All tool actuation must go through the **Tool Gateway** so permissions, budgets, approvals, and auditability remain non-bypassable.

## Orchestrator Capability Contract (OCC)

Any orchestration engine is acceptable **if** it supports the following. Use this as a checklist when selecting or building orchestration:

1. **Serializable run state**  
   Orchestration state can be persisted and replayed (for audit and recovery).

2. **Checkpoint/resume semantics**  
   The system can checkpoint at known boundaries and resume deterministically.

3. **Interrupts**  
   The orchestrator can **pause** for approvals, scope escalation, or safety review—and then **continue safely** (structured resume, not ad-hoc).

4. **Structured event emission**  
   The orchestrator emits **machine-readable events** for tracing and evidence capture (so governance and observability do not depend on proprietary formats).

5. **Termination controls**  
   Hard limits on steps/loops/time with **deterministic stop** behaviour (no “best effort” only).

6. **Gateway-only tool invocation**  
   The orchestrator does **not** call tools directly; all actuation flows through the **Tool Gateway**. Governance primitives (ACC, budgets, approvals, verification gates) sit above orchestration and constrain it.

If an engine cannot satisfy these, treat it as **runtime plumbing** only and do not rely on it for audit, recovery, or safety; add a shim or gateway so that tool calls and critical transitions still go through your governance layer.

## When to use multi-agent / orchestrator

- **Single-agent first:** Prefer one agent with incremental tools; add orchestration only when task structure justifies it (e.g. parallelizable research, retrieval, summarization). Avoid premature orchestration overhead.
- **Central orchestrator as validation bottleneck:** If you do scale to multiple agents, prefer a **central orchestrator** that validates intermediate outputs, enforces budgets, and prevents errors from propagating. Research shows independent multi-agent systems can amplify errors (e.g. 17×) while centralized coordination can contain amplification (e.g. ~4×) by acting as a validation bottleneck.
- **Orchestration ≠ governance:** Adopt orchestration tools for **velocity and coordination mechanics**; keep **enforcement and authority transitions** in the governance layer (ACC, Tool Gateway, OCC requirements) so the system stays safe as orchestration technology changes.

## Where OCC and ACC meet

- The **ACC** (Agent Control Contract) defines the **policy** (autonomy, tools, budgets, DoD, escalation). It is read by the platform and/or supervisor.
- The **orchestration** layer executes the plan and respects **interrupts** and **budgets**; it does not decide what is allowed—it asks the gateway and obeys ACC-driven limits.
- The **Tool Gateway** is the single place where “can this tool be called with these args?” is answered; the orchestrator only **requests** calls and receives allow/block/approval_required. So: **OCC** = what the orchestrator must support; **ACC** = what the run is allowed to do; **Gateway** = where it is enforced.

## Checklist for building orchestration properly

- [ ] Orchestration engine satisfies OCC: serializable state, checkpoint/resume, interrupts, structured events, termination controls, gateway-only tool invocation.
- [ ] No direct tool calls from the orchestrator; all go through the Tool Gateway.
- [ ] Governance primitives (ACC, budgets, approvals, verification gates, audit) sit **above** orchestration and constrain it.
- [ ] Single-agent default; add multi-agent/orchestrator only when task structure justifies it; prefer central orchestrator as validation bottleneck.
- [ ] Orchestration is treated as **replaceable**; governance and operational semantics remain stable if you swap the engine.

## Additional resources

- Performance pillar (OCC definition): `docs/10-pillar-performance.md`
- Introduction (orchestration vs governance layers): `docs/02-introduction.md`
- Ecosystem interoperability (governance above orchestration): `docs/14-ecosystem-interoperability.md`
- Reliability (orchestrator as control point): `docs/07-pillar-reliability.md`
- Whitepaper: https://agenticaf.io/
