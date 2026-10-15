# Async UI State

Read when the changed surface searches, submits, paginates, retries, or can be left during a request. These are implementation guards for the agreed UX flow; reuse the project's state owner and persistence rules.

1. **Define the states.** Distinguish initial loading, refresh with existing content, success, empty, recoverable error and stale/offline data. Preserve user input and usable last-good content. Render partial success explicitly rather than presenting it as complete.
2. **Own the operation.** Block duplicate submissions while pending. For searches or filters, cancel superseded requests if supported; otherwise compare a request ID/query snapshot before applying either success or error. Pagination deduplicates IDs and stops at the authoritative end marker.
3. **Handle leaving.** Dispose widget-owned timers, controllers and subscriptions. After awaits, check mounted state before context/setState work. Define whether the state owner continues or cancels an operation when navigating away; leaving a screen is not proof the server cancelled it.
4. **Recover accurately.** Keep the same input for retry. After an uncertain write outcome, reconcile with the authoritative state or existing idempotency mechanism before repeating the write. A timeout does not prove failure. Money, permissions and irreversible actions show confirmed success only after authoritative completion.
5. **Prove changed branches.** Exercise the affected failure path and repeated action. When stale requests or navigation are possible, test reversed completion order and leaving before completion. State what persists, what cancels, and what remains unverified.

Backend idempotency, offline queue design and authorization architecture are outside this UI skill. Preserve their existing contracts; flag a missing contract instead of inventing a UI-only guarantee.
