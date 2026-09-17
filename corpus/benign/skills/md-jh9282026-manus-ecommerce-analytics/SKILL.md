---
name: ecommerce-analytics
description: 'Track and optimize e-commerce performance using conversion metrics, customer analytics, and data-driven insights. Use for: measuring conversion rates, analyzing customer lifetime value, reducing cart abandonment, optimizing average order value, tracking retention metrics, implementing A/B tests, analyzing funnel performance, and making data-driven decisions to improve online store profitability.'
---

# E-Commerce Analytics

Track, analyze, and optimize e-commerce performance using comprehensive metrics frameworks, funnel analysis, and customer behavior insights to drive revenue growth.

## Overview

E-commerce analytics turns raw store data into actionable insights that improve conversion rates, increase average order value, reduce abandonment, and maximize customer lifetime value. This skill covers the essential metrics, analysis frameworks, and optimization strategies every e-commerce business needs — from basic KPI tracking to advanced cohort analysis and predictive modeling.

## Core E-Commerce Metrics

### Revenue & Conversion Metrics

| Metric | Formula | Benchmark | Optimization Lever |
|--------|---------|-----------|-------------------|
| Conversion Rate | Orders / Sessions × 100 | 2–4% (overall) | UX, pricing, trust signals |
| Average Order Value (AOV) | Total Revenue / Orders | Industry-dependent | Bundling, upsell, thresholds |
| Revenue Per Visitor (RPV) | Total Revenue / Sessions | CR × AOV | Combined optimization |
| Cart Abandonment Rate | (Carts − Orders) / Carts × 100 | 65–75% | Checkout UX, shipping, trust |
| Add-to-Cart Rate | Sessions with Add-to-Cart / Total Sessions | 5–15% | PDP optimization, CTAs |
| Checkout Completion Rate | Orders / Checkout Initiated | 40–55% | Checkout flow, payment options |
| Return Rate | Returned Orders / Total Orders | 10–30% (apparel higher) | Product info, sizing, quality |

### Customer Metrics

| Metric | Formula | Benchmark | Why It Matters |
|--------|---------|-----------|---------------|
| Customer Lifetime Value (CLV) | Avg Order Value × Purchase Frequency × Customer Lifespan | 3–5x CAC | Long-term profitability |
| Customer Acquisition Cost (CAC) | Marketing Spend / New Customers | CLV/CAC >3:1 | Unit economics |
| Repeat Purchase Rate | Returning Customers / Total Customers | 25–40% | Retention health |
| Purchase Frequency | Orders / Unique Customers (annual) | 2–4x/year | Engagement depth |
| Time Between Purchases | Avg days between orders | Industry-dependent | Replenishment timing |
| Churn Rate | Customers not repurchasing in expected window | <25% annual | Retention effectiveness |
| NPS | Promoters (%) − Detractors (%) | >50 | Brand health |

## Funnel Analysis Framework

### Standard E-Commerce Funnel

| Stage | Metric | Typical Drop-off | Optimization Focus |
|-------|--------|-----------------|--------------------|
| 1. Awareness | Sessions, unique visitors | — | SEO, ads, content |
| 2. Interest | Pages/session, time on site | 40–60% | Content, navigation, search |
| 3. Consideration | Product views, add-to-cart | 50–70% | PDP, imagery, reviews, pricing |
| 4. Intent | Checkout initiated | 25–40% | Cart UX, shipping preview, trust |
| 5. Purchase | Order completed | 35–60% | Checkout flow, payment, errors |
| 6. Retention | Repeat purchase | 60–80% | Email, loyalty, experience |

### Cart Abandonment Recovery

| Recovery Tactic | Timing | Expected Recovery | Implementation |
|----------------|--------|------------------|----------------|
| Exit-intent popup | On exit | 5–10% | Easy |
| Email #1 (reminder) | 1 hour | 10–15% | Easy |
| Email #2 (incentive) | 24 hours | 5–8% | Easy |
| Email #3 (urgency) | 72 hours | 2–4% | Easy |
| SMS reminder | 2 hours | 8–12% | Medium |
| Retargeting ads | 1–7 days | 3–5% | Medium |
| Push notification | 30 minutes | 5–8% | Medium |
| **Total recovery rate** | — | **25–40%** | — |

## AOV Optimization Strategies

