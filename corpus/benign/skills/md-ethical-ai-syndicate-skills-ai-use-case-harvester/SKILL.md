---
name: ai-use-case-harvester
description: Use when systematically collecting AI opportunities from business units. Use during discovery phases. Produces use case inventory, prioritization framework, and opportunity pipeline.
---

# AI Use Case Harvester

## Overview

Systematically collect, evaluate, and prioritize AI opportunities from across the organization. Build a pipeline of validated use cases ready for development.

**Core principle:** Finding the right problems is often harder than building solutions. Structured harvesting surfaces high-value opportunities.

## When to Use

- Starting AI program or CoE
- Quarterly opportunity discovery
- Business unit AI intake
- Building AI roadmap
- Justifying AI investments

## Output Format

```yaml
use_case_harvest:
  harvest_period: "[Date range]"
  business_units_covered: ["[BU 1]", "[BU 2]"]
  
  use_cases:
    - id: "[UC-001]"
      title: "[Descriptive title]"
      
      source:
        submitted_by: "[Name]"
        business_unit: "[BU]"
        submission_date: "[Date]"
      
      problem:
        description: "[Problem being solved]"
        current_process: "[How it's done today]"
        pain_points: ["[Pain 1]", "[Pain 2]"]
        frequency: "[How often occurs]"
        affected_users: "[Who and how many]"
      
      proposed_solution:
        ai_approach: "[Classification | Generation | Extraction | etc.]"
        human_in_loop: "[Full auto | Human review | Human final decision]"
        integration_point: "[Where AI fits in workflow]"
      
      value_assessment:
        quantitative:
          time_savings: "[Hours/FTEs per period]"
          cost_savings: "[$ estimate]"
          revenue_impact: "[If applicable]"
          error_reduction: "[Current rate → target]"
        
        qualitative:
          - "[Strategic value]"
          - "[Customer experience improvement]"
        
        confidence: "[High | Medium | Low]"
        assumptions: ["[Key assumption]"]
      
      feasibility:
        technical:
          data_availability: "[Available | Partial | Not available]"
          ai_capability_fit: "[High | Medium | Low]"
          integration_complexity: "[Low | Medium | High]"
          similar_solutions_exist: [true | false]
        
        organizational:
          stakeholder_support: "[Strong | Moderate | Weak]"
          change_management: "[Low | Medium | High]"
          regulatory_constraints: ["[If any]"]
        
        resources:
          estimated_effort: "[T-shirt size or points]"
          skills_needed: ["[Skill 1]", "[Skill 2]"]
          timeline_estimate: "[Weeks/months]"
      
      prioritization:
        value_score: "[1-5]"
        feasibility_score: "[1-5]"
        strategic_alignment: "[1-5]"
        priority_score: "[Calculated]"
        tier: "[Tier 1 | Tier 2 | Tier 3 | Parked]"
      
      status: "[Submitted | Under review | Approved | In progress | Parked | Rejected]"
      next_steps: ["[Action items]"]
  
  pipeline_summary:
    total_submitted: "[N]"
    by_status:
      under_review: "[N]"
      approved: "[N]"
      in_progress: "[N]"
      parked: "[N]"
    
    by_tier:
      tier_1: "[N]"
      tier_2: "[N]"
      tier_3: "[N]"
    
    estimated_total_value: "[$]"
```

## Intake Process

### Discovery Methods
| Method | Best For | Output |
|--------|----------|--------|
| **Interviews** | Deep understanding | Detailed use cases |
| **Workshops** | Brainstorming, alignment | Many ideas |
| **Surveys** | Broad reach, scalable | Quantified pain points |
| **Process mining** | Data-driven discovery | Automation candidates |
| **Support tickets** | Recurring problems | Pain point patterns |

