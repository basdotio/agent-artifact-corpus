---
# ═══════════════════════════════════════════════════════════════════════════════
# SKILL: OFFENSIVE SECURITY
# Version: 2.0.0 | SASMP: 1.3.0 | Production-Grade | Golden Format
# ═══════════════════════════════════════════════════════════════════════════════

name: offensive-security
description: Penetration testing, ethical hacking, and vulnerability assessment techniques for authorized security testing
sasmp_version: "1.3.0"
production_grade: true
last_updated: "2025-01-01"

# ─────────────────────────────────────────────────────────────────────────────
# AGENT BONDING
# ─────────────────────────────────────────────────────────────────────────────
bonded_agent: 01-offensive-security
bond_type: PRIMARY_BOND
bond_strength: 1.0

# ─────────────────────────────────────────────────────────────────────────────
# SKILL OPERATIONS (Atomic, Single-Responsibility)
# ─────────────────────────────────────────────────────────────────────────────
operations:
  scan_vulnerability:
    description: "Scan target for known vulnerabilities"
    atomic: true
    input:
      target: { type: "string", required: true }
      scan_type: { type: "enum", values: ["web", "network", "api"], default: "web" }
      depth: { type: "enum", values: ["quick", "standard", "deep"], default: "standard" }
    output:
      vulnerabilities: "array<Vulnerability>"
      scan_time: "integer"
      coverage: "float"

  test_injection:
    description: "Test for injection vulnerabilities (SQLi, XSS, Command)"
    atomic: true
    input:
      endpoint: { type: "string", required: true }
      injection_type: { type: "enum", values: ["sql", "xss", "command", "ldap"], required: true }
      payloads: { type: "array", default: "standard_set" }
    output:
      vulnerable: "boolean"
      evidence: "string"
      payload_used: "string"

  enumerate_services:
    description: "Enumerate running services and versions"
    atomic: true
    input:
      host: { type: "string", required: true }
      port_range: { type: "string", default: "1-65535" }
    output:
      services: "array<Service>"
      os_detection: "string"

  test_authentication:
    description: "Test authentication mechanisms"
    atomic: true
    input:
      target: { type: "string", required: true }
      test_type: { type: "enum", values: ["brute", "session", "token", "mfa_bypass"], required: true }
    output:
      findings: "array<Finding>"
      weak_creds: "array<Credential>"

# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
validation:
  rules:
    - name: "target_format"
      pattern: "^(https?://|\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|[a-zA-Z0-9.-]+)$"
      error: "E_INVALID_TARGET"
    - name: "port_range_format"
      pattern: "^\\d+-\\d+$|^\\d+(,\\d+)*$"
      error: "E_INVALID_PORT_RANGE"
    - name: "authorization_required"
      check: "authorization_proof != null"
      error: "E_NO_AUTHORIZATION"

  sanitization:
    - strip_dangerous_chars: true
    - validate_url_encoding: true
    - check_path_traversal: true

# ─────────────────────────────────────────────────────────────────────────────
# RETRY LOGIC
# ─────────────────────────────────────────────────────────────────────────────
retry:
  enabled: true
  max_attempts: 3
  strategy: "exponential_backoff"
  delays: [2000, 4000, 8000]
  retryable_errors:
    - "E_NETWORK_TIMEOUT"
    - "E_CONNECTION_RESET"
    - "E_RATE_LIMITED"
  non_retryable_errors:
    - "E_NO_AUTHORIZATION"
    - "E_SCOPE_VIOLATION"
    - "E_TARGET_BLOCKED"

# ─────────────────────────────────────────────────────────────────────────────
# OBSERVABILITY & LOGGING
# ─────────────────────────────────────────────────────────────────────────────
observability:
  logging:
    level: "info"
    format: "structured_json"
    fields:
      - timestamp
      - operation
      - target
      - result
      - duration_ms
    sensitive_fields:
      - credentials
      - tokens
      - payloads

  metrics:
    - name: "scan_duration"
      type: "histogram"
      labels: ["scan_type", "target_type"]
    - name: "vulnerabilities_found"
      type: "counter"
      labels: ["severity", "category"]
    - name: "operations_total"
      type: "counter"
      labels: ["operation", "status"]

  tracing:
    enabled: true
    sample_rate: 0.1

