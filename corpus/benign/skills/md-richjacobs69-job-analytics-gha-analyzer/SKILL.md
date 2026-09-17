---
name: gha-analyzer
description: Analyze GitHub Actions workflow runs for the job-analytics scraping pipeline. Use when asked to analyze GHA logs, debug workflow failures, optimize batch timing, investigate classifier or deduplication issues, or review pipeline performance across Greenhouse, Lever, Ashby, Workable, and SmartRecruiters sources.
---

# GitHub Actions Pipeline Analyzer

Analyze GitHub Actions workflow runs for debugging, optimization, and issue detection in the job-analytics scraping pipeline.

## When to Use This Skill

Trigger when user asks to:
- Analyze GitHub Actions logs or workflow runs
- Debug workflow failures or errors
- Optimize batch timing or parallelization
- Investigate classifier issues (job_family, skills extraction)
- Review deduplication behavior
- Check pipeline health (Greenhouse, Lever, Ashby, Workable, SmartRecruiters)
- Find rate limiting or API issues
- Review pipeline data quality
- Analyze costs and performance trends

## Prerequisites: Verify GitHub API Access

### Preferred: GitHub CLI (`gh`)

The `gh` CLI is installed and authenticated. **Prefer `gh` over raw API calls** -- it handles auth, pagination, and JSON parsing automatically.

```bash
# Verify gh is available and authenticated
gh auth status

# Quick test - list recent workflow runs
gh run list --repo RichJacobs69/job-analytics --limit 5
```

**Common `gh` commands for this skill:**

```bash
# List runs (all workflows)
gh run list --repo RichJacobs69/job-analytics --limit 20

# List runs for a specific workflow
gh run list --repo RichJacobs69/job-analytics --workflow scrape-greenhouse.yml --limit 10

# List only failed runs
gh run list --repo RichJacobs69/job-analytics --status failure --limit 10

# View a specific run's details
gh run view <RUN_ID> --repo RichJacobs69/job-analytics

# View run logs
gh run view <RUN_ID> --repo RichJacobs69/job-analytics --log

# View failed step logs only
gh run view <RUN_ID> --repo RichJacobs69/job-analytics --log-failed

# List workflow files
gh workflow list --repo RichJacobs69/job-analytics

# View workflow details
gh workflow view scrape-greenhouse.yml --repo RichJacobs69/job-analytics

# Get run data as JSON (for scripting)
gh run list --repo RichJacobs69/job-analytics --json databaseId,name,status,conclusion,createdAt --limit 10

# Get job-level details as JSON
gh run view <RUN_ID> --repo RichJacobs69/job-analytics --json jobs

# Use gh api for advanced queries
gh api repos/RichJacobs69/job-analytics/actions/runs?per_page=5 --jq '.workflow_runs[] | "\(.id) | \(.name) | \(.conclusion) | \(.created_at)"'
```

### Fallback: GITHUB_TOKEN + Python requests

If `gh` is not available, fall back to the GITHUB_TOKEN approach:

```bash
# Check if GITHUB_TOKEN is set
grep GITHUB_TOKEN .env
```

**Expected:** Line showing `GITHUB_TOKEN=ghp_...` or `GITHUB_TOKEN=github_pat_...`