| Strategy | How It Works | Expected AOV Lift | Effort |
|----------|-------------|-------------------|--------|
| Free shipping threshold | "Free shipping over $X" (set 20–30% above current AOV) | 10–15% | Low |
| Product bundling | Pre-configured bundles at 10–15% discount | 15–25% | Medium |
| Cross-sell on cart page | "Frequently bought together" recommendations | 5–10% | Medium |
| Upsell on PDP | "Upgrade to premium" with comparison | 8–15% | Medium |
| Volume discounts | "Buy 2 get 10% off, buy 3 get 20% off" | 10–20% | Low |
| Gift with purchase | Free item above threshold | 8–12% | Low |
| Loyalty points multiplier | "Earn 2x points on orders over $X" | 5–10% | Medium |

## Cohort Analysis Guide

### Monthly Acquisition Cohort Table

| Cohort | Month 0 | Month 1 | Month 2 | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|---------|---------|---------|----------|
| Jan 2026 | 100% | 25% | 18% | 15% | 10% | 6% |
| Feb 2026 | 100% | 28% | 20% | 16% | — | — |
| Mar 2026 | 100% | 30% | 22% | — | — | — |

**How to read:** Jan cohort = customers who first purchased in Jan. 25% made a second purchase in Feb.

### Key Cohort Insights to Extract

| Analysis | What It Reveals | Action |
|----------|----------------|--------|
| Cohort retention curves | Are newer cohorts retaining better? | Validate product/experience improvements |
| Revenue per cohort | Which acquisition channels produce highest LTV? | Shift budget to best channels |
| Time-to-second-purchase | How long until repeat? | Time email campaigns to this window |
| Cohort size trends | Is acquisition growing or shrinking? | Adjust marketing spend |

## Analytics Tool Stack

| Tool | Purpose | Key Capability | Price |
|------|---------|---------------|-------|
| Google Analytics 4 | Web analytics foundation | Funnel analysis, attribution, audiences | Free |
| Shopify Analytics | Shopify-native reporting | Sales, customers, inventory reports | Included |
| Mixpanel / Amplitude | Product analytics | Event tracking, user journeys, retention | $$–$$$ |
| Hotjar / FullStory | Behavior analytics | Heatmaps, session recordings, rage clicks | $–$$ |
| Klaviyo / Drip | Email analytics | Campaign performance, CLV, segmentation | $$–$$$ |
| Looker / Tableau | BI dashboards | Custom dashboards, data blending | $$$–$$$$ |
| Google Optimize / VWO | A/B testing | Experimentation, personalization | $–$$$ |

## A/B Testing for E-Commerce

### What to Test (Priority Order)

| Element | Expected Impact | Traffic Required | Test Duration |
|---------|----------------|-----------------|---------------|
| Pricing / offers | High | Low (500+ conversions) | 1–2 weeks |
| Checkout flow (steps, fields) | High | Medium (1,000+) | 2–4 weeks |
| Product page layout | Medium-High | Medium | 2–4 weeks |
| CTA copy and color | Medium | Low | 1–2 weeks |
| Navigation / search | Medium | High (2,000+) | 2–4 weeks |
| Homepage hero | Low-Medium | High | 2–4 weeks |
| Email subject lines | Medium | Low (per campaign) | Per send |

### Statistical Significance

- Minimum **95% confidence** before calling a winner
- Run tests for at least **2 full business cycles** (typically 2 weeks)
- Don't peek at results early — use sequential testing if you must
- Calculate required sample size BEFORE starting: use Evan Miller's calculator or VWO's

## Best Practices

1. **Track RPV, not just conversion rate** — A lower conversion rate at higher AOV can mean more revenue
2. **Segment everything** — Overall metrics hide the story; segment by device, channel, new vs. returning, geography
3. **Measure the full funnel** — Top-of-funnel metrics without bottom-of-funnel context are misleading
4. **Build cohort views first** — Cohort analysis reveals trends that aggregate metrics mask
5. **Automate reporting** — Build dashboards that update daily; manual reporting wastes analyst time
6. **Test one thing at a time** — Multivariate testing requires massive traffic; most stores should do A/B

## Using the Reference Files

### When to Read Each Reference

**`/references/conversion-metrics-kpis.md`** — Read when setting up KPI tracking, building scorecards, or benchmarking your store's performance against industry standards.

**`/references/customer-behavior-analysis.md`** — Read when conducting cohort analysis, building CLV models, segmenting customers, or analyzing purchase patterns.

**`/references/analytics-tools-implementation.md`** — Read when implementing analytics tools (GA4, Mixpanel, etc.), configuring e-commerce tracking, or building custom dashboards.
