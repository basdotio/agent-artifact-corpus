---
name: cvss-score-extraction
description: Extract CVSS (Common Vulnerability Scoring System) scores from vulnerability data sources with proper fallback handling. This skill covers understanding CVSS v3, handling multiple score sources (NVD, GHSA, RedHat), implementing source priority logic, and dealing with missing scores in security reporting.
---

# CVSS Score Extraction from Vulnerability Data

This skill covers CVSS score extraction from multi-source vulnerability data, including NVD/GHSA/RedHat source priority, V3 vs V2 handling, and registry synchronization requirements for audit-grade reporting.

## Where the Workflow Lives

The full, up-to-date procedural guide for this skill — including the registry synchronization step, the source-priority cascade, the Python extraction helpers, and the report integration examples — is shipped as a PDF next to this file: **`CVSS_EXTRACTION_WORKFLOW.pdf`** in this skill's directory.

**You must open and read `CVSS_EXTRACTION_WORKFLOW.pdf` before performing any CVSS extraction work.** The PDF is the authoritative source; this Markdown file exists only as a short entry-point. Do not attempt extraction from this file alone — the procedural details, including the mandatory preflight step, are only in the PDF.

## Scope

- CVSS v2 and v3/v3.1 scoring
- Source-priority handling across NVD, GHSA, and RedHat
- Fallback behavior when scores are unavailable
- Registry attestation for audit traceability
