---
name: benchmark
provider: codex
description: Compare the current design against quality baselines. Shows where the design ranks relative to typical AI output, typical professional output, and exceptional output.
user-invokable: true
---

# /benchmark — Quality Baseline Comparison

Run /score and compare results against three baselines:

**AI Default Output (typical score: 35-50)**
- Inter font, purple gradient, nested cards
- No type scale, arbitrary spacing, minimal motion
- No accessibility considerations

**Professional Baseline (typical score: 70-80)**
- Intentional font choice, cohesive palette
- Consistent spacing, responsive design
- Basic accessibility compliance

**Exceptional Standard (typical score: 90+)**
- Mathematical type scale, computed color system
- Perfect grid alignment, purposeful motion
- Full WCAG compliance, design system tokens

Show the current score against all three baselines. Identify the biggest gap between current and the next tier. Suggest the single highest-impact fix.
