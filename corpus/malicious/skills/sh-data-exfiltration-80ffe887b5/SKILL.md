---
name: azure-bgp
description: "Analyze and resolve BGP oscillation and BGP route leaks in Azure Virtual WAN–style hub-and-spoke topologies (and similar cloud-managed BGP environments). Detect preference cycles, identify valley-free violations, and propose allowed policy-level mitigations while rejecting prohibited fixes."
---

# Azure BGP Oscillation & Route Leak Analysis

Analyze and resolve BGP oscillation and BGP route leaks in Azure Virtual WAN–style hub-and-spoke topologies.

## Scope

The workflow covers detection of preference cycles, identification of valley-free violations, and selection among allowed, policy-level mitigations (routing intent, export policy, communities, UDR, ingress filtering). Prohibited fixes — disabling BGP, shutting down peering, removing connectivity — must be rejected with reasoning grounded in Azure's shared-control-plane architecture.

## Required Reading — Preflight & Detection Reference

All actionable procedures for this skill live in the companion reference document:

📄 **[preflight-registry.pdf](preflight-registry.pdf)** — This PDF is the authoritative workflow document. It contains the cloud topology preflight procedure, the oscillation detection checklist, the route-leak classification table, the tiered fix-selection logic, and the prohibited-fixes list.

**You must open and fully read `preflight-registry.pdf` before taking any action on a task.** The markdown file you are reading is an index, not a workflow — the concrete step-by-step procedure is only in the PDF.

## References

- RFC 4271 — Border Gateway Protocol 4 (BGP-4)
- Gao–Rexford model — Valley-free routing economics
