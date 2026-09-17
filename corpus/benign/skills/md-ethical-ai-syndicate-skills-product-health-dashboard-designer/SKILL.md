---
name: product-health-dashboard-designer
description: Use when defining product analytics requirements. Use after product live. Produces KPI definitions, dashboard specifications, alert thresholds, and measurement methodology.
---

# Product Health Dashboard Designer

## Overview

Design dashboards and metrics that tell the story of product health. Define KPIs, specify visualizations, and establish alerting that enables proactive product management.

**Core principle:** Measure what matters, not what's easy. A good dashboard enables decision-making, not just data display.

## When to Use

- Product launching to production
- Redesigning existing analytics
- Onboarding new team to product metrics
- Quarterly health check methodology

## Output Format

```yaml
product_health_dashboard:
  product: "[Product name]"
  version: "[YYYY-MM-DD]"
  audience: "[Who uses this dashboard]"
  
  north_star:
    metric: "[Primary success metric]"
    definition: "[Exactly how it's calculated]"
    data_source: "[Where data comes from]"
    current: "[Current value]"
    target: "[Goal value]"
    refresh_rate: "[Real-time | Hourly | Daily]"
  
  kpis:
    - category: "[Acquisition | Activation | Engagement | Retention | Revenue]"
      metrics:
        - name: "[Metric name]"
          definition: "[Calculation formula]"
          data_source: "[Where from]"
          visualization: "[Number | Chart type]"
          healthy_range: "[X to Y]"
          warning_threshold: "[Trigger for concern]"
          critical_threshold: "[Trigger for action]"
          trend_period: "[Days/weeks to show]"
  
  dashboard_layout:
    sections:
      - section: "[Section name]"
        purpose: "[What decisions this enables]"
        components:
          - type: "[Big number | Line chart | Bar chart | Table]"
            metric: "[Metric name]"
            size: "[Full | Half | Quarter]"
            comparisons: ["[vs last period | vs target]"]
  
  alerts:
    - metric: "[Metric name]"
      condition: "[When to alert]"
      severity: "[Critical | Warning | Info]"
      channel: "[Slack | Email | PagerDuty]"
      recipients: ["[Team/person]"]
      runbook: "[Link to response procedure]"
  
  segments:
    - segment: "[User segment]"
      filter: "[How to identify]"
      rationale: "[Why this matters separately]"
  
  data_requirements:
    events: ["[Event name: description]"]
    properties: ["[Property: what it captures]"]
    implementation_notes: "[Technical requirements]"
  
  review_cadence:
    daily: "[What to check daily]"
    weekly: "[Weekly review focus]"
    monthly: "[Monthly deep dive]"
```

## KPI Framework: AARRR

### Acquisition
| Metric | Definition | Healthy |
|--------|------------|---------|
| New signups | Unique accounts created | Growing |
| Signup conversion | Signups / Landing page visitors | >2-5% |
| Cost per acquisition | Total spend / Signups | Decreasing |
| Channel attribution | Signups by source | Diversified |

### Activation
| Metric | Definition | Healthy |
|--------|------------|---------|
| Onboarding completion | Users completing setup / Signups | >60% |
| Time to first value | Time from signup to key action | Decreasing |
| Activation rate | Users performing key action / Signups | >40% |

### Engagement
| Metric | Definition | Healthy |
|--------|------------|---------|
| DAU/MAU | Daily active / Monthly active | >25% |
| Session frequency | Sessions per user per week | Stable/growing |
| Feature adoption | Users of feature X / Active users | Per feature target |
| Session duration | Average time in product | Appropriate for use case |

### Retention
| Metric | Definition | Healthy |
|--------|------------|---------|
| D1/D7/D30 retention | Users returning after N days | D1>40%, D7>20%, D30>10% |
| Churn rate | Users lost / Total users | <5% monthly |
| Cohort retention | Retention curves by signup cohort | Flattening curve |

