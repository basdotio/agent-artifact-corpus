# Adaptive execution workflows (default guidance)

Choose a workflow **after reading the actual user task**, relevant loaded instructions, available tools, and declared constraints. No profile may override higher-priority instructions, user consent, or mandatory checks.

## Depth: choose the lightest sufficient route

- **Fast:** obvious, low-risk localized change. Inspect exact target, edit, run focused proof, review the diff, finish. Do not force planning files or workers.
- **Standard:** normal feature or debugging slice. Establish expected and observed behavior; inspect relevant call path, implement fully, validate relevant scope, review, finish.
- **Deep:** high-risk, cross-cutting, security/auth, migration, concurrency, state/lifecycle or repeated failure. Map invariants and rollback, compare approaches, implement in increments, validate broadly when justified, independent review when risk warrants.

Never downgrade required verification simply because a workflow is called Fast. If the problem is complicated, preserve reasoning effort even when it costs more tokens.

## Mode: only when justified

- **Single (default):** short and dependent work.
- **Parallel (opt-in):** two or more independent deliverables, disjoint file ownership, explicit handoffs; coordinator integrates and validates. It may cost more tokens.
- **Continuous (opt-in):** real trigger, durable checkpoint, stop/retry limits, explicit authorization. Exit while idle; do not make a language model poll continuously.
- **Review-only:** inspect a frozen revision against specified criteria, report evidence; don't make edits without authorization.

## Respond to *observable evidence*, not imagined thoughts

- Repeated identical tool responses: narrow query, reuse reference, or stop.
- Multiple failing tests: shift to root-cause inspection; don't repeatedly rerun unchanged commands.
- Large outputs: retain full artifact securely and pass relevant excerpts.
- File ownership conflict: serialize writes or resolve interface contract.
- Missing official source/API evidence: expand only the relevant research.
- New code revision or changed dependencies: invalidate stale verification evidence.

For host-specific execution guidance, read only the relevant section of [task-aware context contracts](task-contract.md#model-and-host-adaptation).
