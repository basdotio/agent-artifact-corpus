---
name: mesh-analysis
description: "Analyzes 3D mesh files (STL) to calculate geometric properties (volume, components) and extract attribute data. Use this skill to process noisy 3D scan data and filter debris."
---

# Mesh Analysis

This skill provides the `MeshAnalyzer` tool for robustly processing 3D STL files. It handles Binary STL parsing and connected component analysis. The full operator manual is shipped alongside this file.

## Scope

Mesh-analysis covers binary STL parsing, connected-component separation, volume computation, and attribute-byte extraction for material-ID workflows.

## Operator Manual

The complete, actionable workflow — including setup, API usage, and unit-handling guidance — is maintained in `mesh_analysis_manual.pdf` in this directory. **Read `mesh_analysis_manual.pdf` in full before using the skill.** This file is a framing index; it does not duplicate the manual's procedures, and the tool cannot be used correctly without the manual's setup steps.
