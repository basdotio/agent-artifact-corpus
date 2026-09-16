# Free Shipping Threshold Analysis - Quick Reference

## What This Skill Does

Analyzes your actual order data to recommend profitable free shipping thresholds instead of guessing.

## When to Use

- Before launching a free shipping offer
- When revising existing shipping thresholds
- During promotion planning cycles
- Quarterly business reviews
- After major product launches or pricing changes

## How to Trigger

### Simple Request
>
> "Run a free shipping threshold analysis on my order data"

### Specific Request
>
> "Analyze my last 6 months of orders to recommend the best free shipping threshold. I want to see order clustering, hero products, and margin protection analysis."

### Custom Timeframe
>
> "Run threshold analysis on orders from January through June 2025"

## What You'll Get

### 1. Executive Summary

- Where orders cluster (the sweet spot)
- Hero products and their price points
- Current shipping economics
- Bottom-line recommendation with rationale

### 2. Order Distribution Analysis

- Visual/table showing order value buckets
- Identification of high-volume zones
- Long-tail analysis

### 3. Hero Products Report

- Top 10-20 products by revenue
- Their average selling prices
- Revenue contribution percentages
- Product category patterns

### 4. Threshold Recommendations

For each recommended threshold:

- Dollar amount
- Hypothesis (what it tests)
- Volume metrics (% of orders)
- Margin protection assessment
- Risk level
- Expected impact

### 5. "Do Not Test" List

Thresholds to avoid with clear explanations

### 6. Implementation Roadmap

Step-by-step testing plan with timeline

## Key Concepts

### Order Clustering

Where most of your orders naturally fall in value. Testing thresholds where customers already spend = higher success probability.

### Hero Products  

Your revenue drivers. Their price points anchor threshold decisions. Test below hero price (removes friction) or above (tests basket expansion).

### Margin-to-Shipping Ratio

Your margin divided by shipping cost. Minimum safe ratio is 3:1. Higher is better.

Example:

- Order margin: $24
- Shipping cost: $8  
- Ratio: 3:1 (acceptable)

### The Three Zones

**DON'T TEST: Too Low**

- Below low-margin product zone
- Shipping cost > margin
- Money loser even if conversion increases

**SMART ZONE: Test Here**  

- Has existing order volume
- Protects margin
- Tests realistic customer behavior

**DON'T TEST: Too High**

- Insufficient order volume
- Can't get statistically significant results
- Wastes time

### Hypothesis Framing

Every threshold tests specific customer behavior:

**Below Hero Price** ($50 when hero is $75)

- Tests if shipping cost blocks conversion
- "Are people not buying because of shipping fees?"

**Above Hero Price** ($100 when hero is $75)  

- Tests if customers add items to qualify
- "Will people buy more to get free shipping?"

## Decision Framework

```
IF most orders < $50 AND hero product = $40
THEN test $35-45 (removes friction)

IF most orders $50-$100 AND hero product = $75  
THEN test $75 (captures volume) AND $100 (tests add behavior)

IF shipping cost > $10 AND margins tight
THEN test higher thresholds only (margin protection)

IF shipping cost < $5 AND margins strong
THEN can test lower thresholds (less risk)
```

## Common Pitfalls to Avoid

❌ **Testing too low**: Don't include low-margin products  
✓ **Test above your danger zone** (margin-to-shipping ratio < 3:1)

❌ **Testing without volume**: Don't test where <10% of orders occur  
✓ **Test where customers already spend money**

❌ **Ignoring shipping costs**: Free shipping isn't "free"  
✓ **Calculate actual margin impact** before rolling out

❌ **No control group**: Can't measure impact without A/B test  
✓ **Always split-test** before site-wide implementation

❌ **Only watching AOV**: Revenue up but profit down = failure  
✓ **Monitor margin dollars per order** as primary KPI

## Success Metrics

**Primary KPIs**:

- Margin dollars per order (most important)
- Conversion rate (traffic → sale)
- Revenue per session (overall impact)

**Secondary KPIs**:

