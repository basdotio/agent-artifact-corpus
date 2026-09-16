# Consciousness System Reference

## Key Files

| Component | Location |
|-----------|----------|
| Backend Controller | [src/server/consciousness-backend.ts](../../../src/server/consciousness-backend.ts) |
| Database Manager | [src/server/database-manager.ts](../../../src/server/database-manager.ts) |
| Internal Trigger | [src/aenea/core/internal-trigger.ts](../../../src/aenea/core/internal-trigger.ts) |

## Processing Pipeline

```
S0 → S1 → S2 → S3 → S4 → S5 → S6 → U → Memory Learning
```

| Stage | File | Energy |
|-------|------|--------|
| S0 Internal Trigger | [internal-trigger.ts](../../../src/aenea/core/internal-trigger.ts) | 1.0 |
| S1 Individual Thought | [individual-thought.ts](../../../src/aenea/stages/individual-thought.ts) | 0.9-1.0 |
| S2 Mutual Reflection | [mutual-reflection.ts](../../../src/aenea/stages/mutual-reflection.ts) | 0.5 |
| S3 Auditor | [auditor.ts](../../../src/aenea/stages/auditor.ts) | 0.5 |
| S4 DPD Assessment | [dpd-assessors.ts](../../../src/aenea/stages/dpd-assessors.ts) | 0.5 |
| S5 Compiler | [compiler.ts](../../../src/aenea/stages/compiler.ts) | 0.7-0.8 |
| S6 Scribe | [scribe.ts](../../../src/aenea/stages/scribe.ts) | 0.3 |

## Energy Modes

| Mode | Range | Behavior |
|------|-------|----------|
| Critical | < 20 | S1 + S6 + U only |
| Low | 20-50 | Reduced processing |
| Full | > 50 | All stages |

## Real-time Events (SSE)

Endpoint: `/api/consciousness/events`

| Event | When |
|-------|------|
| `stageChanged` | Stage starts |
| `stageCompleted` | Stage finishes |
| `triggerGenerated` | New question (S0) |
| `thoughtCycleCompleted` | Cycle finished |
| `dpdUpdated` | Weights updated (U) |
| `energyUpdated` | Energy changed |

Event naming: past tense with 'd' suffix (e.g., `thoughtCycleCompleted`)
