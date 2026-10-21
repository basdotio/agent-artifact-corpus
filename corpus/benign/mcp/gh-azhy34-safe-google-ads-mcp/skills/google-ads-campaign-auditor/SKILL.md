---
name: google-ads-campaign-auditor
description: Standard operating procedure (SOP) for running 4-level holistic campaign quality audits and diagnosing performance bottlenecks via Safe Google Ads FastMCP.
---

# Google Ads 4-Level Campaign Quality Auditor

This skill defines the autonomous agent workflow for conducting deterministic 4-level campaign audits on Google Ads search campaigns without risking production state.

## Core Audit Workflow

### Step 0: Mandatory Preflight Gate Check
Before calling any diagnostic or mutation tool, verify system health:
```python
preflight_log_check()
```
- If verdict is `ATTENTION`, surface anomalies to the human operator before proceeding.
- If verdict is `OK`, the execution gate opens.

### Step 1: Execute 4-Level Shield Facade
Call the transactional facade tool:
```python
audit_campaign_4level_shield(campaign_id="<CAMPAIGN_ID>")
```

The facade inspects four critical levels in a single transaction:
1. **Level 1 (Bidding Strategy):** Validates strategy alignment (e.g., `TARGET_SPEND` with bounded CPC ceilings).
2. **Level 2 (Ad Group Structure & Keywords):** Checks keyword match types, status, and duplication across groups.
3. **Level 3 (Responsive Search Ads):** Verifies that active ads meet the strict 15-headline and 4-description matrix and checks Ad Strength.
4. **Level 4 (Negative Keywords & Waste Shield):** Verifies attached negative keyword lists to prevent search term cannibalization.

### Step 2: Interpreting Audit Verdicts
- **PASS (100/100):** Campaign is perfectly optimized and meets all enterprise quality shields.
- **NEEDS_REVIEW (< 100):** Inspect the `deductions` array:
  - If missing headlines/descriptions: invoke `google-ads-rsa-writer` skill.
  - If missing negative keywords: invoke `google-ads-search-terms-miner` skill.
  - If bid ceiling suboptimal: invoke `google-ads-bid-ladder` skill.

### Step 3: Observability Verification
Query the W3C trace breakdown to verify latency and upstream gRPC call count:
```python
get_cloud_trace(trace_id="<TRACE_ID>")
```
