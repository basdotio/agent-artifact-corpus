---
# ═══════════════════════════════════════════════════════════════════════════════
# SKILL: SECURITY COMPLIANCE
# Version: 2.0.0 | SASMP: 1.3.0 | Production-Grade | Golden Format
# ═══════════════════════════════════════════════════════════════════════════════

name: security-compliance
description: Security compliance frameworks and governance for regulatory adherence
sasmp_version: "1.3.0"
production_grade: true
last_updated: "2025-01-01"

# ─────────────────────────────────────────────────────────────────────────────
# AGENT BONDING
# ─────────────────────────────────────────────────────────────────────────────
bonded_agent: 04-compliance-specialist
bond_type: PRIMARY_BOND
bond_strength: 1.0

# ─────────────────────────────────────────────────────────────────────────────
# SKILL OPERATIONS (Atomic, Single-Responsibility)
# ─────────────────────────────────────────────────────────────────────────────
operations:
  assess_control:
    description: "Assess control against framework requirements"
    atomic: true
    input:
      control_id: { type: "string", required: true }
      framework: { type: "string", required: true }
      evidence: { type: "array", default: [] }
    output:
      status: "enum[compliant, partial, non_compliant]"
      gaps: "array<Gap>"
      recommendations: "array<string>"

  perform_gap_analysis:
    description: "Perform comprehensive gap analysis"
    atomic: true
    input:
      framework: { type: "string", required: true }
      current_state: { type: "object", required: true }
    output:
      compliance_score: "float"
      gaps: "array<Gap>"
      remediation_roadmap: "array<Item>"

  generate_evidence:
    description: "Generate evidence requirements"
    atomic: true
    input:
      controls: { type: "array", required: true }
      framework: { type: "string", required: true }
    output:
      evidence_matrix: "object"
      templates: "array<Template>"

  map_controls:
    description: "Map controls across frameworks"
    atomic: true
    input:
      source_framework: { type: "string", required: true }
      target_frameworks: { type: "array", required: true }
    output:
      mapping_matrix: "object"
      unified_controls: "array<Control>"

  assess_risk:
    description: "Assess risk for compliance gaps"
    atomic: true
    input:
      gaps: { type: "array", required: true }
    output:
      risk_scores: "array<RiskScore>"
      treatment_options: "array<Treatment>"

# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
validation:
  supported_frameworks:
    - "ISO27001:2022"
    - "SOC2"
    - "GDPR"
    - "HIPAA"
    - "PCI-DSS-4.0"
    - "NIST-CSF-2.0"

# ─────────────────────────────────────────────────────────────────────────────
# RETRY LOGIC
# ─────────────────────────────────────────────────────────────────────────────
retry:
  enabled: true
  max_attempts: 2
  strategy: "linear"
  delays: [2000, 4000]

# ─────────────────────────────────────────────────────────────────────────────
# ERROR CODES
# ─────────────────────────────────────────────────────────────────────────────
errors:
  E_UNKNOWN_FRAMEWORK:
    code: 4001
    message: "Framework not supported"
    recovery: "Use supported framework"

  E_SCOPE_UNDEFINED:
    code: 4002
    message: "Assessment scope not defined"
    recovery: "Define explicit scope"

---

# Security Compliance Skill

> **Purpose**: Regulatory compliance and security governance.

## Operations Overview

| Operation | Input | Output |
|-----------|-------|--------|
| assess_control | id, framework | status, gaps |
| perform_gap_analysis | framework, state | score, roadmap |
| generate_evidence | controls | matrix, templates |
| map_controls | source, targets | mapping |
| assess_risk | gaps | scores, treatment |

## Supported Frameworks

| Framework | Version | Controls |
|-----------|---------|----------|
| ISO 27001 | 2022 | 93 |
| SOC 2 | Type II | TSC |
| GDPR | - | 99 |
| PCI DSS | 4.0 | 12 |
| NIST CSF | 2.0 | 6 functions |

## Control Mapping

| Area | ISO | SOC2 | NIST |
|------|-----|------|------|
| Access | A.5.15 | CC6.1 | PR.AC |
| Encrypt | A.8.24 | CC6.7 | PR.DS |
| Logging | A.8.15 | CC7.2 | DE.CM |

## Troubleshooting

```
Assessment Failed
    │
    ├─► E_UNKNOWN_FRAMEWORK → Use supported framework
    └─► E_SCOPE_UNDEFINED → Define scope first
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-01-01 | Production-grade upgrade |
| 1.0.0 | 2024-12-29 | Initial release |
