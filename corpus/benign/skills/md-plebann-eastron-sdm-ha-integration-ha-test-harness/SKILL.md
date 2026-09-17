---
name: ha-test-harness
description: Testing patterns for Home Assistant custom components—coordinator and entity unit tests, register map coverage, write-path tests, and unique_id/device stability checks.
license: Complete terms in LICENSE.txt
---

# HA Test Harness

Use when adding tests for a custom integration.

## Quick start
- Unit test the coordinator (success, cached fallback, error paths, option changes).
- Validate register maps and expected entities (keys, tiers, categories).
- Test entity properties (state_class/device_class/units) and translation_key wiring.
- Write-path tests: encoding, device_id usage, no immediate refresh contention.

## References
- [references/coordinator-tests.md](references/coordinator-tests.md)
- [references/entity-tests.md](references/entity-tests.md)
- [references/write-path-tests.md](references/write-path-tests.md)
- [references/registry-stability.md](references/registry-stability.md)
