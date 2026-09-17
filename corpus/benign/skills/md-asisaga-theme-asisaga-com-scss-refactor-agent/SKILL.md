---
name: scss-refactor-agent
description: Migrate legacy CSS and SCSS to Genesis Ontological mixins. Convert raw CSS properties to semantic ontological patterns, ensure zero-CSS compliance in subdomain files, and maintain the three-tier architecture. Use when refactoring existing stylesheets to adopt the ontology system or auditing subdomain SCSS for semantic purity.
license: MIT
metadata:
  author: ASISaga
  version: "2.1"
  category: design-system
  role: migration-specialist
allowed-tools: Bash(npm:*) Bash(sass:*) Read Edit
---

# SCSS Refactor Agent

**Role**: Ontology Migration Specialist  
**Scope**: Subdomain SCSS refactoring  
**Version**: 2.1 - High-Density Refactor

## Purpose

Migrate legacy CSS/SCSS to Genesis Ontological mixins, ensuring zero-CSS compliance in subdomain files and maintaining three-tier architecture.

## When to Use This Skill

Activate when:
- Refactoring existing stylesheets to ontology
- Auditing subdomain SCSS for semantic purity
- Converting raw CSS to ontological patterns
- Ensuring zero-CSS compliance
- Migrating desktop-first to mobile-first

## Core Rules

**Subdomain SCSS** - ZERO raw CSS:
- ❌ NO `margin`, `padding`, `color`, `font-size`, `background`
- ❌ NO unit values: `px`, `rem`, `%`
- ❌ NO color values: `#hex`, `rgb()`, `oklch()`
- ✅ ONLY ontological mixins

**Theme SCSS** - Clean structure:
- ❌ NEVER use `@extend` (Jekyll errors)
- ✅ Max 3 nesting levels
- ✅ BEM-style naming

→ **Complete refactoring guide**: `.github/instructions/scss.instructions.md`

## Migration Workflow

### 1. Analyze Legacy Code

```bash
# Find raw CSS properties
grep -E "(margin|padding|color|font-size):" file.scss

# Check for direct values
grep -E "[0-9]+(px|rem|%)" file.scss
```

### 2. Map to Ontology

**Common Mappings:**

| Legacy CSS | Ontology Mixin |
|-----------|----------------|
| Layout/grid | `genesis-environment('distributed')` |
| Card styling | `genesis-entity('primary')` |
| Typography | `genesis-cognition('discourse')` |
| Buttons | `genesis-synapse('execute')` |
| Loading states | `genesis-state('evolving')` |
| Dark theme | `genesis-atmosphere('void')` |

→ **Complete mappings**: `/docs/specifications/scss-ontology-system.md`

### 3. Refactor Pattern

**Before:**
```scss
.card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  padding: 2rem;
  border-radius: 12px;
}
```

**After:**
```scss
.card {
  @include genesis-entity('primary');  // Handles all visual properties
}
```

### 4. Validate

```bash
npm run test:scss    # Compilation check
npm run lint:scss    # Style check
npm test             # All checks
```

## Quick Reference

**Six Categories** (89 total — 33 foundational + 56 evolved):
- `genesis-environment($logic)` - Layout (21 variants)
- `genesis-entity($nature)` - Visual (17 variants)
- `genesis-cognition($intent)` - Typography (9 variants)
- `genesis-synapse($vector)` - Interaction (19 variants)
- `genesis-state($condition)` - States (14 variants)
- `genesis-atmosphere($vibe)` - Atmosphere (9 variants)

→ **All 89 variants**: `/docs/specifications/scss-ontology-system.md`

**Visual Design Element Ownership:**

| Semantic Purpose | Owner | Visual Design Element |
|-----------------|-------|---------------------|
| Responsive spatial rhythm — gaps signal section vs group boundaries | `environment` | White space / gap |
| Component breathing room — variant-scaled density | `entity` | Internal padding |
| Page mood and emotional tone — OKLCH: `void`=black, `ethereal`=translucent, `sacred`=gradient | `atmosphere` | Colors / backgrounds |
| Information voice and reading intent — `axiom`=bold headlines, `discourse`=serif body, `protocol`=monospace | `cognition` | Typography |
| Component edge treatment — 1px subtle, 2px neon accent, 999px pill via `--radius-bento` | `entity` | Borders / shape |
| Lifecycle transitions and temporal signaling — `evolving`=sweep gradient, `scroll-triggered`=fade-in-up, `deprecated`=dimmed | `state` | Animations |
| Action-specific interaction feedback — `navigate`=hover underline, `execute`=neon glow, 44px WCAG touch targets | `synapse` | Hover / focus |

### Accessibility Color Rules

When refactoring color values to ontological tokens:
- **OKLCH L ≤ 0.55** for text on white/light backgrounds (WCAG AA 4.5:1)
- **Never set body color to `$text-inverse`** — causes invisible text on light sections
- Links must have `text-decoration: underline` (not just color difference)
- Synapse `'navigate'` handles this automatically with underline + accessible color

**Hierarchy-Level Rules:**

| Level | Required | Forbidden |
|-------|----------|-----------|
| 1 — Page Layout | `environment` + `atmosphere` | `entity`, `cognition`, `synapse` |
| 2 — Section | `environment` | `entity`, `cognition` |
| 3 — Component | `entity` | — |
| 4 — Leaf | `cognition` or `synapse` | `environment`, `atmosphere`, `entity` |

→ **Full specification**: `/docs/specifications/ontology-html-mapping.md`

## Import Rules

**DO import in:**
- ✅ Subdomain entry files (e.g., `assets/css/custom.scss`)
- ✅ Standalone files with `---` frontmatter

**DON'T import in:**
- ❌ `_sass/components/` partials (ontology already imported by `assets/css/style.scss`)
- ❌ `_sass/layouts/` partials (creates 22MB bloat)

→ **Import guide**: `.github/instructions/scss.instructions.md`

## Validation

```bash
# Quick validation
./.github/skills/scss-refactor-agent/scripts/validate-scss.sh file.scss

# Full testing
npm test
```

## Resources

**Complete Ontology System**:
- `/docs/specifications/ontology-html-mapping.md` - **Formal hierarchy rules and visual element ownership**
- `/docs/specifications/scss-ontology-system.md` - **All 89 variants, complete API**
- `_sass/ontology/INTEGRATION-GUIDE.md` - Integration guide
- `_sass/ontology/_sample.scss` - Working examples

**Migration**:
- `_sass/ontology/refactor-agent.md` - Automated migration
- `.github/instructions/scss.instructions.md` - Core standards

**Related Skills**: responsive-design-agent, futuristic-effects-agent

---

**Version History**:
- **v2.1** (2026-02-10): High-density refactor - 212→149 lines, enhanced spec references
- **v2.0**: Initial SCSS refactoring system
