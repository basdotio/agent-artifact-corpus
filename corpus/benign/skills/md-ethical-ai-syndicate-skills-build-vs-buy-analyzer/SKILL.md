---
name: build-vs-buy-analyzer
description: Use when deciding between custom AI development and vendor solutions. Use before project commitment. Produces structured analysis with scoring and recommendation.
---

# Build vs Buy Analyzer

## Overview

Conduct structured analysis of build vs buy decisions for AI capabilities. Compare total cost, time to value, strategic fit, and risk to make informed technology decisions.

**Core principle:** The right answer depends on your context. Analyze systematically rather than defaulting to either build or buy.

## When to Use

- Starting new AI initiative
- Vendor proposing solution you could build
- Technical team proposing to build commoditized capability
- Renewing vendor contract with alternative

## Output Format

```yaml
build_vs_buy_analysis:
  capability: "[What we're trying to achieve]"
  analysis_date: "[YYYY-MM-DD]"
  decision_needed_by: "[Date]"
  
  context:
    business_need: "[What problem we're solving]"
    urgency: "[Timeline requirements]"
    strategic_importance: "[How critical]"
    unique_requirements: ["[What's special about our needs]"]
  
  options:
    build:
      description: "[What building would entail]"
      approach: "[High-level approach]"
      
      costs:
        development: "[$]"
        timeline: "[Months]"
        ongoing_operations: "[$/year]"
        total_3_year: "[$]"
      
      capabilities:
        - capability: "[Capability]"
          fit: "[Full | Partial | No]"
          notes: "[Details]"
      
      advantages:
        - "[Advantage 1]"
      
      disadvantages:
        - "[Disadvantage 1]"
      
      risks:
        - risk: "[Risk]"
          likelihood: "[H/M/L]"
          impact: "[H/M/L]"
          mitigation: "[If possible]"
    
    buy:
      vendor: "[Vendor name]"
      product: "[Product]"
      
      costs:
        implementation: "[$]"
        timeline: "[Months]"
        ongoing_subscription: "[$/year]"
        total_3_year: "[$]"
      
      capabilities:
        - capability: "[Capability]"
          fit: "[Full | Partial | No]"
          notes: "[Details]"
      
      advantages:
        - "[Advantage 1]"
      
      disadvantages:
        - "[Disadvantage 1]"
      
      risks:
        - risk: "[Risk]"
          likelihood: "[H/M/L]"
          impact: "[H/M/L]"
          mitigation: "[If possible]"
  
  scoring:
    criteria:
      - criterion: "Total cost of ownership"
        weight: "[%]"
        build_score: "[1-5]"
        buy_score: "[1-5]"
      
      - criterion: "Time to value"
        weight: "[%]"
        build_score: "[1-5]"
        buy_score: "[1-5]"
    
    weighted_total:
      build: "[Score]"
      buy: "[Score]"
  
  recommendation:
    decision: "[Build | Buy | Hybrid]"
    rationale: "[Why]"
    conditions: ["[Any conditions]"]
    next_steps: ["[Actions]"]
```

## Evaluation Criteria

### Cost Factors
| Factor | Build | Buy |
|--------|-------|-----|
| Upfront | Development labor, infrastructure | License, implementation |
| Ongoing | Maintenance, operations, upgrades | Subscription, support tiers |
| Hidden | Opportunity cost, technical debt | Customization, integration |
| Exit | N/A | Migration, data extraction |

### Time Factors
| Factor | Build | Buy |
|--------|-------|-----|
| To launch | 6-18 months typical | 1-6 months typical |
| To full value | Longer (custom to needs) | Faster (proven solution) |
| To iterate | Flexible | Dependent on vendor |

### Strategic Factors
| Factor | Favors Build | Favors Buy |
|--------|-------------|-----------|
| Differentiation | Core competitive advantage | Commodity capability |
| Control | Need full control | Standard use case |
| Expertise | Have or building capability | Not core competency |
| Scale | Unique scale requirements | Standard scale |

### Risk Factors
| Risk | Build | Buy |
|------|-------|-----|
| Execution | Might not deliver | Vendor might not fit |
| Timeline | Delays common | Implementation delays |
| Quality | Unknown until done | Can evaluate before |
| Dependency | On your team | On vendor |
| Lock-in | Tech debt | Vendor lock-in |

## Scoring Framework

### Score Scale
| Score | Meaning |
|-------|---------|
| 5 | Strongly favors this option |
| 4 | Favors this option |
| 3 | Neutral |
| 2 | Disadvantages this option |
| 1 | Strongly disadvantages |

### Standard Criteria Weights
```yaml
default_weights:
  total_cost: 25%
  time_to_value: 20%
  capability_fit: 20%
  strategic_alignment: 15%
  risk: 15%
  flexibility: 5%
```

## Decision Framework

### When to Build
```yaml
build_indicators:
  strong:
    - "Core competitive differentiator"
    - "No solution meets requirements"
    - "Regulatory/compliance mandates custom"
    - "Long-term strategic asset"
  
  moderate:
    - "Have strong internal capability"
    - "Need deep integration with custom systems"
    - "Vendor costs prohibitive at scale"
    - "Need full control over roadmap"
```

### When to Buy
```yaml
buy_indicators:
  strong:
    - "Commodity capability (not differentiating)"
    - "Proven solutions exist"
    - "Speed to market critical"
    - "Lack internal expertise"
  
  moderate:
    - "Best practices embedded in product"
    - "Vendor roadmap aligns with needs"
    - "Risk of internal project failure"
    - "Focus resources elsewhere"
```

### Hybrid Options
```yaml
hybrid_approaches:
  buy_and_customize:
    when: "Platform fits but needs customization"
    example: "LLM API + custom prompts and workflows"
  
  build_on_platform:
    when: "Need custom but want accelerators"
    example: "ML platform + custom models"
  
  buy_now_build_later:
    when: "Speed now, control later"
    example: "Start with vendor, migrate when scale justifies"
```

## Total Cost Comparison

```yaml
tco_template:
  year_1:
    build:
      development: 400000
      infrastructure: 50000
      operations: 100000
      total: 550000
    
    buy:
      license: 200000
      implementation: 100000
      customization: 50000
      total: 350000
  
  year_3_cumulative:
    build: 850000  # Operations grows slower
    buy: 850000    # Subscription adds up
  
  year_5_cumulative:
    build: 1150000
    buy: 1450000   # Crossover point
```

## Common Mistakes

| Mistake | Problem | Prevention |
|---------|---------|------------|
| Underestimating build time | 2x+ overruns common | Add 50-100% buffer |
| Ignoring ongoing costs | Build seems cheaper | Model 3-5 year TCO |
| Overestimating customization | Could configure instead | POC before deciding |
| Vendor lock-in ignored | Painful exit later | Evaluate exit costs |
| Opportunity cost | Could build other things | Factor in alternatives |

## Checklist

- [ ] Business need clearly defined
- [ ] Unique requirements documented
- [ ] Build option fully scoped
- [ ] Buy options evaluated
- [ ] Costs estimated (3-5 year TCO)
- [ ] Timeline compared
- [ ] Risks assessed
- [ ] Scoring completed
- [ ] Recommendation justified
- [ ] Stakeholders aligned
