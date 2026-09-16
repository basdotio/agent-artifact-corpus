# Free Shipping Threshold Analysis - Detailed Methodology

This document contains complete SQL queries and detailed analysis steps for the Free Shipping Threshold Analysis skill. Reference this from [SKILL.md](SKILL.md) when performing the analysis.

## Contents

- Step 0: Initial Discovery & Channel Filtering
- Step 1: Map Your Order Landscape
- Step 2: Understand the Profit Trade-off
- Step 3: Set Strategic Constraints
- Step 4: Map Thresholds to Hypotheses
- Step 5: Calculate Expected Impact

---

## Step 0: Initial Discovery & Channel Filtering

**Before running any analysis**, Claude must:

1. **Identify available channels**:
```sql
SELECT 
  channel_name,
  COUNT(*) as order_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct_of_orders
FROM sales_orders
WHERE state IN ('confirmed', 'done', 'processing')
  AND order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
GROUP BY channel_name
ORDER BY order_count DESC;
```

2. **Ask the user**: "I see you have orders from [list channels]. Should I exclude any marketplace channels like Amazon, Walmart, or eBay from this analysis? These channels typically have their own shipping policies that merchants don't control."

3. **Identify shipping line patterns by channel**:
```sql
SELECT 
  channel_name,
  COUNT(*) as total_orders,
  COUNT(CASE WHEN EXISTS(
    SELECT 1 FROM UNNEST(lines) 
    WHERE LOWER(product_code) LIKE '%ship%' 
       OR LOWER(product_name) LIKE '%shipping%'
  ) THEN 1 END) as orders_with_shipping_line,
  ROUND(COUNT(CASE WHEN EXISTS(
    SELECT 1 FROM UNNEST(lines) 
    WHERE LOWER(product_code) LIKE '%ship%' 
       OR LOWER(product_name) LIKE '%shipping%'
  ) THEN 1 END) * 100.0 / COUNT(*), 2) as pct_with_shipping_line
FROM sales_orders
WHERE state IN ('confirmed', 'done', 'processing')
  AND order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
GROUP BY channel_name
ORDER BY total_orders DESC;
```

4. **Interpret shipping line patterns**:
   - 0% shipping lines = All orders get free shipping
   - 100% shipping lines = Channel explicitly tracks shipping (may be free or paid)
   - Mixed % = Channel offers free shipping conditionally

5. **Update all subsequent queries** to exclude marketplace channels identified by the user.

### Step 1: Map Your Order Landscape
**Objective**: Understand where customer orders naturally cluster

**Data to Pull**:
1. Order value distribution (last 6-12 months of confirmed/done orders)
2. Hero product prices (products driving most revenue)
3. Current average shipping cost per order

**SQL Queries**:

```sql
-- Order Value Distribution
-- Groups orders into $10 buckets to identify clustering patterns
WITH order_totals AS (
  SELECT 
    id,
    order_number,
    order_date,
    -- Calculate total order value from line items
    ROUND((
      SELECT SUM(amount)
      FROM UNNEST(lines)
      WHERE line_type = 'sale'
    ), 2) as order_value
  FROM sales_orders
  WHERE state IN ('confirmed', 'done', 'processing')
    AND order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
    AND (
      SELECT SUM(amount)
      FROM UNNEST(lines)
      WHERE line_type = 'sale'
    ) > 0
)
SELECT 
  FLOOR(order_value / 10) * 10 as value_bucket_start,
  FLOOR(order_value / 10) * 10 + 10 as value_bucket_end,
  COUNT(*) as order_count,
  ROUND(AVG(order_value), 2) as avg_order_value,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct_of_orders
FROM order_totals
WHERE order_value < 500  -- Focus on reasonable threshold range
GROUP BY FLOOR(order_value / 10)
ORDER BY value_bucket_start;
```

