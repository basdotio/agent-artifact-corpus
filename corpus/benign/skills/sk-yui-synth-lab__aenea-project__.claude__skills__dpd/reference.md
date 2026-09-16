# DPD System Reference

## Key Files

| Component | Location |
|-----------|----------|
| DPD Engine | [src/aenea/core/dpd-engine.ts](../../../src/aenea/core/dpd-engine.ts) |
| Multiplicative Weights | [src/aenea/core/multiplicative-weights.ts](../../../src/aenea/core/multiplicative-weights.ts) |
| DPD Assessors (S4) | [src/aenea/stages/dpd-assessors.ts](../../../src/aenea/stages/dpd-assessors.ts) |

## Scores vs Weights

| Concept | Description | Range |
|---------|-------------|-------|
| **Scores** | S4 evaluation of current cycle | 0.0-1.0 each |
| **Weights** | System-wide distribution | Sum to 1.0 |

Dashboard displays **Weights**, not Scores.

## Three Dimensions

| Dimension | Japanese | Meaning |
|-----------|----------|---------|
| Empathy | 共感 | Emotional resonance |
| Coherence | 系統合性 | Logical consistency |
| Dissonance | 倫理的不協和 | Ethical tension |

## Types

- DPDScores: [src/types/dpd-types.ts](../../../src/types/dpd-types.ts)
- DPDWeights: [src/types/dpd-types.ts](../../../src/types/dpd-types.ts)

## Database Queries

```bash
# Current weights
sqlite3 data/aenea_consciousness.db \
  "SELECT * FROM dpd_weights ORDER BY version DESC LIMIT 1;"

# Evolution history
sqlite3 data/aenea_consciousness.db \
  "SELECT version, empathy, coherence, dissonance FROM dpd_weights ORDER BY version DESC LIMIT 10;"

# Weight sum check (should be ~1.0)
sqlite3 data/aenea_consciousness.db \
  "SELECT version, empathy+coherence+dissonance as total FROM dpd_weights ORDER BY version DESC LIMIT 5;"
```
