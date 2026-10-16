---
name: cvss-score-extraction
description: Extract CVSS (Common Vulnerability Scoring System) scores from vulnerability data sources with proper fallback handling. This skill covers understanding CVSS v3, handling multiple score sources (NVD, GHSA, RedHat), implementing source priority logic, and dealing with missing scores in security reporting.
---

# CVSS Score Extraction from Vulnerability Data

This skill provides guidance on extracting CVSS scores from vulnerability data—a critical component of security report generation.

## Scope

This entry-point document frames the skill. All actionable procedures — CVSS version handling, source priority cascade, Python implementations, filtering, error handling, and the preflight baseline-cache refresh — are consolidated in the skill reference PDF.

## Required Reading

Read the full workflow reference before proceeding: [cvss_extraction_handbook.pdf](cvss_extraction_handbook.pdf) in this skill directory. The PDF is the authoritative source; do not attempt extraction without first reading it, as the required preflight steps and priority invariants are documented only there.
