# Block Templates

각 블록의 복사 가능한 템플릿. 유저에게 제시할 때 placeholder를 `[...]`로 표시.

---

## Header Block

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# [Project Name]

[Framework + version] application for [purpose/domain]. [Key tech stack summary in one sentence].
```

---

## Tech Stack Block

```markdown
## Technical Stack & Conventions

**Framework**: [e.g., Next.js 15 App Router + TypeScript strict mode]
**Database**: [e.g., Supabase (PostgreSQL)]
**UI**: [e.g., shadcn/ui + Tailwind CSS v4]
**State**: [e.g., @tanstack/react-query (server) + Zustand (client)]
**Forms**: [e.g., react-hook-form + Zod schemas]
**Package Manager**: [e.g., pnpm]

### Path Aliases
- `@/lib/services` - [Description]
- `@/lib/auth` - [Description]
- `@/types/models.ts` - [Description]
- `@/types/enums.ts` - [Description]
```

---

## Terminology Block

```markdown
## Terminology Guide

| Code/DB | Korean | English | Description |
|---------|--------|---------|-------------|
| **[code_term]** | [한글] | [English] | [설명] |

**Key Points:**
- **Code/Database**: English terms
- **UI/Messages**: Korean terms
- **Never** use "[잘못된 용어]" in UI - always "[올바른 용어]"
```

---

## Supabase Block

```markdown
## Supabase Configuration

### Database Schema CLI Tool

**ALWAYS use the CLI to query database schema instead of reading `types/database.types.ts` directly.**

```bash
[package_manager] run db:schema tables              # List all tables
[package_manager] run db:schema table [table_name]   # Show specific table
[package_manager] run db:schema enums                # List all enums
[package_manager] run db:schema enum [enum_name]     # Show specific enum
[package_manager] run db:schema search [keyword]     # Search tables/enums
```

### Environment (Dev / Prod)

**Development:**
- Project ID: `[dev_project_id]`
- Project Name: `[dev_project_name]`
- Region: `[region]`

**Production:**
- Project ID: `[prod_project_id]`
- Project Name: `[prod_project_name]`
- Region: `[region]`

**Switching:**
- DEV: `supabase link --project-ref [dev_project_id]`
- PROD: `supabase link --project-ref [prod_project_id]`
```

---

## Auth & User State Block

```markdown
## Authentication System

**NEVER** use direct `supabase.auth.getUser()` or `supabase.auth.getSession()`.

### Quick Reference

```typescript
// Client-side (React)
import { useUserStore } from '@/stores/user-store'
const user = useUserStore((state) => state.user)

// Server Actions / API Routes
import { [serverAuthFunction] } from '@/lib/auth/server'
const auth = await [serverAuthFunction]()
```

### Permission Utilities

[PermissionGuard / RoleGuard / checkPermission usage examples]

**Core Files:** `[/lib/auth/README.md]`
```

---

## 3-Layer Architecture Block

```markdown
## Data Layer Architecture (MANDATORY)

```
Component Layer → Hook Layer → Service Layer
(UI only)         (TanStack Query)  (Supabase queries)
```

### Layer Rules

| Layer | Path | Allowed | Forbidden |
|-------|------|---------|-----------|
| **Service** | `/lib/services/` | `createClient()`, Supabase queries | - |
| **Hook** | `/hooks/` | Import service functions, TanStack Query | Supabase client |
| **Component** | `/app/`, `/components/` | Import hooks | Supabase client, inline useQuery |

### Forbidden Patterns

```typescript
// FORBIDDEN - Direct Supabase in components
import { createClient } from '@/lib/supabase/client'

// FORBIDDEN - Inline query in components
const { data } = useQuery({ queryFn: async () => { ... } })

// FORBIDDEN - Supabase in hooks
export function useData() { return useQuery({ queryFn: async () => { createClient() } }) }
```
```

---

## SSOT & Type System Block

```markdown
## SSOT (Single Source of Truth)

### Type System

**NEVER** manually define database types.

```typescript
// CORRECT
import { [ModelType] } from '@/types/models'
import { [EnumType] } from '@/types/enums'

// WRONG
interface [ModelType] { id: string; ... }
```

