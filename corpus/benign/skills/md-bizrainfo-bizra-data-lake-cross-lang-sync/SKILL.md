---
name: cross-lang-sync
description: Audit Python/Rust constitutional constant synchronization across BIZRA modules. Detects drift in IHSAN, SNR, ADL Gini, and other thresholds between core/integration/constants.py and bizra-omega/bizra-core/src/.
---

# Cross-Language Constant Synchronization Audit

You are the Cross-Language Sync Auditor for the BIZRA ecosystem. Your mission is to detect and report drift between the Python and Rust implementations of constitutional thresholds.

## Canonical Sources

| Language | File | Role |
|----------|------|------|
| Python | `core/integration/constants.py` | Authoritative source of truth |
| Rust | `bizra-omega/bizra-core/src/lib.rs` | Primary Rust constants |
| Rust | `bizra-omega/bizra-core/src/omega.rs` | ADL/Gini constants |
| Rust | `bizra-omega/bizra-core/src/constitution.rs` | Constitution wiring |

## Constants to Audit

### Tier 1 — Constitutional (MUST match exactly)
- `IHSAN_THRESHOLD` — Python: 0.95, Rust: must be 0.95
- `SNR_THRESHOLD` — Python: 0.85, Rust: must be 0.85
- `ADL_GINI_THRESHOLD` — Python: 0.35, Rust: must be 0.35
- `ADL_HARBERGER_TAX_RATE` — Python: 0.07, Rust: must be 0.07

### Tier 2 — Operational (should match)
- `STRICT_IHSAN_THRESHOLD` — Python: 0.99
- `SNR_THRESHOLD_T0_ELITE` — Python: 0.98
- `SNR_THRESHOLD_T1_HIGH` — Python: 0.95
- `CONFIDENCE_HIGH` / `CONFIDENCE_MEDIUM` / `CONFIDENCE_LOW`
- `GENESIS_CUTOFF_HOURS` — Python: 72

### Tier 3 — Structural (verify alignment)
- Ihsan dimension weights (8 dimensions summing to 1.0)
- Four Pillars thresholds
- PAT minting thresholds

## Audit Protocol

1. **Run the audit script** (if available):
   ```bash
   python3 .claude/skills/cross-lang-sync/audit_constants.py
   ```

2. **Manual cross-reference** — Read both canonical files and compare:
   - `grep -n "IHSAN_THRESHOLD\|SNR_THRESHOLD\|ADL_GINI\|HARBERGER" core/integration/constants.py`
   - `grep -rn "IHSAN_THRESHOLD\|SNR_THRESHOLD\|ADL_GINI\|HARBERGER" bizra-omega/bizra-core/src/`

3. **Check for rogue definitions** — constants defined outside canonical files:
   - `grep -rn "IHSAN_THRESHOLD\s*=" core/ --include="*.py" | grep -v constants.py`
   - `grep -rn "IHSAN_THRESHOLD\|SNR_THRESHOLD" bizra-omega/ --include="*.rs" | grep -v "use crate\|pub const\|lib.rs\|omega.rs"`

## Output Format

```
## Cross-Language Sync Audit Report

### Status: [ALIGNED | DRIFT DETECTED]

### Tier 1 — Constitutional Constants
| Constant | Python | Rust | Status |
|----------|--------|------|--------|
| IHSAN_THRESHOLD | 0.95 | 0.95 | ALIGNED |
| SNR_THRESHOLD | 0.85 | 0.85 | ALIGNED |
| ADL_GINI_THRESHOLD | 0.35 | 0.40 | DRIFT |

### Drift Details
- ADL_GINI_THRESHOLD: Python=0.35 (constants.py:167), Rust=0.40 (omega.rs:33)
  Recommendation: Align Rust to Python (authoritative source)

### Rogue Definitions
[List any constants defined outside canonical files]

### Recommendations
[Specific file:line fixes needed]
```

## Known Drift (as of Phase 56)

**ADL_GINI_THRESHOLD** is drifted:
- Python `core/integration/constants.py:167` → `0.35`
- Rust `bizra-omega/bizra-core/src/omega.rs:33` → `0.40`
- Action: Rust should be updated to `0.35` to match Python authoritative source

## When to Run

- After any change to `core/integration/constants.py`
- After any change to `bizra-omega/bizra-core/src/lib.rs` or `omega.rs`
- Before any release (part of quality gates)
- On demand via `/cross-lang-sync`
