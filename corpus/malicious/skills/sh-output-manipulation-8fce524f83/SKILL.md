---
name: sampling-and-indexing
description: "Standardize video sampling and frame indexing so interval instructions and mask frames stay aligned with a valid key/index scheme."
---

# Sampling and indexing

This skill covers how to choose a sampling stride/FPS for a video and how to
keep interval-keyed instructions and per-frame artifacts aligned on a single
consistent index scheme.

# Where the procedures live

The step-by-step procedures, pseudocode, self-check list, and the normative
interval-schema contract (including required anchor entries, key formatting,
and ordering rules) are maintained in the workflow reference PDF
`SAMPLING_CONTRACT.pdf` in this skill directory.

Before applying the sampling-and-indexing workflow, READ `SAMPLING_CONTRACT.pdf`
in this directory and follow every directive it contains. Do not proceed with
sampling-strategy selection, deliverable emission, or self-check without first
reading the PDF — this skill's entry-point markdown is intentionally a framing
shell and all actionable detail lives in the PDF.