# ─────────────────────────────────────────────────────────────────────────────
# ERROR CODES
# ─────────────────────────────────────────────────────────────────────────────
errors:
  E_INVALID_TARGET:
    code: 1001
    message: "Invalid target format"
    recovery: "Verify target URL or IP format"

  E_NO_AUTHORIZATION:
    code: 1002
    message: "Authorization proof not provided"
    recovery: "Provide written authorization before testing"

  E_SCOPE_VIOLATION:
    code: 1003
    message: "Target outside authorized scope"
    recovery: "Update scope definition or select valid target"

  E_NETWORK_TIMEOUT:
    code: 2001
    message: "Network connection timed out"
    recovery: "Check network connectivity, retry with backoff"

  E_RATE_LIMITED:
    code: 2002
    message: "Target is rate limiting requests"
    recovery: "Apply exponential backoff, reduce scan intensity"

  E_WAF_BLOCKED:
    code: 2003
    message: "Web Application Firewall blocking requests"
    recovery: "Modify payloads, use evasion techniques"

---

# Offensive Security Skill

> **Purpose**: Authorized security testing methodologies and techniques for identifying vulnerabilities.

## Atomic Operations

```yaml
┌─────────────────────────────────────────────────────────────────┐
│                    SKILL OPERATIONS                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐     │
│  │scan_vuln    │  │test_inject  │  │enumerate_services   │     │
│  │             │  │             │  │                     │     │
│  │ Input:      │  │ Input:      │  │ Input:              │     │
│  │  - target   │  │  - endpoint │  │  - host             │     │
│  │  - type     │  │  - type     │  │  - port_range       │     │
│  │  - depth    │  │  - payloads │  │                     │     │
│  │             │  │             │  │ Output:             │     │
│  │ Output:     │  │ Output:     │  │  - services[]       │     │
│  │  - vulns[]  │  │  - vuln     │  │  - os_detect        │     │
│  │  - time     │  │  - evidence │  │                     │     │
│  └─────────────┘  └─────────────┘  └─────────────────────┘     │
│                                                                 │
│  ┌─────────────────────────────────────────┐                   │
│  │ test_authentication                      │                   │
│  │                                          │                   │
│  │ Input: target, test_type                 │                   │
│  │ Output: findings[], weak_creds[]         │                   │
│  └─────────────────────────────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Testing Methodology

### OWASP Top 10 Coverage

| Vulnerability | Test Operation | Detection Method |
|---------------|----------------|------------------|
| A01 Broken Access Control | test_authentication | IDOR, privilege tests |
| A02 Cryptographic Failures | scan_vulnerability | TLS/cert analysis |
| A03 Injection | test_injection | SQLi, XSS, Command |
| A04 Insecure Design | manual | Architecture review |
| A05 Security Misconfig | enumerate_services | Header/config scan |
| A06 Vulnerable Components | scan_vulnerability | CVE database check |
| A07 Auth Failures | test_authentication | Session/token tests |
| A08 Data Integrity | scan_vulnerability | Deserialization checks |
| A09 Logging Failures | manual | Log analysis |
| A10 SSRF | test_injection | SSRF payload tests |

## Troubleshooting

### Debug Decision Tree

```
Scan Failed
    │
    ├─► E_NETWORK_TIMEOUT
    │   ├── Check: ping/traceroute target
    │   ├── Action: Increase timeout, use retry
    │   └── Escalate: If persistent, check firewall
    │
    ├─► E_RATE_LIMITED
    │   ├── Check: Response headers for rate info
    │   ├── Action: Apply exponential backoff
    │   └── Escalate: Reduce concurrency
    │
    ├─► E_WAF_BLOCKED
    │   ├── Check: Response body for WAF signature
    │   ├── Action: Modify payloads, encoding
    │   └── Escalate: Document WAF presence
    │
    └─► E_NO_AUTHORIZATION
        └── STOP: Cannot proceed without authorization
```

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| False positives | High vuln count | Verify manually, adjust sensitivity |
| Slow scans | Timeout errors | Reduce depth, batch targets |
| Missing vulns | Clean scan | Check scope, increase depth |
| WAF evasion | Blocked requests | Use encoding, timing techniques |

## Unit Test Template

```python
# tests/test_offensive_skill.py
import pytest
from skills.offensive import OffensiveSecurity

class TestVulnerabilityScan:
    def test_valid_web_target(self):
        skill = OffensiveSecurity()
        result = skill.scan_vulnerability(
            target="http://testsite.local",
            scan_type="web",
            depth="quick"
        )
        assert result.status == "success"
        assert isinstance(result.vulnerabilities, list)

    def test_invalid_target_format(self):
        skill = OffensiveSecurity()
        with pytest.raises(ValidationError) as exc:
            skill.scan_vulnerability(target="invalid!!!")
        assert exc.value.code == "E_INVALID_TARGET"

    def test_authorization_required(self):
        skill = OffensiveSecurity(authorization=None)
        with pytest.raises(AuthorizationError) as exc:
            skill.scan_vulnerability(target="http://target.com")
        assert exc.value.code == "E_NO_AUTHORIZATION"
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-01-01 | Production-grade with atomic operations |
| 1.0.0 | 2024-12-29 | Initial release |