- Average order value (AOV)
- Items per order
- Orders clustering at threshold (gaming behavior)
- Customer lifetime value (long-term view)

## Red Flags During Testing

🚩 **Stop or adjust if**:

- Margin dollars decreasing despite revenue growth
- High threshold gaming (orders at $50.01 when threshold is $50)
- Conversion increase but customer quality decreases
- Returns spiking (customers ordering more they don't want)
- Unit economics break (CAC + shipping > LTV)

## Data Requirements

**Minimum**:

- 6 months of order history
- 1,000+ orders for statistical validity
- Product pricing data
- Order line items

**Recommended**:

- Actual shipping cost per order
- Product margin data
- 12 months of history (captures seasonality)
- Customer segment data

**Nice to Have**:

- Return rate by order value
- Customer acquisition cost
- Repeat purchase rates
- Cart abandonment data

## Integration Checklist

Before implementing recommendations:

**Data Validation**

- [ ] Confirmed actual shipping costs  
- [ ] Validated product margins
- [ ] Checked for seasonal patterns
- [ ] Reviewed by finance team

**Technical Setup**

- [ ] Configured in e-commerce platform
- [ ] Analytics tracking in place  
- [ ] A/B test properly configured
- [ ] Control group defined

**Stakeholder Alignment**  

- [ ] Marketing aware of test
- [ ] CS team briefed on changes
- [ ] Finance approved margin impact
- [ ] Executive sponsor assigned

**Success Criteria**

- [ ] Defined minimum acceptable results
- [ ] Set test duration (2-4 weeks minimum)
- [ ] Established decision tree (if X, then Y)
- [ ] Scheduled analysis review meeting

## Sample Decision Tree

```
After 2 weeks of A/B testing at $50 threshold:

IF margin dollars UP by 5%+ AND conversion UP
→ Roll out to 100%, test higher threshold next

IF margin dollars FLAT but conversion UP 10%+  
→ Continue test another 2 weeks to confirm

IF margin dollars DOWN despite conversion increase
→ End test, try higher threshold ($75)

IF no significant change in any metrics
→ Shipping may not be primary friction, try $35 or investigate other barriers
```

## Quarterly Review Process

Every 3 months:

1. Re-run order distribution analysis
2. Check if hero products have changed
3. Validate shipping costs haven't increased
4. Review threshold performance metrics
5. Adjust if needed for seasonal patterns

## When Results Don't Match Expectations

**If test shows negative results**:

- Don't panic - you learned what doesn't work
- Try alternative threshold before abandoning
- Consider that shipping may not be main friction
- Investigate other conversion barriers (product page UX, checkout flow, etc.)

**If test shows marginal results**:

- Calculate break-even based on customer LTV
- Consider segment-specific thresholds
- May be worth it for customer acquisition even if margin-neutral

**If test shows amazing results**:

- Validate data quality (too good to be true?)
- Check for external factors (was there a holiday?)
- Ensure long-term sustainability before rollout
- Plan for increased shipping costs at scale

## Advanced Strategies

Once basic threshold tested:

**Segmented Thresholds**:

- Different thresholds for new vs. returning customers
- Geographic thresholds (higher for remote areas)  
- Product category thresholds (higher margin categories = lower threshold)

**Dynamic Thresholds**:

- Change by season (higher during holidays)
- Flash threshold promotions (weekend only)
- Personalized based on customer history

**Threshold Stacking**:

- $50 free ground shipping
- $100 free expedited shipping
- Creates tier incentive system

## Resources

**Main Documentation**: SKILL.md (comprehensive methodology)  
**This Document**: Quick reference when you need fast answers

## Questions?

Ask Claude:

- "Explain why you recommended $X threshold"
- "What would happen if I tested $Y instead?"
- "How do I know if my test is working?"
- "Should I stop my test early?"
- "Why is my margin-to-shipping ratio important?"

---

**Remember**: This framework tells you WHERE to test, not whether free shipping will work for your business. Always A/B test before full rollout, and monitor profitability, not just revenue.