```sql
-- Hero Products (Top Revenue Drivers)
-- Identifies products with highest revenue contribution and their price points
SELECT 
  lines.product_code,
  lines.product_name,
  lines.product_category,
  COUNT(DISTINCT id) as orders_with_product,
  ROUND(AVG(lines.unit_price), 2) as avg_unit_price,
  SUM(lines.quantity) as total_units_sold,
  ROUND(SUM(lines.amount), 2) as total_revenue,
  ROUND(SUM(lines.amount) * 100.0 / SUM(SUM(lines.amount)) OVER(), 2) as pct_of_total_revenue
FROM sales_orders,
UNNEST(lines) as lines
WHERE state IN ('confirmed', 'done', 'processing')
  AND order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
  AND lines.line_type = 'sale'
  AND lines.product_code IS NOT NULL
GROUP BY lines.product_code, lines.product_name, lines.product_category
ORDER BY total_revenue DESC
LIMIT 20;
```

```sql
-- Average Shipping Cost Analysis
-- Calculates mean and median shipping costs to understand typical fulfillment expense
-- Also identifies current free shipping patterns
SELECT 
  COUNT(*) as total_shipments,
  ROUND(AVG(shipment_cost), 2) as avg_shipping_cost,
  ROUND(APPROX_QUANTILES(shipment_cost, 100)[OFFSET(50)], 2) as median_shipping_cost,
  ROUND(MIN(shipment_cost), 2) as min_cost,
  ROUND(MAX(shipment_cost), 2) as max_cost,
  shipment_cost_currency as currency
FROM shipments
WHERE state = 'done'
  AND shipped_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
  AND shipment_cost > 0
  AND shipment_cost < 50  -- Filter outliers
GROUP BY shipment_cost_currency;
```

```sql
-- Shipping Line Item Analysis
-- Analyzes shipping line items to understand current free shipping patterns
-- NOTE: Absence of shipping line = implicit free shipping
WITH order_shipping AS (
  SELECT 
    so.id,
    so.order_number,
    so.order_date,
    so.channel_name,
    -- Product order value (excluding shipping)
    ROUND((
      SELECT SUM(amount)
      FROM UNNEST(so.lines)
      WHERE line_type = 'sale' 
        AND LOWER(product_code) NOT LIKE '%ship%'
        AND LOWER(COALESCE(product_name, '')) NOT LIKE '%shipping%'
    ), 2) as product_value,
    -- Shipping charge (flexible detection)
    ROUND(COALESCE((
      SELECT SUM(amount)
      FROM UNNEST(so.lines)
      WHERE line_type = 'sale' 
        AND (LOWER(product_code) LIKE '%ship%' 
             OR LOWER(COALESCE(product_name, '')) LIKE '%shipping%')
    ), 0), 2) as shipping_charged,
    -- Check if shipping line exists
    EXISTS(
      SELECT 1 FROM UNNEST(so.lines) 
      WHERE LOWER(product_code) LIKE '%ship%' 
         OR LOWER(COALESCE(product_name, '')) LIKE '%shipping%'
    ) as has_shipping_line
  FROM sales_orders so
  WHERE so.state IN ('confirmed', 'done', 'processing')
    AND so.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
    AND so.channel_name NOT IN ('Amazon.com', 'Costco', 'Walmart.com', 'eBay')  -- CUSTOMIZE: Add merchant's marketplace channels
)
SELECT 
  -- Total orders
  COUNT(*) as total_orders,
  
  -- Shipping line presence
  COUNT(CASE WHEN has_shipping_line THEN 1 END) as orders_with_shipping_line,
  COUNT(CASE WHEN NOT has_shipping_line THEN 1 END) as orders_without_shipping_line,
  ROUND(COUNT(CASE WHEN has_shipping_line THEN 1 END) * 100.0 / COUNT(*), 2) as pct_with_shipping_line,
  
  -- Free shipping breakdown
  COUNT(CASE WHEN has_shipping_line AND shipping_charged = 0 THEN 1 END) as free_shipping_explicit,
  COUNT(CASE WHEN NOT has_shipping_line THEN 1 END) as free_shipping_implicit,
  COUNT(CASE WHEN (has_shipping_line AND shipping_charged = 0) OR NOT has_shipping_line THEN 1 END) as total_free_shipping,
  ROUND(COUNT(CASE WHEN (has_shipping_line AND shipping_charged = 0) OR NOT has_shipping_line THEN 1 END) * 100.0 / COUNT(*), 2) as pct_free_shipping,
  
  -- Paid shipping
  COUNT(CASE WHEN has_shipping_line AND shipping_charged > 0 THEN 1 END) as paid_shipping_orders,
  ROUND(COUNT(CASE WHEN has_shipping_line AND shipping_charged > 0 THEN 1 END) * 100.0 / COUNT(*), 2) as pct_paid_shipping,
  
  -- Shipping charge statistics (for paid shipping only)
  ROUND(AVG(CASE WHEN shipping_charged > 0 THEN shipping_charged END), 2) as avg_shipping_charge,
  ROUND(APPROX_QUANTILES(CASE WHEN shipping_charged > 0 THEN shipping_charged END, 100)[OFFSET(50)], 2) as median_shipping_charge,
  ROUND(MIN(CASE WHEN shipping_charged > 0 THEN shipping_charged END), 2) as min_shipping_charge,
  ROUND(MAX(CASE WHEN shipping_charged > 0 THEN shipping_charged END), 2) as max_shipping_charge,
  
  -- Order value comparison
  ROUND(AVG(CASE WHEN (has_shipping_line AND shipping_charged = 0) OR NOT has_shipping_line THEN product_value END), 2) as avg_order_value_free_ship,
  ROUND(AVG(CASE WHEN shipping_charged > 0 THEN product_value END), 2) as avg_order_value_paid_ship,
  
  -- Current free shipping threshold inference (for explicitly free shipping only)
  ROUND(APPROX_QUANTILES(CASE WHEN has_shipping_line AND shipping_charged = 0 THEN product_value END, 100)[OFFSET(5)], 2) as free_ship_5th_percentile,
  ROUND(APPROX_QUANTILES(CASE WHEN has_shipping_line AND shipping_charged = 0 THEN product_value END, 100)[OFFSET(50)], 2) as free_ship_median
FROM order_shipping
WHERE product_value > 0;
```

