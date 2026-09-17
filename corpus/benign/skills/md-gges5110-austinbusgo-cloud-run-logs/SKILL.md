---
name: cloud-run-logs
description: Investigate Google Cloud Run service logs using gcloud CLI. Use this whenever the user wants to check logs, debug errors, investigate crashes, or monitor a Cloud Run service. Triggers on phrases like "check the logs", "what's in the logs", "investigate the logs", "Cloud Run errors", or any request to diagnose a deployed backend service.
---

# Cloud Run Log Investigation

Fetch and analyze logs from a Google Cloud Run service using `gcloud logging read`.

## Default service config for this repo

- **Service**: `austinbusgo-backend`
- **Region**: `us-central1`
- **Project**: `austin-bus-go`

## Fetching logs

Use `gcloud logging read` (not `gcloud beta run services logs read`, which requires the beta component):

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE" \
  --limit=50 \
  --format="table(timestamp,severity,textPayload,jsonPayload.message)" \
  --project=PROJECT
```

To filter by severity:
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE AND severity>=ERROR" \
  --limit=50 \
  --format="table(timestamp,severity,textPayload,jsonPayload.message)" \
  --project=PROJECT
```

To filter by time window (e.g., last hour):
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE" \
  --freshness=1h \
  --limit=100 \
  --format="table(timestamp,severity,textPayload,jsonPayload.message)" \
  --project=PROJECT
```

## Analysis workflow

1. Fetch recent logs (default: last 50 entries, all severities)
2. Identify the earliest ERROR or startup failure in the trace
3. Read the full stack trace — don't stop at the first line
4. Identify the root cause (the innermost exception, not the wrapping ones)
5. Check whether the error is a startup failure (worker boot), runtime error, or dependency issue
6. Suggest a fix with the relevant file path and line number when possible

## Common patterns in this project

- **Worker failed to boot** — Gunicorn workers crash during startup; look for the `Application startup failed` line and the exception above it
- **`sslmode` with asyncpg** — `DATABASE_URL` contains `?sslmode=require` which is a psycopg2 param; asyncpg needs `ssl=require` instead
- **Missing env vars** — `RuntimeError: Environment variable $X was not set`
- **Import errors** — missing dependency or wrong package name in `pyproject.toml`
- **DB connection refused** — Cloud SQL proxy not configured, wrong `DATABASE_URL` host

## Output format

After fetching and analyzing:

1. **Root cause** — one sentence
2. **Relevant log lines** — the key lines showing the error
3. **Suggested fix** — file path, what to change, and why