**Type Sources:**
- `/types/database.types.ts` - Auto-generated (DO NOT read directly — use CLI)
- `/types/models.ts` - Row, Insert, Update types
- `/types/enums.ts` - All enums with labels & styles

### Enum Management
- After DB change: `[package_manager] run update-type` → update `enums.ts`
- Import labels: `import { [ENUM]_LABELS } from '@/types/enums'`
- Import styles: `import { [ENUM]_STYLE } from '@/types/enums'`

### Common Field Mistakes

| Mistake | Correct |
|---------|---------|
| `[wrong_field]` | `[correct_field]` |
```

---

## Routing Convention Block

```markdown
## Routing Convention

```
/[pattern]                  # [Description]
/[role]/[feature]           # [Description]
```

### Key Routes
- `/[route]` - [Purpose]
```

---

## Database Tables Block

```markdown
## Database Tables Overview

### Core Tables ([N] tables)

**[Category 1]**
- **[table]**: [Description]
- **[junction_table]**: [Relationship description]

**[Category 2]**
- **[table]**: [Description]
```

---

## Constants Strategy Block

```markdown
## Constants Strategy

All shared constants in `[/path/to/constants/]`:

| File | Purpose |
|------|---------|
| `routes.ts` | Route path constants |
| `query-keys.ts` | TanStack Query keys |
| `config.ts` | App configuration |
| `messages.ts` | UI messages |

**Rules:**
- No magic numbers/strings in components
- Query keys centrally managed
- Config values type-safe via `config.ts`
```

---

## Revalidation Strategy Block

```markdown
## Data Revalidation Strategy

**All UI updates MUST be immediate (optimistic).**

### After Mutation
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['[resource]'] })
  toast.success('[message]')
  onClose()  // close modal immediately
}
```

### Server Action Revalidation
```typescript
'use server'
revalidatePath('/[path]')
revalidateTag('[tag]')
```
```

---

## API Integration Block

```markdown
## API Integration Rules

**ALWAYS research API docs before writing integration code.**
- Search web for latest documentation
- Check for breaking changes
- Verify endpoints and auth methods

### [API Name] Integration
**Path**: `/lib/[api]` | **Docs**: `/lib/[api]/README.md`

[Quick start code examples]
```

---

## MCP & Migration Block

```markdown
## Database Migration Policy

**ALL schema changes MUST use Supabase CLI migrations.**

**NEVER:**
- Use Supabase MCP for schema changes
- Make manual changes in Dashboard SQL Editor

**ALWAYS:**
```bash
supabase migration new [description]
# Edit SQL file in supabase/migrations/
supabase db push
[package_manager] run update-type
git add supabase/migrations/
git commit
```
```

---

## Next.js Convention Block

```markdown
## Next.js Conventions

### Server Actions over API Routes
```typescript
// PREFERRED - Server Action
'use server'
export async function [actionName](data: FormData) { ... }

// ONLY for webhooks/external callbacks
// app/api/[route]/route.ts
```
```

---

## NOT TO DOs Block

```markdown
## NOT TO DOs

- Don't run `[dev_command]` on your own (user will execute)
- Don't run `[build_command]` unless instructed
- Never manually define database types - always import from `/types/`
- Never use direct Supabase auth calls - use [auth system]
- Never assume field names - check with CLI or schema doc
- Never import Supabase client in components - use hooks from `/hooks/`
- Never use Supabase MCP for schema changes - CLI migrations only
```

---

## Spec Files Block

```markdown
## Specification Documents

**Read spec files BEFORE implementing features.**

- `spec/[filename].md` - [Description]
- `spec/[dir]/` - [Description]
```

---

## Reference Docs Block

```markdown
## Reference Documentation

- `/[path]` - [Description]
- `/[path]` - [Description]
```

---

## Project Structure Block

```markdown
## Project Structure

```
/app                    - [Description]
/components             - [Description]
/lib                    - [Description]
  /services             - [Description]
  /auth                 - [Description]
/hooks                  - [Description]
/stores                 - [Description]
/types                  - [Description]
/spec                   - [Description]
```
```
