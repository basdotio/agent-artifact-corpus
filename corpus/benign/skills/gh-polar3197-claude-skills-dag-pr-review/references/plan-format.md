# plan.json format

`dagctl.py autoplan` writes a draft plan. You can edit it, and `dagctl.py load` validates it.

```json
{
  "nodes": [
    {"id": "intent", "kind": "intent", "title": "PR intent and risk map", "deps": [], "files": ["..."]},
    {"id": "cluster-billing", "kind": "cluster", "title": "Billing: cents migration", "deps": ["intent"],
     "files": ["src/billing/money.py", "src/billing/charge.py", "src/billing/refund.py"],
     "focus": "Money moved from float to integer cents; check every conversion boundary"},
    {"id": "leaf-billing-charge", "kind": "leaf", "title": "charge.py", "deps": ["cluster-billing"],
     "files": ["src/billing/charge.py"]},
    {"id": "leaf-billing-refund", "kind": "leaf", "title": "refund.py (first half)", "deps": ["cluster-billing"],
     "files": ["src/billing/refund.py:1-220"]},
    {"id": "x-security", "kind": "crosscut", "lens": "security", "title": "Security", "deps": ["intent"],
     "files": ["src/api/refunds.py"]},
    {"id": "x-api", "kind": "crosscut", "lens": "api-compat", "title": "Public API compatibility",
     "deps": ["cluster-billing"], "files": ["src/billing/money.py"], "model": "opus"}
  ],
  "skipped": [
    {"path": "fixtures/big.json", "reason": "test fixture data"}
  ]
}
```

## Node fields

| field | required | notes |
|---|---|---|
| `id` | yes | `[A-Za-z0-9][A-Za-z0-9._-]*`, unique. Used as the result file name. |
| `kind` | yes | `intent`, `cluster`, `leaf` or `crosscut`. Verify nodes are created later by `collect`. |
| `deps` | yes | Ids whose `summary` this node needs. **An edge means "needs context from", not merely "runs after".** |
| `files` | leaf, cluster, crosscut | Changed paths, optionally with a line range in the new file: `path:10-80`. |
| `lens` | crosscut | `security`, `tests`, `performance`, `guidelines`, `api-compat`, `concurrency`, `data-migration` or `general`. |
| `title`, `focus` | no | Shown to the agent. A sharp `focus` is the cheapest way to improve a node. |
| `model` | no | Hint passed back in `next` output (for example `opus` for security, `haiku` for docs leaves). |
| `redact_description` | no | Defaults to true for everything except `intent`. Leave it. |

## Validation rules

- There must be exactly one `intent` node, and it has no deps.
- Deps must exist, and there are no self-dependencies or cycles. `load` reports the ids involved in a cycle.
- Depth: the longest dependency chain is at most 5.
- Node count is at most the tier cap (6, 16 or 40). At runtime, expansion may grow the graph to 1.5 times the cap.
- Every file in the diff must be owned by at least one `leaf`, listed in `skipped` with a reason, or already
  auto-skipped because it is generated, binary or deleted.
- Every file listed in the plan must be part of the diff.

## Good graph shapes

- **Clusters earn their place** when files interact, for example an API handler, its service and its model. A
  cluster with a single leaf is overhead, so point the leaf at `intent` directly.
- **Leaves** should own about 400 changed lines or fewer. For bigger files, use line ranges, or let the leaf request
  expansion at runtime.
- **Crosscuts** usually depend only on `intent`, so they start in wave 2 and run alongside clusters. Make one
  depend on a cluster only when it truly needs that cluster's summary. This lengthens the critical path.
- Put security-sensitive files in their own leaves, so the security lens and the leaf review them independently.
