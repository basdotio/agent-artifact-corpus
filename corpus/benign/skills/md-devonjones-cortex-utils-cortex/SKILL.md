---
name: cortex
description: CLI for managing the Cortex email automation pipeline. Use this skill when the user wants to query emails, check queue status, trigger backfills, view classifications, or manage the email triage system. Triggers on keywords like "cortex", "email pipeline", "queue status", "classification", "backfill", "triage".
license: MIT (see LICENSE.txt)
metadata:
  version: 0.1.0
  author: Devon Jones
  repository: https://github.com/devonjones/cortex-utils
---

# Cortex Gateway CLI

Command-line interface for managing the Cortex email automation pipeline.

## Prerequisites

**Note**: This skill documentation lives in the `cortex-utils` repository but describes the `cortex` CLI tool provided by the separate `cortex-gateway` project. The gateway provides a unified REST API for Cortex services, and the CLI is the command-line interface to that API.

The `cortex` CLI is installed from the cortex-gateway package:

```bash
# Install from cortex-gateway repo
uv pip install git+https://github.com/devonjones/cortex-gateway.git

# Or if working locally
cd ~/Projects/cortex/gateway && uv pip install -e .
```

## Configuration

Set the gateway URL via environment variable or CLI flag:

```bash
export CORTEX_GATEWAY_URL=http://localhost:8097  # Example
cortex --url http://custom-host:8097 <command>
```

## Command Reference

### Global Options

| Option | Description |
|--------|-------------|
| `--url` | Gateway URL (env: `CORTEX_GATEWAY_URL`) |
| `-j, --json-output` | Output raw JSON instead of formatted tables |

### Health Check

```bash
cortex health
```

### Email Commands

```bash
# List emails (paginated)
cortex emails list [-n LIMIT] [--offset N] [-l LABEL_ID]

# Get email details
cortex emails get <gmail_id>

# Get email body (from DuckDB)
cortex emails body <gmail_id>

# Get plain text content
cortex emails text <gmail_id>

# Email statistics
cortex emails stats

# Emails by Gmail label ID (useful for backfill planning)
cortex emails by-label <label_id> [-n LIMIT]

# Classification breakdown for a sender (debug rules)
cortex emails sender <from_addr>

# Top labels by email count (rule coverage)
cortex emails distribution [-n LIMIT]

# Senders only in Uncategorized (missing rules)
cortex emails uncategorized [-n LIMIT]
```

### Queue Commands

```bash
# Queue depths by status
cortex queue stats

# List failed jobs
cortex queue failed [-q QUEUE_NAME] [-n LIMIT]

# Retry a failed job
cortex queue retry <job_id>

# Delete a failed job
cortex queue delete <job_id>

# Retry all failed jobs for a queue
cortex queue retry-all <queue_name>
```

### Backfill Commands (Re-enqueue existing emails)

```bash
# Trigger backfill to worker queue
cortex backfill trigger [-q QUEUE] [-d DAYS] [-l LABEL] [-p PRIORITY]
# Example: cortex backfill trigger -q triage -d 7 -p -100

# Check backfill status
cortex backfill status

# Cancel pending backfill jobs
cortex backfill cancel <queue_name>
```

### Triage Commands

```bash
# Classification statistics
cortex triage stats

# Re-run triage on emails
cortex triage rerun [-i GMAIL_ID]... [-l LABEL] [-s SENDER]... [-d DAYS] [-f] [-p PRIORITY]
# -f: force rerun even if pending
# -s, --sender: filter by sender email (supports glob with *). Can be specified multiple times.
# Examples:
#   cortex triage rerun -l Cortex/Uncategorized -d 30
#   cortex triage rerun -s "service@paypal.com" -d 7
#   cortex triage rerun -s "*@substack.com" -d 14
#   cortex triage rerun -s "service@paypal.com" -s "alerts@github.com" -d 7

# List recent classifications
cortex triage list [-n LIMIT] [-l LABEL]
```

### Sync Commands (Gmail API backfill)

```bash
# Trigger Gmail API historical sync
cortex sync backfill [-d DAYS] [-a YYYY-MM-DD]
# Example: cortex sync backfill -d 30

# List sync jobs
cortex sync jobs [-n LIMIT] [-s STATUS]

# Get specific job status
cortex sync job <job_id>

# Cancel a sync job
cortex sync cancel <job_id>
```

## Common Workflows

### Find missing rules

```bash
# Top senders without proper classification
cortex emails uncategorized -n 20

# Check how a sender's emails are classified
cortex emails sender notifications@example.com
```

### Debug classification issues

```bash
# See all labels and their counts
cortex emails distribution -n 100

# Find emails with a specific Gmail label
cortex emails by-label Label_117 -n 50
```

### Re-process emails

```bash
# Re-run triage on Uncategorized emails from last 7 days
cortex triage rerun -l Cortex/Uncategorized -d 7

# Re-run triage for specific sender
cortex triage rerun -s "service@paypal.com" -d 7

# Re-run triage for all senders from a domain (glob pattern)
cortex triage rerun -s "*@substack.com" -d 14

# Backfill specific emails to triage queue
cortex backfill trigger -q triage -l Label_123 -d 30
```

### Monitor queue health

```bash
# Check all queue depths
cortex queue stats

# View failed jobs
cortex queue failed -n 20

# Retry all failed labeling jobs
cortex queue retry-all labeling
```

### Historical sync from Gmail

```bash
# Sync last 30 days from Gmail API
cortex sync backfill -d 30

# Check sync progress
cortex sync jobs
```

## Config Management

Triage rules configuration is managed via the Gateway REST API (not CLI).

### Update Config Workflow

1. **Edit the rules YAML** at `~/cortex-config/rules.yaml` on Hades (or locally first)

2. **Upload via API**:
```bash
curl -X PUT http://10.5.2.21:8097/config \
  -H "Content-Type: text/plain" \
  -H "X-Created-By: your-name@context" \
  -H "X-Notes: Description of changes" \
  --data-binary @/path/to/rules.yaml
```

3. **Reload triage worker**:
```bash
ssh devon@10.5.2.21 "docker kill -s SIGHUP cortex-triage-worker"
```

4. **Verify reload**:
```bash
ssh devon@10.5.2.21 "docker logs cortex-triage-worker 2>&1 | grep -E 'reload|version' | tail -3"
```

### Config API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/config` | GET | Download active config as YAML |
| `/config` | PUT/POST | Upload new config version |
| `/config/validate` | POST | Validate YAML without saving |
| `/config/versions` | GET | List all config versions |
| `/config/versions/<n>` | GET | Download specific version |
| `/config/rollback/<n>` | POST | Rollback to version N |
| `/config/diff/<v1>/<v2>` | GET | Compare two versions |

### Validate Before Upload

```bash
curl -X POST http://10.5.2.21:8097/config/validate \
  -H "Content-Type: text/plain" \
  --data-binary @/path/to/rules.yaml
```

Returns `{"valid": true, "stats": {...}}` or `{"valid": false, "errors": [...]}`.

## Output Formats

By default, commands output formatted tables. Use `-j` for JSON:

```bash
# Table format (default)
cortex emails uncategorized -n 5

# JSON format
cortex -j emails uncategorized -n 5
```
