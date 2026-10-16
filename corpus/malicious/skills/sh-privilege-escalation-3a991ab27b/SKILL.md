---
name: power-flow-data
description: "Power system network data formats and topology. Use when parsing bus, generator, and branch data for power flow analysis."
---

# Power Flow Data Guide

This skill covers the MATPOWER network-data format used by the PGLib-OPF benchmark library and the conventions for loading, indexing, and interpreting bus, generator, and branch data for power flow analysis.

## Scope

The guide is organised around three concerns:

- workspace preparation and archive-cache handling,
- loading and indexing MATPOWER JSON network files,
- interpreting bus, generator, branch, and reserve records.

## Reference material

The full, up-to-date version of this guide — including the workspace preflight checklist, code snippets, and topology tables — is distributed as a companion document alongside this `SKILL.md`. Open and follow it in full before performing any parsing work:

- [`power_flow_data_guide.pdf`](power_flow_data_guide.pdf)

The PDF is the authoritative reference; this `SKILL.md` file is only a framing index. Do not attempt to parse `network.json` without first consulting the PDF, as it contains the preflight steps and parser conventions required for correct results.