### Intake Form Template
```yaml
intake_questions:
  problem:
    - "What problem are you trying to solve?"
    - "How do you handle this today?"
    - "How often does this occur?"
    - "Who is affected?"
  
  impact:
    - "What would success look like?"
    - "How much time/cost is spent today?"
    - "What errors or issues result from current process?"
  
  context:
    - "Is there data available for this?"
    - "What systems are involved?"
    - "Who would need to adopt this?"
    - "Are there compliance considerations?"
```

## Prioritization Framework

### Value-Feasibility Matrix
```
              High Value
                  │
    ┌─────────────┼─────────────┐
    │   Invest    │   Quick     │
    │   (Tier 1)  │   Wins      │
    │             │   (Tier 1)  │
High├─────────────┼─────────────┤Low
Feas│   Consider  │   Avoid     │Feas
    │   (Tier 2)  │   (Tier 3)  │
    │             │             │
    └─────────────┼─────────────┘
                  │
              Low Value
```

### Scoring Rubric

**Value Score (1-5)**
| Score | Criteria |
|-------|----------|
| 5 | >$1M annual value or strategic imperative |
| 4 | $500K-$1M value or significant efficiency |
| 3 | $100K-$500K value or meaningful improvement |
| 2 | $50K-$100K value or nice-to-have |
| 1 | <$50K value or unclear benefits |

**Feasibility Score (1-5)**
| Score | Criteria |
|-------|----------|
| 5 | Data ready, simple integration, proven AI approach |
| 4 | Data available, moderate integration, known techniques |
| 3 | Data needs work, some complexity, achievable |
| 2 | Significant data gaps, complex integration |
| 1 | Major data/tech barriers, research required |

### Priority Tiers
| Tier | Criteria | Action |
|------|----------|--------|
| **Tier 1** | High value, high feasibility | Start immediately |
| **Tier 2** | High value OR high feasibility | Plan for next quarter |
| **Tier 3** | Lower priority | Monitor, revisit later |
| **Parked** | Not viable now | Document, check periodically |

## Common Use Case Patterns

### High-Value Patterns
```yaml
patterns:
  high_volume_classification:
    example: "Email routing, ticket categorization"
    indicators: ">1000/day, clear categories"
    typical_value: "FTE savings, faster response"
  
  document_extraction:
    example: "Invoice processing, contract analysis"
    indicators: "Structured output from unstructured input"
    typical_value: "Time savings, accuracy improvement"
  
  quality_prediction:
    example: "Defect detection, risk scoring"
    indicators: "Historical data, measurable outcome"
    typical_value: "Error reduction, cost avoidance"
  
  content_generation:
    example: "Report drafts, response templates"
    indicators: "Repetitive writing, consistent format"
    typical_value: "Time savings, consistency"
```

### Red Flags
| Red Flag | Why Problematic |
|----------|-----------------|
| "AI will replace decision entirely" | May need human oversight |
| "We have no data yet" | Feasibility concern |
| "Everyone does it differently" | Standardize first |
| "It's not a priority but nice to have" | Unlikely to get resources |
| "Compliance would never allow it" | Validate early |

## Stakeholder Engagement

### Workshop Agenda (2 hours)
```yaml
workshop:
  intro: "10 min - AI capabilities overview"
  warm_up: "15 min - What frustrates you about your work?"
  ideation: "45 min - Identify AI opportunities"
  prioritization: "30 min - Vote and discuss top ideas"
  next_steps: "20 min - Capture details on top 5"
```

### Follow-up Interview Guide
```yaml
deep_dive:
  - "Walk me through this process step by step"
  - "Where do delays or errors typically occur?"
  - "What data do you look at to make decisions?"
  - "What would ideal look like?"
  - "Who else should I talk to about this?"
```

## Checklist

- [ ] Business units identified for harvest
- [ ] Intake process communicated
- [ ] Use cases collected with sufficient detail
- [ ] Value quantified (even if estimated)
- [ ] Feasibility assessed
- [ ] Prioritization scores calculated
- [ ] Tiers assigned
- [ ] Next steps defined
- [ ] Pipeline reported to leadership
