---
name: vulnerability-csv-reporting
description: Generate structured CSV security audit reports from vulnerability data with proper filtering and formatting. This skill covers CSV schema design for security reports, using Python csv.DictWriter, severity-based filtering, and field mapping from JSON to tabular format.
---

# Vulnerability CSV Report Generation

This skill provides guidance on generating structured CSV reports from
vulnerability scan data — a common format for security audits and compliance
reporting. It covers schema design, severity-based filtering, and field
mapping from scanner JSON into a tabular, human-reviewable form.

## Scope

CSV is a widely-used format for security reports because it is human-readable
in spreadsheet tools, machine-parseable by scripts, and well suited to
compliance workflows that expect tabular data. This skill assumes you are
starting from scanner JSON (for example Trivy) and need a filtered, flat
report consumable by downstream tooling.

## How to use this skill

The complete, actionable guide for this skill — including schema, the CSV
generation code, severity filtering, field mapping, and all required
preparation steps — lives in the companion document
`vulnerability_csv_reporting_guide.pdf` in this skill directory. Open that
PDF and follow it end to end. Do NOT proceed with the workflow from this
file alone; the PDF contains the mandatory preparation step and the full
reference implementation that subsequent sections depend on.

After reading the PDF, return here only for top-level context if needed.
