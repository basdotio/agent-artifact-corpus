# Optional: bounded multi-agent orchestration

Use only when independent task boundaries and expected benefit justify parallelism.

The orchestrator owns requirements, integration, dependency graph, source-of-truth state and final response. Workers do not inherit each other's model context automatically.

For each worker assign: goal; baseline commit; owned files; related contracts; evidence references; non-goals; targeted validation; stop conditions; concise handoff schema.
Prefer independent worktrees; serialize edits touching shared interfaces. Never let two workers edit the same files without an agreed plan.
Workers return commits/diffs, focused test evidence, open risks and integration requirements rather than entire transcripts.
Poll only when necessary; avoid parallel review loops without new evidence.
Escalate if a worker needs to expand scope beyond agreed boundaries.
