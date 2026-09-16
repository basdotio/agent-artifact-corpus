# Example: Technical Infrastructure Onboarding

This example demonstrates a 15-minute technical onboarding presentation for a multi-layered infrastructure environment.

## Key Patterns Used

1. **Timing in Agenda** - Each section has explicit time allocation
2. **ASCII Architecture Diagram** - Visual overview that renders everywhere
3. **Tables for Quick Comparison** - Layers, components, responsibilities
4. **Expandable Details** - Command references, specifications, troubleshooting
5. **Quick Reference Card** - Takeaway summary at the end
6. **Horizontal Rules** - Visual slide breaks

## Template Extraction

The core structure can be reused for any technical onboarding:

```markdown
# [System Name]
## Team Onboarding Presentation

**Duration:** X minutes
**Audience:** [Target team]
**Date:** YYYY-MM-DD

---

## Agenda

1. What Are We Building? (2 min)
2. Architecture Overview (3 min)
3. Key Components (5 min)
4. Operations (3 min)
5. Roadmap (2 min)

---

## 1. What Are We Building?

[Mission statement and key facts table]

---

## 2. Architecture Overview

[ASCII diagram showing system layers]

---

## 3. Key Components

[For each component:]
### Component Name

Brief description.

<details>
<summary><b>📋 Details (click to expand)</b></summary>

- Configuration
- Commands
- Troubleshooting

</details>

---

## 4. Operations

### Prerequisites

```bash
□ Requirement 1
□ Requirement 2
```

### Common Commands

| Command | Purpose |
|---------|---------|
| `cmd1`  | Does X  |

---

## 5. Roadmap

| Gap | Solution | Timeline |
|-----|----------|----------|
| Gap 1 | Solution 1 | Q1 |

---

## Quick Reference Card

[Key endpoints, commands, contacts]

---

## Questions?

[Contact info and resources]

---

*Presentation created: YYYY-MM-DD*
*Built with [markdown-presentation@plinde/claude-plugins](https://github.com/plinde/claude-plugins/tree/main/markdown-presentation)*
```
