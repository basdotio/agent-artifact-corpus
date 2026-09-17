---
name: model-inventory-manager
description: Use when maintaining registry of AI/ML models. Use continuously. Produces model registry, metadata catalog, and governance reporting.
---

# Model Inventory Manager

## Overview

Maintain a comprehensive registry of all AI/ML models in the organization. Track metadata, lineage, risk levels, and compliance status for governance and operations.

**Core principle:** You can't govern what you can't see. A complete model inventory is foundational for AI governance.

## When to Use

- Establishing AI governance
- Regulatory compliance (EU AI Act, etc.)
- Risk assessments
- Audit preparation
- Portfolio planning

## Output Format

```yaml
model_inventory:
  version: "[Version]"
  last_updated: "[YYYY-MM-DD]"
  
  models:
    - model_id: "[Unique ID]"
      name: "[Model name]"
      version: "[Current version]"
      
      classification:
        type: "[Classification | Regression | LLM | etc.]"
        purpose: "[What it does]"
        domain: "[Business domain]"
        risk_tier: "[High | Medium | Low]"
      
      ownership:
        business_owner: "[Name/Team]"
        technical_owner: "[Name/Team]"
        data_owner: "[Name/Team]"
      
      lifecycle:
        status: "[Development | Staging | Production | Deprecated | Retired]"
        deployed_date: "[YYYY-MM-DD]"
        last_updated: "[YYYY-MM-DD]"
        next_review: "[YYYY-MM-DD]"
      
      technical:
        framework: "[TensorFlow | PyTorch | etc.]"
        hosting: "[Where deployed]"
        dependencies: ["[Dependency]"]
        performance_metrics:
          - metric: "[Metric]"
            value: "[Value]"
            threshold: "[Acceptable]"
      
      data:
        training_data: "[Description/reference]"
        features: ["[Key features]"]
        data_sensitivity: "[Classification]"
        data_retention: "[Policy]"
      
      governance:
        bias_audit: 
          completed: "[Date]"
          result: "[Pass | Conditional | Fail]"
        security_review:
          completed: "[Date]"
          result: "[Approved | Pending | Issues]"
        privacy_impact:
          required: [true | false]
          completed: "[Date if applicable]"
        explainability:
          method: "[How explained to users]"
          documentation: "[Link]"
      
      compliance:
        regulations: ["[Applicable regulation]"]
        compliance_status: "[Compliant | In progress | Gap]"
        audit_trail: "[Where to find logs]"
      
      incidents:
        - date: "[Date]"
          type: "[Incident type]"
          resolution: "[How resolved]"
      
      documentation:
        model_card: "[Link]"
        technical_docs: "[Link]"
        user_guide: "[Link]"
  
  summary:
    total_models: "[N]"
    by_status:
      production: "[N]"
      development: "[N]"
      deprecated: "[N]"
    by_risk_tier:
      high: "[N]"
      medium: "[N]"
      low: "[N]"
    reviews_due: "[N in next 30 days]"
    compliance_gaps: "[N]"
```

## Risk Tiering

### Risk Classification
| Tier | Criteria | Governance Requirements |
|------|----------|------------------------|
| **High** | Decisions affecting individuals, safety-critical, regulated | Full documentation, bias audit, human oversight, annual review |
| **Medium** | Significant business impact, customer-facing | Standard documentation, periodic review |
| **Low** | Internal productivity, limited impact | Basic registration, light oversight |

### Risk Assessment Questions
```yaml
risk_questions:
  - question: "Does it make decisions about individuals?"
    high_risk_if: "Yes"
  
  - question: "Is it safety-critical?"
    high_risk_if: "Yes"
  
  - question: "Is it subject to specific regulation?"
    high_risk_if: "Yes"
  
  - question: "Is it customer-facing without human review?"
    high_risk_if: "Yes"
  
  - question: "Does it process sensitive data?"
    medium_risk_if: "Yes"
```

## Required Metadata

### Minimum for All Models
```yaml
required_fields:
  - "model_id"
  - "name"
  - "purpose"
  - "business_owner"
  - "technical_owner"
  - "status"
  - "risk_tier"
  - "data_sensitivity"
```

### Additional for High-Risk
```yaml
high_risk_required:
  - "training_data_documentation"
  - "bias_audit_results"
  - "explainability_method"
  - "human_oversight_process"
  - "incident_response_plan"
  - "regulatory_compliance_mapping"
```

## Model Card Template

```yaml
model_card:
  model_details:
    name: "[Name]"
    version: "[Version]"
    type: "[Type]"
    developers: "[Who built it]"
    date: "[When]"
  
  intended_use:
    primary_use: "[What it's for]"
    users: "[Who uses it]"
    out_of_scope: "[What it's NOT for]"
  
  training_data:
    datasets: "[What was used]"
    preprocessing: "[How data was prepared]"
    limitations: "[Known data gaps]"
  
  performance:
    metrics:
      - metric: "[Metric]"
        value: "[Value]"
        test_set: "[What dataset]"
    performance_by_group:
      - group: "[Subgroup]"
        performance: "[Value]"
  
  ethical_considerations:
    fairness: "[Assessment]"
    privacy: "[Considerations]"
    security: "[Considerations]"
  
  limitations:
    known_limitations: ["[Limitation]"]
    recommendations: ["[How to mitigate]"]
```

## Governance Reporting

### Executive Dashboard
```yaml
governance_dashboard:
  model_count:
    total: "[N]"
    production: "[N]"
    high_risk: "[N]"
  
  compliance:
    fully_compliant: "[%]"
    gaps: "[N models with gaps]"
    overdue_reviews: "[N]"
  
  trends:
    new_models_this_quarter: "[N]"
    retired_this_quarter: "[N]"
    incidents_this_quarter: "[N]"
  
  attention_required:
    - "[Model X] - Review overdue"
    - "[Model Y] - Bias audit needed"
```

## Inventory Maintenance

### Triggers for Update
| Event | Action |
|-------|--------|
| New model deployed | Add to inventory |
| Model updated | Update version, metadata |
| Incident occurs | Log in incident history |
| Review completed | Update audit dates, results |
| Model retired | Update status, retention |

### Review Schedule
| Model Tier | Review Frequency |
|------------|-----------------|
| High risk | Quarterly |
| Medium risk | Semi-annually |
| Low risk | Annually |

## Checklist

- [ ] All production models registered
- [ ] Risk tiers assigned
- [ ] Owners identified
- [ ] Required metadata complete
- [ ] High-risk models have model cards
- [ ] Review schedule established
- [ ] Governance reporting active
- [ ] Retirement process defined
