---
# ═══════════════════════════════════════════════════════════════════════════════
# SKILL: DIGITAL FORENSICS
# Version: 2.0.0 | SASMP: 1.3.0 | Production-Grade | Golden Format
# ═══════════════════════════════════════════════════════════════════════════════

name: digital-forensics
description: Digital forensics and malware analysis for evidence collection and investigation
sasmp_version: "1.3.0"
production_grade: true
last_updated: "2025-01-01"

# ─────────────────────────────────────────────────────────────────────────────
# AGENT BONDING
# ─────────────────────────────────────────────────────────────────────────────
bonded_agent: 03-forensics-analyst
bond_type: PRIMARY_BOND
bond_strength: 1.0

# ─────────────────────────────────────────────────────────────────────────────
# SKILL OPERATIONS (Atomic, Single-Responsibility)
# ─────────────────────────────────────────────────────────────────────────────
operations:
  acquire_evidence:
    description: "Acquire forensic evidence with integrity verification"
    atomic: true
    input:
      source: { type: "string", required: true }
      acquisition_type: { type: "enum", values: ["disk", "memory", "network"], required: true }
    output:
      evidence_path: "string"
      hash_md5: "string"
      hash_sha256: "string"
      chain_of_custody: "object"

  analyze_disk:
    description: "Analyze disk image for artifacts"
    atomic: true
    input:
      image_path: { type: "string", required: true }
      artifact_types: { type: "array", default: ["filesystem", "registry", "browser"] }
    output:
      artifacts: "array<Artifact>"
      timeline: "array<TimelineEntry>"

  analyze_memory:
    description: "Analyze memory dump for processes and malware"
    atomic: true
    input:
      dump_path: { type: "string", required: true }
      profile: { type: "string", optional: true }
    output:
      processes: "array<Process>"
      network_connections: "array<Connection>"
      injected_code: "array<MalwareIndicator>"

  analyze_malware:
    description: "Perform malware analysis"
    atomic: true
    input:
      sample_path: { type: "string", required: true }
      analysis_type: { type: "enum", values: ["static", "dynamic", "both"], default: "both" }
    output:
      classification: "string"
      behavior: "array<Behavior>"
      iocs: "array<IOC>"

  extract_iocs:
    description: "Extract Indicators of Compromise"
    atomic: true
    input:
      evidence_source: { type: "string", required: true }
    output:
      iocs: "array<IOC>"
      stix_bundle: "object"

# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
validation:
  rules:
    - name: "file_exists"
      check: "path.exists(source)"
      error: "E_FILE_NOT_FOUND"
    - name: "hash_format"
      pattern: "^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{64}$"
      error: "E_INVALID_HASH"

# ─────────────────────────────────────────────────────────────────────────────
# RETRY LOGIC
# ─────────────────────────────────────────────────────────────────────────────
retry:
  enabled: true
  max_attempts: 2
  strategy: "linear"
  delays: [5000, 10000]
  retryable_errors:
    - "E_TOOL_TIMEOUT"
  non_retryable_errors:
    - "E_EVIDENCE_CORRUPTED"
    - "E_HASH_MISMATCH"

# ─────────────────────────────────────────────────────────────────────────────
# OBSERVABILITY
# ─────────────────────────────────────────────────────────────────────────────
observability:
  chain_of_custody:
    enabled: true
    log_all_access: true

# ─────────────────────────────────────────────────────────────────────────────
# ERROR CODES
# ─────────────────────────────────────────────────────────────────────────────
errors:
  E_FILE_NOT_FOUND:
    code: 3001
    message: "Evidence file not found"
    recovery: "Verify file path"

  E_HASH_MISMATCH:
    code: 3002
    message: "Hash verification failed"
    recovery: "Re-acquire evidence if possible"

  E_EVIDENCE_CORRUPTED:
    code: 3003
    message: "Evidence file corrupted"
    recovery: "Document and attempt partial recovery"

---

# Digital Forensics Skill

> **Purpose**: Investigation and evidence analysis.

## Operations Overview

| Operation | Input | Output |
|-----------|-------|--------|
| acquire_evidence | source, type | path, hashes, custody |
| analyze_disk | image_path | artifacts, timeline |
| analyze_memory | dump_path | processes, malware |
| analyze_malware | sample_path | classification, iocs |
| extract_iocs | evidence | iocs, stix |

## Chain of Custody Protocol

```
Evidence → Hash → Document → Copy → Verify → Analyze
```

## Key Artifacts

| OS | Artifact | Location |
|----|----------|----------|
| Windows | Prefetch | C:\Windows\Prefetch |
| Windows | Registry | NTUSER.DAT |
| Linux | auth.log | /var/log |

## Troubleshooting

```
Analysis Failed
    │
    ├─► E_HASH_MISMATCH → Re-acquire or document
    ├─► E_EVIDENCE_CORRUPTED → Partial recovery
    └─► E_FILE_NOT_FOUND → Verify path
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-01-01 | Production-grade upgrade |
| 1.0.0 | 2024-12-29 | Initial release |
