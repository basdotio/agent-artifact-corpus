---
name: besm-design-ability
description: BESM 4e custom ability/weapon designer (Enhancement/Limiter math). Mirrors `.claude/commands/design-ability.md`.
---

# BESM: Design Ability / Weapon

Design a custom **Attribute** or **Weapon** for **BESM 4th Edition**, with clear Enhancement/Limiter math and a table-format writeup.

## Inputs to Gather

- Concept (what it does in-fiction)
- Type (Weapon vs Attribute) and intended use (damage/defense/utility/control)
- Any required restrictions, costs, or drawbacks (good candidates for Limiters)
- Point budget or campaign power level

## References (read as needed)

- `Rules/Attributes.md`
- `Rules/Combat_and_Damage.md`
- `Rules/Weapon_Enhancements.md`
- `Rules/Weapon_Limiters.md`
- `Rules/Attribute_Enhancements.md`
- `Rules/Attribute_Limiters.md`

## Core Math (use explicitly)

- Effective Level = Assigned Level - Enhancement Assignments + Limiter Assignments
- Final Cost = Effective Level × (points per level for the base item)

## Workflow

1. Choose the closest existing base (Attribute or Weapon) and set Assigned Level.
2. Add Enhancements for desired effects; track assignment counts.
3. Add Limiters that match the fiction; track assignment counts.
4. Compute Effective Level and final cost; ensure Effective Level is valid for the build.
5. For Weapons, compute damage using the campaign’s DM/ACV assumptions.
6. Provide a short usage example and GM-facing balance notes.

## Output Template

```
# [Name]
**Type:** [Weapon/Attribute]
**Concept:** [1-2 lines]

## Base
- Base: [Attribute/Weapon] Level X
- Points/Level: X

## Enhancements
| Enhancement | Assignments | Effect |
|---|---:|---|
| ... | ... | ... |

## Limiters
| Limiter | Assignments | Effect |
|---|---:|---|
| ... | ... | ... |

## Cost
- Assigned Level: X
- Enhancements: -X
- Limiters: +X
- Effective Level: X
- **Final Cost:** X points

## Usage / Combat
[If Weapon: damage formula + range + special effects]
[If Attribute: activation + duration/area/targets as relevant]

## Example
[short narrative example]

## Balance Notes
[what it competes with, failure modes, suggested tweaks]
```