```bash
# Test API connection via Python
python -c "import os; from dotenv import load_dotenv; load_dotenv(); import requests; r = requests.get('https://api.github.com/repos/richjacobs/job-analytics/actions/runs?per_page=1', headers={'Authorization': f'token {os.getenv(\"GITHUB_TOKEN\")}'}); print('OK' if r.status_code == 200 else f'Error: {r.status_code}')"
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `gh` not found | Install via `winget install GitHub.cli` then `gh auth login --web` |
| `gh` not authenticated | Run `gh auth login --web` and follow browser flow |
| `GITHUB_TOKEN` not in .env | Create token at https://github.com/settings/tokens with `repo` and `workflow` scopes |
| `401 Unauthorized` | Token expired or invalid - regenerate at GitHub |
| `403 Forbidden` | Token lacks required scopes - needs `repo` and `workflow` |
| `404 Not Found` | Check repository name spelling |

**If neither `gh` nor GitHub API access is available, inform the user and stop analysis.**

## Repository Context

The job-analytics repository has six scraping workflows and two maintenance workflows:

| Workflow | Schedule | Description |
|----------|----------|-------------|
| `scrape-greenhouse.yml` | Mon/Tue/Thu/Fri 7AM UTC | Batched (4 batches, ~100 companies each) |
| `scrape-lever.yml` | Mon/Wed/Fri 6PM UTC | 182 companies |
| `scrape-ashby.yml` | Tue/Thu 6PM UTC | 169 companies |
| `scrape-workable.yml` | Wed/Sat 6PM UTC | 135 companies |
| `scrape-smartrecruiters.yml` | Thu/Sun 8PM UTC | 35 companies |
| `url-validation-stats.yml` | Mon-Fri 9AM UTC | URL validation + employer stats |
| `refresh-employer-metadata.yml` | Sun 8AM UTC | Seed, enrich, backfill |

## Analysis Workflow

**Note:** All commands use the GitHub REST API via Python. Ensure `GITHUB_TOKEN` is set in `.env`.

### Step 1: Fetch Recent Runs

```python
# List recent workflow runs (all workflows)
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
r = requests.get('https://api.github.com/repos/richjacobs/job-analytics/actions/runs?per_page=20',
    headers={'Authorization': f'token {token}'})
