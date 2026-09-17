---
name: n8n
description: Design, build, debug, and operate n8n automations. Use when working with n8n workflows (JSON), nodes, expressions, triggers/webhooks, executions, credentials, or when calling the n8n public REST API to list/create/update/activate workflows and inspect executions.
---

# n8n

Use this skill to reliably work with n8n as an automation engine: design workflows, generate/import/export workflow JSON, debug executions, and (when enabled) operate n8n via its public REST API.

## Quick start (pick a path)

1) **Workflow design / changes (no API needed)**
- Clarify: trigger, inputs, outputs, schedule, error handling, idempotency.
- Produce: either a workflow JSON export, or step-by-step UI instructions to build it.
- For JSON structure + conventions: read `{baseDir}/references/workflow-json.md`.

2) **Operate n8n via REST API (recommended for repeatable ops)**
- Requires: `N8N_BASE_URL` + `N8N_API_KEY`.
- Use the helper script: `{baseDir}/scripts/n8n_api.py`.
- For auth/pagination details: read `{baseDir}/references/n8n-api.md`.

## Workflow decision tree

- If the user says **“here’s my exported workflow JSON”** → validate/modify JSON, return a new JSON export.
- If the user says **“build this in my n8n UI”** → produce exact node-by-node build instructions.
- If the user says **“deploy / activate / list / run / inspect executions”** → use the REST API helper script.
- If the user says **“webhook isn’t firing / workflow failed”** → use the debugging checklist in `{baseDir}/references/troubleshooting.md`.

## Core workflows

### A) Create or update a workflow (JSON-first)

1. Define the spec (minimal)
- Trigger (Webhook/Cron/Manual)
- Data sources + credentials
- Transformations (expressions/code)
- Side effects (write/send)
- Error strategy (continue on fail vs stop, retries, alerting)

2. Create/modify workflow JSON
- Prefer small diffs.
- Keep credentials references by name/id only; never embed secrets.
- See `{baseDir}/references/workflow-json.md`.

3. Import/update
- UI: import JSON.
- API: use `{baseDir}/scripts/n8n_api.py` (examples in `references/n8n-api.md`).

4. Activate + verify
- Activate workflow.
- Run a controlled test; inspect execution + node outputs.

### B) Debug an execution

1. Confirm the trigger event occurred (webhook hit / schedule ran / manual start).
2. Inspect the last execution and identify the failing node.
3. Check common causes: missing credentials, expression errors, data shape mismatch, rate limits.
4. Add observability: temporary Set/Code nodes to log key fields; consider an “Error Trigger” workflow.

Use `{baseDir}/references/troubleshooting.md` for a systematic checklist.

### C) Build a webhook-based integration

1. Choose trigger: **Webhook** node.
2. Decide contract: method, path, auth, expected JSON schema.
3. Add validation: fail fast for missing required fields.
4. Make it idempotent: detect duplicate events (store event id / hash).
5. Respond: set explicit HTTP response body/status.

## Security + safety

- Treat API keys as secrets. Never paste keys into workflow JSON, prompts, or logs.
- Use least privilege scopes where available.
- Prefer test instances / test workflows for destructive operations.

See `{baseDir}/references/security.md`.

## Bundled resources

- `{baseDir}/scripts/n8n_api.py`: lightweight CLI for n8n REST API calls (GET/POST/PATCH/DELETE).
- `{baseDir}/references/n8n-api.md`: auth, base URL conventions, pagination, example calls.
- `{baseDir}/references/workflow-json.md`: how to read/modify workflow exports safely.
- `{baseDir}/references/troubleshooting.md`: debugging playbook (webhooks, executions, credentials, data mapping).
- `{baseDir}/assets/workflow-spec-template.md`: a fill-in template for new automations.