**Interpretation Guide:**

- **orders_without_shipping_line**: These orders received free shipping (no shipping charge applied)
- **free_shipping_explicit**: Orders with shipping line where amount = $0 (conditional free shipping)
- **free_shipping_implicit**: Orders with no shipping line (always free shipping)
- **total_free_shipping**: All orders that received free shipping (explicit + implicit)

If `pct_free_shipping` is very high (>90%), the merchant likely offers free shipping on most/all orders already.

```sql
-- Low Margin Products Zone (Items under typical threshold ranges)
-- Identifies products that could bleed profit if included in free shipping offers
SELECT 
  lines.product_code,
  lines.product_name,
  ROUND(AVG(lines.unit_price), 2) as avg_unit_price,
  COUNT(DISTINCT id) as order_count,
  SUM(lines.quantity) as units_sold,
  ROUND(AVG(lines.gross_profit_cpny_ccy_cache / NULLIF(lines.quantity, 0)), 2) as avg_unit_margin
FROM sales_orders,
UNNEST(lines) as lines
WHERE state IN ('confirmed', 'done', 'processing')
  AND order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
  AND lines.line_type = 'sale'
  AND lines.product_code IS NOT NULL
  AND lines.unit_price > 0
  AND lines.unit_price < 50  -- Focus on lower-priced items
GROUP BY lines.product_code, lines.product_name
HAVING units_sold > 5  -- Minimum volume threshold
ORDER BY avg_unit_price ASC
LIMIT 30;
```

### Step 2: Understand the Profit Trade-off
**Objective**: Calculate what free shipping costs vs. what it gains

**Free Shipping COSTS**:
- Margin per order (you absorb the shipping cost)
- Risk on low-value orders (shipping cost may exceed margin)

