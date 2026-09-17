---
name: synthetic-data-planner
description: Use when planning synthetic data generation for AI training/testing. Use when real data is limited or restricted. Produces generation strategy, quality requirements, and validation approach.
---

# Synthetic Data Planner

## Overview

Plan synthetic data generation for AI training and testing when real data is insufficient, restricted, or needs augmentation. Define generation strategies, quality requirements, and validation approaches.

**Core principle:** Synthetic data is only valuable if it faithfully represents reality. Plan generation carefully to avoid garbage-in-garbage-out.

## When to Use

- Insufficient real training data
- Privacy restrictions on real data
- Edge case augmentation needed
- Testing scenarios hard to find naturally
- Pre-production testing without real data

## Output Format

```yaml
synthetic_data_plan:
  project: "[Project name]"
  date: "[YYYY-MM-DD]"
  
  context:
    purpose: "[Training | Testing | Both]"
    problem: "[Why synthetic data is needed]"
    real_data_available: "[What exists]"
    gap: "[What's missing]"
  
  requirements:
    volume: "[How much data needed]"
    features: ["[Features to generate]"]
    distributions: 
      - feature: "[Feature]"
        distribution: "[Target distribution]"
    
    relationships:
      - "[Correlation or dependency to maintain]"
    
    quality_criteria:
      - criterion: "[Quality measure]"
        threshold: "[Acceptable value]"
  
  generation_approach:
    method: "[Rule-based | Statistical | ML-based | LLM | Hybrid]"
    
    tools: ["[Tools to use]"]
    
    process:
      - step: "[Step description]"
        output: "[What it produces]"
    
    privacy_considerations:
      - "[How privacy is ensured]"
  
  edge_cases:
    - scenario: "[Edge case to generate]"
      frequency: "[How many examples]"
      method: "[How to generate]"
  
  validation:
    statistical:
      - "[Distribution comparison]"
      - "[Correlation preservation]"
    
    utility:
      - "[How useful for downstream task]"
    
    privacy:
      - "[Ensure no real data leakage]"
  
  risks:
    - risk: "[Risk]"
      mitigation: "[How to address]"
  
  timeline:
    generation: "[Duration]"
    validation: "[Duration]"
    iteration: "[Buffer for fixes]"
```

## Generation Methods

### Rule-Based
```yaml
rule_based:
  best_for: "Structured data with known rules"
  approach: "Define rules, generate combinations"
  pros: ["Predictable", "Fast", "Controllable"]
  cons: ["Limited realism", "May miss patterns"]
  
  example:
    feature: "email"
    rule: "{first}.{last}@{domain}.com"
    variations: "Random from name and domain lists"
```

### Statistical
```yaml
statistical:
  best_for: "Preserving distributions and correlations"
  approach: "Sample from learned distributions"
  pros: ["Preserves statistics", "Scalable"]
  cons: ["May not capture complex relationships"]
  
  tools: ["Faker", "SDV", "Gretel"]
```

### ML-Based (GANs, VAEs)
```yaml
ml_based:
  best_for: "Complex, high-dimensional data"
  approach: "Train generative model on real data"
  pros: ["Captures complex patterns", "High fidelity"]
  cons: ["Requires training data", "May memorize"]
  
  tools: ["CTGAN", "Gretel", "Mostly AI"]
```

### LLM-Based
```yaml
llm_based:
  best_for: "Text, semi-structured content"
  approach: "Prompt LLM to generate examples"
  pros: ["Diverse", "Handles context", "Few-shot capable"]
  cons: ["May hallucinate", "Consistency challenges"]
  
  approach:
    - "Provide examples of desired format"
    - "Prompt for specific variations"
    - "Validate against schema"
```

## Quality Validation

### Statistical Fidelity
```yaml
statistical_tests:
  univariate:
    - test: "Kolmogorov-Smirnov"
      purpose: "Distribution similarity"
      threshold: "p > 0.05"
    
    - test: "Chi-square"
      purpose: "Categorical distribution"
      threshold: "p > 0.05"
  
  multivariate:
    - test: "Correlation matrix comparison"
      purpose: "Relationship preservation"
      threshold: "< 0.1 difference"
```

### Utility Testing
```yaml
utility_tests:
  train_on_synthetic:
    method: "Train model on synthetic, test on real"
    acceptable: "Within 10% of real-data performance"
  
  augmentation:
    method: "Train on real + synthetic vs real only"
    acceptable: "Improvement on edge cases"
```

### Privacy Testing
```yaml
privacy_tests:
  membership_inference:
    purpose: "Check if real records are identifiable"
    threshold: "Attack success < 55%"
  
  attribute_inference:
    purpose: "Check if attributes can be inferred"
    threshold: "No sensitive attribute exposure"
```

## Edge Case Generation

```yaml
edge_case_strategy:
  identification:
    - "Review failure cases from real data"
    - "Brainstorm boundary conditions"
    - "Consult domain experts"
  
  generation:
    - category: "Boundary values"
      examples: ["Max length", "Empty", "Special characters"]
    
    - category: "Rare combinations"
      examples: ["Unusual but valid scenarios"]
    
    - category: "Error conditions"
      examples: ["Invalid inputs to test handling"]
  
  balancing:
    - "Determine realistic frequency"
    - "May over-sample for training robustness"
```

## Checklist

- [ ] Purpose and requirements defined
- [ ] Generation method selected
- [ ] Feature distributions specified
- [ ] Relationships to preserve documented
- [ ] Edge cases identified
- [ ] Validation approach defined
- [ ] Privacy protections planned
- [ ] Quality thresholds set
