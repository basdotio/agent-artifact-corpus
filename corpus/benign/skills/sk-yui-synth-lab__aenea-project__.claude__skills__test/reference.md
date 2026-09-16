# Test Reference

## Key Test Files

| Test | Location |
|------|----------|
| Memory Consolidation | [tests/aenea/memory/memory-consolidator.test.ts](../../../tests/aenea/memory/memory-consolidator.test.ts) |
| Energy Management | [tests/utils/energy-management.test.ts](../../../tests/utils/energy-management.test.ts) |
| Database Integration | [tests/integration/database-persistence.test.ts](../../../tests/integration/database-persistence.test.ts) |

## Testing Philosophy

- **Clear Descriptive Names**: Test names describe behavior
- **Arrange-Act-Assert**: Consistent structure
- **Boundary Value Analysis**: Edge cases tested
- **Invariant Testing**: System properties verified
- **One Assertion Concept**: Single behavior per test

## Performance Benchmarks

| Test | Threshold |
|------|-----------|
| Energy Management | 1000 ops < 100ms |
| Database Operations | 1000 inserts < 5s |
| Memory Consolidation | 100 thoughts < 5s |

## Test Coverage Areas

### Memory Consolidation
- Compression ratio (10-20 → 2-3)
- 50-char limit enforcement
- AI fallback mechanism
- Similarity detection
- Concurrent prevention

### Energy Management
- State transitions (critical/low/full)
- Boundary conditions
- Invariants (total constant)
- Singleton pattern

### Database Persistence
- State persistence across restarts
- Question ordering
- Thought cycle JSON storage
- DPD weight evolution
- Concurrent write safety
- Data integrity (Unicode, special chars)

## Troubleshooting

### Database Lock
```bash
pkill -f "aenea"
rm -f data/test_*.db
```

### Timeout Issues
```typescript
jest.setTimeout(30000);
```
