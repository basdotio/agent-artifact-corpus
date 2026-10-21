---
name: google-ads-search-terms-miner
description: Standard operating procedure for mining search terms, correlating spend with GA4 engagement, and harvesting negative keywords to eliminate ad budget leaks.
---

# Google Ads Search Terms Mining & Negative Keyword Harvesting

Autonomous agent playbook for identifying low-intent search queries, cross-referencing spend against GA4 on-site engagement, and deploying negative keyword shields.

## Core Mining Workflow

### Step 1: Harvest Search Terms & Costs
Fetch recent search queries triggered by broad/phrase match keywords:
```python
mine_search_terms_and_harvest_negatives(
    campaign_id="<CAMPAIGN_ID>",
    lookback_days=30,
    cost_threshold_eur=5.0
)
```

### Step 2: GA4 Cross-Referencing & Leak Detection
Evaluate terms against on-site engagement:
- **Cost > 10.00 EUR with 0 conversions:** Flag for immediate review.
- **Average Session Duration < 10 seconds (GA4 Bounce):** Indicates mismatch between user search intent and landing page copy.
- **Irrelevant Modifier Infiltration:** Terms containing competitor names, free download keywords, DIY tutorials, or wholesale intents.

### Step 3: Deploy Negative Keyword Shields
Add discovered waste terms to the campaign-level negative keyword list:
```python
add_negative_keywords(
    campaign_id="<CAMPAIGN_ID>",
    negative_keywords=["cheap", "free download", "diy tutorial", "vector stock"],
    match_type="EXACT"
)
```

### Step 4: Verify Shield Application
Confirm that the negative keyword shield is active and blocking unwanted search queries:
```python
audit_campaign_4level_shield(campaign_id="<CAMPAIGN_ID>")
```
