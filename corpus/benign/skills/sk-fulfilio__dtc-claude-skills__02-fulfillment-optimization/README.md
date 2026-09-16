---
title: Fulfillment Optimization Analysis
description: Analyze warehouse shipment backlogs to optimize batch picking and packing workflows. Get actionable recommendations for clearing order backlogs and improving fulfillment efficiency.
author: Fulfil.IO
version: 1.0
tags: [fulfillment, warehouse, picking, packing, optimization]
learn_more_url: https://fulfil.io/resources/claude-skills/fulfillment-optimization
---

# Fulfillment Optimization Analysis Skill

## Quick Start

This skill helps Fulfil merchants analyze their shipment backlog and generate actionable recommendations for clearing orders efficiently.

## What It Does

Instead of applying generic warehouse advice, this skill analyzes your specific order composition to recommend:

1. **Order Profile Classification** - Understanding whether you're single-unit dominant, multi-unit dominant, or balanced
2. **Batch Picking Opportunities** - Which SKUs can be pre-printed and packed vs. need mixed batching
3. **Product Pairing Analysis** - Products frequently bought together for co-location
4. **Bottleneck Identification** - Whether picking or packing is your constraint
5. **Wave Execution Plan** - Prioritized waves to clear your backlog efficiently

## How to Use

### Prerequisites
- Access to Fulfil data warehouse via MCP connector OR
- CSV/Excel export with shipment data (shipment_id, sku, quantity, status)
- Active shipment backlog to analyze

### Usage
Simply ask Claude:

> "Analyze my shipment backlog and recommend how to clear it efficiently"

Or more specifically:

> "I have 500 orders backed up. Help me create a picking and packing plan to clear them."

Claude will:
1. Confirm scope (channels, warehouses, shipment states)
2. Query your shipments and moves data
3. Analyze order composition (single vs. multi-unit distribution)
4. Identify top SKUs and batching candidates
5. Provide tailored recommendations based on YOUR data

### What You'll Get

**Executive Summary**: Backlog size and estimated days to clear at current velocity

**Order Composition Analysis**:
- Single vs. multi-unit distribution
- SKU line distribution per order
- Dominant order profile classification

**Top SKUs**:
- Highest frequency products
- Batching candidates (pre-print vs. mixed batch)
- Case quantity thresholds

**Product Pairing Analysis**: Products frequently ordered together for warehouse co-location

**Numbered Recommendations**: Tailored to your specific order profile, not generic advice

**Wave Execution Plan**:
- Grouped by workflow type
- Estimated shipment counts per wave
- Priority sequencing

## Key Principles

This analysis is built on these core principles:

- **Data Drives Recommendations**: Analyze composition first, then recommend. Different merchants have vastly different order profiles.
- **Identify the Bottleneck**: Packing is often the constraint for single-unit operations; picking is often the constraint for complex multi-SKU operations.
- **Bundle Awareness**: Built-on-fly bundles don't have inventory—components do. Never flag bundle inventory issues.
- **Case Quantity Threshold**: The dividing line between "Pre-Print & Pack" and "Mixed Batch" is typically 1 case worth of orders (~20-30 units if unknown).
- **Optimize for the Majority First**: Whatever segment represents the largest share of orders gets the first and most detailed recommendation.

## Common Scenarios

### Scenario 1: Single-Unit Dominant (>60% single-unit orders)
**Focus**: Throughput speed
**Recommendations**:
- Pre-Print & Pack for high-volume SKUs (grab cases, pre-print labels, sort by carrier)
- Mixed Single-Unit Batch for low-volume SKUs (combine into one pick pass)
- More packing stations than pickers (1:2 or 1:3 ratio)

### Scenario 2: Multi-Unit Dominant (>60% multi-unit orders)
**Focus**: Pick complexity and packing accuracy
**Recommendations**:
- Multi-SKU Batch Picking with zone grouping
- Product co-location based on pairing analysis
- Packing station workflow with scan verification
- More pickers than packers

### Scenario 3: Balanced Mix (40-60% each)
**Focus**: Workflow segmentation
**Recommendations**:
- Separate waves by order type
- Dedicated stations for single-unit vs. multi-unit
- Flexible staffing allocation

## Workflow Types Explained

### Pre-Print & Pack (Single-SKU, High Volume)
Best for SKUs with 20+ single-unit orders waiting:
1. Grab full cases/pallet of the SKU
2. Pre-print all shipping labels
3. Sort by carrier while packing
4. Apply label and ship

### Mixed Single-Unit Batch (Single-SKU, Low Volume)
Best for SKUs with <20 single-unit orders:
1. Combine all low-volume SKUs into one batch
2. Pick all in one warehouse pass
3. Scan at packing station
4. System prints correct label per scan

### Multi-SKU Batch Picking
Best for orders with multiple different products:
1. Group orders by similar SKU combinations
2. Pick waves grouped by zone/location
3. Assembly and verification at packing station

## Data Quality Notes

The analysis automatically:
- Filters by shipment state (assigned, waiting)
- Excludes cancelled moves
- Identifies bundle SKUs to avoid false inventory alerts
- Calculates shipping velocity from recent history
- Validates sufficient data for meaningful patterns

## When to Re-Run

- **Daily/Weekly**: During peak season or large backlogs
- **After Process Changes**: New picking carts, packing stations, or workflows
- **Warehouse Reorganization**: After moving product locations
- **Staffing Changes**: New picker/packer ratios
- **Channel Mix Shifts**: New sales channels with different order profiles

## Output Format

The skill generates a comprehensive PDF report with:
1. Executive summary
2. Order composition tables
3. Top SKUs with batching candidates
4. Product pairing analysis
5. Numbered recommendations
6. Wave execution plan
7. Shipping velocity chart
8. Bottom line summary

## Technical Details

- **Platform**: Runs on Fulfil data warehouse (BigQuery) or user-provided CSV/Excel
- **Key Tables**: shipments, moves (nested), inventory_by_location
- **Query Performance**: Optimized for large datasets
- **Privacy**: All data stays in your Fulfil instance

## Support

For questions or issues:
1. Review the SKILL.md for detailed query templates
2. Verify MCP connector is properly configured
3. Ensure shipment data includes moves (line items)
4. Check that shipment states are correctly set in Fulfil

## Version
v1.0 - Warehouse fulfillment optimization methodology
