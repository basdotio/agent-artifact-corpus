# Task-aware execution contracts (default)

TuckBit is a **task-conditioned guide**, not an always-on instruction-rewriting engine.

## Derive the plan from authoritative inputs

Use the exact user request, applicable instructions the runtime actually exposed, its available tools, and declared project constraints. Preserve explicit exclusions, approvals, deadlines, output contract and acceptance criteria. Do not infer that a tool or source is enabled merely because its name exists in a local index.

1. Resolve the task goal and completion check from the user request.
2. Extract explicit constraints **without rewriting or weakening their meaning**.
3. Identify applicable host-provided policy and project instructions. The model may see them when the host injects them; an external script must not claim to read private hidden prompts.
4. Discover only the required tool metadata via native search or an approved local catalog. Tool names alone do not grant authorization.
5. Choose a single-agent or task-bounded parallel/continuous strategy only when explicitly requested or clearly justified.
6. Follow the actual agent runtime's available controls, limitations, and permissions. Never attempt to read or simulate hidden chain-of-thought.
7. Run appropriate targeted checks and mandatory integrated checks, then produce a compact evidence receipt.

## Model and host adaptation

- Codex: favor concise, explicit acceptance criteria, scoped paths, native skills, and selected reasoning settings; don't force parallel workers or rigid micro-instructions.
- Claude Code: allow subagents to receive task-bounded packets, respect their separate contexts, native tool search, approvals, and supported hooks.
- Gemini CLI: honor GEMINI.md context, skill activation consent, and the runtime's available hook lifecycle.
- Other supported hosts: fall back to portable skill instructions and conservative explicit task contracts. Don't invent host support.

These are **documented runtime behaviors**, not insight into private model reasoning. Different model versions may respond differently; optimize only from measured outcomes rather than guesses.

## Explicit local task compilation

For developers who want a no-model preview, use the optional local `scripts/plan_task.py` with a self-authored JSON contract. The file must be supplied explicitly. The script does not read AGENTS.md, CLAUDE.md, GEMINI.md, the user's global files, secret stores, or native permissions. References to instruction files in the JSON are informational paths—not automatically read or ranked as authoritative.

The compiler currently **does not semantically parse arbitrary freeform prompts**. That remains the job of the actual agent until we build and benchmark a properly scoped, opt-in runtime adapter.

A proposed plan is advisory: preserve the full user message and never substitute the generated summary for it.
