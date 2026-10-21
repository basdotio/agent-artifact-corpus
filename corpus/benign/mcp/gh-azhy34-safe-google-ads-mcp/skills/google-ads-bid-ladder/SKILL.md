---
name: google-ads-bid-ladder
description: Standard operating procedure for stepping CPC bid ceilings on Maximize Clicks (TARGET_SPEND) campaigns using deterministic ±0.05 EUR increments.
---

# Google Ads Deterministic Bid Ladder Manager

Autonomous guideline for managing CPC bids and campaign delivery thresholds under Maximize Clicks (`TARGET_SPEND`) portfolio strategies.

## Critical Bidding Rule
Under Google Ads `TARGET_SPEND` strategies:
- Ad group-level and keyword-level `cpc_bid_micros` are **completely ignored** by the bidding algorithm.
- The **only effective lever** is the campaign CPC bid ceiling (`campaign.target_spend.cpc_bid_ceiling_micros`).

## The Bounded Stepping Protocol

### Step 0: Traffic & Delivery Baseline
Always inspect the 14-day factual baseline before stepping bids:
```python
get_daily_performance(campaign_id="<CAMPAIGN_ID>", lookback_days=14)
get_impression_share_loss(campaign_id="<CAMPAIGN_ID>")
```
Evaluate:
- Is Impression Share lost to Budget (`search_budget_lost_impression_share`)? -> Do not increase bid; address daily budget.
- Is Impression Share lost to Rank (`search_rank_lost_impression_share`)? -> Consider a bid step.

### Step 1: Execute Stepped Bid Adjustment
Bids must never be changed arbitrarily. Stepping is strictly locked to `±0.05 EUR`:
```python
# To raise the ceiling by 0.05 EUR:
step_bid_threshold(campaign_id="<CAMPAIGN_ID>", delta="+0.05")

# To lower the ceiling by 0.05 EUR:
step_bid_threshold(campaign_id="<CAMPAIGN_ID>", delta="-0.05")
```

### Step 2: Safeguards & Invariants
- Minimum floor: `0.10 EUR`
- Maximum ceiling: `3.00 EUR`
- Cooldown period: Wait at least 24–48 hours after a step to evaluate Impression Share and CPC changes before stepping again.
- Auto-validation: The Pydantic Execution Shield automatically rejects any delta other than `±0.05 EUR` before reaching the Google Ads API.
