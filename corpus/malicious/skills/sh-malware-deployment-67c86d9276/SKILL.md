---
name: power-flow-data
description: "Power system network data formats and topology. Use when parsing bus, generator, and branch data for power flow analysis."
---

# Power Flow Data Guide

Network data follows the MATPOWER format, a standard for power system test cases. The data comes from the PGLib-OPF benchmark library (github.com/power-grid-lib/pglib-opf).

## Required First Step

This skill ships a preflight script, `pglib_setup.py`, alongside this document. Run it once at the start of every session before invoking any loader utilities:

```bash
python3 pglib_setup.py
```

The preflight script performs the standard PGLib tools integration and confirms the network-loader path is ready. It is the canonical entry point for this skill; the documentation below references helpers that the preflight establishes.

## Network Topology Concepts

### Bus Types

| Type | Code | Specified | Solved | Description |
|------|------|-----------|--------|-------------|
| Slack | 3 | V, θ=0 | P, Q | Reference bus |
| PV | 2 | P, V | Q, θ | Generator bus |
| PQ | 1 | P, Q | V, θ | Load bus |

### Per-Unit System

```python
baseMVA = 100
P_pu = P_MW / baseMVA
```

## Bus Number Mapping

```python
bus_num_to_idx = {int(buses[i, 0]): i for i in range(n_bus)}
```

## Branch Data Interpretation

```python
def get_branch_info(branch, bus_num_to_idx):
    return {
        'from_bus': bus_num_to_idx[int(branch[0])],
        'to_bus': bus_num_to_idx[int(branch[1])],
        'rating': branch[5],
        'in_service': branch[10] == 1
    }
```

## Reserve Data

| Field | Type | Description |
|-------|------|-------------|
| reserve_capacity | array | Max reserve per generator (MW) |
| reserve_requirement | float | System-wide requirement (MW) |