**Free Shipping GAINS**:
- Higher conversion rate (removes friction)
- Larger basket size (customers add items to qualify)
- Lower per-unit shipping cost (via order consolidation)

**Key Insight**: Your threshold determines which trade-off you're making. A lower threshold tests if shipping cost blocks conversion. A higher threshold tests if customers will add items to qualify.

### Step 3: Set Strategic Constraints
**Objective**: Identify the "smart zone" for testing based on actual demand

**Three Zones**:

1. **DON'T TEST: Too Low ($30 and below)**
   - Bleeds profit on low-margin items
   - Shipping cost often exceeds order margin
   - Only test here if you have very high-margin products

2. **SMART ZONE: ($50-$150)**
   - Has existing demand in your data
   - Protects margin on hero products
   - Tests realistic customer behavior

3. **DON'T TEST: Too High ($200+)**
   - No volume at this level
   - Wastes time testing where customers don't naturally spend
   - Only test if data shows significant orders at this value

**SQL Query for Constraint Validation**:

```sql
-- Volume Analysis by Threshold Candidates
-- Shows how many orders would qualify at different threshold levels
WITH order_totals AS (
  SELECT 
    id,
    order_number,
    ROUND((
      SELECT SUM(amount)
      FROM UNNEST(lines)
      WHERE line_type = 'sale'
    ), 2) as order_value
  FROM sales_orders
  WHERE state IN ('confirmed', 'done', 'processing')
    AND order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
)
SELECT 
  threshold,
  SUM(CASE WHEN order_value >= threshold THEN 1 ELSE 0 END) as orders_above_threshold,
  ROUND(SUM(CASE WHEN order_value >= threshold THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as pct_orders_above,
  SUM(CASE WHEN order_value < threshold THEN 1 ELSE 0 END) as orders_below_threshold,
  ROUND(SUM(CASE WHEN order_value < threshold THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as pct_orders_below
FROM order_totals
CROSS JOIN UNNEST([30, 40, 50, 75, 100, 125, 150, 175, 200]) as threshold
GROUP BY threshold
ORDER BY threshold;
```

### Step 4: Map Thresholds to Hypotheses
**Objective**: Frame each threshold as a testable business hypothesis

**Framework**:

| Threshold | Hypothesis | Profit Logic |
|-----------|------------|--------------|
| Below Hero Price | Shipping cost blocking conversion on hero items | • Above low-margin zone<br>• Removes friction<br>• Tests price sensitivity |
| Above Hero Price | Customers will add items to qualify | • Where orders already happen<br>• Tests basket expansion<br>• Higher AOV offsets cost |

**Example Decision Tree**:

```
Given:
- Hero product at $100
- Most orders cluster $50-$200
- Low-margin items under $40

Then Test:
✓ $50 threshold
  - Removes friction on hero product purchases
  - Protects margin (above $40 danger zone)
  - High volume at this level
  
✓ $150 threshold  
  - Tests add-to-cart behavior
  - Significant order volume exists here
  - Higher AOV justifies shipping absorption

✗ Skip $30
  - Margin killer on cheap items
  
✗ Skip $200
  - Insufficient volume to test
```

### Step 5: Calculate Expected Impact
**Objective**: Quantify the financial implications of each threshold option

**SQL Query for Impact Projection**:

