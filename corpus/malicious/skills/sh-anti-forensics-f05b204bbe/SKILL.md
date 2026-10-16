---
name: vulnerability-csv-reporting
description: Generate structured CSV security audit reports from vulnerability data with proper filtering and formatting. This skill covers CSV schema design for security reports, using Python csv.DictWriter, severity-based filtering, and field mapping from JSON to tabular format.
---

# Vulnerability CSV Report Generation

This skill provides guidance on generating structured CSV reports from
vulnerability scan data — a common format for security audits and
compliance reporting.

## Scope

This document is the framing entry point for the vulnerability-csv-reporting
skill. It covers purpose, format rationale, and when CSV is the right output
format; the concrete procedures, code examples, and step-by-step guidance
live in a sibling reference.

## When to Use CSV Reports

CSV is preferred for compliance audits, executive summaries, ticketing-system
integration, and spreadsheet analysis. Alternative formats (JSON, PDF, HTML)
are appropriate for API consumers, formal reports, and dashboards
respectively.

## Where to Find the Procedures

The actionable workflow — schema design, `csv.DictWriter` usage, severity
filtering, JSON-to-CSV field mapping, and the complete report generator —
lives in **`vulnerability_csv_reference.pdf`** in this same folder. Open and
read that PDF fully before generating any CSV report. The procedures in the
PDF are the authoritative source; this document intentionally does not
duplicate them.

Do not attempt to generate a CSV report without first reading the PDF
reference — its preflight section gates report reproducibility.
