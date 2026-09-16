# CLAUDE.md Block Definitions

CLAUDE.md를 구성하는 모든 블록의 정의, 필수 여부, 작성 가이드.

## Table of Contents

1. [Header Block](#1-header-block)
2. [Tech Stack Block](#2-tech-stack-block)
3. [Terminology Block](#3-terminology-block)
4. [Supabase Block](#4-supabase-block)
5. [Auth & User State Block](#5-auth--user-state-block)
6. [3-Layer Architecture Block](#6-3-layer-architecture-block)
7. [SSOT & Type System Block](#7-ssot--type-system-block)
8. [Routing Convention Block](#8-routing-convention-block)
9. [Database Tables Block](#9-database-tables-block)
10. [Constants Strategy Block](#10-constants-strategy-block)
11. [Revalidation Strategy Block](#11-revalidation-strategy-block)
12. [API Integration Block](#12-api-integration-block)
13. [MCP & Migration Block](#13-mcp--migration-block)
14. [Spec Files Block](#14-spec-files-block)
15. [Next.js Convention Block](#15-nextjs-convention-block)
16. [NOT TO DOs Block](#16-not-to-dos-block)
17. [Reference Docs Block](#17-reference-docs-block)
18. [Project Structure Block](#18-project-structure-block)

---

## Block Categories

| Category | Blocks | When Required |
|----------|--------|---------------|
| **Required** | Header, Tech Stack, NOT TO DOs | Always |
| **Supabase** | Supabase, Database Tables, MCP & Migration, SSOT | Supabase 사용 시 |
| **Next.js** | Next.js Convention, Routing Convention | Next.js 사용 시 |
| **Architecture** | 3-Layer, Auth, Revalidation | 팀/프로젝트 규칙 있을 때 |
| **Domain** | Terminology, Spec Files, Constants | 도메인 특수성 있을 때 |
| **Reference** | Reference Docs, Project Structure, API Integration | 상세 정보 있을 때 |

---

## 1. Header Block

**Required**: YES (always)

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# [Project Name]

[Framework] application for [purpose]. [1-2 sentence with key tech identifiers]
```

**Rules:**
- 프로젝트명은 코드/레포명이 아닌 사람이 읽을 수 있는 이름
- 기술 스택 핵심 키워드 포함 (Next.js, Supabase 등)
- 목적을 한 문장으로 명확히

---

## 2. Tech Stack Block

**Required**: YES (always)

```markdown
## Technical Stack & Conventions

**Framework**: Next.js 15 App Router + TypeScript strict mode + Supabase (PostgreSQL)
**UI**: shadcn/ui (new-york style) + Tailwind CSS v4
**State**: @tanstack/react-query (server) + Zustand (client)
**Forms**: react-hook-form + Zod schemas
**Package Manager**: pnpm

### Path Aliases
- `@/lib/services` - All Supabase database operations
- `@/lib/auth` - Authentication system
- `@/types/models.ts` - Centralized database types
- `@/types/enums.ts` - All database enums
```

**Rules:**
- 버전 명시 (특히 breaking change가 있는 프레임워크)
- Path Alias는 실제 import 경로와 일치해야 함
- "Claude가 이미 아는 라이브러리 설명"은 제외

---

## 3. Terminology Block

**Required**: 도메인 용어가 있을 때 (한글 프로젝트는 거의 필수)

```markdown
## Terminology Guide

| Code/DB | Korean | English | Description |
|---------|--------|---------|-------------|
| **center** | 가맹점 | Franchise Center | 개별 영어 학원 |
| **branch** | 지사 | Regional Branch | 지역 지사 |

**Key Points:**
- **Code/Database**: English terms (`center`, `branch`)
- **UI/Messages**: Korean terms (가맹점, 지사)
- **Never** use "센터" in UI - always "가맹점"
```

**Rules:**
- 코드/DB 용어 ↔ UI 용어 매핑 명시
- "절대 사용하지 말 것" 항목 강조
- 비즈니스 도메인의 계층 구조 표현

---

## 4. Supabase Block

**Required**: Supabase 사용 시

```markdown
## Supabase Environment Configuration

### Database Schema CLI Tool

**ALWAYS use the CLI to query database schema instead of reading the entire `types/database.types.ts` file.**

```bash
npm run db:schema tables              # List all tables
npm run db:schema table students      # Show specific table schema
npm run db:schema enums               # List all enums
npm run db:schema enum user_role      # Show specific enum values
npm run db:schema search center       # Search for tables/enums
```

### Environment (Dev / Prod)

**Development:**
- Project ID: `xxxxx`
- Project Name: `project-dev`

**Production:**
- Project ID: `yyyyy`
- Project Name: `project-prod`

**Switching:**
- DEV: `supabase link --project-ref xxxxx`
- PROD: `supabase link --project-ref yyyyy`
```

**Rules:**
- `database.types.ts` 직접 읽기 금지 명시 (context 절약)
- CLI 스크립트 경로와 명령어 정확히 기재
- Dev/Prod project ref 반드시 포함
- Organization ID, Region 포함 (선택)

**CLI Setup (db-schema):**
- `db:schema` CLI가 없으면 bundled `scripts/db-schema.ts`를 프로젝트에 복사
- `package.json`에 `"db:schema": "tsx scripts/db-schema.ts"` 추가
- `tsx` dev dependency 필요 (`pnpm add -D tsx`)
- `DB_TYPES_PATH` 환경변수로 `database.types.ts` 경로 커스터마이징 가능
- 기본 경로: `types/database.types.ts`, 자동 대체 탐색: `src/types/`, `lib/`, `src/lib/`

---

## 5. Auth & User State Block

**Required**: 인증 시스템 있을 때

```markdown
## Authentication System

**NEVER** use direct `supabase.auth.getUser()`. Use [custom auth system].

### Quick Reference

```typescript
// Client-side (React)
import { useUserStore } from '@/stores/user-store'
const user = useUserStore((state) => state.user)

// API Routes / Server Actions
import { getServerAuth } from '@/lib/auth/server'
const auth = await getServerAuth()
```

**Core Files:** `/lib/auth/README.md`
```

**Rules:**
- "사용하지 말 것" 패턴 먼저 명시
- Client/Server 양쪽 패턴 모두 포함
- 권한 체크 유틸리티 포함 (PermissionGuard, RoleGuard 등)
- 핵심 파일 경로 명시

---

## 6. 3-Layer Architecture Block

**Required**: 레이어 분리 규칙 있을 때

```markdown
## Data Layer Architecture (MANDATORY)

```
Component Layer → Hook Layer → Service Layer
(UI only)         (TanStack Query)  (Supabase queries)
```

- **Service Layer** (`/lib/services/`): Supabase `createClient()` is ONLY allowed here
- **Hook Layer** (`/hooks/`): TanStack Query hooks. Import service functions only
- **Component Layer**: Import hooks only. No Supabase client. No inline useQuery

### Forbidden Patterns

```typescript
// FORBIDDEN - Direct Supabase in components
import { createClient } from '@/lib/supabase/client'
function MyComponent() { const supabase = createClient() }

// FORBIDDEN - Inline TanStack Query in components
function MyComponent() { const { data } = useQuery({ queryFn: async () => { ... } }) }

// FORBIDDEN - Supabase in hooks
export function useStudents() { return useQuery({ queryFn: async () => { const supabase = createClient() } }) }
```
```

**Rules:**
- ASCII 다이어그램으로 레이어 시각화
- 각 레이어의 파일 경로와 네이밍 컨벤션
- FORBIDDEN 패턴 반드시 포함 (Claude가 가장 많이 틀리는 부분)

---

## 7. SSOT & Type System Block

**Required**: 타입 시스템 규칙 있을 때

```markdown
## SSOT (Single Source of Truth)

### Type System

**NEVER** manually define database types. Always import:

```typescript
// CORRECT
import { User, Student } from '@/types/models'
import { UserRole } from '@/types/enums'

// WRONG
interface User { id: string; ... }
type UserRole = 'admin' | 'user'
```

**Type Sources:**
- `/types/database.types.ts` - Auto-generated (source of truth)
- `/types/models.ts` - Row, Insert, Update types
- `/types/enums.ts` - All enums with labels & styles

### Enum Management

- SSOT: `database.types.ts` (auto-generated)
- Central file: `enums.ts` — all DB enum types, Korean labels, style mappings
- Never hardcode enum values in components
- After DB schema change: `pnpm run update-type` → update `enums.ts`

### Database Field Verification

**ALWAYS check schema before writing queries. Never assume field names.**

| Common Mistake | Correct Field |
|---|---|
| `users.center_id` | Use `center_users` junction table |
| `students.name` | `students.full_name` |
```

**Rules:**
- import 경로 정확히 명시
- enum 관리 워크플로우 (DB 변경 → 타입 재생성 → enums.ts 업데이트)
- Common Mistakes 테이블 포함

---

## 8. Routing Convention Block

**Required**: 라우팅 패턴이 있을 때

```markdown
## Routing Convention

### Route Structure
```
/[role]/[feature]           # Role-based routing
/center/dashboard           # Center dashboard
/branch/settings            # Branch settings
/headquarter/users          # HQ user management
```

### Dynamic Routes
- `[id]` — numeric ID
- `[slug]` — string slug
- `(group)` — route group (layout sharing)
```

**Rules:**
- 실제 프로젝트 라우팅 패턴과 일치
- 역할(role) 기반 라우팅이면 역할별 경로 예시
- Layout 그룹 사용 시 명시

---

## 9. Database Tables Block

**Required**: Supabase 사용 시

```markdown
## Database Tables Overview

### Core Tables (N tables)

**User & Organization**
- **users**: User accounts with role-based permissions
- **center_users**: Center staff membership (junction table)

**Academic Operations**
- **classes**: Class templates with schedule info
- **class_sessions**: Individual class instances

**Financial**
- **tuition_bills**: Monthly billing records
```

**Rules:**
- 카테고리별로 그룹핑
- 각 테이블 한 줄 설명
- Junction table은 관계 설명
- Removed/Deprecated 테이블 경고

---

## 10. Constants Strategy Block

**Required**: 상수 관리 전략 있을 때

```markdown
## Constants Strategy

All shared constants in `/lib/constants/` or `/constants/`:

```
/constants
├── routes.ts       # Route paths
├── query-keys.ts   # TanStack Query keys
├── config.ts       # App configuration
└── messages.ts     # UI messages (Korean)
```

**Rules:**
- Magic numbers/strings 금지
- Query keys 중앙 관리
- 환경변수는 `.env` → `config.ts`로 타입 안전하게 접근
```

---

## 11. Revalidation Strategy Block

**Required**: 데이터 갱신 패턴 있을 때

```markdown
## Data Revalidation Strategy

### Core Principle
**All UI updates MUST be immediate (optimistic).**

### Patterns

**Modal submit → Immediate update:**
```typescript
const mutation = useMutation({
  mutationFn: updateStudent,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['students'] })
    toast.success('저장되었습니다')
    onClose()  // close modal immediately
  }
})
```

**List page → Auto refetch:**
- `invalidateQueries` after mutation
- `refetchOnWindowFocus: true` for stale data

**Server Actions:**
- `revalidatePath()` / `revalidateTag()` after mutation
```

**Rules:**
- Optimistic update 기본 원칙
- Modal 닫기 타이밍
- invalidateQueries vs refetch 선택 기준
- Server Action 사용 시 revalidation 방법

---

## 12. API Integration Block

**Required**: 외부 API 연동 시

```markdown
## API Integration Rules

### Research First
**ALWAYS research the API before writing integration code.**
- Search web for latest documentation
- Check for breaking changes in recent versions
- Verify endpoint URLs and auth methods

### Integration Pattern
```typescript
// /lib/api/[service-name].ts
export async function callExternalApi(params: Params): Promise<Response> {
  // API call logic
}
```

### [Specific API] Integration
**Path**: `/lib/[api]` | **Docs**: `/lib/[api]/README.md`
[Quick start with code examples]
```

---

## 13. MCP & Migration Block

**Required**: Supabase 사용 시

```markdown
## Database Migration Policy

**ALL schema changes MUST use Supabase CLI migrations.**

**NEVER:**
- Use Supabase MCP for schema changes
- Make manual changes in Dashboard
- Use SQL Editor for DDL operations

**ALWAYS:**
- `supabase migration new <description>` to create
- Write SQL in `supabase/migrations/`
- `supabase db push` to apply
- Commit migration files to Git

### Migration Workflow
```bash
supabase migration new add_example_table
# Edit generated SQL file
supabase db push
pnpm run update-type   # Regenerate types
git add supabase/migrations/
git commit
```
```

---

## 14. Spec Files Block

**Required**: 기획 문서가 있을 때

```markdown
## Specification Documents

**Read spec files BEFORE implementing features.**

- `spec/01-prd.md` - Product requirements
- `spec/02-tech-stack.md` - Technology decisions
- `spec/03-design-system.md` - UI/UX guidelines
- `spec/04-mvp-roadmap.md` - Development milestones
- `spec/database-schema.md` - CRITICAL: Full database schema
- `spec/detailed-features/` - Feature specifications
```

---

## 15. Next.js Convention Block

**Required**: Next.js 사용 시

```markdown
## Next.js Conventions

### Server Actions over API Routes
**Prefer Server Actions** for data mutations:

```typescript
// CORRECT - Server Action
'use server'
export async function createStudent(data: FormData) { ... }

// AVOID - API Route (use only for webhooks/external calls)
// app/api/students/route.ts
```

### When to use API Routes
- Webhook endpoints
- External service callbacks
- Public API endpoints
```

**Rules:**
- Server Action 우선 사용 원칙
- API Route 사용 허용 케이스 명시
- `'use server'` 디렉티브 예시

---

## 16. NOT TO DOs Block

**Required**: YES (always)

```markdown
## NOT TO DOs

- Don't run `npm run dev` (user will execute)
- Don't run `npm run build` unless instructed
- Never manually define database types - always import
- Never use direct Supabase auth calls - use JWT cookie system
- Never assume field names - always check schema
- Never import Supabase client in components - use hooks
- Never use Supabase MCP for schema changes - CLI only
```

**Rules:**
- prefix로 구분하기 쉽게
- 각 항목에 올바른 대안 포함
- 가장 빈번한 위반부터 나열

---

## 17. Reference Docs Block

**Required**: 상세 문서가 있을 때

```markdown
## Reference Documentation

- `/lib/auth/README.md` - Complete authentication guide
- `/spec/database-schema.md` - Full database schema
- `/spec/detailed-features/` - Feature specifications (Korean)
```

---

## 18. Project Structure Block

**Required**: 프로젝트 규모가 클 때

```markdown
## Project Structure

```
/app                    - Next.js App Router pages
/components             - Reusable UI components
/lib                    - Utility functions
  /auth                 - Authentication system
  /services             - All Supabase functions
/hooks                  - Custom React hooks
/stores                 - Zustand state stores
/types                  - TypeScript type definitions
/spec                   - Specifications
```
```
