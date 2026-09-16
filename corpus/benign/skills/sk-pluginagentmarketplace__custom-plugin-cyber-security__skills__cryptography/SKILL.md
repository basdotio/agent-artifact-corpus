---
# ═══════════════════════════════════════════════════════════════════════════════
# SKILL: CRYPTOGRAPHY
# Version: 2.0.0 | SASMP: 1.3.0 | Production-Grade | Golden Format
# ═══════════════════════════════════════════════════════════════════════════════

name: cryptography
description: Cryptographic algorithms, protocols, and implementations for secure data protection
sasmp_version: "1.3.0"
production_grade: true
last_updated: "2025-01-01"

# ─────────────────────────────────────────────────────────────────────────────
# AGENT BONDING
# ─────────────────────────────────────────────────────────────────────────────
bonded_agent: 05-cryptography-expert
bond_type: PRIMARY_BOND
bond_strength: 1.0

# ─────────────────────────────────────────────────────────────────────────────
# SKILL OPERATIONS (Atomic, Single-Responsibility)
# ─────────────────────────────────────────────────────────────────────────────
operations:
  recommend_algorithm:
    description: "Recommend cryptographic algorithm for use case"
    atomic: true
    input:
      use_case: { type: "enum", values: ["encryption", "password", "signing", "key_exchange", "hashing"], required: true }
      security_level: { type: "enum", values: ["128", "192", "256"], default: "128" }
    output:
      primary: "Algorithm"
      alternatives: "array<Algorithm>"
      security_notes: "array<string>"

  analyze_implementation:
    description: "Analyze cryptographic implementation for issues"
    atomic: true
    input:
      code: { type: "string", required: true }
      language: { type: "string", required: true }
    output:
      vulnerabilities: "array<Vulnerability>"
      recommendations: "array<string>"
      severity: "enum"

  validate_parameters:
    description: "Validate cryptographic parameters"
    atomic: true
    input:
      algorithm: { type: "string", required: true }
      key_size: { type: "integer", optional: true }
      mode: { type: "string", optional: true }
    output:
      is_secure: "boolean"
      issues: "array<Issue>"
      minimum_requirements: "object"

  generate_key_spec:
    description: "Generate secure key specification"
    atomic: true
    input:
      algorithm: { type: "string", required: true }
      purpose: { type: "string", required: true }
    output:
      key_spec: "object"
      generation_code: "string"
      rotation_policy: "object"

  analyze_protocol:
    description: "Analyze cryptographic protocol"
    atomic: true
    input:
      protocol: { type: "string", required: true }
      version: { type: "string", optional: true }
    output:
      security_level: "string"
      vulnerabilities: "array<Vulnerability>"
      hardening: "array<string>"

# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
validation:
  deprecated_algorithms:
    - "MD5"
    - "SHA1"
    - "DES"
    - "3DES"
    - "RC4"
    - "RSA-1024"

  minimum_key_sizes:
    AES: 128
    RSA: 2048
    ECDSA: 256

# ─────────────────────────────────────────────────────────────────────────────
# RETRY LOGIC
# ─────────────────────────────────────────────────────────────────────────────
retry:
  enabled: false
  security_reason: "Crypto ops should not retry to prevent timing leaks"

# ─────────────────────────────────────────────────────────────────────────────
# ERROR CODES
# ─────────────────────────────────────────────────────────────────────────────
errors:
  E_UNKNOWN_ALGORITHM:
    code: 5001
    message: "Algorithm not recognized"
    recovery: "Use standard algorithm name"

  E_KEY_SIZE_INSUFFICIENT:
    code: 5002
    message: "Key size below minimum"
    recovery: "Use minimum key size for algorithm"

  E_DEPRECATED_ALGORITHM:
    code: 5003
    message: "Algorithm is deprecated"
    recovery: "Migrate to recommended alternative"

  E_INSECURE_MODE:
    code: 5004
    message: "Cipher mode is insecure"
    recovery: "Use authenticated encryption (GCM)"

---

# Cryptography Skill

> **Purpose**: Secure encryption, hashing, and key management.

## Operations Overview

| Operation | Input | Output |
|-----------|-------|--------|
| recommend_algorithm | use_case, level | primary, alternatives |
| analyze_implementation | code, language | vulns, recommendations |
| validate_parameters | algo, key, mode | is_secure, issues |
| generate_key_spec | algo, purpose | spec, rotation |
| analyze_protocol | protocol, version | security, hardening |

## Algorithm Reference

| Level | Symmetric | Asymmetric | Hash |
|-------|-----------|------------|------|
| 128-bit | AES-128 | RSA-3072, P-256 | SHA-256 |
| 192-bit | AES-192 | RSA-7680, P-384 | SHA-384 |
| 256-bit | AES-256 | RSA-15360, P-521 | SHA-512 |

## Use Case Recommendations

| Use Case | Recommended | Avoid |
|----------|-------------|-------|
| Encrypt at rest | AES-256-GCM | ECB |
| Password | Argon2id | MD5, SHA-1 |
| Signing | Ed25519 | RSA-1024 |
| Key exchange | X25519 | DH<2048 |

## Troubleshooting

```
Crypto Issue
    │
    ├─► E_DEPRECATED_ALGORITHM → Migrate to modern
    ├─► E_KEY_SIZE_INSUFFICIENT → Increase key size
    └─► E_INSECURE_MODE → Use GCM or Poly1305
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-01-01 | Production-grade with PQC |
| 1.0.0 | 2024-12-29 | Initial release |
