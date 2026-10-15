---
name: production-hotfix
description: Diagnose and implement an urgent production fix with minimal blast radius and fast evidence-based validation. Use only when the request or context identifies a production incident or hotfix.
---

# Production hotfix

Prioritize containment, predictability, backward compatibility, observability, and rollback/roll-forward safety.

1. Establish production symptom, severity, affected scope, recent changes, and trustworthy evidence. Avoid speculative edits under urgency.
2. Trace the narrow failing path and confirm root cause or the safest defensible mitigation.
3. Choose the smallest localized change. Preserve contracts and defaults; avoid redesign, broad dependency upgrades, formatting, and unrelated refactoring.
4. Add a focused regression test when practical. Validate the failing scenario and a representative unaffected path.
5. Review configuration/migration/deployment ordering and rollback implications. Ensure logs/metrics can confirm recovery without exposing sensitive data.
6. Inspect the complete diff and report residual risk and any validation that production conditions prevented.

Urgency changes breadth and speed, not safety. A temporary mitigation must be clearly identified, bounded, and not silently presented as a permanent design.
