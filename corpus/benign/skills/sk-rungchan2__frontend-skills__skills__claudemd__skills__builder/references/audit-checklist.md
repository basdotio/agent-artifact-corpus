# CLAUDE.md Audit Checklist

기존 CLAUDE.md를 블록 단위로 검사하여 누락/개선 사항을 리포트.

---

## Audit Process

### Step 1: Detect Tech Stack

프로젝트의 `package.json`, `tsconfig.json`, 디렉토리 구조를 확인하여 사용 중인 기술 스택 감지:

| Detect | How | Required Blocks |
|--------|-----|-----------------|
| Supabase | `@supabase/supabase-js` in deps | Supabase, MCP & Migration, Database Tables, SSOT |
| Next.js | `next` in deps | Next.js Convention, Routing Convention |
| TanStack Query | `@tanstack/react-query` in deps | 3-Layer Architecture, Revalidation Strategy |
| Zustand | `zustand` in deps | Auth & User State (user store) |
| shadcn/ui | `components/ui/` dir exists | - |

### Step 2: Check Required Blocks

**Always Required:**

```
[ ] Header Block
    - Project name present?
    - Tech stack summary present?
    - Purpose description present?

[ ] Tech Stack Block
    - Framework with version?
    - UI library?
    - State management?
    - Path aliases?

[ ] NOT TO DOs Block
    - At least 5 items?
    - "Don't run dev/build" included?
    - Key anti-patterns listed?
```

### Step 3: Check Conditional Blocks

**If Supabase detected:**

```
[ ] Supabase Block
    - CLI script commands documented?
    - "Don't read database.types.ts directly" rule?
    - Dev project ref?
    - Prod project ref?

[ ] MCP & Migration Block
    - "NEVER use MCP for schema changes" rule?
    - Migration workflow (new → push → update-type → commit)?

[ ] Database Tables Block
    - Table count stated?
    - Tables grouped by category?
    - Each table has one-line description?
    - Junction tables explained?

[ ] SSOT & Type System Block
    - Type import sources listed?
    - "NEVER manually define types" rule?
    - Enum management workflow?
    - Common field mistakes table?
```

**If Next.js detected:**

```
[ ] Next.js Convention Block
    - Server Action preference stated?
    - API Route exception cases listed?

[ ] Routing Convention Block
    - Route patterns documented?
    - Dynamic route conventions?
```

**If TanStack Query detected:**

```
[ ] 3-Layer Architecture Block
    - Layer diagram present?
    - Each layer's path and rules?
    - Forbidden patterns with code examples?

[ ] Revalidation Strategy Block
    - Optimistic update principle?
    - invalidateQueries pattern?
    - Modal close timing?
```

### Step 4: Check Quality Metrics

**For each existing block:**

```
[ ] Context Efficiency
    - Code examples preferred over prose?
    - Tables used for comparison data?
    - No redundant information?

[ ] Error Prevention
    - CORRECT/WRONG examples present?
    - Common mistakes documented?
    - Specific file paths (not vague references)?

[ ] Actionability
    - Commands are copy-pasteable?
    - Import paths are exact?
    - Rules are unambiguous?
```

---

## Audit Report Format

```markdown
# CLAUDE.md Audit Report

**Project**: [name]
**Date**: [date]
**Tech Stack Detected**: [list]

## Block Status

| Block | Status | Notes |
|-------|--------|-------|
| Header | OK / MISSING / NEEDS_IMPROVEMENT | [detail] |
| Tech Stack | OK / MISSING / NEEDS_IMPROVEMENT | [detail] |
| ... | ... | ... |

## Missing Blocks (Required)

1. **[Block Name]** - [Why it's needed based on tech stack]

## Improvement Suggestions

1. **[Block Name]** - [What to improve]
   - Current: [what it says now]
   - Suggested: [what it should say]

## Redundancies Found

1. [Description of duplicate/redundant content]
```

---

## Common Issues by Block

### Header
- Missing tech stack keywords → Claude can't contextualize project
- Too verbose → wastes tokens on obvious info

### Supabase
- Missing CLI commands → Claude reads full database.types.ts (token waste)
- Missing project refs → Claude can't help with env switching
- Duplicate environment sections (common copy-paste error)

### 3-Layer Architecture
- Missing FORBIDDEN patterns → Claude puts Supabase in components
- Vague layer descriptions → Claude unsure where to put code

### SSOT
- Missing field mistake table → Claude uses wrong field names repeatedly
- Missing enum workflow → types get out of sync

### NOT TO DOs
- Too few items → important anti-patterns not covered
- Missing alternatives → Claude doesn't know what to do instead

### Terminology
- Missing Korean↔English mapping → Claude uses wrong terms in UI
- Missing "never use" terms → Claude uses forbidden terminology
