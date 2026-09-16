---
title: Free Shipping Threshold Analysis
description: Determine your most profitable free shipping threshold using data-driven analysis of order patterns, hero products, and shipping economics.
author: Fulfil.IO
version: 1.0
tags: [shipping, pricing, analytics, optimization]
learn_more_url: https://fulfil-website-b7a103a9a1c8.herokuapp.com/resources/claude-skills/free-shipping-threshold
---

# Free Shipping Threshold Analysis Skill

## Quick Start

This skill helps Fulfil merchants determine their most profitable free shipping threshold using their actual order data.

## What It Does

Instead of guessing or blindly copying competitors, this skill analyzes your specific business data to recommend:

1. **Where your orders naturally cluster** - Understanding your order value distribution
2. **Your hero products** - Products driving the most revenue and their price points  
3. **Shipping economics** - Your actual average shipping costs
4. **Smart thresholds to test** - Data-backed recommendations with profit protection
5. **Thresholds to avoid** - Values that would hurt margins or lack sufficient volume

## How to Use

### Prerequisites
- Access to Fulfil data warehouse via MCP connector
- At least 6 months of order history (minimum 1,000 orders recommended)
- Shipping cost data in your shipments table

### Usage
Simply ask Claude:

> "Run a free shipping threshold analysis on my order data"

Or more specifically:

> "Analyze my order data to recommend the best free shipping threshold. Focus on the last 6 months."

Claude will:
1. Query your sales_orders and shipments tables
2. Analyze order value distribution
3. Identify hero products and their pricing
4. Calculate shipping cost averages
5. Provide threshold recommendations with detailed reasoning

### What You'll Get

**Executive Summary**: Quick overview of findings and recommendations

**Order Landscape**: Visual breakdown of where your orders cluster by value

**Hero Products**: Your top revenue drivers and their price points

**Threshold Recommendations**: 
- Specific dollar amounts to test
- Hypothesis for each (what customer behavior it tests)
- Volume and margin analysis
- Risk assessment
- Expected impact calculations

**Do Not Test List**: Thresholds to avoid with explanations

**Next Steps**: Testing sequence and success criteria

## Key Insights From The Analysis

This analysis is based on Victor Paycro's methodology that emphasizes:

- **Data First**: Use YOUR data, not industry benchmarks
- **Margin Protection**: Never test thresholds that include too many low-margin products
- **Volume Validation**: Only test where customers already spend money
- **Hypothesis Framing**: Each threshold tests different customer behavior
- **Profitability Focus**: AOV increases mean nothing if margins erode

## Common Scenarios

### Scenario 1: DTC Brand with Hero Product at $95
**Recommendation**: Test $75 and $125
- $75 removes friction on hero purchases
- $125 tests basket expansion behavior
- Skip $40 (margin killer) and $200 (no volume)

### Scenario 2: Multi-Product Catalog, Orders Cluster $30-$80
**Recommendation**: Test $50
- Covers majority of order range
- Above low-margin danger zone
- Reasonable customer expectation

### Scenario 3: High AOV Business, Orders $150+
**Recommendation**: Test $125-$175
- Matches natural customer spending
- Strong margin protection
- Tests incrementality on already-high orders

## Data Quality Notes

The analysis automatically:
- Excludes canceled/failed orders
- Filters out shipping line items
- Removes outlier shipping costs
- Validates sufficient data volume
- Alerts if patterns are unclear

## When to Re-Run

- **Quarterly**: Capture seasonal changes
- **After Product Launches**: New hero products may shift optimal threshold
- **Pricing Changes**: Hero product price updates affect recommendations
- **Shipping Cost Changes**: Carrier rate increases impact economics
- **Catalog Shifts**: Major changes to product mix

## Integration Points

This analysis informs:
- Shopify free shipping rule configuration
- Promotion strategy planning
- Pricing optimization initiatives
- Inventory strategy (what to push to hit thresholds)
- Email/SMS marketing campaigns around threshold incentives

## Important Caveats

⚠️ **This analysis tells you WHERE to test, not WHETHER free shipping will work**

- Always A/B test before full rollout
- Monitor conversion rate AND profitability
- Consider different thresholds for different customer segments
- Account for fulfillment complexity (some items cost more to ship)
- Factor in return rates if offering free returns too

## Technical Details

- **Platform**: Runs on Fulfil data warehouse (BigQuery)
- **Data Timeframe**: Default 6 months, adjustable
- **Query Performance**: Optimized for large datasets
- **Privacy**: All data stays in your Fulfil instance

## Support

For questions or issues:
1. Check the skill's detailed methodology section
2. Verify data quality in your Fulfil instance
3. Ensure MCP connector is properly configured
4. Review sample queries for customization options

## Example Output Preview

```
EXECUTIVE SUMMARY

Based on your last 6 months of order data:

Order Landscape:
Your orders cluster between $40-$120, with a clear peak at $75-$95 (38% of all orders)

Hero Products:
1. Premium Bundle ($89) - 22% of revenue
2. Starter Kit ($49) - 15% of revenue  
3. Deluxe Package ($129) - 12% of revenue

Shipping Economics:
Avg: $9.25 | Median: $8.50 | Range: $5-$18

RECOMMENDATIONS:

Test #1: $75 Threshold
✓ Tests friction removal on hero product purchases
✓ 42% of orders would qualify
✓ Margin-to-shipping ratio: 7.2:1 (strong protection)
✓ Estimated monthly cost: $3,850
✓ Risk: Low - well above margin danger zone

Test #2: $125 Threshold
✓ Tests basket expansion behavior  
✓ 26% of orders would qualify
✓ Margin-to-shipping ratio: 9.8:1 (excellent protection)
✓ Estimated monthly cost: $2,200
✓ Risk: Medium - depends on add-to-cart behavior

DO NOT TEST:
✗ $40 - Margin-to-shipping ratio only 2.1:1 (margin killer)
✗ $200 - Only 6% of orders (insufficient volume)

Next Steps:
1. A/B test $75 threshold for 2-4 weeks
2. Monitor conversion rate, AOV, and margin dollars
3. If successful, test $125 with existing customers
```

## Version
v1.0 - Based on Victor Paycro's threshold optimization methodology