for run in r.json().get('workflow_runs', []):
    print(f\"{run['id']} | {run['name'][:30]:30} | {run['status']:12} | {run['conclusion'] or 'running':10} | {run['created_at'][:10]}\")
"

# List runs for specific workflow (by workflow file name)
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
# Get workflow ID first
wf = requests.get('https://api.github.com/repos/richjacobs/job-analytics/actions/workflows',
    headers={'Authorization': f'token {token}'}).json()
wf_id = next((w['id'] for w in wf['workflows'] if 'greenhouse' in w['path']), None)
if wf_id:
    r = requests.get(f'https://api.github.com/repos/richjacobs/job-analytics/actions/workflows/{wf_id}/runs?per_page=10',
        headers={'Authorization': f'token {token}'})
    for run in r.json().get('workflow_runs', []):
        print(f\"{run['id']} | {run['status']:12} | {run['conclusion'] or 'running':10} | {run['created_at']}\")
"

# Check for failed runs
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
r = requests.get('https://api.github.com/repos/richjacobs/job-analytics/actions/runs?status=failure&per_page=10',
    headers={'Authorization': f'token {token}'})
for run in r.json().get('workflow_runs', []):
    print(f\"{run['id']} | {run['name'][:30]:30} | {run['created_at'][:10]}\")
"
```

### Step 2: Get Detailed Run Information

```python
# View specific run details (replace RUN_ID)
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
RUN_ID = 'REPLACE_ME'
r = requests.get(f'https://api.github.com/repos/richjacobs/job-analytics/actions/runs/{RUN_ID}',
    headers={'Authorization': f'token {token}'})
run = r.json()
print(f\"Run: {run['name']}\")
print(f\"Status: {run['status']} / {run['conclusion']}\")
print(f\"Started: {run['created_at']}\")
print(f\"Updated: {run['updated_at']}\")
print(f\"URL: {run['html_url']}\")
"

# Get jobs for a run
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
RUN_ID = 'REPLACE_ME'
r = requests.get(f'https://api.github.com/repos/richjacobs/job-analytics/actions/runs/{RUN_ID}/jobs',
    headers={'Authorization': f'token {token}'})
for job in r.json().get('jobs', []):
    print(f\"{job['name']}: {job['conclusion']} ({job['started_at']} - {job['completed_at']})\")
"

# Download logs for a specific run (returns zip file URL)
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
RUN_ID = 'REPLACE_ME'
r = requests.get(f'https://api.github.com/repos/richjacobs/job-analytics/actions/runs/{RUN_ID}/logs',
    headers={'Authorization': f'token {token}'}, allow_redirects=False)
print(f\"Logs URL: {r.headers.get('Location', 'Not available')}\")
"
```

### Step 3: Analyze for Specific Issues

## Issue Detection Patterns

### 1. Classifier Issues

Look for these patterns in logs:

```
[ERROR] Failed to parse.*response as JSON
[WARNING] Unknown job_subfamily
job_family auto-assigned:
Skills enriched: \d+/\d+ mapped
```

**Common Classifier Problems:**
- `Unknown job_subfamily` - LLM returned invalid subfamily code
- JSON parse errors - LLM response malformed
- Skills mapping failures - Unknown skills not in ontology
- `out_of_scope` misclassification - Title filtering missed edge case

### 2. Deduplication Issues

Look for these patterns:

```
was_duplicate.*True
action.*updated|inserted|skipped
duplicate key.*unique constraint
23505.*error
```

**Dedupe Metrics to Extract:**
- Count of `was_duplicate: True` vs `False`
- Ratio of `inserted` vs `updated` vs `skipped`
- Cross-source duplicates (same job from multiple ATS sources)

### 3. Timing and Performance

Look for these patterns:

```
GREENHOUSE BATCH \d+
Companies: \d+ of \d+
Range:.*->
Indices: \[\d+:\d+\]
Cost: \$[\d.]+
Latency: \d+ms
```

**Timing Metrics to Extract:**
- Total run duration per workflow
- Per-company scraping time (Greenhouse: ~47 sec each)
- LLM classification latency (typical: 200-500ms per job)
- Rate limit delays

### 4. Rate Limiting and API Errors

Look for these patterns:

```
rate limit|429|too many requests
RetryError|retry|backoff
APIConnectionError|timeout
quota exceeded|billing
```

**API Issues:**
- Gemini/Claude rate limits
- Supabase connection errors
- Greenhouse/Lever scraping blocks

## Extended Pipeline Observations

### 6. Data Quality Checks

Look for these patterns indicating data quality issues:

```
# Missing required fields
Missing city_code
Missing employer_name
Missing title_display

# Working arrangement issues
working_arrangement.*unknown
working_arrangement.*null

# Salary extraction
salary_min.*null.*salary_max.*null
currency.*null

# Location parsing
locations.*\[\]
city_code.*unk
```

**Data Quality Metrics:**
- Null rate for key fields (seniority, working_arrangement, salary)
- `unk` city_code frequency (location extraction failures)
- Empty skills array rate
- Working arrangement distribution (should see mix of onsite/hybrid/remote)

### 7. Company-Specific Issues

Look for patterns by company:

```
# Company timeout/failure patterns
Scraping.*failed
No jobs found for
timeout.*exceeded

# Companies with unusual counts
Jobs found: 0
Jobs found: [0-2]
Jobs found: [100+]
```

**Company Health Checks:**
- Companies consistently returning 0 jobs (careers page changed?)
- Companies timing out (too many jobs or slow page?)
- Companies with suspiciously high job counts (might be duplicating)
- New companies not appearing in logs (config not updated?)

### 8. Cross-Source Analysis

When analyzing across sources:

```
# Source identification
data_source.*greenhouse|lever|ashby|workable|smartrecruiters

# Merge indicators
deduplicated.*True
merged_from_source
original_url_secondary
```

**Cross-Source Metrics:**
- Cross-ATS overlap rate (same job appearing in multiple sources)
- Classification accuracy by source

### 9. Agency Detection Effectiveness

Look for agency-related patterns:

```
# Agency blocklist hits
agency.*blocked|filtered
agency_blacklist
Blocked agency

# Agency classification
is_agency.*True
agency_confidence.*high|medium
```

**Agency Metrics:**
- Jobs blocked by agency blocklist
- Jobs classified as agency that slipped through
- False positive rate (legitimate companies flagged)
- New agencies appearing (add to blocklist)

### 10. Skills Extraction Quality

Look for skills-related patterns:

```
Skills enriched: \d+/\d+
family_code.*null
skills.*\[\]
MAXIMUM 20 skills
```

**Skills Metrics:**
- Average skills extracted per job
- Unmapped skills rate (family_code: null)
- Most common unmapped skills (candidates for ontology)
- Skills distribution by job family (data jobs should have SQL/Python)

### 11. LLM Cost Tracking

Look for cost patterns:

```
Cost: \$[\d.]+
total_cost.*[\d.]+
Token usage: \d+ input, \d+ output
Latency: \d+ms
```

**Cost Metrics:**
- Total cost per workflow run
- Average cost per job (~$0.00388 for Claude Haiku)
- Cost trends over time (increasing = more jobs or longer descriptions)
- Provider comparison (Gemini 88% cheaper than Claude)

### 12. Job Flow Analysis

Track job progression through pipeline:

```
# Raw job insertion
insert_raw_job_upsert
action.*inserted

# Classification
classify_job
job_family.*product|data|delivery|out_of_scope

# Enriched job creation
insert_enriched_job
job_hash
```

**Flow Metrics:**
- Raw jobs -> Classified jobs ratio (should be ~1:1)
- Out of scope rejection rate (with title filtering, should be low)
- Classification error rate
- Enriched job upsert vs insert rate

### 13. Workflow Timing Patterns

Analyze timing trends:

```python
# Get timing for last 10 Greenhouse runs
python -c "
import os, requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
wf = requests.get('https://api.github.com/repos/richjacobs/job-analytics/actions/workflows',
    headers={'Authorization': f'token {token}'}).json()
wf_id = next((w['id'] for w in wf['workflows'] if 'greenhouse' in w['path']), None)
if wf_id:
    r = requests.get(f'https://api.github.com/repos/richjacobs/job-analytics/actions/workflows/{wf_id}/runs?per_page=10',
        headers={'Authorization': f'token {token}'})
    for run in r.json().get('workflow_runs', []):
        start = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
        duration = (end - start).total_seconds() / 60
        print(f\"{run['id']} | {run['conclusion']:10} | {duration:5.1f} min | {run['created_at'][:10]}\")
"
```

**Timing Benchmarks:**
| Workflow | Expected Duration | Alert Threshold |
|----------|------------------|-----------------|
| Greenhouse Batch | 45-90 min | >100 min |
| Lever | 10-20 min | >25 min |
| Ashby | 10-20 min | >30 min |
| Workable | 10-20 min | >30 min |
| SmartRecruiters | 5-15 min | >25 min |

### 14. Workflow Summary Artifacts

Check step summary output:

```python
# View run summary
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
RUN_ID = 'REPLACE_ME'
r = requests.get(f'https://api.github.com/repos/richjacobs/job-analytics/actions/runs/{RUN_ID}',
    headers={'Authorization': f'token {token}'})
run = r.json()
print(f\"Run: {run['name']}\")
print(f\"Status: {run['status']} / {run['conclusion']}\")
print(f\"Commit: {run['head_sha'][:7]}\")
print(f\"URL: {run['html_url']}\")
"
```

**Summary Verification:**
- Expected batch count matches actual
- Company range looks correct
- No gaps in batch coverage (Batch 1, 2, 3, 4)

## Diagnostic Commands

### Quick Health Check

```python
# Last 5 runs status summary
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
r = requests.get('https://api.github.com/repos/richjacobs/job-analytics/actions/runs?per_page=5',
    headers={'Authorization': f'token {token}'})
for run in r.json().get('workflow_runs', []):
    print(f\"{run['name'][:35]:35} | {run['status']:12} | {run['conclusion'] or 'running':10} | {run['created_at']}\")
"

# Check if any workflow is currently running
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
r = requests.get('https://api.github.com/repos/richjacobs/job-analytics/actions/runs?status=in_progress',
    headers={'Authorization': f'token {token}'})
runs = r.json().get('workflow_runs', [])
if runs:
    for run in runs:
        print(f\"RUNNING: {run['name']} (ID: {run['id']}) started {run['created_at']}\")
else:
    print('No workflows currently running')
"
```

### Deep Dive on Failures

```python
# Get failed run details and job info
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
RUN_ID = 'REPLACE_ME'
# Get jobs
r = requests.get(f'https://api.github.com/repos/richjacobs/job-analytics/actions/runs/{RUN_ID}/jobs',
    headers={'Authorization': f'token {token}'})
for job in r.json().get('jobs', []):
    print(f\"Job: {job['name']} - {job['conclusion']}\")
    for step in job.get('steps', []):
        status = '[FAIL]' if step['conclusion'] == 'failure' else '[OK]'
        print(f\"  {status} {step['name']}\")
"
```

### Performance Analysis

```python
# Get timing data for recent runs across all workflows
python -c "
import os, requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
r = requests.get('https://api.github.com/repos/richjacobs/job-analytics/actions/runs?per_page=15',
    headers={'Authorization': f'token {token}'})
print(f\"{'ID':12} | {'Workflow':35} | {'Duration':10} | {'Status':10} | Date\")
print('-' * 90)
for run in r.json().get('workflow_runs', []):
    start = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
    duration = (end - start).total_seconds() / 60
    print(f\"{run['id']} | {run['name'][:35]:35} | {duration:6.1f} min | {run['conclusion'] or 'running':10} | {run['created_at'][:10]}\")
"
```

### Database State Check (via Supabase)

After workflow runs, verify database state:

```python
# Check recent job counts
python wrappers/check_pipeline_status.py

# Verify no orphaned raw jobs
SELECT COUNT(*) FROM raw_jobs WHERE id NOT IN (SELECT raw_job_id FROM enriched_jobs);
```

## Output Format

When analyzing, produce a structured report:

```markdown
## GHA Pipeline Analysis Report

**Run Analyzed:** [RUN_ID] - [Workflow Name]
**Date:** [Date]
**Status:** [success/failure/cancelled]
**Duration:** [X minutes]

### Summary Stats
- Jobs Processed: X
- New Jobs Inserted: Y
- Duplicates Updated: Z
- Out of Scope: W

### Issues Found

1. **[Issue Category]** - [Severity: Critical/Warning/Info]
   - Description: [What happened]
   - Log excerpt: [Relevant log lines]
   - Suggested fix: [Action to take]

### Data Quality

| Metric | Value | Expected | Status |
|--------|-------|----------|--------|
| Null seniority rate | X% | <20% | OK/WARN |
| Unknown working_arrangement | X% | <10% | OK/WARN |
| Unmapped skills | X% | <15% | OK/WARN |
| Agency detection | X blocked | N/A | INFO |

### Performance

| Metric | Value | Benchmark |
|--------|-------|-----------|
| Total Duration | X min | 45-90 min |
| Avg per Company | X sec | ~47 sec |
| LLM Latency | X ms | <500 ms |
| Total Cost | $X.XX | ~$0.50/batch |

### Recommendations

1. [Optimization suggestion]
2. [Config change needed]
3. [Monitoring alert to add]
```

## Common Fixes

| Issue | Fix |
|-------|-----|
| Classifier JSON parse error | Check if job description truncated; increase token limit |
| Unknown job_subfamily | Add to `config/job_family_mapping.yaml` |
| High duplicate rate | Normal for incremental runs; check if >90% suggests stale data |
| Rate limit errors | Reduce batch size or add delays |
| Timeout on Greenhouse | Increase `timeout-minutes` or reduce batch size |
| Company returns 0 jobs | Verify careers page URL in company_ats_mapping.json |
| High unmapped skills | Add common skills to `config/skill_family_mapping.yaml` |
| Agency slipping through | Add to `config/agency_blacklist.yaml` |
| Location parse failures | Check `config/location_mapping.yaml` patterns |

## Files to Reference

- `.github/workflows/scrape-greenhouse.yml` - Greenhouse workflow config
- `.github/workflows/scrape-lever.yml` - Lever workflow config
- `pipeline/classifier.py` - LLM classification logic
- `pipeline/db_connection.py` - Deduplication logic (generate_job_hash, upsert)
- `pipeline/agency_detection.py` - Agency pattern matching
- `config/greenhouse/company_ats_mapping.json` - Greenhouse company list (302)
- `config/lever/company_mapping.json` - Lever company list (61)
- `config/job_family_mapping.yaml` - Subfamily -> family mapping
- `config/skill_family_mapping.yaml` - Skill family assignments
- `config/agency_blacklist.yaml` - Blocked recruitment agencies
- `config/location_mapping.yaml` - Location pattern matching
- `docs/epic7_automation_planning.md` - Automation architecture