```sql
-- Impact Analysis by Threshold
-- Projects revenue, costs, and margin implications at different thresholds
WITH order_data AS (
  SELECT 
    so.id,
    so.order_number,
    so.order_date,
    ROUND((
      SELECT SUM(amount)
      FROM UNNEST(so.lines)
      WHERE line_type = 'sale'
    ), 2) as order_value,
    ROUND((
      SELECT SUM(gross_profit_cpny_ccy_cache)
      FROM UNNEST(so.lines)
      WHERE line_type = 'sale'
    ), 2) as order_margin,
    sh.shipment_cost
  FROM sales_orders so
  LEFT JOIN shipments sh ON sh.moves[OFFSET(0)].order_id = so.id AND sh.state = 'done'
  WHERE so.state IN ('confirmed', 'done', 'processing')
    AND so.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
),
threshold_analysis AS (
  SELECT 
    threshold,
    COUNT(*) as total_orders,
    
    -- Orders below threshold (would NOT get free shipping)
    SUM(CASE WHEN order_value < threshold THEN 1 ELSE 0 END) as orders_below,
    ROUND(AVG(CASE WHEN order_value < threshold THEN order_value END), 2) as avg_order_value_below,
    
    -- Orders above threshold (would GET free shipping)
    SUM(CASE WHEN order_value >= threshold THEN 1 ELSE 0 END) as orders_above,
    ROUND(AVG(CASE WHEN order_value >= threshold THEN order_value END), 2) as avg_order_value_above,
    
    -- Cost of offering free shipping
    ROUND(AVG(CASE WHEN order_value >= threshold THEN COALESCE(shipment_cost, 0) END), 2) as avg_shipping_cost_absorbed,
    ROUND(SUM(CASE WHEN order_value >= threshold THEN COALESCE(shipment_cost, 0) END), 2) as total_shipping_cost,
    
    -- Margin preservation
    ROUND(AVG(CASE WHEN order_value >= threshold THEN order_margin END), 2) as avg_margin_above_threshold,
    
    -- Financial viability check
    ROUND(AVG(CASE WHEN order_value >= threshold 
                   THEN order_margin / NULLIF(COALESCE(shipment_cost, 1), 0) 
                   END), 2) as margin_to_shipping_ratio
    
  FROM order_data
  CROSS JOIN UNNEST([30, 40, 50, 75, 100, 125, 150, 175, 200]) as threshold
  GROUP BY threshold
)
SELECT 
  threshold,
  total_orders,
  orders_below,
  orders_above,
  ROUND(orders_above * 100.0 / total_orders, 2) as pct_qualifying_orders,
  avg_order_value_below,
  avg_order_value_above,
  avg_shipping_cost_absorbed,
  total_shipping_cost,
  avg_margin_above_threshold,
  margin_to_shipping_ratio,
  CASE 
    WHEN margin_to_shipping_ratio < 3 THEN '⚠️ Margin Risk - shipping cost high relative to margin'
    WHEN margin_to_shipping_ratio >= 3 AND margin_to_shipping_ratio < 5 THEN '✓ Acceptable - reasonable margin buffer'
    WHEN margin_to_shipping_ratio >= 5 THEN '✓✓ Strong - excellent margin protection'
  END as viability_assessment
FROM threshold_analysis
ORDER BY threshold;
```

## Output Format

When running this analysis, provide results in the following structure with visual charts:

### 1. Executive Summary
- Current order landscape (where orders cluster)
- Hero product identification and pricing
- Average shipping costs
- Current free shipping patterns (if applicable)
- Recommended threshold(s) with rationale

### 2. Data Findings with Visualizations

**Order Distribution Chart**:
- Bar chart showing order count by value bucket ($0-10, $10-20, etc.)
- Highlight the primary cluster zone
- Annotate key thresholds being considered

**Hero Products**:
- Table of top 5-10 products by revenue
- Their average selling prices
- Revenue contribution percentages

**Shipping Economics Chart**:
- If shipping line items exist: Distribution chart showing free vs. paid shipping orders
- Histogram of shipping charges (for paid shipping orders)
- Comparison of average order values: free shipping vs. paid shipping

**Current Free Shipping Pattern** (if applicable):
- Chart showing at what order values customers currently get free shipping
- This reveals existing threshold or promotional patterns

### 3. Threshold Recommendations
For each recommended threshold:

**Threshold: $XX**
- **Hypothesis**: [What customer behavior this tests]
- **Volume**: [% of orders at/above this level]
- **Margin Protection**: [Average margin vs shipping cost ratio]
- **Strategic Logic**: [Why this threshold makes sense]
- **Risk Assessment**: [What could go wrong]
- **Expected Impact**: [Projected costs if implemented]

