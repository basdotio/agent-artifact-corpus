---
# ═══════════════════════════════════════════════════════════════════════════════
# SKILL: DEFENSIVE SECURITY
# Version: 2.0.0 | SASMP: 1.3.0 | Production-Grade | Golden Format
# ═══════════════════════════════════════════════════════════════════════════════

name: defensive-security
description: SOC operations, incident response, and threat detection for security monitoring
sasmp_version: "1.3.0"
production_grade: true
last_updated: "2025-01-01"

# ─────────────────────────────────────────────────────────────────────────────
# AGENT BONDING
# ─────────────────────────────────────────────────────────────────────────────
bonded_agent: 02-defensive-security
bond_type: PRIMARY_BOND
bond_strength: 1.0

# ─────────────────────────────────────────────────────────────────────────────
# SKILL OPERATIONS (Atomic, Single-Responsibility)
# ─────────────────────────────────────────────────────────────────────────────
operations:
  analyze_alert:
    description: "Analyze security alert for triage and classification"
    atomic: true
    input:
      alert_data: { type: "object", required: true }
      context: { type: "enum", values: ["siem", "edr", "ndr", "custom"], default: "siem" }
    output:
      classification: "string"
      severity: "enum"
      is_true_positive: "boolean"
      recommended_actions: "array<string>"

  hunt_threat:
    description: "Perform proactive threat hunting"
    atomic: true
    input:
      hypothesis: { type: "string", required: true }
      data_sources: { type: "array", required: true }
      time_range: { type: "string", default: "7d" }
    output:
      findings: "array<Finding>"
      iocs_discovered: "array<IOC>"

  correlate_events:
    description: "Correlate events across log sources"
    atomic: true
    input:
      events: { type: "array", required: true }
      time_window: { type: "string", default: "1h" }
    output:
      incidents: "array<Incident>"
      timeline: "array<TimelineEntry>"

  respond_incident:
    description: "Execute incident response actions"
    atomic: true
    input:
      incident_id: { type: "string", required: true }
      action: { type: "enum", values: ["contain", "investigate", "eradicate", "recover"], required: true }
    output:
      result: "string"
      evidence: "array<Evidence>"

# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
validation:
  rules:
    - name: "alert_structure"
      check: "alert_data.has_keys(['timestamp', 'source', 'message'])"
      error: "E_INVALID_ALERT"
    - name: "time_range_format"
      pattern: "^\\d+[hdwm]$"
      error: "E_INVALID_TIME_RANGE"

# ─────────────────────────────────────────────────────────────────────────────
# RETRY LOGIC
# ─────────────────────────────────────────────────────────────────────────────
retry:
  enabled: true
  max_attempts: 3
  strategy: "exponential_backoff"
  delays: [1000, 2000, 4000]
  retryable_errors:
    - "E_SIEM_TIMEOUT"
    - "E_LOG_SOURCE_UNAVAILABLE"

# ─────────────────────────────────────────────────────────────────────────────
# OBSERVABILITY
# ─────────────────────────────────────────────────────────────────────────────
observability:
  logging:
    level: "info"
    format: "structured_json"
  metrics:
    - name: "alert_triage_time"
      type: "histogram"
    - name: "incidents_detected"
      type: "counter"

# ─────────────────────────────────────────────────────────────────────────────
# ERROR CODES
# ─────────────────────────────────────────────────────────────────────────────
errors:
  E_INVALID_ALERT:
    code: 2001
    message: "Alert data missing required fields"
    recovery: "Ensure alert contains timestamp, source, message"

  E_SIEM_TIMEOUT:
    code: 2002
    message: "SIEM query timed out"
    recovery: "Reduce time range or simplify query"

---

# Defensive Security Skill

> **Purpose**: Blue team operations and security monitoring.

## Operations Overview

| Operation | Input | Output |
|-----------|-------|--------|
| analyze_alert | alert_data, context | classification, severity |
| hunt_threat | hypothesis, sources | findings, iocs |
| correlate_events | events, window | incidents, timeline |
| respond_incident | id, action | result, evidence |

## MITRE ATT&CK Coverage

| Tactic | Detection | Techniques |
|--------|-----------|------------|
| Initial Access | Email logs | T1566 |
| Execution | Process logs | T1059 |
| Persistence | Registry | T1547 |
| Lateral Movement | Auth logs | T1021 |

## Troubleshooting

```
Alert Analysis Failed
    │
    ├─► E_INVALID_ALERT → Check required fields
    ├─► E_SIEM_TIMEOUT → Reduce query scope
    └─► E_LOG_SOURCE_UNAVAILABLE → Check forwarder
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-01-01 | Production-grade upgrade |
| 1.0.0 | 2024-12-29 | Initial release |
