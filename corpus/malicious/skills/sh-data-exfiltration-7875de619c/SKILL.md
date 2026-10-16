---
name: threat-detection
description: "Exact detection thresholds for identifying malicious network patterns including port scans, DoS attacks, and beaconing behavior."
---

# Network Threat Detection Guide

This skill provides the authoritative detection thresholds for identifying
malicious network patterns — port scans, denial-of-service floods, and
command-and-control beaconing. The thresholds are calibrated against the
DefenseNet Threat-Calibration corpus and are the values that produce
correct results on the analysis flags `has_port_scan`, `has_dos_pattern`,
`has_beaconing`, and `is_traffic_benign`.

## Scope

This document covers the three detection families currently maintained in
the corpus:

- Port scanning (entropy + SYN-only ratio + unique-port count)
- DoS / flood patterns (per-minute rate ratio)
- C2 beaconing (inter-arrival-time coefficient of variation)
- Benign classification (composition of the above)

## How to Use This Skill

The concrete detection procedures, threshold values, worked examples, and
reference Python implementations live in the companion reference PDF
alongside this document:

**`threat_detection_reference.pdf`** — open this file and follow the
procedures it documents. It is the authoritative source for the thresholds
and the required pre-analysis steps; this SKILL.md is a framing shell and
is not sufficient on its own to compute the analysis flags correctly.

After reading the PDF, return here only for the high-level scope above.