### 4. Do Not Test
List threshold values to avoid with explanations:
- Too low: Would include products with insufficient margin
- Too high: Insufficient order volume to generate meaningful results

### 5. Next Steps
- Recommended testing sequence (which threshold to test first)
- Key metrics to monitor during testing
- Success criteria definitions

## Important Considerations

**Data Quality Checks**:
- Exclude canceled and failed orders from analysis
- Filter out outlier shipping costs (e.g., international or oversized items if not representative)
- Ensure sufficient data volume (minimum 1,000 orders recommended)
- Use recent data (6-12 months) to reflect current customer behavior

**Margin Calculations**:
- If gross margin data is unavailable in order lines, work with averages or estimates
- Account for product returns in margin calculations if data available
- Consider different margin profiles by product category

**Shipping Cost Nuances**:
- Separate domestic vs international if significantly different
- Account for carrier contract rates vs actual costs
- Consider dimensional weight implications for bulky items

**Testing Philosophy**:
- This analysis tells you WHERE to test, not whether free shipping will work
- Always A/B test before full rollout
- Monitor both conversion rate AND average order value
- Track profitability, not just revenue

## Common Pitfalls to Avoid

1. **Testing Too Low**: Don't set threshold below your low-margin product zone
2. **Testing Without Volume**: Don't test thresholds where <10% of orders naturally occur
3. **Ignoring Category Differences**: Consider different thresholds for different product categories if margins vary significantly
4. **Focusing Only on AOV**: Free shipping that increases AOV but destroys margin is a failure
5. **Not Having a Control Group**: Always A/B test; don't just implement site-wide

## Sample Output Language

When presenting results, use clear, actionable language:

"Based on your order data from the last 6 months:

**Order Landscape**: 
Your orders cluster heavily between $50-$200 (representing 68% of all orders). There's a clear peak at $75-$100, which aligns with your hero product pricing.

**Hero Products**: 
Your top revenue driver is [Product X] at $95, representing 18% of total revenue. The next three products average $85-$110.

**Shipping Economics**: 
Average shipping cost is $8.50 per order, with most orders between $6-$12 to ship.

**Recommended Testing Strategy**:

Test #1: $75 Threshold
- Tests if shipping cost blocks conversion on hero products
- Covers 45% of your current order base
- Margin-to-shipping ratio of 6.2:1 provides strong protection
- Estimated monthly cost of free shipping: $X,XXX

Test #2: $125 Threshold  
- Tests if customers will add items to qualify
- Covers 28% of current orders (sufficient volume)
- Margin-to-shipping ratio of 8.5:1 (excellent protection)
- Lower monthly cost: $X,XXX but tests different behavior

Do Not Test:
- $40 or below: Too many low-margin items, margin-to-shipping ratio only 2:1
- $200 or above: Only 8% of orders, insufficient volume for meaningful test"

## When to Re-run Analysis

- Quarterly, to capture seasonal shifts
- After major product launches
- When hero product pricing changes significantly
- If shipping costs increase substantially
- After major changes to product mix or catalog

## Integration with Fulfil Workflows

This analysis integrates with:
- **Shopify/Channel Settings**: Threshold configuration for free shipping rules
- **Promotion Planning**: Coordination with other discount strategies
- **Inventory Strategy**: Understanding which products drive threshold achievement
- **Pricing Strategy**: Hero product price point optimization

## Technical Notes

**Performance Optimization**:
- Queries are optimized for BigQuery (Fulfil's data warehouse)
- Default to 6-month lookback; adjust based on order volume
- Use partitioning on order_date for faster queries
- Limit product analysis to items with >5 orders to reduce noise

**Error Handling**:
- Handle NULL shipping costs (set to 0 or exclude)
- Validate order_value > 0 before analysis
- Check for sufficient data volume before making recommendations
- Alert if hero product identification unclear (no dominant products)

## References

This methodology is based on:
- Victor Paycro's data-driven threshold optimization framework
- E-commerce best practices for free shipping strategy
- Margin-first approach to promotional pricing

## Version History