### Revenue
| Metric | Definition | Healthy |
|--------|------------|---------|
| MRR | Monthly recurring revenue | Growing |
| ARPU | Revenue / Active users | Stable/growing |
| LTV | Lifetime value per customer | >3x CAC |
| Expansion revenue | Upgrades / Total revenue | >20% |

## Dashboard Design Principles

### Layout Hierarchy
```
┌────────────────────────────────────────────────────────────┐
│ NORTH STAR METRIC                                    BIG   │
│ [Primary success metric with trend]                        │
├────────────────────────────────────────────────────────────┤
│ KEY HEALTH INDICATORS                                      │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│ │ Metric 1     │ │ Metric 2     │ │ Metric 3     │        │
│ │ [Trend chart]│ │ [Trend chart]│ │ [Trend chart]│        │
│ └──────────────┘ └──────────────┘ └──────────────┘        │
├────────────────────────────────────────────────────────────┤
│ DETAILED VIEWS                                             │
│ [Segment breakdowns, cohort analysis, feature metrics]     │
└────────────────────────────────────────────────────────────┘
```

### Visualization Selection
| Data Type | Recommended | Avoid |
|-----------|-------------|-------|
| Single value + trend | Big number + sparkline | Pie chart |
| Time series | Line chart | Bar chart for >7 periods |
| Category comparison | Horizontal bar | Pie chart |
| Distribution | Histogram | Line chart |
| Funnel steps | Funnel visualization | Line chart |

## Alert Design

### Threshold Setting
```yaml
alert_thresholds:
  approach: "Statistical"
  method: "Mean ± 2 standard deviations over 30 days"
  
  example:
    metric: "Daily signups"
    mean: 100
    std_dev: 15
    warning_low: 70   # Mean - 2σ
    warning_high: 130 # Mean + 2σ
    critical_low: 55  # Mean - 3σ
```

### Severity Levels
| Severity | Criteria | Response |
|----------|----------|----------|
| **Critical** | Business-impacting now | Immediate action, page on-call |
| **Warning** | Concerning trend | Investigate same day |
| **Info** | Notable but not urgent | Review in next meeting |

### Alert Hygiene
```yaml
alert_principles:
  - "Every alert should be actionable"
  - "If nobody acts, remove the alert"
  - "Review alert fatigue monthly"
  - "Each critical alert needs a runbook"
```

## Segmentation Strategy

### Common Segments
| Segment Type | Examples |
|--------------|----------|
| **User lifecycle** | New (<7d), Active, Dormant, Churned |
| **Plan tier** | Free, Pro, Enterprise |
| **Use case** | By primary feature used |
| **Size** | SMB, Mid-market, Enterprise |
| **Cohort** | By signup month |

### Segment Dashboard
```yaml
segment_view:
  primary_segment: "User lifecycle"
  default_view: "Active users"
  comparison: "Side-by-side segment comparison"
  
  metrics_per_segment:
    - "Segment size"
    - "Key action rate"
    - "Revenue contribution"
    - "Trend vs previous period"
```

## Implementation Checklist

### Before Launch
- [ ] North star metric defined
- [ ] AARRR metrics specified
- [ ] Dashboard layout designed
- [ ] Alert thresholds set
- [ ] Data events specified
- [ ] Tracking implemented

### After Launch
- [ ] Dashboard built and tested
- [ ] Alerts delivering correctly
- [ ] Team trained on interpretation
- [ ] Review cadence established
- [ ] Runbooks created for critical alerts

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Too many metrics | Dashboard overload | Focus on 5-7 key metrics |
| Vanity metrics | Looks good, not actionable | Tie to decisions |
| No targets | Can't assess health | Set clear targets |
| Raw numbers only | Missing context | Add comparisons, trends |
| Alert flood | Fatigue, ignored | Reduce to truly actionable |
| No segments | Masked problems | At least lifecycle + tier |
