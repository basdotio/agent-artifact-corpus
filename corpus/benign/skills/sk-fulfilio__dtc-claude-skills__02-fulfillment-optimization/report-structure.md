# Report Structure Reference

## Document Sections

### 1. Title Block
- Report title: "[Channel Name] Batch Picking & Packing Optimization"
- Subtitle: "Warehouse: [Warehouse Name] ([Code])"
- Date generated

### 2. Executive Summary
Single paragraph covering:
- Total assigned shipments count
- Days of work at current velocity
- Key composition stat (e.g., "65% are multi-SKU orders" or "72% are single-unit")
- Primary optimization opportunity based on their specific profile

### 3. Order Composition Analysis
Two tables:

**Unit Distribution Table**
| Units per Order | Shipments | % of Total |
|-----------------|-----------|------------|
| 1 unit          | X         | X%         |
| 2 units         | X         | X%         |
| 3-5 units       | X         | X%         |
| 6+ units        | X         | X%         |

**SKU Line Distribution Table**
| SKUs per Order  | Shipments | % of Total |
|-----------------|-----------|------------|
| 1 SKU           | X         | X%         |
| 2 SKUs          | X         | X%         |
| 3+ SKUs         | X         | X%         |

**Highlight the dominant segment** - this drives recommendation priority.

### 4. Order Profile Classification
State the merchant's profile based on data:
- Single-Unit Dominant (>60% single-unit)
- Multi-Unit Dominant (>60% multi-unit)
- Balanced Mix (40-60% split)

This determines which recommendations apply.

### 5. Top SKUs Table
| SKU | Orders | % | Type |
|-----|--------|---|------|
| ... | ...    | % | Standard/Built-on-fly |

For multi-unit dominant: also show avg units per order by SKU.

### 6. Recommendations (tailored to profile)
Each recommendation includes:
- **Numbered heading** with descriptive title
- **Target:** What orders this applies to
- **Process:** Numbered steps
- **Impact box:** Highlighted summary of expected outcome

**Order recommendations by volume impact** - largest segment first.

### 7. Batch Picking Candidates Table
Adapt based on profile:

**For single-unit dominant:**
| SKU | Single-Unit Orders | Primary Location | Default Box |

**For multi-unit dominant:**
| SKU Combination | Orders | Pick Zones | Avg Units |

### 8. Product Pairing Table (if multi-SKU orders significant)
| Product 1 | Product 2 | Frequency |
|-----------|-----------|-----------|

Skip this section if single-SKU orders dominate.

### 9. Operational Setup
Adapt staffing based on bottleneck:

**If packing is bottleneck (single-unit heavy):**
| Role | Recommended | Ratio |
|------|-------------|-------|
| Pickers | 1-2 | 1:2+ packers |
| Packing Stations | 3-4 | |

**If picking is bottleneck (multi-SKU heavy):**
| Role | Recommended | Ratio |
|------|-------------|-------|
| Pickers | 3-4 | 2:1 vs packers |
| Packing Stations | 1-2 | |

### 10. Wave Execution Plan
| Wave | Description | Shipments | Method |
|------|-------------|-----------|--------|

Adapt waves to merchant's actual order profile. Don't force a single-unit wave structure on a multi-unit merchant.

### 11. Shipping Velocity Table
| Date | Shipments | Units |
|------|-----------|-------|
Last 7 days with average noted below.

### 12. Bottom Line
3-4 bullet points summarizing expected outcomes if recommendations implemented.

## Formatting Guidelines

- Use consistent color scheme (blue headers, green for high-impact items)
- Highlight bundles/built-on-fly items in yellow
- Bold key statistics
- Keep tables compact with right-aligned numbers
- Add italicized notes below tables where clarification needed
- **Emphasize the dominant order profile** in executive summary and recommendations

## Adapting to Different Profiles

### Single-Unit Dominant Merchants
- Lead with Pre-Print & Pack recommendations
- Emphasize packing station throughput
- Wave plan focuses on SKU-based batches
- Staffing: more packers than pickers

### Multi-Unit Dominant Merchants
- Lead with pick path optimization
- Emphasize zone picking and co-location
- Wave plan focuses on order complexity tiers
- Staffing: more pickers, packing stations for verification
- Product pairing analysis becomes critical

### Balanced Mix Merchants
- Segment workflows clearly
- Separate waves for single-unit vs multi-unit
- May need flexible staffing that shifts through the day
